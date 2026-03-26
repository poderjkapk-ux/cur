# admin_reports.py
import logging
import pytz
from datetime import datetime, time, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from models import get_db, Courier, DeliveryJob, CourierTransaction, DeliveryPartner
from auth import check_admin_auth
from templates_saas import GLOBAL_STYLES
from crud_settings import get_setting

router = APIRouter()

def format_local_time(utc_dt, tz_string='Europe/Kiev', fmt='%H:%M'):
    """Конвертує UTC datetime у локальний час заданого часового поясу."""
    if not utc_dt:
        return "-"
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    try:
        local_tz = pytz.timezone(tz_string)
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime(fmt)
    except pytz.UnknownTimeZoneError:
        return utc_dt.strftime(fmt)

def get_reports_html(
    couriers, 
    start_date_str, 
    end_date_str, 
    selected_courier_id, 
    total_orders, 
    total_cancelled, 
    total_commission, 
    real_money, 
    bonus_money,
    transactions_data,
    online_count,
    activity_data,
    unassigned_cancelled_jobs=None
):
    # Підрахунок відсотків
    total_resolved = total_orders + total_cancelled
    success_percent = (total_orders / total_resolved * 100) if total_resolved > 0 else 0
    cancel_percent = (total_cancelled / total_resolved * 100) if total_resolved > 0 else 0

    # Опції для випадаючого списку кур'єрів
    courier_options = '<option value="all">Всі кур\'єри (Загальний звіт)</option>'
    for c in couriers:
        selected = "selected" if str(c.id) == str(selected_courier_id) else ""
        courier_options += f'<option value="{c.id}" {selected}>{c.name} (ID: {c.id})</option>'

    # Формування таблиці активності кур'єрів
    activity_rows = ""
    if not activity_data:
        activity_rows = "<tr><td colspan='3' style='text-align:center;'>Немає активності за обраний період.</td></tr>"
    else:
        for item in activity_data:
            activity_rows += f"""
            <tr>
                <td data-label="Кур'єр"><b style="color:#f8fafc;">{item['name']}</b></td>
                <td data-label="Виконано замовлень" style="text-align: center;">{item['orders']}</td>
                <td data-label="Середній час виконання" style="text-align: center;"><b>{item['avg_time_min']} хв</b></td>
            </tr>
            """

    # --- НОВИЙ БЛОК: СКАСОВАНІ ЗАМОВЛЕННЯ БЕЗ КУР'ЄРА ---
    cancelled_html = ""
    if unassigned_cancelled_jobs:
        c_rows = ""
        for job in unassigned_cancelled_jobs:
            t_created = format_local_time(job.created_at, fmt='%d.%m %H:%M')
            partner_name = job.partner.name if getattr(job, 'partner', None) else "Невідомо"
            
            c_rows += f"""
            <tr style="background: rgba(239, 68, 68, 0.15);">
                <td data-label="Створено">{t_created}</td>
                <td data-label="Замовлення"><b style="color:#f8fafc;">#{job.id}</b></td>
                <td data-label="Заклад"><b>{partner_name}</b></td>
                <td data-label="Адреса">{job.dropoff_address}</td>
                <td data-label="Ціна">{job.order_price} ₴ (+{job.delivery_fee} ₴ доставка)</td>
                <td data-label="Статус"><span class="badge" style="background: #ef4444; color: white;">Не знайдено кур'єра</span></td>
            </tr>
            """
            
        cancelled_html = f"""
        <div class="panel" style="margin-top: 20px; border: 1px dashed #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.2);">
            <h2 style="margin-top: 0; color: #fca5a5; display: flex; align-items: center; gap: 10px;">
                <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i> Втрачені замовлення (Скасовані, бо не знайдено кур'єра)
            </h2>
            <div style="overflow-x:auto;">
                <table class="details-table">
                    <thead>
                        <tr>
                            <th>Час</th>
                            <th>ID</th>
                            <th>Заклад</th>
                            <th>Адреса доставки</th>
                            <th>Сума</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {c_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

    # Детальна таблиця транзакцій та таймінгів
    details_html = ""
    if transactions_data is not None:
        details_html = """
        <div class="panel" style="margin-top: 20px;">
            <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                <i class="fa-solid fa-list-ul" style="color: #8b5cf6;"></i> Деталізація по замовленнях та грошах
            </h2>
            <div style="overflow-x:auto;">
                <table class="details-table">
                    <thead>
                        <tr>
                            <th>Час (Створено)</th>
                            <th>Кур'єр</th>
                            <th>Транзакція / Сума</th>
                            <th>Замовлення (ID / Адреса)</th>
                            <th style="text-align: right;">Таймінги доставки</th>
                            <th>Опис</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        if not transactions_data:
            details_html += "<tr><td colspan='6' style='text-align:center;'>Немає транзакцій за обраний період.</td></tr>"
        else:
            for txn, courier, job in transactions_data:
                t_created = format_local_time(txn.created_at, fmt='%H:%M:%S')
                
                amount_val = f"{abs(txn.amount):.2f} ₴"
                if txn.type == 'commission':
                    badge = f'<span class="badge commission">Списання (-{amount_val})</span>'
                elif txn.type == 'deposit' and txn.cash_received:
                    badge = f'<span class="badge deposit">Готівка (+{amount_val})</span>'
                elif txn.type == 'deposit' and not txn.cash_received:
                    badge = f'<span class="badge bonus">Безготівка/Бонус (+{amount_val})</span>'
                else:
                    badge = f'<span class="badge" style="background:#475569;color:white;">{txn.type} ({txn.amount})</span>'

                job_info = "—"
                timings = "—"
                if job:
                    job_info = f"<b style='color:#f8fafc;'>#{job.id}</b><br><small style='color:#94a3b8; line-height:1.2; display:block; margin-top:4px;'>{job.dropoff_address}</small>"
                    t_j_c = format_local_time(job.created_at)
                    t_j_a = format_local_time(job.accepted_at)
                    t_j_d = format_local_time(job.delivered_at)
                    timings = f"""
                    <div class="time-block"><span class="time-label">Створено:</span> <b>{t_j_c}</b></div>
                    <div class="time-block"><span class="time-label">Прийнято:</span> <b>{t_j_a}</b></div>
                    <div class="time-block"><span class="time-label">Доставлено:</span> <b style="color:#4ade80;">{t_j_d}</b></div>
                    """
                
                details_html += f"""
                <tr>
                    <td data-label="Час транзакції">{t_created}</td>
                    <td data-label="Кур'єр"><b style="color:#f8fafc;">{courier.name}</b><br><small style="color:#64748b;">ID: {courier.id}</small></td>
                    <td data-label="Транзакція" class="cell-col">{badge}</td>
                    <td data-label="Замовлення" class="cell-col">{job_info}</td>
                    <td data-label="Таймінги" class="cell-col" style="text-align: right;">{timings}</td>
                    <td data-label="Опис" style="color:#cbd5e1; font-size:0.85rem;">{txn.description or '-'}</td>
                </tr>
                """
        details_html += "</tbody></table></div></div>"

    return f"""
    <!DOCTYPE html><html><head><title>Звіти та Статистика</title>{GLOBAL_STYLES}
    <style>
        .panel {{ background: #1e293b; padding: 25px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }}
        .stat-card {{ background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }}
        .stat-card h3 {{ margin: 0; font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px; }}
        .stat-card .val {{ font-size: 2rem; font-weight: bold; color: white; }}
        .filter-form {{ display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 20px; }}
        .filter-form .form-group {{ display: flex; flex-direction: column; gap: 5px; }}
        .filter-form label {{ font-size: 0.85rem; color: #94a3b8; font-weight: bold; }}
        .filter-form input, .filter-form select {{ padding: 12px; border-radius: 8px; background: #334155; border: 1px solid #475569; color: white; min-width: 150px; font-size:1rem; }}
        
        /* СТИЛІ ДЛЯ ДЕТАЛЬНОЇ ТАБЛИЦІ */
        .details-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95rem; }}
        .details-table th, .details-table td {{ padding: 14px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; vertical-align: middle; }}
        .details-table th {{ color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        .details-table tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
        
        .badge {{ padding: 5px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: bold; display: inline-block; }}
        .badge.commission {{ background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge.deposit {{ background: rgba(74, 222, 128, 0.15); color: #86efac; border: 1px solid rgba(74, 222, 128, 0.3); }}
        .badge.bonus {{ background: rgba(236, 72, 153, 0.15); color: #f9a8d4; border: 1px solid rgba(236, 72, 153, 0.3); }}

        .time-block {{ font-size: 0.85rem; color: #f8fafc; margin-bottom: 4px; display: flex; justify-content: flex-end; gap: 10px; }}
        .time-label {{ color: #94a3b8; }}

        /* АДАПТИВНІСТЬ (МОБІЛЬНІ ПРИСТРОЇ) */
        @media (max-width: 800px) {{
            .details-table thead {{ display: none; }}
            .details-table tbody tr {{
                display: block;
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
            }}
            .details-table td {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255,255,255,0.05);
                text-align: right;
            }}
            .details-table td:last-child {{ border-bottom: none; padding-bottom: 0; }}
            .details-table td::before {{
                content: attr(data-label);
                font-weight: 600;
                color: #64748b;
                font-size: 0.85rem;
                text-align: left;
                margin-right: 15px;
            }}
            .cell-col {{ display: flex; flex-direction: column; align-items: flex-end; text-align: right !important; }}
            .time-block {{ justify-content: flex-end; width: 100%; }}
        }}
    </style>
    </head>
    <body>
        <div style="max-width: 1300px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap: wrap; gap: 15px;">
                <h1 style="margin: 0;"><i class="fa-solid fa-chart-line"></i> Фінансовий Звіт</h1>
                <a href="/admin/delivery" class="btn" style="width:auto; padding: 10px 20px;"><i class="fa-solid fa-arrow-left"></i> Назад в Control Panel</a>
            </div>

            <div class="panel">
                <form method="get" action="/admin/delivery/reports" class="filter-form">
                    <div class="form-group">
                        <label>З дати:</label>
                        <input type="date" name="start_date" value="{start_date_str}" required>
                    </div>
                    <div class="form-group">
                        <label>По дату:</label>
                        <input type="date" name="end_date" value="{end_date_str}" required>
                    </div>
                    <div class="form-group">
                        <label>Фільтр по кур'єру:</label>
                        <select name="courier_id">
                            {courier_options}
                        </select>
                    </div>
                    <button type="submit" class="btn" style="width:auto; padding: 12px 24px; background: #6366f1; align-self: stretch;">Сформувати звіт</button>
                </form>

                <div class="grid-4">
                    <div class="stat-card" style="border-bottom: 3px solid #10b981;">
                        <h3>🟢 Кур'єрів онлайн</h3>
                        <div class="val" style="color: #10b981;">{online_count}</div>
                        <small style="color:#94a3b8; font-size:0.75rem;">в даний момент</small>
                    </div>

                    <div class="stat-card" style="border-bottom: 3px solid #3b82f6;">
                        <h3>📦 Успішних замовлень</h3>
                        <div class="val" style="color: #3b82f6;">{total_orders}</div>
                        <small style="color:#94a3b8; font-size:0.75rem;">за обраний період</small>
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
                </div>
            </div>

            <div class="panel" style="margin-top: 20px; border: 1px dashed #3b82f6;">
                <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-chart-pie" style="color: #8b5cf6;"></i> Конверсія замовлень (Виконані / Скасовані)
                </h2>
                <div style="display: flex; gap: 30px; align-items: center; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 250px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #94a3b8; font-weight: bold;">Успішні ({total_orders})</span>
                            <span style="color: #3b82f6; font-weight: bold;">{success_percent:.1f}%</span>
                        </div>
                        <div style="width: 100%; background: rgba(0,0,0,0.3); border-radius: 10px; height: 14px; overflow: hidden; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05);">
                            <div style="width: {success_percent}%; background: linear-gradient(90deg, #2563eb, #3b82f6); height: 100%; border-radius: 10px;"></div>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #94a3b8; font-weight: bold;">Скасовані ({total_cancelled})</span>
                            <span style="color: #ef4444; font-weight: bold;">{cancel_percent:.1f}%</span>
                        </div>
                        <div style="width: 100%; background: rgba(0,0,0,0.3); border-radius: 10px; height: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05);">
                            <div style="width: {cancel_percent}%; background: linear-gradient(90deg, #dc2626, #ef4444); height: 100%; border-radius: 10px;"></div>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 150px; text-align: center; background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                        <h3 style="margin: 0; color: #94a3b8; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em;">Всього оброблено</h3>
                        <div style="font-size: 3rem; font-weight: bold; color: white; margin-top: 10px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">{total_resolved}</div>
                    </div>
                </div>
            </div>

            <div class="panel" style="margin-top: 20px;">
                <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-stopwatch" style="color: #3b82f6;"></i> Статистика по кур'єрам (за період)
                </h2>
                <div style="overflow-x:auto;">
                    <table class="details-table">
                        <thead>
                            <tr>
                                <th>Кур'єр</th>
                                <th style="text-align: center;">Виконано замовлень</th>
                                <th style="text-align: center;">Середній час виконання</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activity_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
            {cancelled_html}
            {details_html}
            
        </div>
    </body></html>
    """

@router.get("/admin/delivery/reports", response_class=HTMLResponse)
async def admin_reports_page(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    courier_id: str = "all",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    # 1. Визначаємо дати для звіту (за замовчуванням - сьогоднішня дата для обох)
    today = datetime.utcnow().date()
    
    if not start_date:
        target_start_date = today
    else:
        try:
            target_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            target_start_date = today

    if not end_date:
        target_end_date = today
    else:
        try:
            target_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            target_end_date = today
            
    # Перестраховка: якщо обрана початкова дата більша за кінцеву - міняємо їх місцями
    if target_start_date > target_end_date:
        target_start_date, target_end_date = target_end_date, target_start_date
        
    start_date_str = target_start_date.strftime("%Y-%m-%d")
    end_date_str = target_end_date.strftime("%Y-%m-%d")

    # Створюємо межі періоду (від 00:00:00 початкової дати до 23:59:59 кінцевої дати)
    start_of_day = datetime.combine(target_start_date, time.min)
    end_of_day = datetime.combine(target_end_date, time.max)

    # 2. Отримуємо список усіх кур'єрів для фільтра
    couriers = (await db.execute(select(Courier).order_by(Courier.name))).scalars().all()

    # 3. Формуємо базові умови для запитів (фільтр по діапазону дат)
    job_conditions = [
        DeliveryJob.status == "delivered",
        DeliveryJob.delivered_at >= start_of_day,
        DeliveryJob.delivered_at <= end_of_day
    ]
    
    # Умови для скасованих замовлень
    cancel_conditions = [
        DeliveryJob.status == "cancelled",
        DeliveryJob.created_at >= start_of_day,
        DeliveryJob.created_at <= end_of_day
    ]
    
    transaction_conditions = [
        CourierTransaction.created_at >= start_of_day,
        CourierTransaction.created_at <= end_of_day
    ]

    # Додаємо фільтр по кур'єру, якщо обрано конкретного
    if courier_id and courier_id != "all" and courier_id.isdigit():
        c_id = int(courier_id)
        job_conditions.append(DeliveryJob.courier_id == c_id)
        cancel_conditions.append(DeliveryJob.courier_id == c_id) 
        transaction_conditions.append(CourierTransaction.courier_id == c_id)

    # --- ЗАПИТ 1: Кількість успішних замовлень ---
    orders_query = select(func.count(DeliveryJob.id)).where(and_(*job_conditions))
    total_orders = (await db.execute(orders_query)).scalar() or 0

    # --- ЗАПИТ: Кількість скасованих замовлень ---
    cancelled_query = select(func.count(DeliveryJob.id)).where(and_(*cancel_conditions))
    total_cancelled = (await db.execute(cancelled_query)).scalar() or 0

    # --- ЗАПИТ 2: Списано комісії (type == 'commission') ---
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

    # --- ЗАПИТ 5: Деталізація транзакцій ---
    details_query = select(CourierTransaction, Courier, DeliveryJob).join(
        Courier, CourierTransaction.courier_id == Courier.id
    ).outerjoin(
        DeliveryJob, CourierTransaction.job_id == DeliveryJob.id
    ).where(
        and_(*transaction_conditions)
    ).order_by(
        CourierTransaction.created_at.desc()
    )
    
    details_result = await db.execute(details_query)
    transactions_data = details_result.all()

    # --- ЗАПИТ 6: Скільки кур'єрів онлайн ЗАРАЗ ---
    online_query = select(func.count(Courier.id)).where(Courier.is_online == True)
    online_count = (await db.execute(online_query)).scalar() or 0

    # --- ЗАПИТ 7: Активність та середній час доставки ---
    jobs_query = select(DeliveryJob).where(and_(*job_conditions))
    jobs_for_stats = (await db.execute(jobs_query)).scalars().all()
    
    courier_dict = {c.id: c.name for c in couriers}
    courier_stats = {}
    
    for job in jobs_for_stats:
        cid = job.courier_id
        if not cid:
            continue
            
        if cid not in courier_stats:
            courier_stats[cid] = {
                'name': courier_dict.get(cid, f"Невідомий (ID: {cid})"),
                'orders': 0,
                'total_seconds': 0,
                'timed_orders': 0
            }
            
        courier_stats[cid]['orders'] += 1
        
        # Рахуємо час виконання: від 'accepted_at' до 'delivered_at'
        if job.accepted_at and job.delivered_at:
            delta = job.delivered_at - job.accepted_at
            courier_stats[cid]['total_seconds'] += delta.total_seconds()
            courier_stats[cid]['timed_orders'] += 1

    # Формуємо список і рахуємо середнє
    activity_data = []
    for cid, data in courier_stats.items():
        if data['timed_orders'] > 0:
            avg_seconds = data['total_seconds'] / data['timed_orders']
            avg_min = int(avg_seconds // 60)
        else:
            avg_min = 0
            
        activity_data.append({
            'name': data['name'],
            'orders': data['orders'],
            'avg_time_min': avg_min
        })

    # Сортуємо по кількості замовлень (від більшого до меншого)
    activity_data.sort(key=lambda x: x['orders'], reverse=True)

    # --- НОВИЙ ЗАПИТ: Отримуємо скасовані замовлення, де не було призначено кур'єра ---
    unassigned_cancelled_jobs = []
    # Показуємо їх тільки якщо дивимося загальний звіт по всім кур'єрам
    if courier_id == "all" or not courier_id:
        unassigned_cancel_conditions = [
            DeliveryJob.status == "cancelled",
            DeliveryJob.courier_id.is_(None), # Кур'єр не був призначений
            DeliveryJob.created_at >= start_of_day,
            DeliveryJob.created_at <= end_of_day
        ]
        unassigned_query = select(DeliveryJob).options(
            joinedload(DeliveryJob.partner)
        ).where(and_(*unassigned_cancel_conditions)).order_by(DeliveryJob.created_at.desc())
        
        unassigned_cancelled_jobs = (await db.execute(unassigned_query)).scalars().all()

    return get_reports_html(
        couriers=couriers,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        selected_courier_id=courier_id,
        total_orders=total_orders,
        total_cancelled=total_cancelled,
        total_commission=total_commission,
        real_money=real_money,
        bonus_money=bonus_money,
        transactions_data=transactions_data,
        online_count=online_count,
        activity_data=activity_data,
        unassigned_cancelled_jobs=unassigned_cancelled_jobs
    )