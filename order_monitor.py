import asyncio
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from models import async_session_maker, DeliveryJob, Courier, DeliveryPartner

# Импортируем сервис бота для отправки сообщений
import bot_service

# Получаем ID админа для тревожных уведомлений (берем из окружения, как в app.py)
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID")

async def monitor_stale_orders(ws_manager):
    """
    Фоновая задача (Background Task).
    Периодически проверяет базу на наличие заказов, которые долго висят в статусе 'pending'.
    
    Аргументы:
    ws_manager -- экземпляр ConnectionManager из app.py (для рассылки WebSocket, если понадобится)
    """
    logging.info("🕵️ Запуск моніторингу завислих замовлень (Order Monitor)...")
    
    while True:
        try:
            # Проверяем каждую минуту
            await asyncio.sleep(60)
            
            async with async_session_maker() as db:
                now = datetime.utcnow()
                
                # =======================================================
                # СЦЕНАРИЙ 1: 5 МИНУТ -> "ГОРЯЧИЙ ЗАКАЗ" КУРЬЕРАМ
                # =======================================================
                # Ищем заказы, созданные между 5 и 6 минутами назад
                time_5_min_ago = now - timedelta(minutes=5)
                time_6_min_ago = now - timedelta(minutes=6)
                
                query_5 = select(DeliveryJob).where(
                    DeliveryJob.status == "pending",
                    DeliveryJob.created_at <= time_5_min_ago,
                    DeliveryJob.created_at > time_6_min_ago
                )
                jobs_5 = (await db.execute(query_5)).scalars().all()
                
                if jobs_5:
                    # Находим всех курьеров, которые онлайн и у которых есть Telegram
                    online_couriers = (await db.execute(
                        select(Courier).where(Courier.is_online == True, Courier.telegram_chat_id.is_not(None))
                    )).scalars().all()
                    
                    for job in jobs_5:
                        msg_text = (
                            f"🔥 <b>ГАРЯЧЕ ЗАМОВЛЕННЯ!</b>\n"
                            f"Чекає вже 5 хвилин! Хто забере?\n\n"
                            f"💵 <b>{job.delivery_fee} грн</b>\n"
                            f"📍 Куди: {job.dropoff_address}\n"
                            f"🚀 <i>Поспішайте прийняти в додатку!</i>"
                        )
                        # Рассылаем всем свободным курьерам в личку
                        for courier in online_couriers:
                            await bot_service.send_telegram_message(courier.telegram_chat_id, msg_text)
                        
                        logging.info(f"Order #{job.id}: Sent HOT notification to {len(online_couriers)} couriers.")


                # =======================================================
                # СЦЕНАРИЙ 2: 10 МИНУТ -> ТРЕВОГА ПАРТНЕРУ И АДМИНУ
                # =======================================================
                # Ищем заказы, созданные между 10 и 11 минутами назад
                time_10_min_ago = now - timedelta(minutes=10)
                time_11_min_ago = now - timedelta(minutes=11)
                
                query_10 = select(DeliveryJob).options(joinedload(DeliveryJob.partner)).where(
                    DeliveryJob.status == "pending",
                    DeliveryJob.created_at <= time_10_min_ago,
                    DeliveryJob.created_at > time_11_min_ago
                )
                jobs_10 = (await db.execute(query_10)).scalars().all()
                
                for job in jobs_10:
                    # 2.1. Уведомление Партнеру (Ресторану)
                    if job.partner and job.partner.telegram_chat_id:
                        partner_msg = (
                            f"⚠️ <b>Кур'єра не знайдено (вже 10 хв)!</b>\n\n"
                            f"Замовлення #{job.id} на адресу: {job.dropoff_address}.\n"
                            f"Поточна ціна доставки: {job.delivery_fee} грн.\n\n"
                            f"💡 <b>Рекомендуємо збільшити ціну доставки, щоб зацікавити кур'єрів!</b>"
                        )
                        await bot_service.send_telegram_message(job.partner.telegram_chat_id, partner_msg)
                    
                    # 2.2. Уведомление Главному Админу
                    if ADMIN_CHAT_ID:
                        admin_msg = (
                            f"🆘 <b>УВАГА! Проблемне замовлення!</b>\n"
                            f"Партнер: {job.partner.name if job.partner else 'Unknown'}\n"
                            f"ID замовлення: #{job.id}\n"
                            f"Статус: 'pending' вже понад 10 хвилин.\n"
                            f"Прийміть міри!"
                        )
                        await bot_service.send_telegram_message(ADMIN_CHAT_ID, admin_msg)
                        
                    logging.warning(f"Order #{job.id}: Sent STALE warning to Partner and Admin.")

        except Exception as e:
            logging.error(f"❌ Помилка в order_monitor: {e}")
            await asyncio.sleep(60) # Если база упала, ждем минуту перед повтором