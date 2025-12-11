import logging
import uvicorn
import os
import secrets
import httpx
import asyncio
import json
import uuid
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

# --- 1. Імпорти проекту ---
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
    DeliveryPartner, DeliveryJob, PendingVerification,
    create_db_tables, get_db
)
from auth import check_admin_auth

# --- FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials, messaging

# --- 2. Завантаження конфігурації зі змінних оточення ---
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", "restify.site")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Restify_Bot") 

# --- 3. Ініціалізація FastAPI та Firebase ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# Ініціалізація Firebase Admin SDK
# Файл firebase_credentials.json повинен лежати в тій же папці, що і app.py
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase_credentials.json"):
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
            logging.info("Firebase Admin ініціалізовано успішно.")
        else:
            logging.warning("firebase_credentials.json не знайдено! Push-сповіщення не працюватимуть.")
    except Exception as e:
        logging.warning(f"Помилка ініціалізації Firebase: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Запуск... Підключення до БД та створення таблиць...")
    await create_db_tables()
    
    # Завантаження конфігу (із захистом від збоїв)
    load_config() 
    
    # --- ЗАПУСК TELEGRAM БОТА ---
    if bot_service.bot:
        asyncio.create_task(bot_service.start_bot())
        logging.info("Telegram Bot Polling запущено через bot_service.")
    else:
        logging.warning("TG_BOT_TOKEN не встановлено, бот вимкнено.")
    
    # --- ЗАПУСК МОНІТОРИНГУ ЗАВИСЛИХ ЗАМОВЛЕНЬ ---
    asyncio.create_task(order_monitor.monitor_stale_orders(manager))
    logging.info("Моніторинг замовлень (Order Monitor) запущено.")
    
    logging.info("Додаток запущено.")
    yield
    logging.info("Завершення роботи.")

app = FastAPI(
    title="Restify SaaS Control Plane",
    lifespan=lifespan
)

# --- ПІДКЛЮЧЕННЯ РОУТЕРА АДМІНКИ ДОСТАВКИ ---
app.include_router(admin_delivery.router)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        # Зберігаємо підключення: id -> websocket
        self.active_couriers: Dict[int, WebSocket] = {}
        self.active_partners: Dict[int, WebSocket] = {}

    # --- Методи для КУР'ЄРІВ ---
    async def connect_courier(self, websocket: WebSocket, courier_id: int):
        await websocket.accept()
        self.active_couriers[courier_id] = websocket
        logging.info(f"Courier {courier_id} connected to WS")

    def disconnect_courier(self, courier_id: int):
        if courier_id in self.active_couriers:
            del self.active_couriers[courier_id]
            logging.info(f"Courier {courier_id} disconnected from WS")

    async def broadcast_order_to_couriers(self, job_data: dict):
        """Відправляє замовлення всім активним кур'єрам"""
        active_ids = list(self.active_couriers.keys())
        for c_id in active_ids:
            connection = self.active_couriers.get(c_id)
            if connection:
                try:
                    await connection.send_json({"type": "new_order", "data": job_data})
                except Exception as e:
                    logging.error(f"WS Error (Courier {c_id}): {e}")
                    self.disconnect_courier(c_id)

    async def notify_courier(self, courier_id: int, message: dict):
        """Відправляє повідомлення конкретному кур'єру"""
        if courier_id in self.active_couriers:
            try:
                await self.active_couriers[courier_id].send_json(message)
            except Exception as e:
                logging.error(f"WS Error (Courier {courier_id}): {e}")
                self.disconnect_courier(courier_id)

    # --- Методи для ПАРТНЕРІВ (Ресторанів) ---
    async def connect_partner(self, websocket: WebSocket, partner_id: int):
        await websocket.accept()
        self.active_partners[partner_id] = websocket
        logging.info(f"Partner {partner_id} connected to WS")

    def disconnect_partner(self, partner_id: int):
        if partner_id in self.active_partners:
            del self.active_partners[partner_id]

    async def notify_partner(self, partner_id: int, message: dict):
        """Відправляє повідомлення конкретному ресторану"""
        if partner_id in self.active_partners:
            try:
                await self.active_partners[partner_id].send_json(message)
            except Exception as e:
                logging.error(f"WS Error (Partner {partner_id}): {e}")
                self.disconnect_partner(partner_id)

manager = ConnectionManager()

# --- 4. Логіка вітрини (config.json) ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "admin_id": "", "bot_token": "", "price_light": "300",
    "price_full": "600", "currency": "$",
    "custom_btn_text": "", "custom_btn_content": ""
}

def load_config():
    def write_defaults():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()

    if not os.path.exists(CONFIG_FILE):
        return write_defaults()
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("File is empty")
            config = json.loads(content)
            
    except (json.JSONDecodeError, ValueError, Exception) as e:
        logging.error(f"ПОМИЛКА CONFIG.JSON: {e}. Файл пошкоджено. Відновлюю стандартні налаштування.")
        try:
            os.rename(CONFIG_FILE, f"{CONFIG_FILE}.bak")
        except:
            pass
        return write_defaults()
    
    updated = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            updated = True
            
    if updated:
        save_config(config)
        
    return config

def save_config(new_config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
    except Exception as e:
        logging.error(f"Не вдалося зберегти config.json: {e}")

# --- 6. Ендпоінти (Роутинг) - ЗАГАЛЬНІ ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    config = load_config()
    return HTMLResponse(content=templates_saas.get_landing_page_html(config))

# === ЛОГІКА ДЛЯ ВЛАСНИКІВ РЕСТОРАНІВ (SAAS USER) ===

@app.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request, message: str = None, type: str = "error"):
    token = request.cookies.get("access_token")
    if token:
        user = await auth.get_current_user_from_token(token, async_session_maker)
        if user:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates_saas.get_login_page(message, type)

@app.get("/register", response_class=HTMLResponse)
async def get_register_form(request: Request):
    token = request.cookies.get("access_token")
    if token:
        user = await auth.get_current_user_from_token(token, async_session_maker)
        if user:
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
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
            url="/login?message=Невірний email або пароль", 
            status_code=status.HTTP_302_FOUND
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, samesite="strict", max_age=604800)
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    current_user: User = Depends(auth.get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(
            joinedload(User.instances)
        )
    )
    user_with_instances = result.unique().scalar_one_or_none()
    if not user_with_instances:
        return RedirectResponse(url="/logout")
    return templates_saas.get_dashboard_html(user_with_instances, user_with_instances.instances)

# --- API ДЛЯ VERIFICATION (TELEGRAM AUTH) ---

@app.post("/api/auth/init_verification")
async def init_verification(db: AsyncSession = Depends(get_db)):
    """Генерує токен для реєстрації і створює запис у БД"""
    token = str(uuid.uuid4())
    verification = PendingVerification(token=token, status="created")
    db.add(verification)
    await db.commit()
    
    return JSONResponse({
        "token": token,
        "link": f"https://t.me/{BOT_USERNAME}?start=reg_{token}"
    })

@app.get("/api/auth/check_verification/{token}")
async def check_verification(token: str, db: AsyncSession = Depends(get_db)):
    verif = await db.get(PendingVerification, token)
    
    if not verif:
        return JSONResponse({"status": "error", "message": "Token not found"})
    
    if verif.status == "verified" and verif.phone:
        return JSONResponse({
            "status": "verified",
            "phone": verif.phone
        })
        
    return JSONResponse({"status": "waiting"})

# --- РЕЄСТРАЦІЯ SAAS КОРИСТУВАЧА ---

@app.post("/api/register")
async def handle_registration(
    email: str = Form(...),
    password: str = Form(...),
    verification_token: str = Form(...), 
    db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return JSONResponse(status_code=400, content={"detail": "Номер телефону не підтверджено через Telegram."})

    existing_user = await auth.get_user_by_email(db, email)
    if existing_user:
        return JSONResponse(status_code=400, content={"detail": "Цей email вже зареєстрований."})

    hashed_password = auth.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.delete(verif)
    
    await db.commit()
    await db.refresh(new_user)
    
    return JSONResponse(content={"detail": "User created successfully."})


# === ЛОГІКА ДЛЯ КУР'ЄРІВ (COURIER PWA) ===

@app.get("/courier/login", response_class=HTMLResponse)
async def courier_login_page(request: Request, message: str = None, db: AsyncSession = Depends(get_db)):
    # --- ПЕРЕВІРКА КУК ПЕРЕД ВІДОБРАЖЕННЯМ ФОРМИ ---
    token = request.cookies.get("courier_token")
    if token:
        try:
            courier = await auth.get_current_courier(token, db)
            if courier:
                return RedirectResponse(url="/courier/app", status_code=302)
        except Exception:
            pass # Токен невалідний, показуємо форму входу
    
    return templates_courier.get_courier_login_page(message)

@app.get("/courier/register", response_class=HTMLResponse)
async def courier_register_page():
    return templates_courier.get_courier_register_page()

@app.post("/api/courier/register")
async def api_courier_register(
    name: str = Form(...),
    password: str = Form(...),
    verification_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return JSONResponse(status_code=400, content={"detail": "Номер телефону не підтверджено через Telegram."})

    phone = verif.phone

    existing = await auth.get_courier_by_phone(db, phone)
    if existing:
        return JSONResponse(status_code=400, content={"detail": "Цей номер телефону вже зареєстрований"})
    
    hashed = auth.get_password_hash(password)
    new_courier = Courier(
        name=name, 
        phone=phone, 
        hashed_password=hashed,
        telegram_chat_id=verif.telegram_chat_id 
    )
    db.add(new_courier)
    await db.delete(verif)
    await db.commit()
    
    return JSONResponse({"status": "ok"})

@app.post("/api/courier/login")
async def api_courier_login(
    phone: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    courier = await auth.authenticate_courier(db, phone, password)
    if not courier:
        return RedirectResponse("/courier/login?message=Невірні дані або акаунт заблоковано", status_code=302)
    
    token = auth.create_access_token(data={"sub": f"courier:{courier.phone}"})
    
    resp = RedirectResponse("/courier/app", status_code=302)
    
    # --- БЕЗПЕЧНЕ ВСТАНОВЛЕННЯ КУКИ (HTTPS CHECK) ---
    is_secure = ROOT_DOMAIN.startswith("https") # True, якщо сайт на HTTPS
    
    resp.set_cookie(
        key="courier_token", 
        value=token, 
        httponly=True, 
        max_age=604800, # 7 днів
        samesite="lax", 
        secure=is_secure 
    )
    return resp

@app.get("/courier/app", response_class=HTMLResponse)
async def courier_pwa_main(
    courier: Courier = Depends(auth.get_current_courier)
):
    return templates_courier.get_courier_pwa_html(courier)

@app.get("/courier/logout")
async def courier_logout():
    resp = RedirectResponse("/courier/login", status_code=302)
    resp.delete_cookie("courier_token")
    return resp

@app.post("/api/courier/toggle_status")
async def courier_toggle_status(
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    courier.is_online = not courier.is_online
    await db.commit()
    return JSONResponse({"is_online": courier.is_online})

@app.post("/api/courier/location")
async def courier_update_location(
    lat: float = Form(...),
    lon: float = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    courier.lat = lat
    courier.lon = lon
    courier.last_seen = datetime.utcnow()
    await db.commit()
    return JSONResponse({"status": "ok"})

# --- ЕНДПОІНТ: Збереження FCM токена кур'єра ---
@app.post("/api/courier/fcm_token")
async def update_fcm_token(
    token: str = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    """Зберігає токен пристрою кур'єра для Push-повідомлень"""
    logging.info(f"[PUSH] Кур'єр {courier.id} ({courier.name}) оновив FCM токен: {token[:15]}...")
    
    courier.fcm_token = token
    await db.commit()
    return JSONResponse({"status": "updated"})

# --- ЕНДПОІНТ: Service Worker для Firebase ---
@app.get("/firebase-messaging-sw.js")
async def get_firebase_sw():
    content = """
    importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
    importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');

    firebase.initializeApp({
        apiKey: "AIzaSyC_amFOh032cBcaeo3f1woLmlwhe6Fyr_k",
        authDomain: "restifysite.firebaseapp.com",
        projectId: "restifysite",
        storageBucket: "restifysite.firebasestorage.app",
        messagingSenderId: "679234031594",
        appId: "1:679234031594:web:cc77807a88c5a03b72ec93"
    });

    const messaging = firebase.messaging();

    // Обробник фонових повідомлень
    messaging.onBackgroundMessage(function(payload) {
      console.log('[firebase-messaging-sw.js] Received background message ', payload);
      
      const notificationTitle = payload.notification.title;
      const notificationOptions = {
        body: payload.notification.body,
        icon: 'https://cdn-icons-png.flaticon.com/512/7542/7542190.png', 
        tag: 'new-order',
        data: { url: '/courier/app' } 
      };

      return self.registration.showNotification(notificationTitle, notificationOptions);
    });

    // Обробник кліку по сповіщенню
    self.addEventListener('notificationclick', function(event) {
        event.notification.close();
        
        event.waitUntil(
            clients.matchAll({type: 'window', includeUncontrolled: true}).then(windowClients => {
                for (var i = 0; i < windowClients.length; i++) {
                    var client = windowClients[i];
                    if (client.url.indexOf('/courier/app') !== -1 && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow('/courier/app');
                }
            })
        );
    });
    """
    return Response(content=content, media_type="application/javascript")

# --- ФУНКЦІЯ ВІДПРАВКИ PUSH ---
async def send_push_to_couriers(courier_tokens: List[str], title: str, body: str):
    if not courier_tokens: return
    try:
        success_count = 0
        for token in courier_tokens:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            )
            messaging.send(message) 
            success_count += 1 

        logging.info(f"Sent {success_count} pushes.")
    except Exception as e:
        logging.error(f"Push Error: {e}")

# --- WebSocket для кур'єрів ---
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

    await manager.connect_courier(websocket, courier.id)
    
    # Синхронізація "висячих" замовлень
    try:
        result = await db.execute(
            select(DeliveryJob)
            .options(joinedload(DeliveryJob.partner))
            .where(DeliveryJob.status == "pending")
        )
        pending_jobs = result.scalars().all()
        
        for job in pending_jobs:
            payment_label = {
                "prepaid": "✅ Оплачено",
                "cash": "💵 Готівка від клієнта",
                "buyout": "💰 Потрібен викуп"
            }.get(job.payment_type, "Оплата")

            job_data = {
                "id": job.id,
                "address": job.dropoff_address,
                "restaurant": job.partner.name if job.partner else "Невідомий заклад",
                "restaurant_address": job.partner.address if job.partner else "",
                "fee": job.delivery_fee,
                "price": job.order_price,
                "comment": f"[{payment_label}] {job.comment or ''}"
            }
            await websocket.send_json({"type": "new_order", "data": job_data})
    except Exception as e:
        logging.error(f"Error syncing pending orders for courier {courier.id}: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_courier(courier.id)
    except Exception as e:
        logging.error(f"WS Error: {e}")
        manager.disconnect_courier(courier.id)


# --- API ДЛЯ PWA ---

@app.get("/api/courier/history")
async def get_courier_history(
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
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
            "date": j.created_at.strftime("%d.%m %H:%M"),
            "address": j.dropoff_address,
            "price": j.delivery_fee,
            "status": j.status
        })
    return JSONResponse(data)

@app.get("/api/courier/active_job")
async def get_active_job(
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DeliveryJob).options(joinedload(DeliveryJob.partner))
        .where(DeliveryJob.courier_id == courier.id)
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
    )
    job = result.scalars().first()
    
    if not job:
        return JSONResponse({"active": False})
    
    partner_name = job.partner.name if job.partner else "Невідомий заклад (Видалено)"
    partner_address = job.partner.address if job.partner else "Адреса не знайдена"
    partner_phone = job.partner.phone if job.partner else ""
    
    # Додаємо інформацію про оплату в коментар для відображення в інтерфейсі кур'єра
    payment_label = {
        "prepaid": "✅ Оплачено",
        "cash": "💵 Готівка від клієнта",
        "buyout": "💰 Потрібен викуп"
    }.get(job.payment_type, "Оплата")

    return JSONResponse({
        "active": True,
        "job": {
            "id": job.id,
            "status": job.status,
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
            "delivery_fee": job.delivery_fee
        }
    })

@app.post("/api/courier/update_job_status")
async def update_job_status(
    job_id: int = Form(...),
    status: str = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.courier_id != courier.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    job.status = status
    
    # --- ОНОВЛЕНО: Фіксація часу ---
    now = datetime.utcnow()
    if status == "picked_up":
        job.picked_up_at = now
    elif status == "delivered":
        job.delivered_at = now
        
    await db.commit()

    msg_text = ""
    color = "#e2e8f0"
    
    if status == "picked_up":
        msg_text = f"✅ Кур'єр {courier.name} забрав замовлення."
        color = "#bfdbfe" 
    elif status == "delivered":
        msg_text = f"🎉 Замовлення #{job.id} успішно доставлено!"
        color = "#bbf7d0" 

    if msg_text:
        await manager.notify_partner(job.partner_id, {
            "type": "order_update",
            "job_id": job.id,
            "status": status,
            "status_text": status,
            "status_color": color,
            "courier_name": courier.name,
            "message": msg_text
        })

        partner = await db.get(DeliveryPartner, job.partner_id)
        if partner and partner.telegram_chat_id:
            tg_text = f"📦 <b>Замовлення #{job.id}</b>\n{msg_text}\nКур'єр: {courier.name}"
            asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))

    return JSONResponse({"status": "ok", "new_status": status})

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

    if not job:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    if job.status != "pending":
        return JSONResponse({"status": "error", "message": "Це замовлення вже забрав інший кур'єр"}, status_code=409)

    job.status = "assigned"
    job.courier_id = courier.id
    
    # --- ОНОВЛЕНО: Фіксація часу прийняття ---
    job.accepted_at = datetime.utcnow()
    
    await db.commit()

    await manager.notify_partner(job.partner_id, {
        "type": "order_update",
        "job_id": job.id,
        "status": "assigned",
        "status_text": "assigned",
        "status_color": "#fef08a", 
        "courier_name": courier.name,
        "message": f"🚴 Кур'єр {courier.name} прийняв замовлення! Очікуйте."
    })

    partner = await db.get(DeliveryPartner, job.partner_id)
    if partner and partner.telegram_chat_id:
        tg_text = (
            f"🚴 <b>Замовлення #{job.id} прийнято!</b>\n"
            f"Кур'єр: {courier.name}\n"
            f"Телефон: {courier.phone}\n"
            f"<i>Очікуйте прибуття кур'єра до закладу.</i>"
        )
        asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))

    return JSONResponse({"status": "ok", "message": "Замовлення прийнято! Рушайте до закладу."})


# === ЗОВНІШНЄ API ДЛЯ РЕСТОРАНІВ ===

@app.get("/api/external/couriers/nearby")
async def get_nearby_couriers(
    lat: float, lon: float, radius_km: float = 5.0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Courier).where(Courier.is_online == True)
    )
    couriers = result.scalars().all()
    
    data = []
    for c in couriers:
        if c.lat and c.lon:
            data.append({
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "lat": c.lat,
                "lon": c.lon,
                "last_seen": c.last_seen.isoformat() if c.last_seen else None
            })
    return JSONResponse(data)


# === ЛОГІКА ДЛЯ ПАРТНЕРІВ ===

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
        if hasattr(partner, 'is_active') and not partner.is_active:
            raise HTTPException(status_code=403, detail="Account is banned")
            
        return partner
    except Exception:
        raise HTTPException(status_code=401)

@app.get("/partner/login", response_class=HTMLResponse)
async def partner_login_page(message: str = ""):
    return templates_partner.get_partner_auth_html(is_register=False, message=message)

@app.get("/partner/register", response_class=HTMLResponse)
async def partner_register_page(message: str = ""):
    return templates_partner.get_partner_auth_html(is_register=True, message=message)

@app.post("/partner/register")
async def partner_register_action(
    name: str = Form(...),
    address: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    verification_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    verif = await db.get(PendingVerification, verification_token)
    if not verif or verif.status != "verified":
         return templates_partner.get_partner_auth_html(is_register=True, message="Телефон не підтверджено.")
    
    phone = verif.phone

    existing = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == email))
    if existing.scalar():
        return templates_partner.get_partner_auth_html(is_register=True, message="Цей email вже зареєстрований")
    
    hashed = auth.get_password_hash(password)
    partner = DeliveryPartner(
        name=name, 
        phone=phone, 
        address=address, 
        email=email, 
        hashed_password=hashed,
        telegram_chat_id=verif.telegram_chat_id
    )
    db.add(partner)
    await db.delete(verif)
    await db.commit()
    
    return RedirectResponse("/partner/login", status_code=303)

@app.post("/partner/login")
async def partner_login_action(
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == email))
    partner = result.scalar_one_or_none()
    
    if not partner or not auth.verify_password(password, partner.hashed_password):
        return templates_partner.get_partner_auth_html(is_register=False, message="Невірний email або пароль")

    if hasattr(partner, 'is_active') and not partner.is_active:
        return templates_partner.get_partner_auth_html(is_register=False, message="Ваш акаунт заблоковано адміністратором.")
    
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
async def partner_dashboard(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    try:
        partner = await get_current_partner(request, db)
    except HTTPException:
        return RedirectResponse("/partner/login")
        
    result = await db.execute(select(DeliveryJob).where(DeliveryJob.partner_id == partner.id).order_by(DeliveryJob.id.desc()))
    jobs = result.scalars().all()
    
    return templates_partner.get_partner_dashboard_html(partner, jobs)

@app.get("/api/partner/track_courier/{job_id}")
async def track_courier_location(
    job_id: int,
    partner: DeliveryPartner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error"}, status_code=403)
        
    if not job.courier_id:
        return JSONResponse({"status": "waiting"})

    courier = await db.get(Courier, job.courier_id)
    
    return JSONResponse({
        "status": "ok",
        "lat": courier.lat,
        "lon": courier.lon,
        "name": courier.name,
        "phone": courier.phone,
        "job_status": job.status,
        "last_seen": courier.last_seen.isoformat() if courier.last_seen else None
    })

# --- ГЕОКОДИНГ ---
async def geocode_address(address: str):
    """Перетворює адресу в координати через Nominatim (OSM)"""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "RestifyDelivery/1.0 (admin@restify.site)"}
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=10.0)
            data = resp.json()
            if data and len(data) > 0:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            logging.error(f"Geocoding Error: {e}")
            
    return None, None

# --- ОНОВЛЕНИЙ ЕНДПОІНТ СТВОРЕННЯ ЗАМОВЛЕННЯ ---
@app.post("/api/partner/create_order")
async def create_partner_order(
    dropoff_address: str = Form(...),
    customer_phone: str = Form(...),
    customer_name: str = Form(""),
    order_price: float = Form(0.0),
    delivery_fee: float = Form(50.0),
    comment: str = Form(""),
    payment_type: str = Form("prepaid"), # НОВЕ ПОЛЕ: Тип оплати
    db: AsyncSession = Depends(get_db),
    partner: DeliveryPartner = Depends(get_current_partner)
):
    # 1. Геокодинг
    lat, lon = await geocode_address(dropoff_address)

    # 2. Створення замовлення
    job = DeliveryJob(
        partner_id=partner.id,
        dropoff_address=dropoff_address,
        dropoff_lat=lat,
        dropoff_lon=lon,
        customer_phone=customer_phone,
        customer_name=customer_name,
        order_price=order_price,
        delivery_fee=delivery_fee,
        comment=comment,
        payment_type=payment_type, # Зберігаємо тип
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 3. WebSocket Broadcast (з інформацією про оплату)
    payment_label = {
        "prepaid": "✅ Оплачено",
        "cash": "💵 Готівка від клієнта",
        "buyout": "💰 Потрібен викуп"
    }.get(payment_type, "Оплата")

    order_data = {
        "id": job.id,
        "address": dropoff_address,
        "lat": lat,
        "lon": lon,
        "restaurant": partner.name,
        "restaurant_address": partner.address,
        "fee": delivery_fee,
        "price": order_price,
        # Додаємо мітку оплати в коментар, щоб кур'єр бачив одразу
        "comment": f"[{payment_label}] {comment}" 
    }
    await manager.broadcast_order_to_couriers(order_data)

    # 4. Telegram Broadcast
    result = await db.execute(
        select(Courier).where(Courier.is_online == True, Courier.telegram_chat_id != None)
    )
    online_couriers_tg = result.scalars().all()
    
    tg_msg = (
        f"🔥 <b>Нове замовлення!</b>\n"
        f"💵 Дохід: <b>{delivery_fee} грн</b>\n"
        f"💳 <b>{payment_label}</b>\n"
        f"📍 Звідки: {partner.name} ({partner.address})\n"
        f"🏁 Куди: {dropoff_address}\n\n"
        f"<i>Зайдіть у додаток, щоб прийняти!</i>"
    )
    
    for c in online_couriers_tg:
        asyncio.create_task(bot_service.send_telegram_message(c.telegram_chat_id, tg_msg))

    # 5. Firebase Push
    online_couriers_result = await db.execute(select(Courier).where(Courier.is_online == True))
    online_couriers = online_couriers_result.scalars().all()
    
    couriers_with_token = [c for c in online_couriers if c.fcm_token]
    tokens = [c.fcm_token for c in couriers_with_token]
    
    if tokens:
        logging.info(f"[PUSH] Відправка {len(tokens)} повідомлень.")
        asyncio.create_task(
            send_push_to_couriers(
                tokens, 
                "🔥 Нове замовлення!", 
                f"💰 {delivery_fee} грн | {partner.name} -> {dropoff_address}"
            )
        )
    else:
        logging.warning("[PUSH] Немає доступних токенів для відправки.")

    return RedirectResponse("/partner/dashboard", status_code=303)

# --- НОВЕ API: ПОВІДОМИТИ КУР'ЄРА ПРО ГОТОВНІСТЬ ЗАМОВЛЕННЯ ---
@app.post("/api/partner/order_ready")
async def partner_order_ready(
    job_id: int = Form(...),
    partner: DeliveryPartner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)

    # Статус можно менять только если заказ назначен или в ожидании
    if job.status not in ["assigned", "pending"]:
         return JSONResponse({"status": "error", "message": "Невірний статус замовлення"}, status_code=400)

    job.status = "ready"
    job.ready_at = datetime.utcnow()
    await db.commit()

    # 1. Сповіщення Кур'єра (якщо призначений)
    if job.courier_id:
        # WebSocket
        await manager.notify_courier(job.courier_id, {
            "type": "job_update",
            "job_id": job.id,
            "status": "ready",
            "message": "🍽️ Замовлення готове! Можна забирати."
        })
        
        # Telegram
        courier = await db.get(Courier, job.courier_id)
        if courier and courier.telegram_chat_id:
            await bot_service.send_telegram_message(
                courier.telegram_chat_id, 
                f"✅ <b>Замовлення #{job.id} ГОТОВЕ!</b>\nЗаклад чекає на вас."
            )
            
        # Push (Firebase)
        if courier and courier.fcm_token:
             asyncio.create_task(send_push_to_couriers(
                [courier.fcm_token],
                "🍳 Замовлення готове!",
                f"Забирайте замовлення #{job.id} у {partner.name}"
             ))

    return JSONResponse({"status": "ok", "message": "Статус оновлено: Готово до видачі"})

# --- НОВЕ: СКАСУВАННЯ ЗАМОВЛЕННЯ (Правило 3 хвилин) ---
@app.post("/api/partner/cancel_order")
async def partner_cancel_order(
    job_id: int = Form(...),
    partner: DeliveryPartner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)

    # Якщо замовлення вже доставлено або скасовано
    if job.status in ["delivered", "cancelled"]:
         return JSONResponse({"status": "error", "message": "Замовлення вже завершено або скасовано"}, status_code=400)

    # Перевірка часу, якщо кур'єр вже призначений
    if job.status == "assigned" and job.accepted_at:
        time_passed = datetime.utcnow() - job.accepted_at
        if time_passed > timedelta(minutes=3):
            minutes_passed = int(time_passed.total_seconds() / 60)
            return JSONResponse({
                "status": "error", 
                "message": f"Запізно! Кур'єр прийняв замовлення {minutes_passed} хв тому (ліміт скасування - 3 хв)."
            }, status_code=400)

    old_status = job.status
    job.status = "cancelled"
    await db.commit()

    # Сповіщення (логіка сповіщення кур'єра може бути додана тут)
    if old_status == "assigned" and job.courier_id:
        logging.info(f"Замовлення #{job.id} скасовано, кур'єр {job.courier_id} буде сповіщений при оновленні.")

    return JSONResponse({"status": "ok", "message": "Замовлення скасовано."})

# --- НОВЕ: ОЦІНКА КУР'ЄРА ---
@app.post("/api/partner/rate_courier")
async def partner_rate_courier(
    job_id: int = Form(...),
    rating: int = Form(...),
    review: str = Form(""),
    partner: DeliveryPartner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)

    if job.status != "delivered":
        return JSONResponse({"status": "error", "message": "Можна оцінювати тільки завершені замовлення"}, status_code=400)

    job.courier_rating = rating
    job.courier_review = review
    await db.commit()

    return JSONResponse({"status": "ok", "message": "Дякуємо за оцінку!"})


# --- WebSocket для Партнерів ---
@app.websocket("/ws/partner")
async def websocket_partner_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    token = websocket.cookies.get("partner_token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        sub = payload.get("sub")
        if not sub or not sub.startswith("partner:"):
            await websocket.close()
            return
        partner_id = int(sub.split(":")[1])
    except Exception:
        await websocket.close()
        return

    await manager.connect_partner(websocket, partner_id)
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        manager.disconnect_partner(partner_id)


# --- 7. ЕНДПОІНТ СТВОРЕННЯ САЙТУ (SAAS) ---

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
            content={"detail": f"Цей домен '{client_name_base}' вже зайнятий. Спробуйте іншу назву."}
        )

    try:
        result_data = provision.create_new_client_instance(
            client_name_base=client_name_base, 
            root_domain=ROOT_DOMAIN,
            client_bot_token=client_bot_token,
            admin_bot_token=admin_bot_token,
            admin_chat_id=admin_chat_id
        )
        
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

        asyncio.create_task(send_tg_notification(name, phone, plan, result_data))
        return JSONResponse(result_data)

    except Exception as e:
        logging.error(f"КРИТИЧНА ПОМИЛКА РОЗГОРТАННЯ: {e}")
        await db.rollback()
        return JSONResponse(
            status_code=500, 
            content={"detail": f"Помилка розгортання: {e}. Перевірте лог."}
        )

# --- 8. ЕНДПОІНТ: Управління проектом ---

@app.post("/api/instance/control", response_class=JSONResponse)
async def handle_instance_control(
    instance_id: int = Form(...),
    action: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    instance = await db.get(Instance, instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Проект не знайдено.")
    
    if instance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас немає прав на управління цим проектом.")

    msg = ""
    try:
        if action == "stop":
            if instance.status == "suspended":
                raise HTTPException(status_code=400, detail="Проект вже зупинено.")
                
            if not provision.stop_instance(instance.container_name):
                raise HTTPException(status_code=500, detail="Помилка при зупинці контейнера.")
            instance.status = "suspended"
            msg = "Проект успішно зупинено."
        
        elif action == "start":
            if instance.status == "active":
                raise HTTPException(status_code=400, detail="Проект вже запущено.")

            if not provision.start_instance(instance.container_name):
                raise HTTPException(status_code=500, detail="Помилка при запуску контейнера.")
            instance.status = "active"
            msg = "Проект успішно запущено."
        
        else:
            raise HTTPException(status_code=400, detail="Неприпустима дія.")

        await db.commit()
    except Exception as e:
        await db.rollback()
        logging.error(f"Помилка управління інстансом {instance_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка: {e}")

    return JSONResponse(content={"message": msg, "new_status": instance.status})

@app.post("/api/instance/delete", response_class=JSONResponse)
async def handle_instance_delete(
    instance_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    instance = await db.get(Instance, instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Проект не знайдено.")
    
    if instance.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас немає прав на видалення цього проекту.")

    try:
        container_name = instance.container_name
        logging.warning(f"Користувач {current_user.email} ініціював видалення {container_name}")
        
        if not provision.delete_client_instance(container_name):
            raise HTTPException(status_code=500, detail="Помилка при видаленні ресурсів.")
        
        await db.delete(instance)
        await db.commit()
        logging.info(f"Запис про {container_name} видалено з БД.")

    except Exception as e:
        await db.rollback()
        logging.error(f"Помилка видалення інстанса {instance_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка: {e}")

    return JSONResponse(content={"message": "Проект успішно видалено."})


# --- 10. Адмінка SaaS (SUPER ADMIN) ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    _ = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db),
    message: str = None,
    type: str = "success"
):
    result = await db.execute(
        select(User, Instance)
        .outerjoin(Instance, User.id == Instance.user_id)
        .order_by(User.id)
    )
    clients = result.all()
    return templates_saas.get_admin_dashboard_html(clients, message, type)

@app.post("/admin/control")
async def admin_control_instance(
    instance_id: int = Form(...),
    action: str = Form(...),
    _ = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    instance = await db.get(Instance, instance_id)
    if not instance:
        return RedirectResponse(url="/admin?message=Екземпляр не знайдено&type=error", status_code=302)

    msg = ""
    try:
        if action == "stop":
            if not provision.stop_instance(instance.container_name):
                return RedirectResponse(url="/admin?message=Помилка при зупинці контейнера&type=error", status_code=302)
            instance.status = "suspended"
            msg = f"Клієнт {instance.subdomain} відключений."
            
        elif action == "start":
            if not provision.start_instance(instance.container_name):
                return RedirectResponse(url="/admin?message=Помилка при запуску контейнера&type=error", status_code=302)
            instance.status = "active"
            instance.next_payment_due = datetime.utcnow() + timedelta(days=30)
            msg = f"Клієнт {instance.subdomain} включений і подовжений."

        elif action == "update":
            if provision.recreate_container_with_new_code(instance.container_name):
                msg = f"Код клієнта {instance.subdomain} успішно оновлено!"
                instance.status = "active"
            else:
                return RedirectResponse(url="/admin?message=Помилка оновлення контейнера (див. логи)&type=error", status_code=302)

        elif action == "force_delete":
            if not provision.delete_client_instance(instance.container_name):
                return RedirectResponse(url="/admin?message=Помилка при видаленні ресурсів&type=error", status_code=302)
            
            await db.delete(instance)
            msg = f"Клієнт {instance.subdomain} безповоротно видалений."

        await db.commit()

    except Exception as e:
        await db.rollback()
        logging.error(f"Admin Action Error: {e}")
        return RedirectResponse(url=f"/admin?message=Помилка сервера: {e}&type=error", status_code=302)

    return RedirectResponse(url=f"/admin?message={msg}", status_code=302)


# --- 11. Налаштування Вітрини ---

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(username: str = Depends(check_admin_auth)):
    config = load_config()
    return templates_saas.get_settings_page_html(config)

@app.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    admin_id: str = Form(""), bot_token: str = Form(""),
    currency: str = Form("$"), price_light: str = Form("300"), price_full: str = Form("600"),
    custom_btn_text: str = Form(""),
    custom_btn_content: str = Form(""),
    username: str = Depends(check_admin_auth)
):
    current_config = load_config()
    current_config.update({
        "admin_id": admin_id.strip(), "bot_token": bot_token.strip(),
        "currency": currency.strip(), "price_light": price_light.strip(), "price_full": price_full.strip(),
        "custom_btn_text": custom_btn_text.strip(),
        "custom_btn_content": custom_btn_content.strip() 
    })
    save_config(current_config)
    return templates_saas.get_settings_page_html(current_config, "Збережено успішно!")

# --- 12. API Ендпоінти ---

@app.post("/api/lead")
async def handle_lead(name: str = Form(...), phone: str = Form(...), interest: str = Form(...)):
    config = load_config()
    if config.get('bot_token') and config.get('admin_id'):
        text = f"🚀 <b>Заявка з Вітрини (Restify)!</b>\n\n👤 {name}\n📱 {phone}\n💎 {interest}"
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"https://api.telegram.org/bot{config['bot_token']}/sendMessage", json={"chat_id": config['admin_id'], "text": text, "parse_mode": "HTML"})
            except Exception as e: 
                logging.error(f"TG Lead Error: {e}")
                return JSONResponse({"status": "error"}, status_code=500)
    return JSONResponse({"status": "ok"})


async def send_tg_notification(name, phone, plan, result_data):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    text = f"""
🚀 <b>НОВИЙ КЛІЄНТ (SaaS)!</b>

👤 {name}
📱 {phone}
💎 {plan}

✅ <b>САЙТ УСПІШНО РОЗГОРНУТО:</b>
Сайт: {result_data['url']}
Адмінка: {result_data['url']}/admin
Логін: {result_data['login']}
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

# --- 13. Запуск Сервера ---
if __name__ == "__main__":
    if not provision.SAAS_ADMIN_PASSWORD:
        logging.critical("КРИТИЧНА ПОМИЛКА: SAAS_ADMIN_PASSWORD не встановлено!")
    
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)