
import os
import logging
import secrets
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from sqlalchemy import select
from models import Courier, DeliveryPartner, PendingVerification, async_session_maker
from auth import get_password_hash

# --- Налаштування ---
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

# Формуємо базовий URL сайту для кнопок повернення
ROOT_DOMAIN = os.environ.get("ROOT_DOMAIN", "restify.site")
SITE_URL = f"https://{ROOT_DOMAIN}" if not ROOT_DOMAIN.startswith("http") else ROOT_DOMAIN

# Ініціалізація бота
bot = Bot(token=TG_BOT_TOKEN) if TG_BOT_TOKEN else None
dp = Dispatcher()

# --- Клавіатури ---

# Кнопка для відправки контакту (зникає після натискання)
kb_contact = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📱 Надіслати мій номер телефону", request_contact=True)]
], resize_keyboard=True, one_time_keyboard=True)

# Кнопка вибору ролі (якщо користувач просто знайшов бота в пошуку)
kb_roles = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🚴 Я Кур'єр"), KeyboardButton(text="🏪 Я Заклад")]
], resize_keyboard=True)

# --- Хендлери (Обробники команд) ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Обробляє команду /start.
    Підтримує параметри: 
    - /start reg_xxxx (реєстрація через сайт)
    - /start partner (з адмінки закладу)
    - /start courier (з PWA кур'єра)
    """
    args = message.text.split()
    chat_id = str(message.chat.id)
    
    # --- Сценарій 1: Реєстрація через сайт (Deep Linking) ---
    if len(args) > 1 and args[1].startswith('reg_'):
        # Отримуємо чистий токен (UUID) без префікса 'reg_'
        token = args[1].replace('reg_', '')
        
        async with async_session_maker() as db:
            # Шукаємо запис, який СТВОРИВ САЙТ (app.py)
            verif = await db.get(PendingVerification, token)
            
            if verif:
                # Оновлюємо запис: прив'язуємо Telegram ID і ставимо статус "чекаємо контакт"
                verif.telegram_chat_id = chat_id
                verif.status = "waiting_contact"
                await db.commit()

                await message.answer(
                    "🔐 <b>Підтвердження реєстрації</b>\n\n"
                    "Для завершення реєстрації на сайті, натисніть кнопку внизу, "
                    "щоб підтвердити свій номер телефону ⬇️", 
                    reply_markup=kb_contact,
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Помилка: Невірний або застарілий токен реєстрації.")
        return

    # --- Сценарій 2: Перехід із адмінки закладу ---
    elif len(args) > 1 and args[1] == 'partner':
        await message.answer(
            "👋 Вітаю! Щоб підключити сповіщення про замовлення для вашого закладу, "
            "натисніть кнопку внизу ⬇️", 
            reply_markup=kb_contact
        )
        
    # --- Сценарій 3: Перехід із додатка кур'єра ---
    elif len(args) > 1 and args[1] == 'courier':
        await message.answer(
            "🚴 Вітаю! Щоб активувати акаунт кур'єра та отримувати замовлення, "
            "натисніть кнопку внизу ⬇️", 
            reply_markup=kb_contact
        )
        
    # --- Сценарій 4: Звичайний старт (без параметрів) ---
    else:
        await message.answer(
            "Вітаю в Restify Delivery! 👋\nБудь ласка, оберіть вашу роль:", 
            reply_markup=kb_roles
        )

@dp.message(F.text == "🚴 Я Кур'єр")
async def role_courier(message: types.Message):
    await message.answer("Щоб зареєструватися або увійти, надішліть номер:", reply_markup=kb_contact)

@dp.message(F.text == "🏪 Я Заклад")
async def role_partner(message: types.Message):
    await message.answer("Щоб підключити сповіщення, надішліть номер:", reply_markup=kb_contact)

@dp.message(F.contact)
async def handle_contact(message: types.Message):
    """
    Головна функція: отримує контакт.
    Пріоритет 1: Перевірка активної сесії реєстрації на сайті.
    Пріоритет 2: Пошук існуючих користувачів (Courier/Partner).
    """
    contact = message.contact
    # Очищаємо номер від зайвих символів (наприклад, +)
    phone = contact.phone_number.replace('+', '')
    chat_id = str(message.chat.id)
    user_name = f"{contact.first_name} {contact.last_name or ''}".strip()
    
    async with async_session_maker() as db:
        
        # --- 1. ПЕРЕВІРКА АКТИВНОЇ РЕЄСТРАЦІЇ (PendingVerification) ---
        # Шукаємо запис для цього chat_id, де ми чекаємо контакт
        pending_result = await db.execute(
            select(PendingVerification)
            .where(PendingVerification.telegram_chat_id == chat_id)
            .where(PendingVerification.status == "waiting_contact")
            .order_by(PendingVerification.created_at.desc())
        )
        pending = pending_result.scalars().first()

        if pending:
            # Це процес реєстрації на сайті!
            pending.phone = phone
            pending.status = "verified" # Сайт побачить цей статус і дозволить реєстрацію
            await db.commit()
            
            await message.answer(
                "✅ <b>Номер успішно підтверджено!</b>\n\n"
                "Тепер поверніться на сайт у браузері — форма реєстрації розблокується автоматично.", 
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            return

        # --- 2. ЛОГІКА ДЛЯ ПАРТНЕРА (ЗАКЛАДУ) ---
        partner = (await db.execute(select(DeliveryPartner).where(DeliveryPartner.phone == phone))).scalar_one_or_none()
        
        if partner:
            partner.telegram_chat_id = chat_id
            await db.commit()
            
            kb_back_partner = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Повернутися в Кабінет", url=f"{SITE_URL}/partner/dashboard")]
            ])
            
            await message.answer(
                f"✅ Заклад <b>{partner.name}</b> успішно підключено!\n"
                f"Тепер ви отримуватимете сповіщення про нові замовлення сюди.", 
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            await message.answer("Натисніть кнопку, щоб повернутися до роботи:", reply_markup=kb_back_partner)
            return

        # --- 3. ЛОГІКА ДЛЯ КУР'ЄРА ---
        courier = (await db.execute(select(Courier).where(Courier.phone == phone))).scalar_one_or_none()
        
        msg_text = ""
        
        if not courier:
            # Якщо кур'єра немає і це не реєстрація через сайт -> реєструємо автоматично (старий метод для кур'єрів)
            raw_password = secrets.token_urlsafe(8)
            hashed = get_password_hash(raw_password)
            
            courier = Courier(
                name=user_name,
                phone=phone,
                hashed_password=hashed,
                is_active=True
            )
            db.add(courier)
            msg_text = (
                f"🆕 <b>Ви успішно зареєстровані як Кур'єр!</b>\n\n"
                f"📱 Ваш логін: <code>{phone}</code>\n"
                f"🔑 Ваш пароль: <code>{raw_password}</code>"
            )
        else:
            msg_text = f"✅ <b>Акаунт кур'єра знайдено!</b>\nРаді бачити вас знову, {courier.name}."

        # Прив'язуємо Telegram
        courier.telegram_chat_id = chat_id
        await db.commit()
        
        # Кнопка переходу в додаток (PWA)
        kb_open_app = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Відкрити Додаток Кур'єра", url=f"{SITE_URL}/courier/login")]
        ])

        await message.answer(msg_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        await message.answer("Натисніть кнопку, щоб почати зміну:", reply_markup=kb_open_app)

# --- Допоміжні функції ---

async def send_telegram_message(chat_id: str, text: str):
    """
    Функція для відправки повідомлень із інших частин програми.
    """
    if bot and chat_id:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Помилка відправки в Telegram ({chat_id}): {e}")

async def start_bot():
    """Запуск поллінгу бота"""
    if bot:
        logging.info("🤖 Telegram Bot запущено...")
        await dp.start_polling(bot)
