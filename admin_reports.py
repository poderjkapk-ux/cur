# admin_reports.py
import logging
import pytz
from datetime import datetime, time, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
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

# =========================================================================================
# 1. HTML ШАБЛОН: ФІНАНСОВИЙ ЗВІТ
# =========================================================================================

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
    total_resolved = total_orders + total_cancelled
    success_percent = (total_orders / total_resolved * 100) if total_resolved > 0 else 0
    cancel_percent = (total_cancelled / total_resolved * 100) if total_resolved > 0 else 0

    courier_options = '<option value="all">Всі кур\'єри (Загальний звіт)</option>'
    for c in couriers:
        selected = "selected" if str(c.id) == str(selected_courier_id) else ""
        courier_options += f'<option value="{c.id}" {selected}>{c.name} (ID: {c.id})</option>'

    activity_rows = ""
    if not activity_data:
        activity_rows = "<tr><td colspan='3' style='text-align:center;'>Немає активності за обраний період.</td></tr>"
    else:
        for item in activity_data:
            activity_rows += f"""
            <tr>
                <td data-label="Кур'єр"><b style="color:#f8fafc;">{item['name']} (ID: {item['courier_id']})</b></td>
                <td data-label="Виконано замовлень" style="text-align: center;">{item['orders']}</td>
                <td data-label="Середній час виконання" style="text-align: center;"><b>{item['avg_time_min']} хв</b></td>
            </tr>
            """

    cancelled_html = ""
    if unassigned_cancelled_jobs:
        c_rows = ""
        for job in unassigned_cancelled_jobs:
            t_created = format_local_time(job.created_at, fmt='%d.%m %H:%M')
            partner_name = job.partner.name if getattr(job, 'partner', None) else "Невідомо"
            phone = getattr(job, 'customer_phone', 'Не вказано')
            job_comment = getattr(job, 'comment', '')
            comment_html = f"<div style='margin-top:5px; padding:4px; background:rgba(250, 204, 21, 0.1); border-left:2px solid #facc15; color:#facc15; font-size:0.8rem;'><i class='fa-solid fa-comment'></i> {job_comment}</div>" if job_comment else ""

            c_rows += f"""
            <tr style="background: rgba(239, 68, 68, 0.15);">
                <td data-label="Створено">{t_created}</td>
                <td data-label="Замовлення">
                    <b style="color:#f8fafc; font-size:1.1rem;">#{job.id}</b><br>
                    <small style="color:#94a3b8;"><i class="fa-solid fa-phone"></i> {phone}</small>
                    {comment_html}
                </td>
                <td data-label="Заклад"><b>{partner_name}</b></td>
                <td data-label="Адреса">{job.dropoff_address}</td>
                <td data-label="Ціна">
                    <b style="color:#4ade80;">{job.order_price} ₴</b><br>
                    <small style="color:#94a3b8;">+{job.delivery_fee} ₴ дост.</small>
                </td>
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
                            <th>ID / Клієнт</th>
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

    details_html = ""
    if transactions_data is not None:
        details_html = """
        <div class="panel" style="margin-top: 20px;">
            <h2 style="margin-top: 0; color: white; display: flex; align-items: center; gap: 10px;">
                <i class="fa-solid fa-list-ul" style="color: #8b5cf6;"></i> Детальна фінансова історія та замовлення
            </h2>
            <div style="overflow-x:auto;">
                <table class="details-table">
                    <thead>
                        <tr>
                            <th style="min-width: 100px;">Час (Транзакція)</th>
                            <th style="min-width: 130px;">Кур'єр</th>
                            <th style="min-width: 150px;">Транзакція / Сума</th>
                            <th style="min-width: 300px;">Повна інформація про замовлення</th>
                            <th style="text-align: right; min-width: 180px;">Всі таймінги</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        if not transactions_data:
            details_html += "<tr><td colspan='5' style='text-align:center;'>Немає транзакцій за обраний період.</td></tr>"
        else:
            for txn, courier, job in transactions_data:
                t_created = format_local_time(txn.created_at, fmt='%d.%m %H:%M:%S')
                
                amount_val = f"{abs(txn.amount):.2f} ₴"
                if txn.type == 'commission':
                    badge = f'<span class="badge commission" style="display:block; text-align:center; margin-bottom:5px;">Списання (-{amount_val})</span>'
                elif txn.type == 'deposit' and txn.cash_received:
                    badge = f'<span class="badge deposit" style="display:block; text-align:center; margin-bottom:5px;">Готівка (+{amount_val})</span>'
                elif txn.type == 'deposit' and not txn.cash_received:
                    badge = f'<span class="badge bonus" style="display:block; text-align:center; margin-bottom:5px;">Безготівка/Бонус (+{amount_val})</span>'
                else:
                    badge = f'<span class="badge" style="background:#475569;color:white; display:block; text-align:center; margin-bottom:5px;">{txn.type} ({txn.amount})</span>'

                desc_html = f"<div style='font-size:0.8rem; color:#cbd5e1; text-align:center;'>{txn.description or '-'}</div>"

                job_info = "<div style='color:#94a3b8; font-style:italic;'>Без прив'язки до замовлення</div>"
                timings = "—"
                
                if job:
                    partner_name = job.partner.name if getattr(job, 'partner', None) else "Невідомо"
                    phone = getattr(job, 'customer_phone', 'Не вказано')
                    price = getattr(job, 'order_price', 0)
                    fee = getattr(job, 'delivery_fee', 0)
                    
                    job_comment = getattr(job, 'comment', '')
                    comment_html = f"<div style='margin-top:8px; padding:6px; background:rgba(250, 204, 21, 0.1); border-left:3px solid #facc15; color:#facc15; font-size:0.85rem;'><i class='fa-solid fa-comment'></i> <b>Коментар:</b> {job_comment}</div>" if job_comment else ""

                    rating_val = getattr(job, 'courier_rating', None)
                    review_val = getattr(job, 'courier_review', '')
                    rating_html = ""
                    if rating_val:
                        review_html_part = f'— <i>{review_val}</i>' if review_val else ''
                        rating_html = f"<div style='margin-top:6px; color:#fbbf24; font-size:0.85rem;'><i class='fa-solid fa-star'></i> <b>Оцінка:</b> {rating_val}/5 {review_html_part}</div>"

                    job_info = f"""
                    <div style="margin-bottom: 6px;">
                        <b style='color:#f8fafc; font-size: 1.15rem;'>#{job.id}</b> 
                        <span class="badge" style="background:#3b82f6; font-size: 0.75rem; margin-left:8px;">{job.status}</span>
                    </div>
                    <div style='color:#cbd5e1; font-size:0.9rem; margin-bottom: 4px;'><i class='fa-solid fa-store' style='width:20px; text-align:center;'></i> <b>Заклад:</b> {partner_name}</div>
                    <div style='color:#cbd5e1; font-size:0.9rem; margin-bottom: 4px;'><i class='fa-solid fa-location-dot' style='width:20px; text-align:center;'></i> <b>Адреса:</b> {job.dropoff_address}</div>
                    <div style='color:#94a3b8; font-size:0.9rem; margin-bottom: 4px;'><i class='fa-solid fa-phone' style='width:20px; text-align:center;'></i> {phone}</div>
                    <div style='color:#4ade80; font-size:0.95rem; font-weight:bold; margin-top:8px;'><i class='fa-solid fa-money-bill-wave' style='width:20px; text-align:center;'></i> Чек: {price} ₴ <span style='color:#94a3b8; font-weight:normal;'>| Доставка: {fee} ₴</span></div>
                    {comment_html}
                    {rating_html}
                    """
                    
                    t_j_c = format_local_time(job.created_at, fmt='%d.%m %H:%M:%S')
                    t_j_a = format_local_time(job.accepted_at, fmt='%d.%m %H:%M:%S')
                    t_j_arr = format_local_time(getattr(job, 'arrived_at_pickup_at', None), fmt='%d.%m %H:%M:%S')
                    t_j_pick = format_local_time(getattr(job, 'picked_up_at', None), fmt='%d.%m %H:%M:%S')
                    t_j_d = format_local_time(job.delivered_at, fmt='%d.%m %H:%M:%S')

                    timings = f"""
                    <div class="time-block"><span class="time-label">Створено:</span> <b>{t_j_c}</b></div>
                    <div class="time-block"><span class="time-label">Прийнято:</span> <b>{t_j_a}</b></div>
                    """
                    if getattr(job, 'arrived_at_pickup_at', None):
                        timings += f'<div class="time-block"><span class="time-label">В закладі:</span> <b>{t_j_arr}</b></div>'
                    if getattr(job, 'picked_up_at', None):
                        timings += f'<div class="time-block"><span class="time-label">Забрано:</span> <b style="color:#fbbf24;">{t_j_pick}</b></div>'
                    
                    if job.status == 'cancelled':
                        timings += f'<div class="time-block"><span class="time-label">Скасовано:</span> <b style="color:#ef4444;">{t_j_d}</b></div>'
                    else:
                        timings += f'<div class="time-block"><span class="time-label">Доставлено:</span> <b style="color:#4ade80;">{t_j_d}</b></div>'
                
                details_html += f"""
                <tr>
                    <td data-label="Час транзакції"><b>{t_created}</b></td>
                    <td data-label="Кур'єр"><b style="color:#f8fafc;">{courier.name}</b><br><small style="color:#64748b;">ID: {courier.id}</small></td>
                    <td data-label="Транзакція" class="cell-col">{badge}{desc_html}</td>
                    <td data-label="Замовлення">{job_info}</td>
                    <td data-label="Таймінги" class="cell-col" style="text-align: right;">{timings}</td>
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
        
        .details-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95rem; }}
        .details-table th, .details-table td {{ padding: 14px 15px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; vertical-align: middle; }}
        .details-table th {{ color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        .details-table tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
        
        .badge {{ padding: 5px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: bold; display: inline-block; }}
        .badge.commission {{ background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge.deposit {{ background: rgba(74, 222, 128, 0.15); color: #86efac; border: 1px solid rgba(74, 222, 128, 0.3); }}
        .badge.bonus {{ background: rgba(236, 72, 153, 0.15); color: #f9a8d4; border: 1px solid rgba(236, 72, 153, 0.3); }}

        .time-block {{ font-size: 0.85rem; color: #f8fafc; margin-bottom: 6px; display: flex; justify-content: flex-end; gap: 10px; }}
        .time-label {{ color: #94a3b8; }}

        @media (max-width: 800px) {{
            .details-table thead {{ display: none; }}
            .details-table tbody tr {{ display: block; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 15px; margin-bottom: 15px; }}
            .details-table td {{ display: flex; justify-content: space-between; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; flex-direction: column; gap: 5px; }}
            .details-table td:last-child {{ border-bottom: none; padding-bottom: 0; }}
            .details-table td::before {{ content: attr(data-label); font-weight: 600; color: #64748b; font-size: 0.85rem; margin-bottom: 5px; text-transform: uppercase; }}
            .cell-col {{ display: flex; flex-direction: column; align-items: flex-start !important; text-align: left !important; width: 100%; }}
            .time-block {{ justify-content: flex-start; width: 100%; }}
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

# =========================================================================================
# 2. HTML ШАБЛОН: АКТИВНІСТЬ ТА БОРГИ
# =========================================================================================

def get_activity_reports_html(low_balance_couriers, inactive_couriers, inactive_partners, days_inactive, tz_string="Europe/Kiev"):
    
    # Хелпер для рендерингу рядків кур'єрів з кнопками та формою поповнення
    def render_courier_row(c, last_date=None):
        phone_clean = c.phone.replace("+", "").replace(" ", "") if c.phone else ""
        status_color = "#4ade80" if c.is_active else "#facc15" 
        btn_action = "ban" if c.is_active else "unban"
        btn_icon = "fa-ban" if c.is_active else "fa-check"
        btn_class = "warn" if c.is_active else "success"
        
        last_seen = format_local_time(last_date, tz_string, '%d.%m %H:%M') if last_date else "Ніколи"
        balance_color = "#ef4444" if getattr(c, 'balance', 0.0) < 0 else "#4ade80"
        
        # Форма поповнення як на головній панелі
        finance_form = f"""
        <form action="/admin/delivery/courier/finance" method="post" style="margin:0; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); min-width: 200px;">
            <input type="hidden" name="id" value="{c.id}">
            <div style="display:flex; gap:5px; margin-bottom: 5px;">
                <input type="number" step="0.01" name="amount" placeholder="+ Сума" style="width:100%; padding:6px; border-radius:4px; background:#334155; border:none; color:white; font-size:0.85rem;" required>
                <button class="btn-mini success" style="background:#4ade80; color:#064e3b; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;" title="Поповнити баланс"><i class="fa-solid fa-plus"></i></button>
            </div>
            <label style="font-size: 0.75rem; color: #94a3b8; display:flex; align-items:center; gap:5px; cursor: pointer; margin-bottom: 5px;">
                <input type="checkbox" name="cash_received" value="true" checked onchange="document.getElementById('desc_{c.id}').required = !this.checked;"> Отримані гроші в касу
            </label>
            <input type="text" name="description" id="desc_{c.id}" placeholder="Коментар (якщо без галочки)" style="width:100%; padding:6px; border-radius:4px; background:#334155; border:none; color:white; font-size:0.8rem; box-sizing: border-box;">
        </form>
        """

        return f"""
        <tr>
            <td data-label="Кур'єр">
                <b style="color:#f8fafc;">{c.name}</b><br>
                <small style="color:#94a3b8;">{c.phone}</small>
            </td>
            <td data-label="Фінанси">
                <div style="color:{balance_color}; font-weight:bold; margin-bottom:5px; font-size: 1.1rem;">{getattr(c, 'balance', 0.0):.2f} ₴</div>
                {finance_form}
            </td>
            <td data-label="Статус">
                <span class="dot" style="background:{status_color}; display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px;"></span> 
                {last_seen}
            </td>
            <td data-label="Дії">
                <div style="display:flex; gap:5px; flex-wrap:wrap; align-items: center;">
                    <a href="https://t.me/+{phone_clean}" target="_blank" class="btn-mini info" style="background:#3b82f6; color:white; padding:6px 12px; border-radius:6px; text-decoration:none;" title="Написати в Telegram"><i class="fa-brands fa-telegram"></i></a>
                    <a href="/admin/delivery/courier/{c.id}/history" class="btn-mini info" style="background:#8b5cf6; color:white; padding:6px 12px; border-radius:6px; text-decoration:none;" title="Історія замовлень"><i class="fa-solid fa-list"></i></a>
                    <form action="/admin/delivery/courier/control" method="post" style="margin:0;">
                        <input type="hidden" name="id" value="{c.id}">
                        <input type="hidden" name="action" value="{btn_action}">
                        <button class="btn-mini {btn_class}" style="padding:6px 12px; border-radius:6px; border:none; cursor:pointer; color:white; background:{'#f59e0b' if btn_class=='warn' else '#4ade80'};" title="Заблокувати / Розблокувати"><i class="fa-solid {btn_icon}"></i></button>
                    </form>
                </div>
            </td>
        </tr>
        """

    low_balance_rows = "".join([render_courier_row(c) for c in low_balance_couriers])
    inactive_c_rows = "".join([render_courier_row(c, last_date) for c, last_date in inactive_couriers])
    
    inactive_p_rows = ""
    for p, last_order in inactive_partners:
        last_date_str = format_local_time(last_order, tz_string, '%d.%m.%Y') if last_order else "Ніколи"
        inactive_p_rows += f"""
        <tr>
            <td data-label="Заклад">
                <b style="color:#f8fafc;">{p.name}</b><br>
                <small style="color:#94a3b8;">{p.address}</small>
            </td>
            <td data-label="Останній раз">{last_date_str}</td>
            <td data-label="Телефон">{p.phone}</td>
            <td data-label="Дії">
                <a href="/admin/delivery/partner/{p.id}/history" class="btn-mini info" style="background:#8b5cf6; color:white; padding:6px 12px; border-radius:6px; text-decoration:none;" title="Історія замовлень"><i class="fa-solid fa-list"></i></a>
            </td>
        </tr>
        """

    # БЕЗПЕЧНІ HTML-БЛОКИ: Винесені з f-рядка для сумісності зі старими версіями Python
    if not low_balance_rows:
        low_balance_table = '<p style="color:#4ade80;">Всі кур\'єри мають позитивний баланс 🎉</p>'
    else:
        low_balance_table = f'<div class="table-wrapper"><table class="details-table"><thead><tr><th>Кур\'єр</th><th>Фінанси (Поповнити)</th><th>Статус</th><th>Дії</th></tr></thead><tbody>{low_balance_rows}</tbody></table></div>'

    if not inactive_c_rows:
        inactive_c_table = '<p style="color:#94a3b8;">Всі кур\'єри активні</p>'
    else:
        inactive_c_table = f'<div class="table-wrapper"><table class="details-table"><thead><tr><th>Кур\'єр</th><th>Фінанси (Поповнити)</th><th>Останній раз</th><th>Дії</th></tr></thead><tbody>{inactive_c_rows}</tbody></table></div>'

    if not inactive_p_rows:
        inactive_p_table = '<p style="color:#94a3b8;">Всі заклади активні</p>'
    else:
        inactive_p_table = f'<div class="table-wrapper"><table class="details-table"><thead><tr><th>Назва</th><th>Останній раз</th><th>Телефон</th><th>Дії</th></tr></thead><tbody>{inactive_p_rows}</tbody></table></div>'

    return f"""
    <!DOCTYPE html><html><head><title>Активність та Борги</title>{GLOBAL_STYLES}
    <style>
        .panel {{ background: #1e293b; padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }}
        .table-wrapper {{ overflow-x: auto; width: 100%; border-radius: 8px; }}
        .details-table {{ width: 100%; border-collapse: collapse; min-width: 600px; }}
        .details-table th, .details-table td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; vertical-align: middle; }}
        .details-table th {{ color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
        .details-table tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
        .btn-nav {{ display: inline-block; padding: 10px 20px; background: #4f46e5; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 0.9rem; }}
        
        @media (max-width: 900px) {{
            .details-table {{ min-width: 100%; }}
            .details-table thead {{ display: none; }}
            .details-table tbody tr {{ display: block; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 15px; margin-bottom: 15px; }}
            .details-table td {{ display: flex; flex-direction: column; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; }}
            .details-table td:last-child {{ border-bottom: none; }}
            .details-table td::before {{ content: attr(data-label); font-weight: bold; color: #94a3b8; font-size: 0.8rem; margin-bottom: 5px; text-transform: uppercase; }}
            .details-table td > div, .details-table td > form {{ width: 100%; }}
        }}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div style="max-width: 1300px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap: wrap; gap: 15px;">
                <h1 style="margin: 0; font-size: 1.5rem;"><i class="fa-solid fa-users-viewfinder"></i> Звіт: Активність та Борги</h1>
                <a href="/admin/delivery" class="btn-nav"><i class="fa-solid fa-arrow-left"></i> Панель керування</a>
            </div>

            <div class="panel" style="border-left: 5px solid #ef4444;">
                <h2 style="color: #fca5a5; margin-top: 0; display:flex; align-items:center; gap:10px;"><i class="fa-solid fa-wallet"></i> Боржники (Баланс < 30 грн)</h2>
                {low_balance_table}
            </div>

            <div class="panel">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;">
                    <h2 style="margin: 0; display:flex; align-items:center; gap:10px; color:white;"><i class="fa-solid fa-person-biking" style="color: #8b5cf6;"></i> Неактивні кур'єри</h2>
                    <form method="get" style="display:flex; gap:10px; align-items:center;">
                        <span style="color:#94a3b8; font-size: 0.9rem;">Не було замовлень більше (днів):</span>
                        <input type="number" name="days" value="{days_inactive}" min="1" max="365" style="width: 70px; padding: 8px; border-radius: 6px; background: #334155; color: white; border: 1px solid #475569;">
                        <button type="submit" style="padding: 8px 15px; background: #3b82f6; border:none; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">Застосувати</button>
                    </form>
                </div>
                {inactive_c_table}
            </div>

            <div class="panel">
                <h2 style="margin-top: 0; display:flex; align-items:center; gap:10px; color:white;"><i class="fa-solid fa-store" style="color: #f59e0b;"></i> Неактивні заклади (> {days_inactive} дн.)</h2>
                {inactive_p_table}
            </div>
        </div>
    </body></html>
    """

# =========================================================================================
# 3. ЕНДПОІНТИ (РОУТИ)
# =========================================================================================

@router.get("/admin/delivery/reports", response_class=HTMLResponse)
async def admin_reports_page(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    courier_id: str = "all",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
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
            
    if target_start_date > target_end_date:
        target_start_date, target_end_date = target_end_date, target_start_date
        
    start_date_str = target_start_date.strftime("%Y-%m-%d")
    end_date_str = target_end_date.strftime("%Y-%m-%d")

    start_of_day = datetime.combine(target_start_date, time.min)
    end_of_day = datetime.combine(target_end_date, time.max)

    couriers = (await db.execute(select(Courier).order_by(Courier.name))).scalars().all()

    job_conditions = [
        DeliveryJob.status == "delivered",
        DeliveryJob.delivered_at >= start_of_day,
        DeliveryJob.delivered_at <= end_of_day
    ]
    
    cancel_conditions = [
        DeliveryJob.status == "cancelled",
        DeliveryJob.created_at >= start_of_day,
        DeliveryJob.created_at <= end_of_day
    ]
    
    transaction_conditions = [
        CourierTransaction.created_at >= start_of_day,
        CourierTransaction.created_at <= end_of_day
    ]

    if courier_id and courier_id != "all" and courier_id.isdigit():
        c_id = int(courier_id)
        job_conditions.append(DeliveryJob.courier_id == c_id)
        cancel_conditions.append(DeliveryJob.courier_id == c_id) 
        transaction_conditions.append(CourierTransaction.courier_id == c_id)

    orders_query = select(func.count(DeliveryJob.id)).where(and_(*job_conditions))
    total_orders = (await db.execute(orders_query)).scalar() or 0

    cancelled_query = select(func.count(DeliveryJob.id)).where(and_(*cancel_conditions))
    total_cancelled = (await db.execute(cancelled_query)).scalar() or 0

    comm_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "commission")
    )
    total_commission_raw = (await db.execute(comm_query)).scalar() or 0.0
    total_commission = abs(total_commission_raw)

    real_money_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "deposit", CourierTransaction.cash_received == True)
    )
    real_money = (await db.execute(real_money_query)).scalar() or 0.0

    bonus_money_query = select(func.sum(CourierTransaction.amount)).where(
        and_(*transaction_conditions, CourierTransaction.type == "deposit", CourierTransaction.cash_received == False)
    )
    bonus_money = (await db.execute(bonus_money_query)).scalar() or 0.0

    details_query = select(CourierTransaction, Courier, DeliveryJob).join(
        Courier, CourierTransaction.courier_id == Courier.id
    ).outerjoin(
        DeliveryJob, CourierTransaction.job_id == DeliveryJob.id
    ).options(
        joinedload(DeliveryJob.partner)
    ).where(
        and_(*transaction_conditions)
    ).order_by(
        CourierTransaction.created_at.desc()
    )
    
    details_result = await db.execute(details_query)
    transactions_data = details_result.all()

    online_query = select(func.count(Courier.id)).where(Courier.is_online == True)
    online_count = (await db.execute(online_query)).scalar() or 0

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
        
        if job.accepted_at and job.delivered_at:
            delta = job.delivered_at - job.accepted_at
            courier_stats[cid]['total_seconds'] += delta.total_seconds()
            courier_stats[cid]['timed_orders'] += 1

    activity_data = []
    for cid, data in courier_stats.items():
        if data['timed_orders'] > 0:
            avg_seconds = data['total_seconds'] / data['timed_orders']
            avg_min = int(avg_seconds // 60)
        else:
            avg_min = 0
            
        activity_data.append({
            'courier_id': cid,
            'name': data['name'],
            'orders': data['orders'],
            'avg_time_min': avg_min
        })

    activity_data.sort(key=lambda x: x['orders'], reverse=True)

    unassigned_cancelled_jobs = []
    if courier_id == "all" or not courier_id:
        unassigned_cancel_conditions = [
            DeliveryJob.status == "cancelled",
            DeliveryJob.courier_id.is_(None), 
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

@router.get("/admin/delivery/activity", response_class=HTMLResponse)
async def admin_activity_report(
    days: int = 7,
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    tz_string = await get_setting(db, "timezone") or "Europe/Kiev"

    # 1. Боржники (баланс < 30)
    low_balance_query = select(Courier).where(Courier.balance < 30.0, Courier.is_active == True)
    low_balance_couriers = (await db.execute(low_balance_query)).scalars().all()

    # 2. Неактивні кур'єри
    subq_c = select(DeliveryJob.courier_id, func.max(DeliveryJob.created_at).label('last_date')).where(DeliveryJob.courier_id.is_not(None)).group_by(DeliveryJob.courier_id).subquery()
    c_query = select(Courier, subq_c.c.last_date).outerjoin(subq_c, Courier.id == subq_c.c.courier_id).where(
        Courier.is_active == True, or_(subq_c.c.last_date == None, subq_c.c.last_date < cutoff_date)
    ).order_by(subq_c.c.last_date.asc().nulls_first())
    inactive_couriers = (await db.execute(c_query)).all()

    # 3. Неактивні заклади
    subq_p = select(DeliveryJob.partner_id, func.max(DeliveryJob.created_at).label('last_date')).group_by(DeliveryJob.partner_id).subquery()
    p_query = select(DeliveryPartner, subq_p.c.last_date).outerjoin(subq_p, DeliveryPartner.id == subq_p.c.partner_id).where(
        DeliveryPartner.is_active == True, or_(subq_p.c.last_date == None, subq_p.c.last_date < cutoff_date)
    ).order_by(subq_p.c.last_date.asc().nulls_first())
    inactive_partners = (await db.execute(p_query)).all()

    return get_activity_reports_html(low_balance_couriers, inactive_couriers, inactive_partners, days, tz_string)