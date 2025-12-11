import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
from contextlib import asynccontextmanager

# --- 1. Настройка подключения к ГЛАВНОЙ БД (main_saas_db) ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен для сайта-витрины (Lander)!")

try:
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    print(f"Ошибка подключения к БД: {e}")
    exit()


class Base(DeclarativeBase):
    pass

# --- 2. Модели данных ---

class User(Base):
    """
    Модель Клиента (Владельца), который регистрируется на сайте-витрине.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- ИЗМЕНЕНИЕ: Один пользователь -> Много экземпляров ---
    # `uselist=False` удалено. Теперь это список.
    instances = relationship("Instance", back_populates="user", cascade="all, delete-orphan")

class Instance(Base):
    """
    Модель Экземпляра (Сайта), который принадлежит клиенту.
    """
    __tablename__ = "instances"
    
    id = Column(Integer, primary_key=True)
    
    # --- ИЗМЕНЕНИЕ: `unique=True` удалено ---
    # Один пользователь может иметь много ID здесь.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=False) 
    
    subdomain = Column(String(100), nullable=False, unique=True)
    
    # Поле URL, которое мы добавили в прошлый раз
    url = Column(String(255), nullable=True) 
    
    container_name = Column(String(100), nullable=False, unique=True)
    admin_pass = Column(String(100), nullable=False) # Пароль для админки CRM (чтобы клиент мог его посмотреть)
    
    status = Column(String(50), default="active") # active, suspended, cancelled
    next_payment_due = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- ИЗМЕНЕНИЕ: `back_populates` указывает на `instances` (множественное число) ---
    user = relationship("User", back_populates="instances")


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
