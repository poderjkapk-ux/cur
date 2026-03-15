# admin_reports.py
import logging
from datetime import datetime, time, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models import get_db, Courier, DeliveryJob, CourierTransaction
from auth import check_admin_auth
from templates_saas import GLOBAL_STYLES
from crud_settings import get_setting

router = APIRouter()

def get_reports_html(
    couriers, 
    selected_date_str, 
    selected_courier_id, 
    total_orders, 
    total_commission, 
    real_money, 
    bonus_money,
    courier_stats=None
):
    # Опции для выпадающего списка курьеров
    courier_options = '<option value="all">Всі кур\'єри (Загальний звіт)</option>'
    for c in couriers:
        selected = "selected" if str(c.id) == str(selected_courier_id) else ""
        courier_options += f'<option value="{c.id}" {selected}>{c.name} (ID: {c.id})</option>'

    # Детальная таблица (если выбран конкретный курьер, можно показать его историю за день)
    details_html = ""
    if courier_stats:
        details_html = f"""
        <div class="panel" style="margin-top: 20px;">
            <h2>Деталізація по кур'єру</h2>
            <p>Ця секція може бути розширена списком конкретних транзакцій або замовлень за обраний день.</p>
        </div>
        """

    return f"""
    <!DOCTYPE html><html><head><title>Звіти та Статистика</title>{GLOBAL_STYLES}
    <style>
        .panel {{ background: #1e293b; padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }}
        .stat-card {{ background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }}
        .stat-card h3 {{ margin: 0; font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px; }}
        .stat-card .val {{ font-size: 2rem; font-weight: bold; color: white; }}
        .filter-form {{ display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 20px; }}
        .filter-form .form-group {{ display: flex; flex-direction: column; gap: 5px; }}
        .filter-form label {{ font-size: 0.85rem; color: #94a3b8; }}
        .filter-form input, .filter-form select {{ padding: 10px; border-radius: 8px; background: #334155; border: 1px solid #475569; color: white; min-width: 200px; }}
    </style>
    </head>
    <body>
        <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h1>📊 Фінансовий Звіт</h1>
                <a href="/admin/delivery" class="btn" style="width:auto; padding: 10px 20px;">← Назад в Control Panel</a>
            </div>

            <div class="panel">
                <form method="get" action="/admin/delivery/reports" class="filter-form">
                    <div class="form-group">
                        <label>Оберіть дату:</label>
                        <input type="date" name="date" value="{selected_date_str}" required>
                    </div>
                    <div class="form-group">
                        <label>Фільтр по кур'єру:</label>
                        <select name="courier_id">
                            {courier_options}
                        </select>
                    </div>
                    <button type="submit" class="btn" style="width:auto; padding: 10px 20px; background: #8b5cf6;">Сформувати звіт</button>
                </form>

                <div class="grid-4">
                    <div class="stat-card" style="border-bottom: 3px solid #3b82f6;">
                        <h3>📦 Успішних замовлень</h3>
                        <div class="val" style="color: #3b82f6;">{total_orders}</div>
                    </div>
                    
                    <div class="stat-card" style="border-bottom: 3px solid #facc15;">
                        <h3>💰 Списано комісії</h3>
                        <div class="val" style="color: #facc15;">{total_commission:.2f} ₴</div>
                        <small style="color:#94a3b8; font-size:0.75rem;">гроші платформи</small>
                    </div>
                    
                    <div class="stat-card" style="border-bottom: 3px solid #4ade80;">
                        <h3>💵 Внесено готівки</h3>
                        <div class="val" style="color: #4ade80;">{real_money:.2f} ₴</div>
                        <small style="color:#94a3b8; font-size:0.75rem;">реальні гроші в касу</small>
                    </div>
                    
                    <div class="stat-card" style="border-bottom: 3px solid #ec4899;">
                        <h3>🎁 Внесено бонусів</h3>
                        <div class="val" style="color: #ec4899;">{bonus_money:.2f} ₴</div>
                        <small style="color:#94a3b8; font-size:0.75rem;">без фізичної готівки</small>
                    </div>
                </div>
            </div>
            
            {details_html}
            
        </div>
    </body></html>
    """

@router.get("/admin/delivery/reports", response_class=HTMLResponse)
async def admin_reports_page(
    request: Request,
    date: str = None,
    courier_id: str = "all",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    # 1. Визначаємо дату для звіту (за замовчуванням - сьогодні)
    if not date:
        target_date = datetime.utcnow().date()
    else:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            target_date = datetime.utcnow().date()
            
    selected_date_str = target_date.strftime("%Y-%m-%d")

    # Створюємо межі дня (від 00:00:00 до 23:59:59)
    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)

    # 2. Отримуємо список усіх кур'єрів для фільтра
    couriers = (await db.execute(select(Courier).order_by(Courier.name))).scalars().all()

    # 3. Формуємо базові умови для запитів (фільтр по даті)
    job_conditions = [
        DeliveryJob.status == "delivered",
        DeliveryJob.delivered_at >= start_of_day,
        DeliveryJob.delivered_at <= end_of_day
    ]
    
    transaction_conditions = [
        CourierTransaction.created_at >= start_of_day,
        CourierTransaction.created_at <= end_of_day
    ]

    # Додаємо фільтр по кур'єру, якщо обрано конкретного
    if courier_id and courier_id != "all" and courier_id.isdigit():
        c_id = int(courier_id)
        job_conditions.append(DeliveryJob.courier_id == c_id)
        transaction_conditions.append(CourierTransaction.courier_id == c_id)

    # --- ЗАПИТ 1: Кількість успішних замовлень ---
    orders_query = select(func.count(DeliveryJob.id)).where(and_(*job_conditions))
    total_orders = (await db.execute(orders_query)).scalar() or 0

    # --- ЗАПИТ 2: Списано комісії (type == 'commission') ---
    # Оскільки комісія записується як мінусове значення, беремо модуль (abs)
    comm_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "commission")
    )
    total_commission_raw = (await db.execute(comm_query)).scalar() or 0.0
    total_commission = abs(total_commission_raw)

    # --- ЗАПИТ 3: Внесено реальних грошей (type == 'deposit', cash_received == True) ---
    real_money_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "deposit", CourierTransaction.cash_received == True)
    )
    real_money = (await db.execute(real_money_query)).scalar() or 0.0

    # --- ЗАПИТ 4: Внесено бонусів / безготівки (type == 'deposit', cash_received == False) ---
    bonus_money_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "deposit", CourierTransaction.cash_received == False)
    )
    bonus_money = (await db.execute(bonus_money_query)).scalar() or 0.0

    return get_reports_html(
        couriers=couriers,
        selected_date_str=selected_date_str,
        selected_courier_id=courier_id,
        total_orders=total_orders,
        total_commission=total_commission,
        real_money=real_money,
        bonus_money=bonus_money
    )