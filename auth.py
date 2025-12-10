import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Импортируем User, Courier и зависимости БД
from models import User, Courier, async_session_maker, get_db

# --- 1. Настройка шифрования паролей ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 2. Настройка JWT-токенов ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 дней

# --- 2.1 Настройка Admin Auth (Moved from app.py) ---
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "supersecret")
security = HTTPBasic()

# Схема OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- 3. Функции работы с паролями ---
def verify_password(plain_password, hashed_password):
    """Проверяет, совпадает ли пароль с хэшем."""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    password_for_verify = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.verify(password_for_verify, hashed_password)

def get_password_hash(password):
    """Создает хэш пароля."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
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

async def get_current_user_from_token(token: str, db_session_factory):
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        if email.startswith("courier:"):
            return None
    except JWTError:
        return None

    async with db_session_factory() as db:
        user = await get_user_by_email(db, email)
        return user

# ==========================================
# ЛОГИКА ДЛЯ ВЛАДЕЛЬЦЕВ РЕСТОРАНОВ (USERS)
# ==========================================

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    token: str | None = Cookie(default=None, alias="access_token"),
    db: AsyncSession = Depends(get_db)
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (missing cookie)",
        )
        
    user = await get_current_user_from_token(token, async_session_maker)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user

# ==========================================
# ЛОГИКА ДЛЯ КУРЬЕРОВ (COURIERS)
# ==========================================

async def get_courier_by_phone(db: AsyncSession, phone: str):
    result = await db.execute(select(Courier).where(Courier.phone == phone))
    return result.scalar_one_or_none()

async def authenticate_courier(db: AsyncSession, phone: str, password: str):
    courier = await get_courier_by_phone(db, phone)
    if not courier:
        return None
    if not courier.is_active:
        return None
        
    if not verify_password(password, courier.hashed_password):
        return None
    return courier

async def get_current_courier(
    token: str | None = Cookie(default=None, alias="courier_token"), 
    db: AsyncSession = Depends(get_db)
):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Courier not authenticated",
        )
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if not sub or not sub.startswith("courier:"):
            raise HTTPException(status_code=401, detail="Invalid token type")
        phone = sub.split(":")[1]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    courier = await get_courier_by_phone(db, phone)
    if not courier:
        raise HTTPException(status_code=401, detail="Courier user not found")
        
    return courier

# ==========================================
# ЛОГИКА ДЛЯ ADMIN (Moved from app.py to fix circular import)
# ==========================================
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