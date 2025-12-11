import logging
import uvicorn
import os
import secrets
import httpx
import asyncio
import json
from contextlib import asynccontextmanager
from typing import List 
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

# --- 1. Импорты проекта ---
import provision  # Логика развертывания (docker run)
import auth       # Логика паролей и JWT-токенов
import templates  # <-- ИМПОРТИРУЕМ НАШИ ШАБЛОНЫ
from models import (
    Base, engine, async_session_maker, User, Instance, 
    create_db_tables, get_db
)

# --- 2. Загрузка конфигурации из переменных окружения ---
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "supersecret")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", "restify.site")

# --- 3. Инициализация FastAPI ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    При старте приложения:
    1. Подключаемся к БД.
    2. Создаем таблицы User и Instance (если их нет) в 'main_saas_db'.
    3. Убеждаемся, что config.json существует.
    """
    logging.info("Запуск... Подключение к БД и создание таблиц...")
    await create_db_tables()
    load_config() 
    logging.info("Приложение запущено.")
    yield
    logging.info("Завершение работы.")

app = FastAPI(
    title="Restify SaaS Control Plane",
    description="Управляет витриной, клиентами, подписками и развертыванием.",
    lifespan=lifespan
)
security = HTTPBasic()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- 4. Логика витрины (config.json) ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "admin_id": "", "bot_token": "", "price_light": "300",
    "price_full": "600", "currency": "$",
    "custom_btn_text": "", "custom_btn_content": "" # Добавляем значения по умолчанию
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    
    # Гарантируем, что новые ключи существуют
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    updated = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            updated = True
            
    if updated:
        save_config(config)
        
    return config

def save_config(new_config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f, indent=4) # Добавил indent для читаемости

# --- 5. Авторизация для /admin и /settings ---
def check_admin_auth(credentials: HTTPBasicCredentials = Depends(security)):
    is_user_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
    is_pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- 6. HTML ШАБЛОНЫ УДАЛЕНЫ ---
# (Весь HTML-код (1000+ строк) перенесен в templates.py)
# ---


# --- 7. Эндпоинты (Роутинг) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Отдает главную страницу (витрину).
    """
    token = request.cookies.get("access_token")
    if token:
        user = await auth.get_current_user_from_token(token, async_session_maker)
        if user:
            pass
            
    # Показываем витрину
    config = load_config()
    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return HTMLResponse(content=templates.get_landing_page_html(config))

@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request, message: str = None, type: str = "error"):
    """Показывает страницу входа."""
    token = request.cookies.get("access_token")
    if token:
        user = await auth.get_current_user_from_token(token, async_session_maker)
        if user:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_login_page(message, type)

@app.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    """Показывает страницу регистрации."""
    token = request.cookies.get("access_token")
    if token:
        user = await auth.get_current_user_from_token(token, async_session_maker)
        if user:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
            
    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_register_page()

@app.get("/logout")
async def logout():
    """Выход из системы (удаляет cookie)."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает email (в поле username) и password из формы,
    проверяет их и возвращает JWT токен в cookie.
    """
    user = await auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Если неверный пароль, возвращаем на /login с ошибкой
        return RedirectResponse(
            url="/login?message=Неверный email или пароль", 
            status_code=status.HTTP_302_FOUND
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    
    # Устанавливаем токен в httpOnly cookie и перенаправляем в кабинет
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="strict")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    current_user: User = Depends(auth.get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """Личный кабинет клиента. Доступен только по токену."""
    
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(
            joinedload(User.instances)
        )
    )
    
    user_with_instances = result.unique().scalar_one_or_none()
    
    if not user_with_instances:
        return RedirectResponse(url="/logout")

    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_dashboard_html(user_with_instances, user_with_instances.instances)

# --- 8. ЭНДПОИНТ СОЗДАНИЯ ---

@app.post("/api/create-instance", response_class=JSONResponse)
async def handle_instance_creation(
    name: str = Form(...),
    phone: str = Form(...),
    client_bot_token: str = Form(...),
    admin_bot_token: str = Form(...),
    admin_chat_id: str = Form(...),
    plan: str = Form("pro"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Создает экземпляр (сайт) для уже залогиненного пользователя.
    Вызывается из /dashboard.
    """
    
    try:
        client_name_base = "".join(filter(lambda c: c.isalnum() or c == '-', name.lower()))[:20]
        if not client_name_base:
            client_name_base = "client"
    except Exception:
        client_name_base = "client"

    target_subdomain = f"{client_name_base}.{ROOT_DOMAIN}"
    existing_instance_res = await db.execute(
        select(Instance).where(Instance.subdomain == target_subdomain)
    )
    if existing_instance_res.scalar_one_or_none():
        return JSONResponse(
            status_code=400, 
            content={"detail": f"Этот домен '{client_name_base}' уже занят. Попробуйте другое название."}
        )

    try:
        # 2. Запускаем полный цикл развертывания
        result_data = provision.create_new_client_instance(
            client_name_base=client_name_base, 
            root_domain=ROOT_DOMAIN,
            client_bot_token=client_bot_token,
            admin_bot_token=admin_bot_token,
            admin_chat_id=admin_chat_id
        )
        
        # 3. Сохраняем данные о созданном экземпляре в нашу БД
        new_instance = Instance(
            user_id=current_user.id,
            subdomain=result_data["subdomain"],
            url=result_data["url"],
            container_name=result_data["container_name"],
            admin_pass=result_data["password"],
            status="active",
            next_payment_due=datetime.utcnow() + timedelta(days=30) 
        )
        db.add(new_instance)
        await db.commit()

        # 4. Отправляем уведомление в Telegram (в фоновом режиме)
        asyncio.create_task(send_tg_notification(name, phone, plan, result_data))
        
        # 5. Возвращаем клиенту его данные
        return JSONResponse(result_data)

    except Exception as e:
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА РАЗВЕРТЫВАНИЯ: {e}")
        await db.rollback()
        return JSONResponse(
            status_code=500, 
            content={"detail": f"Ошибка развертывания: {e}. Проверьте лог."}
        )

# --- 9. ЭНДПОИНТ: Управление проектом (Stop/Start) ---

@app.post("/api/instance/control", response_class=JSONResponse)
async def handle_instance_control(
    instance_id: int = Form(...),
    action: str = Form(...), # "stop" or "start"
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Позволяет залогиненному пользователю управлять СВОИМИ проектами.
    """
    instance = await db.get(Instance, instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    
    if instance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на управление этим проектом.")

    msg = ""
    try:
        if action == "stop":
            if instance.status == "suspended":
                raise HTTPException(status_code=400, detail="Проект уже остановлен.")
                
            if not provision.stop_instance(instance.container_name):
                raise HTTPException(status_code=500, detail="Ошибка при остановке контейнера.")
            instance.status = "suspended"
            msg = "Проект успешно остановлен."
        
        elif action == "start":
            if instance.status == "active":
                raise HTTPException(status_code=400, detail="Проект уже запущен.")

            if not provision.start_instance(instance.container_name):
                raise HTTPException(status_code=500, detail="Ошибка при запуске контейнера.")
            instance.status = "active"
            msg = "Проект успешно запущен."
        
        else:
            raise HTTPException(status_code=400, detail="Недопустимое действие.")

        await db.commit()
    except Exception as e:
        await db.rollback()
        logging.error(f"Ошибка управления инстансом {instance_id} пользователем {current_user.id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")

    return JSONResponse(content={"message": msg, "new_status": instance.status})


# --- 10. ЭНДПОИНТ: Удаление проекта ---

@app.post("/api/instance/delete", response_class=JSONResponse)
async def handle_instance_delete(
    instance_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """
    Позволяет залогиненному пользователю ПОЛНОСТЬЮ удалить свой проект.
    """
    instance = await db.get(Instance, instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    
    if instance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на удаление этого проекта.")

    try:
        container_name = instance.container_name
        
        logging.warning(f"Пользователь {current_user.email} инициировал удаление {container_name}")
        
        if not provision.delete_client_instance(container_name):
            raise HTTPException(status_code=500, detail="Ошибка при удалении ресурсов проекта (контейнера или БД).")
        
        await db.delete(instance)
        await db.commit()
        
        logging.info(f"Запись о {container_name} успешно удалена из main_saas_db.")

    except Exception as e:
        await db.rollback()
        logging.error(f"Ошибка ПОЛНОГО удаления инстанса {instance_id} пользователем {current_user.id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")

    return JSONResponse(content={"message": "Проект успешно удален."})


# --- 11. Админка SaaS (управление клиентами) ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    _ = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db),
    message: str = None,
    type: str = "success"
):
    """
    Главная админ-панель. Показывает список всех пользователей и их экземпляры.
    """
    result = await db.execute(
        select(User, Instance)
        .outerjoin(Instance, User.id == Instance.user_id)
        .order_by(User.id)
    )
    clients = result.all()
    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_admin_dashboard_html(clients, message, type)

@app.post("/admin/control")
async def admin_control_instance(
    instance_id: int = Form(...),
    action: str = Form(...),
    _ = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Обрабатывает действия "Отключить" / "Включить" из админки.
    """
    instance = await db.get(Instance, instance_id)
    if not instance:
        return RedirectResponse(url="/admin?message=Экземпляр не найден&type=error", status_code=302)

    if action == "stop":
        if not provision.stop_instance(instance.container_name):
            return RedirectResponse(url="/admin?message=Ошибка при остановке контейнера&type=error", status_code=302)
        instance.status = "suspended"
        msg = f"Клиент {instance.subdomain} отключен."
        
    elif action == "start":
        if not provision.start_instance(instance.container_name):
            return RedirectResponse(url="/admin?message=Ошибка при запуске контейнера&type=error", status_code=302)
        instance.status = "active"
        instance.next_payment_due = datetime.utcnow() + timedelta(days=30)
        msg = f"Клиент {instance.subdomain} включен и продлен."

    await db.commit()
    return RedirectResponse(url=f"/admin?message={msg}", status_code=302)


# --- 12. Настройки Витрины ---

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(username: str = Depends(check_admin_auth)):
    config = load_config()
    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_settings_page_html(config)

@app.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    admin_id: str = Form(""), bot_token: str = Form(""),
    currency: str = Form("$"), price_light: str = Form("300"), price_full: str = Form("600"),
    # === ИЗМЕНЕНИЕ: Добавляем новые поля из формы ===
    custom_btn_text: str = Form(""),
    custom_btn_content: str = Form(""),
    # ============================================
    username: str = Depends(check_admin_auth)
):
    # Загружаем старый конфиг, чтобы не потерять другие ключи
    current_config = load_config()
    
    # Обновляем ключи
    current_config.update({
        "admin_id": admin_id.strip(), "bot_token": bot_token.strip(),
        "currency": currency.strip(), "price_light": price_light.strip(), "price_full": price_full.strip(),
        # === ИЗМЕНЕНИЕ: Сохраняем новые значения ===
        "custom_btn_text": custom_btn_text.strip(),
        "custom_btn_content": custom_btn_content.strip() # .strip() уберет лишние пробелы по краям
        # ==========================================
    })

    save_config(current_config)
    # ВЫЗЫВАЕМ ШАБЛОН ИЗ templates.py
    return templates.get_settings_page_html(current_config, "Сохранено успешно!")

# --- 13. API Эндпоинты (Заявки и Регистрация) ---

@app.post("/api/lead")
async def handle_lead(name: str = Form(...), phone: str = Form(...), interest: str = Form(...)):
    """Принимает заявку с витрины и шлет в TG"""
    config = load_config()
    if config.get('bot_token') and config.get('admin_id'):
        text = f"🚀 <b>Заявка с Витрины (Restify)!</b>\n\n👤 {name}\n📱 {phone}\n💎 {interest}"
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"https://api.telegram.org/bot{config['bot_token']}/sendMessage", json={"chat_id": config['admin_id'], "text": text, "parse_mode": "HTML"})
            except Exception as e: 
                logging.error(f"TG Lead Error: {e}")
                return JSONResponse({"status": "error"}, status_code=500)
    return JSONResponse({"status": "ok"})


async def send_tg_notification(name, phone, plan, result_data):
    """Отправляет уведомление о НОВОМ КЛИЕНТЕ в ваш Telegram (из env)."""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logging.warning("TG_BOT_TOKEN или TG_CHAT_ID не установлены. Уведомление о регистрации не отправлено.")
        return

    text = f"""
🚀 <b>НОВЫЙ КЛИЕНТ (SaaS)!</b>

👤 {name}
📱 {phone}
💎 {plan}

✅ <b>САЙТ УСПЕШНО РАЗВЕРНУТ:</b>
Сайт: {result_data['url']}
Админка: {result_data['url']}/admin
Логин: {result_data['login']}
Пароль: {result_data['password']}
    """
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
            )
        except Exception as e: 
            logging.error(f"TG Notification Error: {e}")

@app.post("/api/register")
async def handle_registration(
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает данные из формы, регистрирует ТОЛЬКО пользователя.
    """
    existing_user = await auth.get_user_by_email(db, email)
    if existing_user:
        return JSONResponse(status_code=400, content={"detail": "Этот email уже зарегистрирован."})

    hashed_password = auth.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return JSONResponse(content={"detail": "User created successfully."})


# --- 14. Запуск Сервера ---
if __name__ == "__main__":
    if not provision.SAAS_ADMIN_PASSWORD:
        logging.critical("="*50)
        logging.critical("КРИТИЧЕСКАЯ ОШИБКА: SAAS_ADMIN_PASSWORD не установлен!")
        logging.critical("Сервер не сможет создавать базы данных для клиентов.")
        logging.critical("="*50)
    
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)