import logging
import uvicorn
import os
import secrets
import httpx
import asyncio
import json
import uuid
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Запуск... Підключення до БД та створення таблиць...")
    await create_db_tables()
    
    # Завантаження конфігу
    load_config() 
    
    # --- ЗАПУСК TELEGRAM БОТА ---
    if bot_service.bot:
        asyncio.create_task(bot_service.start_bot())
        logging.info("Telegram Bot Polling started via bot_service.")
    else:
        logging.warning("TG_BOT_TOKEN not set, bot disabled.")
    
    # --- ЗАПУСК МОНІТОРИНГУ ЗАМОВЛЕНЬ ---
    asyncio.create_task(order_monitor.monitor_stale_orders(manager))
    logging.info("Order Monitor started.")
    
    logging.info("App started successfully.")
    yield
    logging.info("Shutdown.")

app = FastAPI(title="Restify SaaS Control Plane", lifespan=lifespan)

# --- ПІДКЛЮЧЕННЯ РОУТЕРА АДМІНКИ ДОСТАВКИ ---
app.include_router(admin_delivery.router)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==============================================================================
# UTILS & HELPERS
# ==============================================================================

# --- Розрахунок дистанції (Haversine) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Обчислює відстань у кілометрах між двома точками (Haversine formula).
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    try:
        # Конвертуємо градуси в радіани
        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])

        # Формула гаверсинуса
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 # Радіус Землі в кілометрах
        return round(c * r, 2)
    except Exception:
        return None

# --- Геокодинг з кешуванням (Memory Cache) ---
GEOCODE_CACHE = {}

async def geocode_address(address: str):
    """Перетворює адресу в координати через Nominatim (OSM) з кешуванням."""
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
                GEOCODE_CACHE[address] = res # Зберігаємо в кеш
                return res
        except Exception as e:
            logging.error(f"Geocoding Error: {e}")
            
    return None, None

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
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

# --- Config Logic ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "admin_id": "", "bot_token": "", "price_light": "300", 
    "price_full": "600", "currency": "$", 
    "custom_btn_text": "", "custom_btn_content": ""
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG.copy()

def save_config(new_config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
    except Exception as e:
        logging.error(f"Config save error: {e}")

# ==============================================================================
# GENERAL ROUTES & SAAS LOGIC
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return HTMLResponse(content=templates_saas.get_landing_page_html(load_config()))

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
         return JSONResponse(status_code=400, content={"detail": "Номер телефону не підтверджено через Telegram."})

    if await auth.get_user_by_email(db, email):
        return JSONResponse(status_code=400, content={"detail": "Цей email вже зареєстрований."})

    hashed_password = auth.get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.delete(verif)
    
    await db.commit()
    await db.refresh(new_user)
    
    return JSONResponse(content={"detail": "User created successfully."})

# ==============================================================================
# COURIER LOGIC (AUTH, API, WEBSOCKET)
# ==============================================================================

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
         return JSONResponse(status_code=400, content={"detail": "Номер телефону не підтверджено через Telegram."})

    if await auth.get_courier_by_phone(db, verif.phone):
        return JSONResponse(status_code=400, content={"detail": "Цей номер телефону вже зареєстрований"})
    
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
        return RedirectResponse("/courier/login?message=Невірні дані або акаунт заблоковано", status_code=302)
    
    token = auth.create_access_token(data={"sub": f"courier:{courier.phone}"})
    resp = RedirectResponse("/courier/app", status_code=302)
    is_secure = ROOT_DOMAIN.startswith("https") 
    resp.set_cookie(key="courier_token", value=token, httponly=True, max_age=604800, samesite="lax", secure=is_secure)
    return resp

@app.get("/courier/app", response_class=HTMLResponse)
async def courier_pwa_main(courier: Courier = Depends(auth.get_current_courier)):
    return templates_courier.get_courier_pwa_html(courier)

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
    logging.info(f"[PUSH] Кур'єр {courier.id} ({courier.name}) оновив FCM токен: {token[:15]}...")
    courier.fcm_token = token
    await db.commit()
    return JSONResponse({"status": "updated"})

# --- Firebase Service Worker ---
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
    messaging.onBackgroundMessage(function(payload) {
      self.registration.showNotification(payload.notification.title, {
        body: payload.notification.body,
        icon: 'https://cdn-icons-png.flaticon.com/512/7542/7542190.png', 
        tag: 'new-order', data: { url: '/courier/app' } 
      });
    });
    self.addEventListener('notificationclick', function(event) {
        event.notification.close();
        event.waitUntil(clients.matchAll({type: 'window', includeUncontrolled: true}).then(windowClients => {
            for (var i = 0; i < windowClients.length; i++) {
                var client = windowClients[i];
                if (client.url.indexOf('/courier/app') !== -1 && 'focus' in client) { return client.focus(); }
            }
            if (clients.openWindow) { return clients.openWindow('/courier/app'); }
        }));
    });
    """
    return Response(content=content, media_type="application/javascript")

# --- Push Helper ---
async def send_push_to_couriers(courier_tokens: List[str], title: str, body: str):
    if not courier_tokens: return
    try:
        for token in courier_tokens:
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            )
            messaging.send(msg) 
    except Exception as e:
        logging.error(f"Push Error: {e}")

# =======================================================================
#  OPTIMIZED COURIER WEBSOCKET (Fixes Offline Sync + Distance)
# =======================================================================
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
    
    # --- СИНХРОНІЗАЦІЯ (SYNC PENDING ORDERS) ---
    try:
        # 1. Беремо всі замовлення "в очікуванні" і завантажуємо партнерів
        result = await db.execute(
            select(DeliveryJob)
            .options(joinedload(DeliveryJob.partner))
            .where(DeliveryJob.status == "pending")
        )
        pending_jobs = result.scalars().all()
        
        for job in pending_jobs:
            if not job.partner: continue
            
            # 2. Швидко геокодимо партнера (використовуємо кеш)
            rest_lat, rest_lon = await geocode_address(job.partner.address)
            
            # 3. Рахуємо дистанцію
            dist_to_rest = calculate_distance(courier.lat, courier.lon, rest_lat, rest_lon)
            
            # 4. ФІЛЬТР: Якщо кур'єр далі 20 км від старого замовлення, не показуємо (оптимізація)
            if dist_to_rest is not None and dist_to_rest > 20: 
                continue

            dist_rest_to_client = "?" # Можна порахувати, якщо є координати клієнта
            if job.dropoff_lat and job.dropoff_lon and rest_lat and rest_lon:
                val = calculate_distance(rest_lat, rest_lon, job.dropoff_lat, job.dropoff_lon)
                if val: dist_rest_to_client = val

            payment_label = {
                "prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"
            }.get(job.payment_type, "Оплата")

            job_data = {
                "id": job.id,
                "address": job.dropoff_address,
                "restaurant": job.partner.name,
                "restaurant_address": job.partner.address,
                "fee": job.delivery_fee,
                "price": job.order_price,
                "comment": f"[{payment_label}] {job.comment or ''}",
                "dist_to_rest": dist_to_rest if dist_to_rest is not None else "?",
                "dist_rest_to_client": dist_rest_to_client
            }
            # Відправляємо одразу
            await websocket.send_json({"type": "new_order", "data": job_data})
            
    except Exception as e:
        logging.error(f"Sync error for courier {courier.id}: {e}")

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

@app.get("/api/courier/history")
async def get_courier_history(
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
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
    job_id: int = Form(...), status: str = Form(...),
    courier: Courier = Depends(auth.get_current_courier), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.courier_id != courier.id:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    job.status = status
    now = datetime.utcnow()
    if status == "picked_up": job.picked_up_at = now
    elif status == "delivered": job.delivered_at = now
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
            "type": "order_update", "job_id": job.id, "status": status,
            "status_text": status, "status_color": color,
            "courier_name": courier.name, "message": msg_text
        })
        partner = await db.get(DeliveryPartner, job.partner_id)
        if partner and partner.telegram_chat_id:
            tg_text = f"📦 <b>Замовлення #{job.id}</b>\n{msg_text}\nКур'єр: {courier.name}"
            asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))

    return JSONResponse({"status": "ok", "new_status": status})

# =======================================================================
# FIX: ACCEPT ORDER WITH VALIDATION & NO DB LOCK ERROR
# =======================================================================
@app.post("/api/courier/accept_order")
async def courier_accept_order(
    job_id: int = Form(...),
    courier: Courier = Depends(auth.get_current_courier),
    db: AsyncSession = Depends(get_db)
):
    # 1. Блокируем ТОЛЬКО строку заказа (без JOIN, чтобы не было ошибки FOR UPDATE)
    result = await db.execute(
        select(DeliveryJob).where(DeliveryJob.id == job_id).with_for_update()
    )
    job = result.scalar_one_or_none()

    if not job:
        return JSONResponse({"status": "error", "message": "Замовлення не знайдено"}, status_code=404)
    
    if job.status != "pending":
        return JSONResponse({"status": "error", "message": "Це замовлення вже забрав інший кур'єр"}, status_code=409)

    # 2. Завантажуємо партнера окремо для перевірки дистанції
    partner = await db.get(DeliveryPartner, job.partner_id)
    if not partner:
         return JSONResponse({"status": "error", "message": "Помилка даних партнера"}, status_code=500)

    # --- ГЕО-ВАЛІДАЦІЯ (Ліміт 20 км) ---
    partner_lat, partner_lon = await geocode_address(partner.address)
    
    if partner_lat and partner_lon and courier.lat and courier.lon:
        dist = calculate_distance(courier.lat, courier.lon, partner_lat, partner_lon)
        MAX_ACCEPT_DISTANCE_KM = 20.0 
        
        if dist is not None and dist > MAX_ACCEPT_DISTANCE_KM:
             return JSONResponse({
                 "status": "error", 
                 "message": f"Ви занадто далеко ({dist} км). Максимальна відстань: {MAX_ACCEPT_DISTANCE_KM} км."
             }, status_code=400)
    # -----------------------------------

    job.status = "assigned"
    job.courier_id = courier.id
    job.accepted_at = datetime.utcnow()
    await db.commit()

    # Сповіщаємо партнера
    await manager.notify_partner(job.partner_id, {
        "type": "order_update", "job_id": job.id, "status": "assigned",
        "status_text": "assigned", "status_color": "#fef08a", 
        "courier_name": courier.name, "message": f"🚴 Кур'єр {courier.name} прийняв замовлення! Очікуйте."
    })

    if partner.telegram_chat_id:
        tg_text = f"🚴 <b>Замовлення #{job.id} прийнято!</b>\nКур'єр: {courier.name}\nТелефон: {courier.phone}"
        asyncio.create_task(bot_service.send_telegram_message(partner.telegram_chat_id, tg_text))

    return JSONResponse({"status": "ok", "message": "Замовлення прийнято! Рушайте до закладу."})

# --- External API ---
@app.get("/api/external/couriers/nearby")
async def get_nearby_couriers(
    lat: float, lon: float, radius_km: float = 5.0, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Courier).where(Courier.is_online == True))
    couriers = result.scalars().all()
    data = []
    for c in couriers:
        if c.lat and c.lon:
            data.append({"id": c.id, "name": c.name, "lat": c.lat, "lon": c.lon})
    return JSONResponse(data)

# ==============================================================================
# PARTNER LOGIC
# ==============================================================================

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
        return templates_partner.get_partner_auth_html(is_register=True, message="Цей email вже зареєстрований")
    
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
        return templates_partner.get_partner_auth_html(is_register=False, message="Невірний email або пароль")
    
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
    result = await db.execute(select(DeliveryJob).where(DeliveryJob.partner_id == partner.id).order_by(DeliveryJob.id.desc()))
    return templates_partner.get_partner_dashboard_html(partner, result.scalars().all())

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

# =======================================================================
# OPTIMIZED CREATE ORDER (Handles 1000 Couriers via Async Tasks Loop)
# =======================================================================
@app.post("/api/partner/create_order")
async def create_partner_order(
    dropoff_address: str = Form(...), customer_phone: str = Form(...), customer_name: str = Form(""),
    order_price: float = Form(0.0), delivery_fee: float = Form(50.0), comment: str = Form(""),
    payment_type: str = Form("prepaid"), db: AsyncSession = Depends(get_db), 
    partner: DeliveryPartner = Depends(get_current_partner)
):
    # 1. Geocode Client
    client_lat, client_lon = await geocode_address(dropoff_address)
    
    # 2. Geocode Partner (Once)
    rest_lat, rest_lon = await geocode_address(partner.address)

    # 3. Create Job
    job = DeliveryJob(
        partner_id=partner.id, dropoff_address=dropoff_address, 
        dropoff_lat=client_lat, dropoff_lon=client_lon,
        customer_phone=customer_phone, customer_name=customer_name,
        order_price=order_price, delivery_fee=delivery_fee,
        comment=comment, payment_type=payment_type, status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 4. Get ONLY Online Couriers
    res = await db.execute(select(Courier).where(Courier.is_online == True))
    online_couriers = res.scalars().all()

    payment_label = {"prepaid": "✅ Оплачено", "cash": "💵 Готівка", "buyout": "💰 Викуп"}.get(payment_type, "Оплата")

    # 5. ASYNC BROADCAST FUNCTION
    async def notify_courier_async(courier):
        dist_to_rest = calculate_distance(courier.lat, courier.lon, rest_lat, rest_lon)
        
        # FILTER: Don't notify if > 20 km (Optimization)
        if dist_to_rest is not None and dist_to_rest > 20: 
            return 

        dist_rest_to_client = calculate_distance(rest_lat, rest_lon, client_lat, client_lon)

        personal_data = {
            "id": job.id, "address": dropoff_address, 
            "restaurant": partner.name, "restaurant_address": partner.address,
            "fee": delivery_fee, "price": order_price, "comment": f"[{payment_label}] {comment}",
            "dist_to_rest": dist_to_rest if dist_to_rest is not None else "?",
            "dist_rest_to_client": dist_rest_to_client if dist_rest_to_client is not None else "?"
        }
        
        # Fire WS
        await manager.notify_courier(courier.id, {"type": "new_order", "data": personal_data})
        
        # Fire Push
        if courier.fcm_token:
            d_msg = f"{dist_to_rest} км" if dist_to_rest else ""
            await send_push_to_couriers([courier.fcm_token], "🔥 Нове замовлення!", f"💰 {delivery_fee} грн | {d_msg}")

    # 6. Execute notifications independently (Safe loop)
    if online_couriers:
        for c in online_couriers:
            asyncio.create_task(notify_courier_async(c))

    # 7. Telegram Broadcast (General)
    res_tg = await db.execute(select(Courier).where(Courier.is_online == True, Courier.telegram_chat_id != None))
    for c in res_tg.scalars().all():
        msg = f"🔥 <b>Нове замовлення!</b>\n💰 {delivery_fee} грн\n📍 {partner.name}"
        asyncio.create_task(bot_service.send_telegram_message(c.telegram_chat_id, msg))

    return RedirectResponse("/partner/dashboard", status_code=303)

@app.post("/api/partner/order_ready")
async def partner_order_ready(
    job_id: int = Form(...), partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id: return JSONResponse({"status": "error"}, 404)
    job.status = "ready"
    job.ready_at = datetime.utcnow()
    await db.commit()
    if job.courier_id:
        await manager.notify_courier(job.courier_id, {"type": "job_update", "status": "ready"})
        courier = await db.get(Courier, job.courier_id)
        if courier.fcm_token: await send_push_to_couriers([courier.fcm_token], "🍳 Готово!", "Забирайте замовлення")
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/cancel_order")
async def partner_cancel_order(
    job_id: int = Form(...), partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if not job or job.partner_id != partner.id: return JSONResponse({"status": "error"}, 404)
    if job.status == "assigned" and job.accepted_at:
        if (datetime.utcnow() - job.accepted_at) > timedelta(minutes=3):
            return JSONResponse({"status": "error", "message": "Запізно скасовувати (ліміт 3 хв)"}, 400)
    job.status = "cancelled"
    await db.commit()
    return JSONResponse({"status": "ok"})

@app.post("/api/partner/rate_courier")
async def partner_rate_courier(
    job_id: int = Form(...), rating: int = Form(...), review: str = Form(""), 
    partner: DeliveryPartner = Depends(get_current_partner), db: AsyncSession = Depends(get_db)
):
    job = await db.get(DeliveryJob, job_id)
    if job and job.partner_id == partner.id:
        job.courier_rating = rating; job.courier_review = review
        await db.commit()
    return JSONResponse({"status": "ok"})

@app.websocket("/ws/partner")
async def websocket_partner_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    token = websocket.cookies.get("partner_token")
    if not token: await websocket.close(); return
    try:
        pid = int(auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])["sub"].split(":")[1])
        await manager.connect_partner(websocket, pid)
        while True: await websocket.receive_text()
    except: manager.disconnect_partner(pid)

# ==============================================================================
# SAAS INSTANCE CONTROL API
# ==============================================================================

@app.post("/api/create-instance")
async def handle_instance_creation(
    name: str = Form(...), phone: str = Form(...), client_bot_token: str = Form(...),
    admin_bot_token: str = Form(...), admin_chat_id: str = Form(...), plan: str = Form("pro"),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    try:
        c_name = "".join(x for x in name.lower() if x.isalnum() or x=='-')[:20] or "client"
        sub = f"{c_name}.{ROOT_DOMAIN}"
        if (await db.execute(select(Instance).where(Instance.subdomain == sub))).scalar():
            return JSONResponse(status_code=400, content={"detail": "Subdomain busy"})
        
        res = provision.create_new_client_instance(c_name, ROOT_DOMAIN, client_bot_token, admin_bot_token, admin_chat_id)
        db.add(Instance(
            user_id=current_user.id, subdomain=res["subdomain"], url=res["url"],
            container_name=res["container_name"], admin_pass=res["password"],
            next_payment_due=datetime.utcnow() + timedelta(days=30)
        ))
        await db.commit()
        asyncio.create_task(send_tg_notification(name, phone, plan, res))
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/instance/control")
async def handle_instance_control(
    instance_id: int = Form(...), action: str = Form(...),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    i = await db.get(Instance, instance_id)
    if not i or i.user_id != current_user.id: raise HTTPException(404)
    if action == "stop": provision.stop_instance(i.container_name); i.status = "suspended"
    elif action == "start": provision.start_instance(i.container_name); i.status = "active"
    await db.commit()
    return JSONResponse({"new_status": i.status})

@app.post("/api/instance/delete")
async def handle_instance_delete(
    instance_id: int = Form(...), db: AsyncSession = Depends(get_db), current_user: User = Depends(auth.get_current_user)
):
    i = await db.get(Instance, instance_id)
    if not i or i.user_id != current_user.id: raise HTTPException(404)
    provision.delete_client_instance(i.container_name)
    await db.delete(i)
    await db.commit()
    return JSONResponse({"message": "Deleted"})

# --- ADMIN API ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)):
    res = await db.execute(select(User, Instance).outerjoin(Instance, User.id == Instance.user_id))
    return templates_saas.get_admin_dashboard_html(res.all())

@app.post("/admin/control")
async def admin_control(
    instance_id: int = Form(...), action: str = Form(...), db: AsyncSession = Depends(get_db), _ = Depends(check_admin_auth)
):
    i = await db.get(Instance, instance_id)
    if action == "stop": provision.stop_instance(i.container_name); i.status = "suspended"
    elif action == "start": provision.start_instance(i.container_name); i.status = "active"
    elif action == "update": provision.recreate_container_with_new_code(i.container_name)
    elif action == "force_delete": provision.delete_client_instance(i.container_name); await db.delete(i)
    await db.commit()
    return RedirectResponse("/admin", 302)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(_ = Depends(check_admin_auth)):
    return templates_saas.get_settings_page_html(load_config())

@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, _ = Depends(check_admin_auth)):
    form = await request.form()
    save_config({k: v for k, v in form.items()})
    return templates_saas.get_settings_page_html(load_config(), "Saved")

# --- OTHER HELPERS ---
@app.post("/api/lead")
async def handle_lead(name: str = Form(...), phone: str = Form(...), interest: str = Form(...)):
    conf = load_config()
    if conf.get('bot_token') and conf.get('admin_id'):
        text = f"🚀 Lead!\n{name}\n{phone}\n{interest}"
        async with httpx.AsyncClient() as c:
            await c.post(f"https://api.telegram.org/bot{conf['bot_token']}/sendMessage", json={"chat_id": conf['admin_id'], "text": text})
    return JSONResponse({"status": "ok"})

async def send_tg_notification(name, phone, plan, result_data):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    text = f"🚀 NEW CLIENT!\n{name} | {phone}\nURL: {result_data['url']}"
    async with httpx.AsyncClient() as c:
        await c.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": text})

if __name__ == "__main__":
    if not provision.SAAS_ADMIN_PASSWORD:
        logging.critical("SAAS_ADMIN_PASSWORD not set!")
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)