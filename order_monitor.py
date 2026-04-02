import asyncio
import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import select, text
from sqlalchemy.orm import joinedload
from models import async_session_maker, DeliveryJob, Courier, DeliveryPartner, engine, CourierMotivatorProgress

# Импортируем сервис бота для отправки сообщений
import bot_service

# ИМПОРТ FCM ДЛЯ ОТПРАВКИ ПУШЕЙ ИЗ ФОНОВОЙ ЗАДАЧИ
from firebase_admin import messaging

# Получаем ID админа для тревожных уведомлений (берем из окружения, как в app.py)
ADMIN_CHAT_ID = os.environ.get("TG_CHAT_ID")

# --- НОВА ФОНОВА ЗАДАЧА ДЛЯ СИСТЕМИ МОТИВАТОРІВ ---
async def monitor_expired_motivators(db_session):
    now = datetime.utcnow()
    # Ищем бонусы, срок которых вышел
    query = select(CourierMotivatorProgress).where(
        CourierMotivatorProgress.status == "reward_active",
        CourierMotivatorProgress.reward_end_date <= now
    )
    expired_bonuses = (await db_session.execute(query)).scalars().all()
    
    for prog in expired_bonuses:
        prog.status = "completed" # Бонус отработал свое
        courier = await db_session.get(Courier, prog.courier_id)
        if courier and prog.old_commission is not None:
            courier.commission_rate = prog.old_commission # Возвращаем старую
            
            # Уведомляем курьера о завершении бонуса
            if courier.telegram_chat_id:
                tg_msg = f"ℹ️ <b>Бонус завершено</b>\nЧас дії вашої нагороди вийшов. Ваша комісія повернута до стандартної ({prog.old_commission}%)."
                asyncio.create_task(bot_service.send_telegram_message(courier.telegram_chat_id, tg_msg))
            
    if expired_bonuses:
        await db_session.commit()
        logging.info(f"🔄 Скинуто комісію для {len(expired_bonuses)} кур'єрів (бонус мотиватора вийшов).")
# --------------------------------------------------

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
                
                # --- ВИКЛИК МОНІТОРИНГУ МОТИВАТОРІВ ---
                await monitor_expired_motivators(db)
                # --------------------------------------
                
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
                    # Находим всех курьеров, которые онлайн
                    online_couriers = (await db.execute(
                        select(Courier).where(Courier.is_online == True)
                    )).scalars().all()
                    
                    for job in jobs_5:
                        msg_title = "🔥 ГАРЯЧЕ ЗАМОВЛЕННЯ!"
                        
                        # Текст для Telegram
                        msg_body_tg = (
                            f"Чекає вже 5 хвилин! Хто забере?\n\n"
                            f"💵 <b>{job.delivery_fee} грн</b>\n"
                            f"📍 Куди: {job.dropoff_address}\n"
                            f"🚀 <i>Поспішайте прийняти в додатку!</i>"
                        )
                        
                        # Текст для Push-уведомления
                        msg_body_push = f"💵 {job.delivery_fee} грн. Ніхто не забирає вже 5 хвилин!"

                        for courier in online_couriers:
                            # 1. Отправка в Telegram (если привязан)
                            if courier.telegram_chat_id:
                                await bot_service.send_telegram_message(
                                    courier.telegram_chat_id, 
                                    f"🔥 <b>ГАРЯЧЕ ЗАМОВЛЕННЯ!</b>\n{msg_body_tg}"
                                )
                            
                            # 2. Отправка Firebase Push Notification (Android / PWA)
                            if courier.fcm_token:
                                try:
                                    push_msg = messaging.Message(
                                        token=courier.fcm_token,
                                        notification=messaging.Notification(
                                            title=msg_title, 
                                            body=msg_body_push
                                        ),
                                        data={
                                            "url": "/courier/app", 
                                            "job_id": str(job.id), 
                                            "fee": str(job.delivery_fee)
                                        },
                                        android=messaging.AndroidConfig(priority='high', ttl=0)
                                    )
                                    messaging.send(push_msg)
                                except Exception as e:
                                    logging.error(f"FCM Monitor Error (Courier {courier.id}): {e}")
                        
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
                    if job.partner:
                        # 2.1. Уведомление Партнеру (Ресторану) в Telegram
                        if job.partner.telegram_chat_id:
                            partner_msg = (
                                f"⚠️ <b>Кур'єра не знайдено (вже 10 хв)!</b>\n\n"
                                f"Замовлення #{job.id} на адресу: {job.dropoff_address}.\n"
                                f"Поточна ціна доставки: {job.delivery_fee} грн.\n\n"
                                f"💡 <b>Рекомендуємо збільшити ціну доставки, щоб зацікавити кур'єрів!</b>"
                            )
                            await bot_service.send_telegram_message(job.partner.telegram_chat_id, partner_msg)
                        
                        # 2.2. Уведомление Партнеру через Firebase Push Notification
                        if job.partner.fcm_token:
                            try:
                                push_msg = messaging.Message(
                                    token=job.partner.fcm_token,
                                    notification=messaging.Notification(
                                        title="⚠️ Увага: Затримка замовлення",
                                        body=f"Замовлення #{job.id} не можуть забрати вже 10 хв. Збільште ціну доставки!"
                                    ),
                                    data={
                                        "url": "/partner/dashboard", 
                                        "job_id": str(job.id)
                                    },
                                    android=messaging.AndroidConfig(priority='high', ttl=0)
                                )
                                messaging.send(push_msg)
                            except Exception as e:
                                logging.error(f"FCM Monitor Error (Partner {job.partner.id}): {e}")
                    
                    # 2.3. Уведомление Главному Админу в Telegram
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

                # =======================================================
                # СЦЕНАРІЙ 3: АВТОМАТИЧНЕ ПІДТВЕРДЖЕННЯ ГОТОВНОСТІ
                # =======================================================
                ready_query = select(DeliveryJob).options(
                    joinedload(DeliveryJob.courier), joinedload(DeliveryJob.partner)
                ).where(
                    DeliveryJob.estimated_ready_at <= now,
                    DeliveryJob.ready_at == None, # Тільки ті, де ще не натиснули Готово
                    DeliveryJob.status.in_(["pending", "assigned", "arrived_pickup"])
                )
                jobs_to_ready = (await db.execute(ready_query)).scalars().all()
                
                for job in jobs_to_ready:
                    job.ready_at = now # Автоматично маркуємо готовим
                    
                    # Сповіщаємо кур'єра (якщо вже призначений)
                    if job.courier_id and job.courier:
                        await ws_manager.notify_courier(job.courier_id, {
                            "type": "job_ready", 
                            "message": "🍳 Час приготування вийшов! Замовлення автоматично позначено як Готове."
                        })
                        if job.courier.telegram_chat_id:
                            await bot_service.send_telegram_message(
                                job.courier.telegram_chat_id, 
                                f"🍳 <b>Замовлення #{job.id} готове!</b>\nЧас приготування (таймер) вийшов. Можете забирати пакунок."
                            )
                        if job.courier.fcm_token:
                            try:
                                push_msg = messaging.Message(
                                    token=job.courier.fcm_token,
                                    notification=messaging.Notification(
                                        title="🍳 Замовлення готове!",
                                        body="Час приготування вийшов. Можете забирати."
                                    ),
                                    data={"url": "/courier/app", "job_id": str(job.id)},
                                    android=messaging.AndroidConfig(priority='high', ttl=0)
                                )
                                messaging.send(push_msg)
                            except Exception:
                                pass
                                
                    # Сповіщаємо заклад про автоматичну зміну
                    if job.partner_id and job.partner:
                        await ws_manager.notify_partner(job.partner_id, {
                            "type": "order_update", "job_id": job.id, "status": job.status,
                            "message": f"⏳ Час приготування ({job.id}) вийшов! Автоматично позначено як Готове."
                        })
                        
                if jobs_to_ready:
                    await db.commit()
                    logging.info(f"Auto-marked {len(jobs_to_ready)} orders as ready.")

        except Exception as e:
            logging.error(f"❌ Помилка в order_monitor: {e}")
            await asyncio.sleep(60) # Если база упала, ждем минуту перед повтором