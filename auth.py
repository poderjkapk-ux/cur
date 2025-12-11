import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Cookie # <-- 1. Импортируем Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Импортируем User и зависимости БД
from models import User, async_session_maker, get_db

# --- 1. Настройка шифрования паролей ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 2. Настройка JWT-токенов ---
# Ключ должен храниться в переменных окружения в production
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 дней

# Схема OAuth2 для страницы /login (указывает FastAPI, где эндпоинт для получения токена)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- 3. Функции работы с паролями ---
def verify_password(plain_password, hashed_password):
    """Проверяет, совпадает ли пароль с хэшем."""
    # ОБРЕЗАЕМ ПАРОЛЬ ДО 72 БАЙТ ДЛЯ BCRYPT
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    # Декодируем обратно в строку, игнорируя ошибки, если обрезали пол-символа
    password_for_verify = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.verify(password_for_verify, hashed_password)

def get_password_hash(password):
    """Создает хэш пароля."""
    # ОБРЕЗАЕМ ПАРОЛЬ ДО 72 БАЙТ ДЛЯ BCRYPT
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    # Декодируем обратно в строку, игнорируя ошибки, если обрезали пол-символа
    password_for_hash = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.hash(password_for_hash)

# --- 4. Функции работы с JWT ---
def create_access_token(data: dict):
    """Создает JWT-токен."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(db: AsyncSession, email: str):
    """Находит пользователя по email в БД."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, email: str, password: str):
    """
    Проверяет email и пароль. Возвращает объект User в случае успеха.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None # Пользователь не найден
    if not verify_password(password, user.hashed_password):
        return None # Неверный пароль
    return user

async def get_current_user_from_token(token: str, db_session_factory):
    """
    Извлекает пользователя из JWT токена (используется для проверки cookie).
    """
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None # Невалидный токен

    # Создаем новую сессию для этой асинхронной проверки
    async with db_session_factory() as db:
        user = await get_user_by_email(db, email)
        if user is None:
            return None
        return user

async def get_current_user(
    token: str | None = Cookie(default=None, alias="access_token"), # <-- 2. Меняем зависимость
    db: AsyncSession = Depends(get_db)
):
    """
    Зависимость (Dependency) для FastAPI, которая требует валидный токен
    из cookie и возвращает объект User. Используется для защиты /dashboard.
    """
    if token is None: # <-- 3. Добавляем проверку, что cookie вообще есть
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (missing cookie)",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = await get_current_user_from_token(token, async_session_maker)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user