import logging
import uvicorn
import os
import secrets
import httpx
import asyncio
import json
import uuid
import pytz
from math import radians, cos, sin, asin, sqrt
from contextlib import asynccontextmanager
from typing import List, Dict 
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Header, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

# --- 1. Импорты модулей проекта ---
import provision
import auth 
import templates_saas
import templates_partner
import templates_courier
import admin_delivery
import bot_service
import order_monitor

from models import (
    Base, engine, async_session_maker, User, Instance, Courier, 
    DeliveryPartner, DeliveryJob, PendingVerification, ChatMessage, 
    create_db_tables, get_db
)
from auth import check_admin_auth

# ИМПОРТ ФУНКЦИЙ ДЛЯ РАБОТЫ С НАСТРОЙКАМИ В БД
from crud_settings import get_setting, set_setting, get_all_settings

# --- FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials, messaging

# --- 2. Конфигурация ---
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", "restify.site")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Restify_Bot") 

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# Инициализация Firebase Admin SDK
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase_credentials.json"):
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
            logging.info("Firebase Admin initialized successfully.")
        else:
            logging.warning("firebase_credentials.json not found! Push notifications will not work.")
    except Exception as e:
        logging.warning(f"Firebase Init Error: {e}")

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_couriers: Dict[int, WebSocket] = {}
        self.active_partners: Dict[int, WebSocket] = {}

    # --- Методы для КУРЬЕРОВ ---
    async def connect_courier(self, websocket: WebSocket, courier_id: int):
        await websocket.accept()
        self.active_couriers[courier_id] = websocket
        logging.info(f"Courier {courier_id} connected to WS")

    def disconnect_courier(self, courier_id: int):
        if courier_id in self.active_couriers:
            del self.active_couriers[courier_id]
            logging.info(f"Courier {courier_id} disconnected from WS")

    async def notify_courier(self, courier_id: int, message: dict):
        if courier_id in self.active_couriers:
            try:
                await self.active_couriers[courier_id].send_json(message)
            except Exception as e:
                logging.error(f"WS Error (Courier {courier_id}): {e}")
                self.disconnect_courier(courier_id)

    # --- Методы для ПАРТНЕРОВ (Ресторанов) ---
    async def connect_partner(self, websocket: WebSocket, partner_id: int):
        await websocket.accept()
        self.active_partners[partner_id] = websocket
        logging.info(f"Partner {partner_id} connected to WS")

    def disconnect_partner(self, partner_id: int):
        if partner_id in self.active_partners:
            del self.active_partners[partner_id]

    async def notify_partner(self, partner_id: int, message: dict):
        if partner_id in self.active_partners:
            try:
                await self.active_partners[partner_id].send_json(message)
            except Exception as e:
                logging.error(f"WS Error (Partner {partner_id}): {e}")
                self.disconnect_partner(partner_id)

manager = ConnectionManager()

# --- Настройки по умолчанию для Базы Данных ---
DEFAULT_SETTINGS = {
    "admin_id": "", "bot_token": "", "price_light": "300", 
    "price_full": "600", "currency": "$", 
    "custom_btn_text": "", "custom_btn_content": "",
    "firebase_api_key": "", "firebase_project_id": "",
    "firebase_sender_id": "", "firebase_app_id": "",
    "timezone": "Europe/Kiev" # Добавлен часовой пояс по умолчанию
}

# --- LIFESPAN (Запуск/Остановка) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Startup: Connecting DB & Creating tables...")
    await create_db_tables()
    
    # Инициализация дефолтных настроек в Базе Данных, если их еще нет
    async with async_session_maker() as session:
        for key, default_value in DEFAULT_SETTINGS.items():
            existing = await get_setting(session, key)
            if existing is None:
                await set_setting(session, key, default_value)
                logging.info(f"Ініціалізовано налаштування: {key}")
    
    # Запуск Telegram бота
    if bot_service.bot:
        asyncio.create_task(bot_service.start_bot())
        logging.info("Telegram Bot Polling started.")
    else:
        logging.warning("TG_BOT_TOKEN not set, bot disabled.")
    
    # Запуск монитора заказов
    asyncio.create_task(order_monitor.monitor_stale_orders(manager))
    logging.info("Order Monitor started.")
    
    yield
    logging.info("Shutdown.")

app = FastAPI(title="Restify SaaS Control Plane", lifespan=lifespan)

# Подключение роутера админки доставки
app.include_router(admin_delivery.router)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==============================================================================
# UTILS & HELPERS
# ==============================================================================

def format_local_time(utc_dt, tz_string='Europe/Kiev', fmt='%H:%M'):
    """Конвертує UTC datetime у локальний час заданого часового поясу."""
    if not utc_dt:
        return "-"
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    try:
        local_tz = pytz.timezone(tz_string)
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime(fmt)
    except pytz.UnknownTimeZoneError:
        return utc_dt.strftime(fmt)

# --- Геокодинг ---
GEOCODE_CACHE = {}

async def geocode_address(address: str):
    """Geocoding via Nominatim (OSM) with caching."""
    if not address: return None, None
    if address in GEOCODE_CACHE: return GEOCODE_CACHE[address]

    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "RestifyDelivery/1.0 (admin@restify.site)"}
    params = {"q": address, "format": "json", "limit": 1}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=5.0)
            data = resp.json()
            if data and len(data) > 0:
                res = (float(data[0]["lat"]), float(data[0]["lon"]))
                GEOCODE_CACHE[address] = res 
                return res
        except Exception as e:
            logging.error(f"Geocoding Error: {e}")
            
    return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine formula for distance in km."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        return round(c * 6371, 2)
    except Exception:
        return None


# ==============================================================================
# 1. ОБЩИЕ РОУТЫ И SAAS (ВИТРИНА)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_all_settings(db)
    return HTMLResponse(content=templates_saas.get_landing_page_html(config))

@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request, message: str = None, type: str = "error"):
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates_saas.get_login_page(message, type)

@app.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    return templates_saas.get_register_page()

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    user = await auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        return RedirectResponse(
            url="/login?message=Неверный email или пароль", 
            status_code=status.HTTP_302_FOUND
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="strict", max_age=604800)
    return response

# --- DASHBOARD (Личный кабинет клиента) ---
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    current_user: User = Depends(auth.get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    # Загружаем пользователя вместе с его инстансами
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(joinedload(User.instances))
    )
    user_with_instances = result.unique().scalar_one_or_none()
    
    if not user_with_instances:
        return RedirectResponse(url="/logout")
        
    return templates_saas.get_dashboard_html(user_with_instances, user_with_instances.instances)

# --- VERIFICATION (TELEGRAM AUTH) ---

@app.post("/api/auth/init_verification")
async def init_verification(db: AsyncSession = Depends(get_db)):
    token = str(uuid.uuid4())
    db.add(PendingVerification(token=token, status="created"))
    await db.commit()
    return JSONResponse({"token": token, "link": f"https://t.me/{BOT_USERNAME}?start=reg_{token}"})

@app.get("/api/auth/check_verification/{token}")
async def check_verification(token: str, db: AsyncSession = Depends(get_db)):
    verif = await db.get(PendingVerification, token)
    if verif and verif.status == "verified":
        return JSONResponse({"status": "verified", "phone": verif.phone})
    return JSONResponse({"status": "waiting"})

@app.post("/api/register")
async def handle_registration(
    email: str = Form(...),
    password: str = Form(...),
    verification_token: str = Form(...), 
    db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return JSONResponse(status_code=400, content={"detail": "Номер телефона не подтвержден через Telegram."})

    if await auth.get_user_by_email(db, email):
        return JSONResponse(status_code=400, content={"detail": "Этот email уже зарегистрирован."})

    hashed_password = auth.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.delete(verif)
    
    await db.commit()
    await db.refresh(new_user)
    
    return JSONResponse(content={"detail": "User created successfully."})

# ==============================================================================
# 2. УПРАВЛЕНИЕ ИНСТАНСАМИ (SAAS LOGIC)
# ==============================================================================

@app.post("/api/create-instance")
async def handle_instance_creation(
    name: str = Form(...), phone: str = Form(...), client_bot_token: str = Form(...),
    admin_bot_token: str = Form(...), admin_chat_id: str = Form(...), plan: str = Form("pro"),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    try:
        # Валидация имени
        c_name = "".join(x for x in name.lower() if x.isalnum() or x=='-')[:20] or "client"
        sub = f"{c_name}.{ROOT_DOMAIN}"
        
        # Проверка уникальности
        if (await db.execute(select(Instance).where(Instance.subdomain == sub))).scalar():
            return JSONResponse(status_code=400, content={"detail": "Этот поддомен уже занят. Выберите другое имя."})
        
        # Вызов provision для создания контейнера и БД
        res = provision.create_new_client_instance(c_name, ROOT_DOMAIN, client_bot_token, admin_bot_token, admin_chat_id)
        
        # Сохранение в нашу БД
        db.add(Instance(
            user_id=current_user.id, subdomain=res["subdomain"], url=res["url"],
            container_name=res["container_name"], admin_pass=res["password"],
            next_payment_due=datetime.utcnow() + timedelta(days=30)
        ))
        await db.commit()
        
        # Уведомление администратору SaaS
        asyncio.create_task(send_tg_notification(name, phone, plan, res))
        
        return JSONResponse(res)
    except Exception as e:
        logging.error(f"Create Instance Error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/instance/control")
async def handle_instance_control(
    instance_id: int = Form(...), action: str = Form(...),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    instance = await db.get(Instance, instance_id)
    if not instance or instance.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    if action == "stop":
        provision.stop_instance(instance.container_name)
        instance.status = "suspended"
    elif action == "start":
        provision.start_instance(instance.container_name)
        instance.status = "active"
        
    await db.commit()
    return JSONResponse({"new_status": instance.status, "message": f"Проект {action}ed"})

@app.post("/api/instance/delete")
async def handle_instance_delete(
    instance_id: int = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    instance = await db.get(Instance, instance_id)
    if not instance or instance.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Полное удаление
    if provision.delete_client_instance(instance.container_name):
        await db.delete(instance)
        await db.commit()
        return JSONResponse({"message": "Проект успешно удален."})
    else:
        return JSONResponse(status_code=500, content={"detail": "Ошибка при удалении контейнера."})

# --- ADMIN API (SUPER ADMIN) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)
):
    # Получаем всех клиентов и их инстансы
    res = await db.execute(select(User, Instance).outerjoin(Instance, User.id == Instance.user_id))
    clients = res.all()
    return templates_saas.get_admin_dashboard_html(clients)

@app.post("/admin/control")
async def admin_control(
    instance_id: int = Form(...), action: str = Form(...), 
    db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)
):
    instance = await db.get(Instance, instance_id)
    if not instance:
        return RedirectResponse("/admin?message=Instance not found", status_code=302)

    if action == "stop":
        provision.stop_instance(instance.container_name)
        instance.status = "suspended"
    elif action == "start":
        provision.start_instance(instance.container_name)
        instance.status = "active"
    elif action == "update":
        provision.recreate_container_with_new_code(instance.container_name)
    elif action == "force_delete":
        provision.delete_client_instance(instance.container_name)
        await db.delete(instance)
    
    await db.commit()
    return RedirectResponse("/admin", status_code=302)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)):
    config = await get_all_settings(db)
    return templates_saas.get_settings_page_html(config)

@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)):
    form = await request.form()
    
    # Обрабатываем все поля из формы
    for k, v in form.items():
        if k == "firebase_credentials_json":
            if v.strip():
                try:
                    import json
                    parsed = json.loads(v)
                    # Firebase credentials всё ещё сохраняем в файл, так как SDK требует файл или словарь
                    with open("firebase_credentials.json", "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=4)
                    
                    # Пытаемся инициализировать на лету, если еще не было
                    if not firebase_admin._apps:
                        cred = credentials.Certificate("firebase_credentials.json")
                        firebase_admin.initialize_app(cred)
                except Exception as e:
                    logging.error(f"Ошибка сохранения Firebase JSON: {e}")
        else:
            # Все остальные настройки (цены, токены и т.д.) пишем в БД
            await set_setting(db, k, v)
            
    config = await get_all_settings(db)
    return templates_saas.get_settings_page_html(config, "Налаштування збережено. Щоб ключі Firebase запрацювали на бекенді, виконайте 'docker restart saas_lander_app'.")

# ==============================================================================
# 3. DELIVERY LOGIC (COURIER & PARTNER)
# ==============================================================================

# --- COURIER AUTH ---
@app.get("/courier/login", response_class=HTMLResponse)
async def courier_login_page(request: Request, message: str = None, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("courier_token")
    if token:
        try:
            courier = await auth.get_current_courier(token, db)
            if courier:
                return RedirectResponse(url="/courier/app", status_code=302)
        except Exception:
            pass 
    return templates_courier.get_courier_login_page(message)

@app.get("/courier/register", response_class=HTMLResponse)
async def courier_register_page():
    return templates_courier.get_courier_register_page()

@app.post("/api/courier/register")
async def api_courier_register(
    name: str = Form(...), password: str = Form(...), verification_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return JSONResponse(status_code=400, content={"detail": "Номер телефона не підтверджено."})

    if await auth.get_courier_by_phone(db, verif.phone):
        return JSONResponse(status_code=400, content={"detail": "Цей номер вже зареєстрований"})
    
    db.add(Courier(
        name=name, phone=verif.phone, 
        hashed_password=auth.get_password_hash(password),
        telegram_chat_id=verif.telegram_chat_id 
    ))
    await db.delete(verif)
    await db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/courier/login")
async def api_courier_login(
    phone: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)
):
    courier = await auth.authenticate_courier(db, phone, password)
    if not courier:
        return RedirectResponse("/courier/login?message=Помилка входу", status_code=302)
    
    token = auth.create_access_token(data={"sub": f"courier:{courier.phone}"})
    resp = RedirectResponse("/courier/app", status_code=302)
    is_secure = ROOT_DOMAIN.startswith("https") 
    resp.set_cookie(key="courier_token", value=token, httponly=True, max_age=604800, samesite="lax", secure=is_secure)
    return resp

@app.get("/courier/app", response_class=HTMLResponse)
async def courier_pwa_main(courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)):
    config = await get_all_settings(db)
    return templates_courier.get_courier_pwa_html(courier, config)

@app.get("/courier/logout")
async def courier_logout():
    resp = RedirectResponse("/courier/login", status_code=302)
    resp.delete_cookie("courier_token")
    return resp

@app.post("/api/courier/toggle_status")
async def courier_toggle_status(
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    courier.is_online = not courier.is_online
    await db.commit()
    return JSONResponse({"is_online": courier.is_online})

@app.post("/api/courier/location")
async def courier_update_location(
    lat: float = Form(...), lon: float = Form(...),
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    courier.lat = lat
    courier.lon = lon
    courier.last_seen = datetime.utcnow()
    await db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/courier/fcm_token")
async def update_fcm_token(
    token: str = Form(...), courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    courier.fcm_token = token
    await db.commit()
    return JSONResponse({"status": "updated"})

# --- Helper for Push Couriers ---
async def send_push_to_couriers(courier_tokens: List[str], title: str, body: str, job_id: int = None, fee: float = None):
    if not courier_tokens: return
    try:
        for token in courier_tokens:
            msg = messaging.Message(
                token=token,
                data={
                    "title": title,
                    "body": body,
                    "url": "/courier/app",
                    "job_id": str(job_id) if job_id else "",
                    "fee": str(fee) if fee is not None else "0"
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    ttl=0,
                ),
                apns=messaging.APNSConfig(
                    headers={'apns-priority': '10'},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(content_available=True)
                    )
                )
            )
            messaging.send(msg) 
            logging.info(f"Push sent to {token}")
    except Exception as e:
        logging.error(f"Push Error: {e}")

# --- Helper for Push Partners ---
async def send_push_to_partners(partner_tokens: List[str], title: str, body: str, url: str = "/partner/dashboard", job_id: int = None):
    if not partner_tokens: return
    try:
        for token in partner_tokens:
            payload_data = {
                "title": title,
                "body": body,
                "url": url
            }
            if job_id is not None:
                payload_data["job_id"] = str(job_id)

            msg = messaging.Message(
                token=token,
                data=payload_data,
                android=messaging.AndroidConfig(priority='high', ttl=0),
                apns=messaging.APNSConfig(
                    headers={'apns-priority': '10'},
                    payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True))
                )
            )
            messaging.send(msg)
            logging.info(f"Push sent to partner {token}")
    except Exception as e:
        logging.error(f"Partner Push Error: {e}")

# --- SERVICE WORKER ---
@app.get("/firebase-messaging-sw.js")
async def get_firebase_sw(db: AsyncSession = Depends(get_db)):
    config = await get_all_settings(db)
    api_key = config.get("firebase_api_key", "")
    project_id = config.get("firebase_project_id", "")
    sender_id = config.get("firebase_sender_id", "")
    app_id = config.get("firebase_app_id", "")
    
    content = f"""
    importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
    importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');
    
    firebase.initializeApp({{
        apiKey: "{api_key}",
        authDomain: "{project_id}.firebaseapp.com",
        projectId: "{project_id}",
        storageBucket: "{project_id}.firebasestorage.app",
        messagingSenderId: "{sender_id}",
        appId: "{app_id}"
    }});

    const messaging = firebase.messaging();

    function checkAndSaveOrder(jobId, fee) {{
        return new Promise((resolve) => {{
            if(!jobId || !fee) {{ resolve(true); return; }} 

            var req = indexedDB.open('RestifyPushDB', 1);
            req.onupgradeneeded = function(e) {{ 
                e.target.result.createObjectStore('jobs'); 
            }};
            req.onsuccess = function(e) {{
                var db = e.target.result;
                var tx = db.transaction('jobs', 'readwrite');
                var store = tx.objectStore('jobs');
                var getReq = store.get(jobId);
                
                getReq.onsuccess = function() {{
                    var lastFee = getReq.result;
                    if (lastFee && parseFloat(lastFee) >= parseFloat(fee)) {{
                        resolve(false); 
                    }} else {{
                        store.put(fee, jobId);
                        resolve(true); 
                    }}
                }};
                getReq.onerror = function() {{ resolve(true); }};
            }};
            req.onerror = function() {{ resolve(true); }};
        }});
    }}

    messaging.onBackgroundMessage(function(payload) {{
      console.log('[firebase-messaging-sw.js] Received background message ', payload);
      const data = payload.data || {{}};
      const notificationTitle = data.title || "Restify Courier";
      
      return checkAndSaveOrder(data.job_id, data.fee).then(function(shouldShow) {{
          if (shouldShow) {{
              const notificationOptions = {{
                body: data.body || "Нове повідомлення",
                icon: 'https://cdn-icons-png.flaticon.com/512/7542/7542190.png',
                tag: 'job-' + data.job_id,
                requireInteraction: true,
                data: {{ url: data.url || '/courier/app' }}
              }};
              return self.registration.showNotification(notificationTitle, notificationOptions);
          }}
      }});
    }});

    self.addEventListener('notificationclick', function(event) {{
        event.notification.close();
        const urlToOpen = event.notification.data.url || '/courier/app';
        event.waitUntil(
            clients.matchAll({{type: 'window', includeUncontrolled: true}}).then(windowClients => {{
                for (var i = 0; i < windowClients.length; i++) {{
                    var client = windowClients[i];
                    if (client.url.indexOf(urlToOpen) !== -1 && 'focus' in client) return client.focus();
                }}
                if (clients.openWindow) return clients.openWindow(urlToOpen);
            }})
        );
    }});
    """
    return Response(content=content, media_type="application/javascript")


# --- WEBSOCKET COURIER ---
@app.websocket("/ws/courier")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    token = websocket.cookies.get("courier_token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        courier = await auth.get_current_courier(token, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    courier_id = courier.id 
    await manager.connect_courier(websocket, courier_id)
    
    try:
        while True:
            data_text = await websocket.receive_text()
            
            try:
                data = json.loads(data_text)
                
                if data.get("type") == "init_location":
                    lat = float(data.get("lat"))
                    lon = float(data.get("lon"))
                    
                    courier.lat = lat
                    courier.lon = lon
                    courier.last_seen = datetime.utcnow()
                    await db.commit() 
                    
                    logging.info(f"Courier {courier_id} updated location via WS: {lat}, {lon}")
                    
                    db.expire_all() 
                    
                    active_job_check = await db.execute(
                        select(DeliveryJob.id)
                        .where(DeliveryJob.courier_id == courier_id) 
                        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
                    )
                    
                    if active_job_check.scalar():
                         pass
                    else:
                        pass 
                
                elif data == "ping":
                    await websocket.send_text("pong")

            except json.JSONDecodeError:
                if data_text == "ping":
                    await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect_courier(courier_id) 
    except Exception as e:
        logging.error(f"WS Error: {e}")
        manager.disconnect_courier(courier_id) 

@app.get("/api/courier/open_orders")
async def get_open_orders(
    lat: float, lon: float, 
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    active_check = await db.execute(
        select(DeliveryJob.id)
        .where(DeliveryJob.courier_id == courier.id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
    )
    if active_check.scalar():
        return JSONResponse([]) 

    result = await db.execute(
        select(DeliveryJob)
        .options(joinedload(DeliveryJob.partner))
        .where(DeliveryJob.status == "pending")
    )
    jobs = result.scalars().all()
    
    response_data = []
    
    for job in jobs:
        if not job.partner: continue
        
        rest_lat, rest_lon = await geocode_address(job.partner.address)
        
        dist_to_rest = None
        if rest_lat and rest_lon:
            dist_to_rest = calculate_distance(lat, lon, rest_lat, rest_lon)
        
        sort_dist = dist_to_rest if dist_to_rest is not None else 9999
        
        dist_trip = "?"
        if job.dropoff_lat and job.dropoff_lon and rest_lat and rest_lon:
            val = calculate_distance(rest_lat, rest_lon, job.dropoff_lat, job.dropoff_lon)
            if val: dist_trip = val

        payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(job.payment_type, "Оплата")

        response_data.append({
            "id": job.id,
            "restaurant_name": job.partner.name,
            "restaurant_address": job.partner.address,
            "dropoff_address": job.dropoff_address,
            "fee": job.delivery_fee,
            "price": job.order_price,
            "dist_to_rest": dist_to_rest, 
            "dist_trip": dist_trip,       
            "payment_type": job.payment_type,
            "is_return": job.is_return_required,
            "comment": job.comment,
            "_sort_key": sort_dist
        })

    response_data.sort(key=lambda x: x["_sort_key"])
    
    return JSONResponse(response_data)


@app.get("/api/courier/history")
async def get_courier_history(
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    config = await get_all_settings(db)
    tz = config.get("timezone", "Europe/Kiev")
    
    result = await db.execute(
        select(DeliveryJob)
        .where(DeliveryJob.courier_id == courier.id)
        .where(DeliveryJob.status.in_(["delivered", "cancelled"]))
        .order_by(DeliveryJob.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()
    
    data = []
    for j in jobs:
        data.append({
            "id": j.id,
            "date": format_local_time(j.created_at, tz, "%d.%m %H:%M"),
            "address": j.dropoff_address,
            "price": j.delivery_fee,
            "status": j.status
        })
    return JSONResponse(data)

@app.get("/api/courier/active_job")
async def get_active_job(
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DeliveryJob).options(joinedload(DeliveryJob.partner))
        .where(DeliveryJob.courier_id == courier.id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
    )
    job = result.scalars().first()
    
    if not job:
        return JSONResponse({"active": False})
    
    partner_name = job.partner.name if job.partner else "Невідомий заклад"
    partner_address = job.partner.address if job.partner else "Адреса не знайдена"
    partner_phone = job.partner.phone if job.partner else ""
    
    payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(job.payment_type, "Оплата")
    
    server_status = job.status 
    is_ready = True if (job.ready_at or job.status == 'ready') else False

    return JSONResponse({
        "active": True,
        "job": {
            "id": job.id,
            "status": job.status,
            "server_status": server_status, 
            "is_ready": is_ready,           
            "partner_name": partner_name,
            "partner_address": partner_address,
            "partner_phone": partner_phone, 
            "customer_address": job.dropoff_address,
            "customer_lat": job.dropoff_lat,
            "customer_lon": job.dropoff_lon,
            "customer_phone": job.customer_phone,
            "customer_name": job.customer_name,
            "comment": f"[{payment_label}] {job.comment or ''}",
            "order_price": job.order_price,
            "delivery_fee": job.delivery_fee,
            "payment_type": job.payment_type,
            "is_return_required": job.is_return_required,
            
            # --- НОВЫЕ ПОЛЯ ДЛЯ ТАЙМЕРОВ ---
            "assigned_at": job.accepted_at.isoformat() + "Z" if job.accepted_at else None,
            "picked_up_at": job.picked_up_at.isoformat() + "Z" if job.picked_up_at else None,
            "delivered_at": job.delivered_at.isoformat() + "Z" if job.delivered_at else None,
            "completed_at": None # Заказ исчезает с активного экрана после полного завершения
            # ---------------------------------
        }
    })

@app.post("/api/courier/arrived_pickup")
async def courier_arrived_pickup(
    job_id: int = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.courier_id != courier.id:
        return JSONResponse({"status": "error"}, 404)
    
    job.status = "arrived_pickup"
    job.arrived_at_pickup_at = datetime.utcnow()
    await db.commit()
    
    await manager.notify_partner(job.partner_id, {
        "type": "order_update", 
        "job_id": job.id, 
        "status": "arrived_pickup",
        "status_color": "#facc15", 
        "message": f"👋 Кур'єр {courier.name} прибув і чекає на замовлення!"
    })
    
    partner = await db.get(DeliveryPartner, job.partner_id)
    if partner:
        if partner.telegram_chat_id:
            tg_text = f"👋 <b>Кур'єр {courier.name} прибув!</b>\nЗамовлення #{job.id}. Видайте пакунок."
            asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))
        if partner.fcm_token:
            await send_push_to_partners([partner.fcm_token], f"Кур'єр прибув!", f"Кур'єр {courier.name} чекає на замовлення #{job.id}")
    
    return JSONResponse({"status": "ok"})

@app.post("/api/courier/update_job_status")
async def update_job_status(
    job_id: int = Form(...), status: str = Form(...),
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.courier_id != courier.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    if status == "delivered" and job.is_return_required:
        job.status = "returning"
        job.delivered_at = datetime.utcnow() # <--- ДОБАВЛЕНО ДЛЯ ТАЙМЕРА ПОВЕРНЕННЯ КОШТІВ
        msg_text = f"💰 Кур'єр {courier.name} віддав замовлення і везе гроші назад!"
        color = "#fb923c" 
        
        await manager.notify_partner(job.partner_id, {
            "type": "order_update", "job_id": job.id, "status": "returning",
            "status_text": "Повернення коштів", "status_color": color,
            "message": msg_text
        })
        
        partner = await db.get(DeliveryPartner, job.partner_id)
        if partner:
            if partner.telegram_chat_id:
                tg_text = f"💰 <b>Замовлення #{job.id}</b>\n{msg_text}"
                asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))
            if partner.fcm_token:
                await send_push_to_partners([partner.fcm_token], "Повернення коштів", msg_text)
    else:
        job.status = status
        if status == "picked_up": 
            job.picked_up_at = datetime.utcnow()
            msg_text = f"✅ Кур'єр {courier.name} забрав замовлення."
            status_text = "picked_up"
            color = "#bfdbfe" 
        elif status == "delivered": 
            job.delivered_at = datetime.utcnow()
            msg_text = f"🎉 Замовлення #{job.id} успішно доставлено!"
            status_text = "delivered"
            color = "#bbf7d0"
        else:
             msg_text = f"Статус замовлення #{job.id}: {status}"
             status_text = status
             color = "#e2e8f0"

        await manager.notify_partner(job.partner_id, {
            "type": "order_update", "job_id": job.id, "status": status,
            "status_text": status_text, "status_color": color,
            "courier_name": courier.name, "message": msg_text
        })
        
        partner = await db.get(DeliveryPartner, job.partner_id)
        if partner:
            if partner.telegram_chat_id and status in ["picked_up", "delivered"]:
                tg_text = f"📦 <b>Замовлення #{job.id}</b>\n{msg_text}\nКур'єр: {courier.name}"
                asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))
            if partner.fcm_token:
                await send_push_to_partners([partner.fcm_token], f"Статус: {status_text}", msg_text)

    await db.commit()
    return JSONResponse({"status": "ok", "new_status": job.status})

@app.post("/api/courier/accept_order")
async def courier_accept_order(
    job_id: int = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DeliveryJob).where(DeliveryJob.id == job_id).with_for_update()
    )
    job = result.scalar_one_or_none()

    if not job or job.status != "pending":
        return JSONResponse({"status": "error", "message": "Замовлення вже зайняте"}, status_code=409)

    partner = await db.get(DeliveryPartner, job.partner_id)
    partner_lat, partner_lon = await geocode_address(partner.address)
    
    if partner_lat and courier.lat:
        dist = calculate_distance(courier.lat, courier.lon, partner_lat, partner_lon)
        if dist and dist > 20:
             return JSONResponse({"status": "error", "message": f"Занадто далеко ({dist} км)"}, status_code=400)

    job.status = "assigned"
    job.courier_id = courier.id
    job.accepted_at = datetime.utcnow()
    await db.commit()

    await manager.notify_partner(job.partner_id, {
        "type": "order_update", "job_id": job.id, "status": "assigned",
        "status_text": "assigned", "status_color": "#fef08a", 
        "courier_name": courier.name, "message": f"🚴 Кур'єр {courier.name} прийняв замовлення!"
    })

    if partner.telegram_chat_id:
        tg_text = f"🚴 <b>Замовлення #{job.id} прийнято!</b>\nКур'єр: {courier.name}\nТелефон: {courier.phone}"
        asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))
    
    if partner.fcm_token:
        await send_push_to_partners([partner.fcm_token], "Замовлення прийнято!", f"🚴 Кур'єр {courier.name} прямує до вас")

    return JSONResponse({"status": "ok", "message": "Замовлення прийнято!"})

# ==============================================================================
# CHAT API
# ==============================================================================

@app.get("/api/chat/history/{job_id}")
async def get_chat_history(
    job_id: int, 
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    partner_token = request.cookies.get("partner_token")
    courier_token = request.cookies.get("courier_token")
    
    if not partner_token and not courier_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    config = await get_all_settings(db)
    tz = config.get("timezone", "Europe/Kiev")

    messages = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.job_id == job_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return JSONResponse([{
        "role": m.sender_role,
        "text": m.message,
        "time": format_local_time(m.created_at, tz, "%H:%M")
    } for m in messages.scalars().all()])

@app.post("/api/chat/send")
async def send_chat_message(
    request: Request,
    job_id: int = Form(...),
    message: str = Form(...),
    role: str = Form(...), 
    db: AsyncSession = Depends(get_db)
):
    msg = ChatMessage(job_id=job_id, sender_role=role, message=message)
    db.add(msg)
    
    config = await get_all_settings(db)
    tz = config.get("timezone", "Europe/Kiev")
    
    # Завантажуємо замовлення разом із партнером та кур'єром
    result = await db.execute(
        select(DeliveryJob)
        .options(joinedload(DeliveryJob.partner), joinedload(DeliveryJob.courier))
        .where(DeliveryJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if job:
        ws_msg = {
            "type": "chat_message",
            "job_id": job_id,
            "role": role,
            "text": message,
            "time": format_local_time(datetime.utcnow(), tz, "%H:%M")
        }
        
        # Якщо пише ЗАКЛАД (partner) -> сповіщаємо КУР'ЄРА
        if role == 'partner' and job.courier_id and job.courier:
            await manager.notify_courier(job.courier_id, ws_msg)
            
            tg_text = f"💬 <b>Повідомлення від закладу ({job.partner.name}):</b>\n{message}"
            if job.courier.telegram_chat_id:
                asyncio.create_task(bot_service.send_telegram_message(job.courier.telegram_chat_id, tg_text))
            
            if job.courier.fcm_token:
                await send_push_to_couriers([job.courier.fcm_token], f"Чат: {job.partner.name}", message, job_id=job_id)

        # Якщо пише КУР'ЄР (courier) -> сповіщаємо ЗАКЛАД
        elif role == 'courier' and job.partner:
            await manager.notify_partner(job.partner_id, ws_msg)
            
            courier_name = job.courier.name if job.courier else "Кур'єр"
            tg_text = f"💬 <b>Повідомлення від {courier_name}:</b>\n{message}\nЗамовлення #{job_id}"
            
            if job.partner.telegram_chat_id:
                asyncio.create_task(bot_service.send_telegram_message(job.partner.telegram_chat_id, tg_text))
                
            if job.partner.fcm_token:
                await send_push_to_partners([job.partner.fcm_token], f"Чат від {courier_name}", message, job_id=job_id)
            
    await db.commit()
    return JSONResponse({"status": "ok"})

# --- PARTNER LOGIC ---

async def get_current_partner(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("partner_token")
    if not token: raise HTTPException(status_code=401)
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        sub = payload.get("sub")
        if not sub or not sub.startswith("partner:"): raise HTTPException(status_code=401)
        partner_id = int(sub.split(":")[1])
        partner = await db.get(DeliveryPartner, partner_id)
        if not partner: raise HTTPException(status_code=401)
        if hasattr(partner, 'is_active') and not partner.is_active: raise HTTPException(status_code=403, detail="Banned")
        return partner
    except Exception: raise HTTPException(status_code=401)

# ==========================================
# НАТИВНЫЕ JSON API ДЛЯ ANDROID ПРИЛОЖЕНИЯ ПАРТНЕРА
# ==========================================

@app.post("/api/partner/login_native")
async def api_partner_login_native(email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == email))
    partner = result.scalar_one_or_none()
    
    if not partner or not auth.verify_password(password, partner.hashed_password):
        return JSONResponse({"status": "error", "message": "Невірний логін/пароль"}, status_code=401)
    
    token = auth.create_access_token(data={"sub": f"partner:{partner.id}"})
    resp = JSONResponse({"status": "ok", "partner_name": partner.name})
    resp.set_cookie(key="partner_token", value=token, httponly=True, max_age=604800, samesite="lax")
    return resp

@app.get("/api/partner/orders_native")
async def api_partner_orders_native(partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)):
    config = await get_all_settings(db)
    tz = config.get("timezone", "Europe/Kiev")
    
    result = await db.execute(
        select(DeliveryJob).options(joinedload(DeliveryJob.courier))
        .where(DeliveryJob.partner_id == partner.id).order_by(DeliveryJob.id.desc())
    )
    jobs = result.scalars().all()
    
    data = []
    time_format = '%Y-%m-%d %H:%M:%S'
    
    for j in jobs:
        c_data = None
        if j.courier:
            c_data = {
                "name": j.courier.name, "phone": j.courier.phone,
                "rating": j.courier.avg_rating or 5.0, "rating_count": j.courier.rating_count or 0
            }
        data.append({
            "id": j.id, 
            "status": j.status, 
            "created_at": format_local_time(j.created_at, tz, time_format) if j.created_at else None,
            "accepted_at": format_local_time(j.accepted_at, tz, time_format) if j.accepted_at else None,
            "arrived_at": format_local_time(j.arrived_at_pickup_at, tz, time_format) if j.arrived_at_pickup_at else None,
            "picked_up_at": format_local_time(j.picked_up_at, tz, time_format) if j.picked_up_at else None,
            "delivered_at": format_local_time(j.delivered_at, tz, time_format) if j.delivered_at else None,
            "dropoff_address": j.dropoff_address,
            "order_price": j.order_price, "delivery_fee": j.delivery_fee,
            "payment_type": j.payment_type, "is_return_required": j.is_return_required,
            "is_ready": bool(j.ready_at) or j.status == 'ready',
            "courier": c_data
        })
    return JSONResponse(data)

@app.post("/api/partner/create_order_native")
async def api_create_order_native(
    dropoff_address: str = Form(...), customer_phone: str = Form(...), 
    order_price: float = Form(0.0), delivery_fee: float = Form(50.0), 
    comment: str = Form(""), payment_type: str = Form("prepaid"), 
    is_return_required: bool = Form(False),
    db: AsyncSession = Depends(get_db), partner: DeliveryPartner = Depends(get_current_partner)
):
    client_lat, client_lon = await geocode_address(dropoff_address)
    rest_lat, rest_lon = await geocode_address(partner.address)

    full_comment = comment
    if is_return_required:
        full_comment = f"⚠️ ПОВЕРНЕННЯ КОШТІВ! {full_comment}"
    if payment_type == 'buyout':
        full_comment = f"💰 ВИКУП ({order_price} грн)! {full_comment}"

    job = DeliveryJob(
        partner_id=partner.id, dropoff_address=dropoff_address, 
        dropoff_lat=client_lat, dropoff_lon=client_lon, 
        customer_phone=customer_phone, order_price=order_price, delivery_fee=delivery_fee,
        comment=full_comment, payment_type=payment_type,
        is_return_required=is_return_required, status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    busy_couriers_res = await db.execute(
        select(DeliveryJob.courier_id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
        .where(DeliveryJob.courier_id.is_not(None))
    )
    busy_ids = set(busy_couriers_res.scalars().all())

    res = await db.execute(select(Courier).where(Courier.is_online == True))
    online_couriers = res.scalars().all()
    
    payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(payment_type, "Оплата")

    async def notify_courier_async(courier):
        is_location_fresh = True
        if courier.last_seen:
            diff = datetime.utcnow() - courier.last_seen
            if diff.total_seconds() > 1800: 
                is_location_fresh = False
        
        dist_to_rest = None
        if is_location_fresh and courier.lat and courier.lon and rest_lat and rest_lon:
            dist_to_rest = calculate_distance(courier.lat, courier.lon, rest_lat, rest_lon)
        
        if is_location_fresh and dist_to_rest is not None and dist_to_rest > 20: 
            return 
            
        display_dist = dist_to_rest if (is_location_fresh and dist_to_rest is not None) else "?"

        personal_data = {
            "id": job.id, "address": dropoff_address, 
            "restaurant": partner.name, "restaurant_address": partner.address,
            "fee": delivery_fee, "price": order_price, "comment": f"[{payment_label}] {full_comment}",
            "dist_to_rest": display_dist,
            "is_return": is_return_required,
            "payment_type": payment_type
        }
        
        await manager.notify_courier(courier.id, {"type": "new_order", "data": personal_data})
        
        if courier.fcm_token:
            await send_push_to_couriers([courier.fcm_token], "🔥 Нове замовлення!", f"💰 {delivery_fee} грн", job_id=job.id, fee=delivery_fee)

    for c in online_couriers:
        if c.id in busy_ids: continue
        asyncio.create_task(notify_courier_async(c))

    res_tg = await db.execute(select(Courier).where(Courier.is_online == True, Courier.telegram_chat_id != None))
    for c in res_tg.scalars().all():
        if c.id in busy_ids: continue
        asyncio.create_task(bot_service.send_telegram_message(c.telegram_chat_id, f"🔥 <b>Нове замовлення!</b>\n💰 {delivery_fee} грн\n📍 {partner.name}"))

    return JSONResponse({"status": "ok", "job_id": job.id})

# ==========================================

@app.post("/api/partner/fcm_token")
async def update_partner_fcm_token(
    token: str = Form(...), partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    partner.fcm_token = token
    await db.commit()
    return JSONResponse({"status": "updated"})

@app.get("/partner/login", response_class=HTMLResponse)
async def partner_login_page(message: str = ""):
    return templates_partner.get_partner_auth_html(is_register=False, message=message)

@app.get("/partner/register", response_class=HTMLResponse)
async def partner_register_page(message: str = ""):
    return templates_partner.get_partner_auth_html(is_register=True, message=message)

@app.post("/partner/register")
async def partner_register_action(
    name: str = Form(...), address: str = Form(...), email: str = Form(...),
    password: str = Form(...), verification_token: str = Form(...), db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return templates_partner.get_partner_auth_html(is_register=True, message="Телефон не підтверджено.")
    
    existing = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == email))
    if existing.scalar():
        return templates_partner.get_partner_auth_html(is_register=True, message="Email вже зайнятий")
    
    db.add(DeliveryPartner(
        name=name, phone=verif.phone, address=address, email=email, 
        hashed_password=auth.get_password_hash(password), telegram_chat_id=verif.telegram_chat_id
    ))
    await db.delete(verif)
    await db.commit()
    return RedirectResponse("/partner/login", status_code=303)

@app.post("/partner/login")
async def partner_login_action(
    email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == email))
    partner = result.scalar_one_or_none()
    
    if not partner or not auth.verify_password(password, partner.hashed_password):
        return templates_partner.get_partner_auth_html(is_register=False, message="Невірний логін/пароль")
    
    token = auth.create_access_token(data={"sub": f"partner:{partner.id}"})
    resp = RedirectResponse("/partner/dashboard", status_code=303)
    resp.set_cookie(key="partner_token", value=token, httponly=True, max_age=604800, samesite="lax", secure=True)
    return resp

@app.get("/partner/logout")
async def partner_logout():
    resp = RedirectResponse("/partner/login", status_code=303)
    resp.delete_cookie("partner_token")
    return resp

@app.get("/partner/dashboard", response_class=HTMLResponse)
async def partner_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    try: partner = await get_current_partner(request, db)
    except HTTPException: return RedirectResponse("/partner/login")
    
    # Загружаем настройки, чтобы достать нужный часовой пояс
    config = await get_all_settings(db)
    tz = config.get("timezone", "Europe/Kiev")
    
    result = await db.execute(
        select(DeliveryJob)
        .options(joinedload(DeliveryJob.courier))
        .where(DeliveryJob.partner_id == partner.id)
        .order_by(DeliveryJob.id.desc())
    )
    # Передаем таймзону (tz) последним аргументом в шаблон
    return templates_partner.get_partner_dashboard_html(partner, result.scalars().all(), tz)

@app.post("/api/partner/confirm_return")
async def partner_confirm_return(
    job_id: int = Form(...),
    partner: DeliveryPartner = Depends(get_current_partner), 
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error"}, 404)
        
    job.status = "delivered" 
    job.delivered_at = datetime.utcnow()
    await db.commit()
    
    if job.courier_id:
        await manager.notify_courier(job.courier_id, {
            "type": "job_update", 
            "status": "delivered",
            "message": "✅ Заклад підтвердив отримання коштів. Ви вільні!"
        })
        
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/create_order")
async def create_partner_order(
    dropoff_address: str = Form(...), 
    customer_phone: str = Form(...), 
    customer_name: str = Form(""),
    order_price: float = Form(0.0), 
    delivery_fee: float = Form(50.0), 
    comment: str = Form(""),
    payment_type: str = Form("prepaid"), 
    is_return_required: bool = Form(False),
    lat: float = Form(None),
    lon: float = Form(None),
    db: AsyncSession = Depends(get_db), 
    partner: DeliveryPartner = Depends(get_current_partner)
):
    client_lat, client_lon = lat, lon
    
    if not client_lat or not client_lon:
        client_lat, client_lon = await geocode_address(dropoff_address)

    rest_lat, rest_lon = await geocode_address(partner.address)

    full_comment = comment
    if is_return_required:
        full_comment = f"⚠️ ПОВЕРНЕННЯ КОШТІВ! {full_comment}"
    if payment_type == 'buyout':
        full_comment = f"💰 ВИКУП ({order_price} грн)! {full_comment}"

    job = DeliveryJob(
        partner_id=partner.id, dropoff_address=dropoff_address, 
        dropoff_lat=client_lat, dropoff_lon=client_lon, 
        customer_phone=customer_phone, customer_name=customer_name,
        order_price=order_price, delivery_fee=delivery_fee,
        comment=full_comment, payment_type=payment_type,
        is_return_required=is_return_required,
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    busy_couriers_res = await db.execute(
        select(DeliveryJob.courier_id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
        .where(DeliveryJob.courier_id.is_not(None))
    )
    busy_ids = set(busy_couriers_res.scalars().all())

    res = await db.execute(select(Courier).where(Courier.is_online == True))
    online_couriers = res.scalars().all()
    
    payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(payment_type, "Оплата")

    async def notify_courier_async(courier):
        is_location_fresh = True
        if courier.last_seen:
            diff = datetime.utcnow() - courier.last_seen
            if diff.total_seconds() > 1800: 
                is_location_fresh = False
        
        dist_to_rest = None
        if is_location_fresh and courier.lat and courier.lon and rest_lat and rest_lon:
            dist_to_rest = calculate_distance(courier.lat, courier.lon, rest_lat, rest_lon)
        
        if is_location_fresh and dist_to_rest is not None and dist_to_rest > 20: 
            return 
            
        display_dist = dist_to_rest if (is_location_fresh and dist_to_rest is not None) else "?"

        personal_data = {
            "id": job.id, "address": dropoff_address, 
            "restaurant": partner.name, "restaurant_address": partner.address,
            "fee": delivery_fee, "price": order_price, "comment": f"[{payment_label}] {full_comment}",
            "dist_to_rest": display_dist,
            "is_return": is_return_required,
            "payment_type": payment_type
        }
        
        await manager.notify_courier(courier.id, {"type": "new_order", "data": personal_data})
        
        if courier.fcm_token:
            await send_push_to_couriers([courier.fcm_token], "🔥 Нове замовлення!", f"💰 {delivery_fee} грн", job_id=job.id, fee=delivery_fee)

    for c in online_couriers:
        if c.id in busy_ids: continue
        asyncio.create_task(notify_courier_async(c))

    res_tg = await db.execute(select(Courier).where(Courier.is_online == True, Courier.telegram_chat_id != None))
    for c in res_tg.scalars().all():
        if c.id in busy_ids: continue
        asyncio.create_task(bot_service.send_telegram_message(c.telegram_chat_id, f"🔥 <b>Нове замовлення!</b>\n💰 {delivery_fee} грн\n📍 {partner.name}"))

    return RedirectResponse("/partner/dashboard", status_code=303)

@app.post("/api/partner/order_ready")
async def partner_order_ready(
    job_id: int = Form(...), partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id: return JSONResponse({"status": "error"}, 404)
    
    job.ready_at = datetime.utcnow()
    await db.commit()
    
    if job.courier_id:
        courier = await db.get(Courier, job.courier_id)
        await manager.notify_courier(job.courier_id, {"type": "job_ready", "message": "🍳 Замовлення готове!"})
        
        if courier:
            if courier.telegram_chat_id:
                asyncio.create_task(bot_service.send_telegram_message(courier.telegram_chat_id, f"🍳 <b>Замовлення #{job.id} готове!</b>\nМожете забирати."))
            if courier.fcm_token:
                await send_push_to_couriers([courier.fcm_token], "Замовлення готове!", "Заклад очікує на вас.", job_id=job.id)
        
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/cancel_order")
async def partner_cancel_order(
    job_id: int = Form(...), partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id: return JSONResponse({"status": "error"}, 404)
    job.status = "cancelled"
    await db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/rate_courier")
async def partner_rate_courier(
    job_id: int = Form(...), 
    rating: int = Form(...), 
    review: str = Form(""), 
    partner: DeliveryPartner = Depends(get_current_partner), 
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if job and job.partner_id == partner.id:
        job.courier_rating = rating
        job.courier_review = review
        
        if job.courier_id:
            courier = await db.get(Courier, job.courier_id)
            if courier:
                current_avg = courier.avg_rating or 5.0
                current_count = courier.rating_count or 0
                
                new_count = current_count + 1
                new_avg = ((current_avg * current_count) + rating) / new_count
                
                courier.avg_rating = round(new_avg, 2)
                courier.rating_count = new_count
        
        await db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/boost_order")
async def partner_boost_order(
    job_id: int = Form(...),
    amount: float = Form(10.0),
    partner: DeliveryPartner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DeliveryJob)
        .options(joinedload(DeliveryJob.partner))
        .where(DeliveryJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    if job.status != "pending":
         return JSONResponse({"status": "error", "message": "Замовлення вже прийнято або скасовано"}, status_code=400)
    
    job.delivery_fee += amount
    await db.commit()
    
    rest_lat, rest_lon = await geocode_address(job.partner.address)
    
    payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(job.payment_type, "Оплата")
    
    full_job_data = {
        "id": job.id,
        "address": job.dropoff_address,
        "restaurant": job.partner.name,
        "restaurant_address": job.partner.address,
        "fee": job.delivery_fee,          
        "price": job.order_price,
        "comment": f"[{payment_label}] {job.comment or ''}",
        "payment_type": job.payment_type,
        "is_return": job.is_return_required,
        "dist_to_rest": "?", 
        "dist_rest_to_client": "?" 
    }

    busy_couriers_res = await db.execute(
        select(DeliveryJob.courier_id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
        .where(DeliveryJob.courier_id.is_not(None))
    )
    busy_ids = set(busy_couriers_res.scalars().all())

    online_couriers = (await db.execute(select(Courier).where(Courier.is_online == True))).scalars().all()
    
    for c in online_couriers:
        if c.id in busy_ids: continue
        
        current_dist = "?"
        if c.lat and c.lon and rest_lat and rest_lon:
            d = calculate_distance(c.lat, c.lon, rest_lat, rest_lon)
            if d: current_dist = d
        
        courier_specific_data = full_job_data.copy()
        courier_specific_data["dist_to_rest"] = current_dist

        await manager.notify_courier(c.id, {
            "type": "new_order", 
            "data": courier_specific_data 
        })

        if c.fcm_token:
             await send_push_to_couriers(
                 [c.fcm_token], 
                 "🔥 Ціна зросла!", 
                 f"💰 {job.delivery_fee} грн\n📍 {job.dropoff_address}", 
                 job_id=job.id, 
                 fee=job.delivery_fee
             )
             
        if c.telegram_chat_id:
            tg_msg = f"🔥 <b>Ціна зросла!</b>\nНова ціна: 💰 {job.delivery_fee} грн\n📍 {job.dropoff_address}"
            asyncio.create_task(bot_service.send_telegram_message(c.telegram_chat_id, tg_msg))
        
    return JSONResponse({"status": "ok", "new_fee": job.delivery_fee})

@app.get("/api/partner/track_courier/{job_id}")
async def track_courier_location(
    job_id: int, partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id: return JSONResponse({"status": "error"}, status_code=403)
    if not job.courier_id: return JSONResponse({"status": "waiting"})
    courier = await db.get(Courier, job.courier_id)
    return JSONResponse({
        "status": "ok", "lat": courier.lat, "lon": courier.lon, 
        "name": courier.name, "phone": courier.phone, "job_status": job.status
    })

@app.websocket("/ws/partner")
async def websocket_partner_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    token = websocket.cookies.get("partner_token")
    if not token: 
        await websocket.close()
        return
        
    pid = None 
    try:
        pid = int(auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])["sub"].split(":")[1])
        await manager.connect_partner(websocket, pid)
        while True: 
            await websocket.receive_text()
    except Exception as e: 
        logging.error(f"Partner WS Disconnected: {e}")
        if pid: 
            manager.disconnect_partner(pid)

async def send_tg_notification(name, phone, plan, result_data):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    text = f"🚀 NEW CLIENT!\n{name} | {phone}\nURL: {result_data['url']}"
    async with httpx.AsyncClient() as c:
        await c.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": text})

if __name__ == "__main__":
    if not provision.SAAS_ADMIN_PASSWORD:
        logging.critical("SAAS_ADMIN_PASSWORD not set!")
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)