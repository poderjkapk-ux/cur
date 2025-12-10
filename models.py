import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from contextlib import asynccontextmanager

# --- 1. Настройка подключения к ГЛАВНОЙ БД (main_saas_db) ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Временная заглушка для локальных тестов, если переменная не задана
    print("ВНИМАНИЕ: DATABASE_URL не найден. Убедитесь, что переменные окружения заданы.")

try:
    # Создаем асинхронный движок
    engine = create_async_engine(DATABASE_URL, echo=False)
    # Создаем фабрику сессий
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    print(f"Ошибка подключения к БД: {e}")


class Base(DeclarativeBase):
    pass

# --- 2. Модели данных ---

class User(Base):
    """
    Модель Клиента (Владельца ресторана), который регистрируется на сайте-витрине.
    Использует SaaS решение (свой сайт + бот).
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Один пользователь -> Много экземпляров (проектов)
    instances = relationship("Instance", back_populates="user", cascade="all, delete-orphan")

class Instance(Base):
    """
    Модель Экземпляра (Сайта), который принадлежит клиенту.
    """
    __tablename__ = "instances"
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False) 
    
    subdomain = Column(String(100), nullable=False, unique=True)
    url = Column(String(255), nullable=True) 
    
    container_name = Column(String(100), nullable=False, unique=True)
    admin_pass = Column(String(100), nullable=False) # Пароль для админки CRM
    
    status = Column(String(50), default="active") # active, suspended, cancelled
    next_payment_due = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="instances")

class Courier(Base):
    """
    Модель Курьера (для Uber-like системы).
    Регистрируются через PWA или Telegram-бот.
    """
    __tablename__ = "couriers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    
    # Вход по номеру телефона
    phone = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # ID чата в Telegram для уведомлений
    telegram_chat_id = Column(String(50), nullable=True, unique=True)

    # --- НОВОЕ ПОЛЕ ДЛЯ PUSH-УВЕДОМЛЕНИЙ (FIREBASE) ---
    fcm_token = Column(String(255), nullable=True)
    # --------------------------------------------------

    # Статусы
    is_active = Column(Boolean, default=True)      # Может ли вообще работать (не забанен ли)
    is_online = Column(Boolean, default=False)     # Вышел ли на смену
    
    # Геопозиционирование
    lat = Column(Float, nullable=True)             # Широта
    lon = Column(Float, nullable=True)             # Долгота
    last_seen = Column(DateTime, default=datetime.utcnow) 
    
    created_at = Column(DateTime, default=datetime.utcnow)

class DeliveryPartner(Base):
    """
    Модель Партнера (Ресторан), который вызывает курьеров.
    """
    __tablename__ = "delivery_partners"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False) # Название заведения
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False) 
    hashed_password = Column(String(255), nullable=False)
    
    # ID чата в Telegram для уведомлений
    telegram_chat_id = Column(String(50), nullable=True, unique=True)

    is_active = Column(Boolean, default=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    jobs = relationship("DeliveryJob", back_populates="partner")

class DeliveryJob(Base):
    """
    Заказ на доставку от Партнера для глобальных курьеров.
    """
    __tablename__ = "delivery_jobs"
    
    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey("delivery_partners.id"), nullable=False)
    
    # Детали доставки
    customer_phone = Column(String(50), nullable=False)
    customer_name = Column(String(100), nullable=True)
    dropoff_address = Column(String(255), nullable=False)
    
    # Координаты доставки
    dropoff_lat = Column(Float, nullable=True) 
    dropoff_lon = Column(Float, nullable=True)

    order_price = Column(Float, default=0.0) 
    delivery_fee = Column(Float, default=0.0) 
    comment = Column(String(255), nullable=True)
    
    # Статус: pending, assigned, picked_up, delivered, cancelled
    status = Column(String(20), default="pending")
    
    # Привязка курьера
    courier_id = Column(Integer, ForeignKey("couriers.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    partner = relationship("DeliveryPartner", back_populates="jobs")
    courier = relationship("Courier")

class PendingVerification(Base):
    """
    Тимчасова таблиця для зв'язування сесії браузера з Telegram.
    Використовується при реєстрації через Deep Linking.
    """
    __tablename__ = "pending_verifications"
    
    token = Column(String(100), primary_key=True) # Унікальний UUID з посилання
    status = Column(String(50), default="waiting_contact") # waiting_contact, verified
    
    phone = Column(String(50), nullable=True)       # Номер, який прислав юзер в бот
    telegram_chat_id = Column(String(50), nullable=True) # ID чату юзера
    
    created_at = Column(DateTime, default=datetime.utcnow)


# --- 3. Функции для работы с БД ---

async def create_db_tables():
    """Создает все таблицы в БД (если их нет)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Зависимость (Dependency) для FastAPI для получения сессии БД."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()