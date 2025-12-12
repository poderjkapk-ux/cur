import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from contextlib import asynccontextmanager

# --- 1. Налаштування підключення до ГОЛОВНОЇ БД (main_saas_db) ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Тимчасова заглушка для локальних тестів, якщо змінна не задана
    print("УВАГА: DATABASE_URL не знайдено. Переконайтеся, що змінні оточення задані.")

try:
    # Створюємо асинхронний двигун
    engine = create_async_engine(DATABASE_URL, echo=False)
    # Створюємо фабрику сесій
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    print(f"Помилка підключення до БД: {e}")


class Base(DeclarativeBase):
    pass

# --- 2. Моделі даних ---

class User(Base):
    """
    Модель Клієнта (Власника ресторану), який реєструється на сайті-вітрині.
    Використовує SaaS рішення (свій сайт + бот).
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Один користувач -> Багато екземплярів (проектів)
    instances = relationship("Instance", back_populates="user", cascade="all, delete-orphan")

class Instance(Base):
    """
    Модель Екземпляра (Сайту), який належить клієнту.
    """
    __tablename__ = "instances"
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False) 
    
    subdomain = Column(String(100), nullable=False, unique=True)
    url = Column(String(255), nullable=True) 
    
    container_name = Column(String(100), nullable=False, unique=True)
    admin_pass = Column(String(100), nullable=False) # Пароль для адмінки CRM
    
    status = Column(String(50), default="active") # active, suspended, cancelled
    next_payment_due = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="instances")

class Courier(Base):
    """
    Модель Кур'єра (для Uber-like системи).
    Реєструються через PWA або Telegram-бот.
    """
    __tablename__ = "couriers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    
    # Вхід за номером телефону
    phone = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # ID чату в Telegram для сповіщень
    telegram_chat_id = Column(String(50), nullable=True, unique=True)

    # --- НОВЕ ПОЛЕ ДЛЯ PUSH-СПОВІЩЕНЬ (FIREBASE) ---
    fcm_token = Column(String(255), nullable=True)
    # --------------------------------------------------

    # Статуси
    is_active = Column(Boolean, default=True)      # Чи може взагалі працювати (чи не забанений)
    is_online = Column(Boolean, default=False)     # Чи вийшов на зміну
    
    # Геопозиціонування
    lat = Column(Float, nullable=True)             # Широта
    lon = Column(Float, nullable=True)             # Довгота
    last_seen = Column(DateTime, default=datetime.utcnow) 
    
    created_at = Column(DateTime, default=datetime.utcnow)

class DeliveryPartner(Base):
    """
    Модель Партнера (Ресторан), який викликає кур'єрів.
    """
    __tablename__ = "delivery_partners"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False) # Назва закладу
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False) 
    hashed_password = Column(String(255), nullable=False)
    
    # ID чату в Telegram для сповіщень
    telegram_chat_id = Column(String(50), nullable=True, unique=True)

    is_active = Column(Boolean, default=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Видалення пов'язаних замовлень при видаленні партнера
    jobs = relationship("DeliveryJob", back_populates="partner", cascade="all, delete-orphan")

class DeliveryJob(Base):
    """
    Замовлення на доставку від Партнера для глобальних кур'єрів.
    """
    __tablename__ = "delivery_jobs"
    
    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey("delivery_partners.id"), nullable=False)
    
    # Деталі доставки
    customer_phone = Column(String(50), nullable=False)
    customer_name = Column(String(100), nullable=True)
    dropoff_address = Column(String(255), nullable=False)
    
    # Координати доставки
    dropoff_lat = Column(Float, nullable=True) 
    dropoff_lon = Column(Float, nullable=True)

    order_price = Column(Float, default=0.0) 
    delivery_fee = Column(Float, default=0.0) 
    comment = Column(String(255), nullable=True)

    # --- ОПЛАТА ---
    # prepaid (вже оплачено), cash (клієнт платить кур'єру), buyout (кур'єр викуповує замовлення)
    payment_type = Column(String(50), default="prepaid") 
    
    # Статус: pending, assigned, arrived_pickup, ready, picked_up, delivered, returning, cancelled
    status = Column(String(20), default="pending")
    
    # --- НОВЕ ПОЛЕ: ПОВЕРНЕННЯ КОШТІВ ---
    # True, якщо кур'єр має забрати готівку у клієнта і повернути її в ресторан
    is_return_required = Column(Boolean, default=False) 
    
    # Прив'язка кур'єра
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    
    # --- ЧАСОВІ МІТКИ (TIMESTAMPS) ---
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)  # Коли кур'єр прийняв
    
    # --- НОВЕ ПОЛЕ: КОЛИ КУР'ЄР ПРИБУВ В ЗАКЛАД ---
    arrived_at_pickup_at = Column(DateTime, nullable=True) 
    # ----------------------------------------------
    
    ready_at = Column(DateTime, nullable=True)     # Коли замовлення готове
    picked_up_at = Column(DateTime, nullable=True) # Коли забрав
    delivered_at = Column(DateTime, nullable=True) # Коли доставив
    
    # --- РЕЙТИНГ ---
    courier_rating = Column(Integer, nullable=True) # 1-5 зірок
    courier_review = Column(String(500), nullable=True) # Текст відгуку
    
    partner = relationship("DeliveryPartner", back_populates="jobs")
    courier = relationship("Courier")
    
    # --- НОВЕ: ЧАТ ---
    messages = relationship("ChatMessage", back_populates="job", cascade="all, delete-orphan")

class ChatMessage(Base):
    """
    Повідомлення в чаті між Партнером і Кур'єром в рамках одного замовлення.
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("delivery_jobs.id"), nullable=False)
    
    sender_role = Column(String(20), nullable=False) # 'partner' або 'courier'
    message = Column(String(1000), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("DeliveryJob", back_populates="messages")

class PendingVerification(Base):
    """
    Тимчасова таблиця для зв'язування сесії браузера з Telegram.
    Використовується при реєстрації через Deep Linking.
    """
    __tablename__ = "pending_verifications"
    
    token = Column(String(100), primary_key=True) # Унікальний UUID з посилання
    status = Column(String(50), default="waiting_contact") # waiting_contact, verified
    
    phone = Column(String(50), nullable=True)       # Номер, який надіслав юзер в бот
    telegram_chat_id = Column(String(50), nullable=True) # ID чату юзера
    
    created_at = Column(DateTime, default=datetime.utcnow)


# --- 3. Функції для роботи з БД ---

async def create_db_tables():
    """Створює всі таблиці в БД (якщо їх немає)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Залежність (Dependency) для FastAPI для отримання сесії БД."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()