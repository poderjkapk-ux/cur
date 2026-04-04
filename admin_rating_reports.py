# admin_rating_reports.py
import logging
import pytz
from datetime import datetime, time
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from models import get_db, Courier, DeliveryJob
from auth import check_admin_auth
from templates_saas import GLOBAL_STYLES
from crud_settings import get_setting

router = APIRouter()

def format_local_time(utc_dt, tz_string='Europe/Kiev', fmt='%d.%m.%Y %H:%M'):
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

def get_rating_reports_html(
    couriers, 
    start_date_str, 
    end_date_str, 
    selected_courier_id, 
    sort_by,
    stats_list,
    reviews
):
    # Опції для випадаючого списку кур'єрів
    courier_options = '<option value="all">Всі кур\'єри</option>'
    for c in couriers:
        selected = "selected" if str(c.id) == str(selected_courier_id) else ""
        courier_options += f'<option value="{c.id}" {selected}>{c.name} (ID: {c.id})</option>'

    # Опції для сортування
    sort_options = [
        ("orders_desc", "За кількістю замовлень (спадання)"),
        ("earned_desc", "За заробітком (спадання)"),
        ("rating_desc", "За рейтингом (спадання)"),
    ]
    sort_html = ""
    for val, label in sort_options:
        selected = "selected" if sort_by == val else ""
        sort_html += f'<option value="{val}" {selected}>{label}</option>'

    # Формування таблиці статистики кур'єрів
    stats_rows = ""
    if not stats_list:
        stats_rows = "<tr><td colspan='5' style='text-align:center;'>Немає даних за обраний період.</td></tr>"
    else:
        for item in stats_list:
            period_rating_str = f"⭐ {item['period_rating']}" if item['period_rating'] > 0 else "Немає оцінок"
            global_rating_str = f"⭐ {item['global_rating']}"
            stats_rows += f"""
            <tr>
                <td data-label="Кур'єр"><b style="color:#f8fafc;">{item['name']}</b> <small style="color:#94a3b8;">(ID: {item['courier_id']})</small></td>
                <td data-label="Замовлень (період)" style="text-align: center; font-weight: bold; color: #3b82f6;">{item['orders_count']}</td>
                <td data-label="Заробіток (період)" style="text-align: center; font-weight: bold; color: #4ade80;">{item['earned']:.2f} ₴</td>
                <td data-label="Рейтинг (період)" style="text-align: center; color: #facc15; font-weight: bold;">{period_rating_str}</td>
                <td data-label="Глобальний рейтинг" style="text-align: center; color: #94a3b8;">{global_rating_str}</td>
            </tr>
            """

    # Таблиця відгуків
    reviews_rows = ""
    if not reviews:
        reviews_rows = "<tr><td colspan='6' style='text-align:center;'>Немає відгуків за обраний період.</td></tr>"
    else:
        for r in reviews:
            stars = "⭐" * r['rating']
            reviews_rows += f"""
            <tr>
                <td data-label="Дата">{r['date_str']}</td>
                <td data-label="Замовлення">#{r['job_id']}</td>
                <td data-label="Заклад"><b>{r['partner_name']}</b></td>
                <td data-label="Кур'єр"><b style="color:#f8fafc;">{r['courier_name']}</b></td>
                <td data-label="Оцінка" style="color: #facc15;">{stars} ({r['rating']})</td>
                <td data-label="Відгук" style="font-style: italic; color: #cbd5e1;">{r['review']}</td>
            </tr>
            """

    return f"""
    <!DOCTYPE html><html><head><title>Рейтинг та Відгуки Кур'єрів</title>{GLOBAL_STYLES}
    <style>
        .panel {{ background: #1e293b; padding: 25px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .filter-form {{ display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 20px; }}
        .filter-form .form-group {{ display: flex; flex-direction: column; gap: 5px; }}
        .filter-form label {{ font-size: 0.85rem; color: #94a3b8; font-weight: bold; }}
        .filter-form input, .filter-form select {{ padding: 12px; border-radius: 8px; background: #334155; border: 1px solid #475569; color: white; min-width: 150px; font-size:1rem; }}
        
        .details-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95rem; }}
        .details-table th, .details-table td {{ padding: 14px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; vertical-align: middle; }}
        .details-table th {{ color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        .details-table tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
    </style>
    </head>
    <body>
        <div style="max-width: 1300px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap: wrap; gap: 15px;">
                <h1 style="margin: 0;"><i class="fa-solid fa-star" style="color:#facc15;"></i> Звіт: Рейтинг та Заробіток</h1>
                <a href="/admin/delivery" class="btn" style="width:auto; padding: 10px 20px;"><i class="fa-solid fa-arrow-left"></i> Назад в Control Panel</a>
            </div>

            <div class="panel">
                <form method="get" action="/admin/delivery/rating_reports" class="filter-form">
                    <div class="form-group">
                        <label>З дати:</label>
                        <input type="date" name="start_date" value="{start_date_str}" required>
                    </div>
                    <div class="form-group">
                        <label>По дату:</label>
                        <input type="date" name="end_date" value="{end_date_str}" required>
                    </div>
                    <div class="form-group">
                        <label>Кур'єр:</label>
                        <select name="courier_id">
                            {courier_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Сортування:</label>
                        <select name="sort_by">
                            {sort_html}
                        </select>
                    </div>
                    <button type="submit" class="btn" style="width:auto; padding: 12px 24px; background: #f59e0b; align-self: stretch;">Застосувати</button>
                </form>
            </div>

            <div class="panel" style="margin-top: 20px; border-top: 3px solid #f59e0b;">
                <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                    <i class="fa-solid fa-ranking-star" style="color: #f59e0b;"></i> Статистика Кур'єрів (за обраний період)
                </h2>
                <div style="overflow-x:auto;">
                    <table class="details-table">
                        <thead>
                            <tr>
                                <th>Кур'єр</th>
                                <th style="text-align: center;">Виконано замовлень</th>
                                <th style="text-align: center;">Заробіток (Вартість доставок)</th>
                                <th style="text-align: center;">Середній рейтинг (Період)</th>
                                <th style="text-align: center;">Загальний рейтинг</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stats_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="panel" style="margin-top: 20px;">
                <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                    <i class="fa-regular fa-comments" style="color: #3b82f6;"></i> Останні відгуки та оцінки
                </h2>
                <div style="overflow-x:auto;">
                    <table class="details-table">
                        <thead>
                            <tr>
                                <th>Дата</th>
                                <th>Замовлення</th>
                                <th>Заклад</th>
                                <th>Кур'єр</th>
                                <th>Оцінка</th>
                                <th>Коментар закладу/клієнта</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reviews_rows}
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    </body></html>
    """

@router.get("/admin/delivery/rating_reports", response_class=HTMLResponse)
async def admin_rating_reports_page(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    courier_id: str = "all",
    sort_by: str = "orders_desc",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    # 1. Визначаємо дати (за замовчуванням - сьогодні)
    today = datetime.utcnow().date()
    
    try:
        target_start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else today
        target_end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else today
    except ValueError:
        target_start_date = today
        target_end_date = today
            
    if target_start_date > target_end_date:
        target_start_date, target_end_date = target_end_date, target_start_date
        
    start_date_str = target_start_date.strftime("%Y-%m-%d")
    end_date_str = target_end_date.strftime("%Y-%m-%d")

    start_of_day = datetime.combine(target_start_date, time.min)
    end_of_day = datetime.combine(target_end_date, time.max)

    # 2. Завантажуємо кур'єрів
    couriers_query = await db.execute(select(Courier).order_by(Courier.name))
    couriers = couriers_query.scalars().all()
    courier_map = {c.id: c for c in couriers}

    # 3. Фільтри для замовлень
    job_conditions = [
        DeliveryJob.status == "delivered",
        DeliveryJob.delivered_at >= start_of_day,
        DeliveryJob.delivered_at <= end_of_day
    ]
    if courier_id and courier_id != "all" and courier_id.isdigit():
        job_conditions.append(DeliveryJob.courier_id == int(courier_id))

    # 4. Витягуємо замовлення
    jobs_query = select(DeliveryJob).options(joinedload(DeliveryJob.partner)).where(and_(*job_conditions))
    jobs = (await db.execute(jobs_query)).scalars().all()

    # 5. Агрегуємо статистику та відгуки
    stats = {}
    reviews = []
    
    tz_string = await get_setting(db, "timezone") or "Europe/Kiev"

    for j in jobs:
        cid = j.courier_id
        if not cid or cid not in courier_map: continue

        if cid not in stats:
            stats[cid] = {
                'courier_id': cid,
                'name': courier_map[cid].name,
                'global_rating': getattr(courier_map[cid], 'avg_rating', 5.0),
                'orders_count': 0,
                'earned': 0.0,
                'rating_sum': 0,
                'rating_count': 0,
            }

        stats[cid]['orders_count'] += 1
        stats[cid]['earned'] += float(j.delivery_fee or 0.0)

        # Якщо є оцінка - записуємо для підрахунку середнього за період
        if j.courier_rating:
            stats[cid]['rating_sum'] += j.courier_rating
            stats[cid]['rating_count'] += 1

            reviews.append({
                'date_str': format_local_time(j.delivered_at, tz_string),
                'raw_date': j.delivered_at,
                'job_id': j.id,
                'partner_name': j.partner.name if getattr(j, 'partner', None) else "Невідомо",
                'courier_name': courier_map[cid].name,
                'rating': j.courier_rating,
                'review': j.courier_review or "-"
            })

    # Формуємо список і рахуємо середній рейтинг за період
    stats_list = []
    for cid, data in stats.items():
        data['period_rating'] = round(data['rating_sum'] / data['rating_count'], 2) if data['rating_count'] > 0 else 0.0
        stats_list.append(data)

    # Сортування статистики
    if sort_by == 'earned_desc':
        stats_list.sort(key=lambda x: x['earned'], reverse=True)
    elif sort_by == 'rating_desc':
        stats_list.sort(key=lambda x: x['period_rating'], reverse=True)
    else: # orders_desc (default)
        stats_list.sort(key=lambda x: x['orders_count'], reverse=True)

    # Сортування відгуків (новіші зверху)
    reviews.sort(key=lambda x: x['raw_date'], reverse=True)

    return get_rating_reports_html(
        couriers=couriers,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        selected_courier_id=courier_id,
        sort_by=sort_by,
        stats_list=stats_list,
        reviews=reviews
    )