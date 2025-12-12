from typing import List, Dict
from templates_saas import GLOBAL_STYLES

# Импорт моделей для типизации (с заглушкой на случай циклических импортов)
try:
    from models import DeliveryPartner, DeliveryJob, Courier
except ImportError:
    class DeliveryPartner: pass
    class DeliveryJob: pass
    class Courier: pass

# --- Шаблоны для ПАРТНЕРОВ (Рестораны без сайта) ---

def get_partner_auth_html(is_register=False, message=""):
    """Страница входа/регистрации для Партнеров (с верификацией при регистрации)"""
    title = "Реєстрація Партнера" if is_register else "Вхід для Партнерів"
    action = "/partner/register" if is_register else "/partner/login"
    pwa_meta = '<link rel="manifest" href="/partner/manifest.json">'
    
    verify_script = ""
    verify_style = ""
    verify_block = ""
    phone_input = '<input type="text" name="phone" placeholder="Телефон" required>' 
    submit_attr = ""

    # Если регистрация - добавляем логику верификации
    if is_register:
        verify_style = """
        <style>
            .tg-verify-box { border: 2px dashed var(--border); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; background: rgba(255,255,255,0.02); transition: 0.3s; }
            .tg-verify-box.verified { border-color: var(--status-active); background: rgba(74, 222, 128, 0.1); }
            .tg-btn { background: #24A1DE; color: white; padding: 12px 20px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; gap: 10px; font-weight: 600; margin-top: 10px; transition: 0.2s; }
            .tg-btn:hover { background: #1b8bbf; transform: translateY(-2px); }
            .hidden { display: none; }
            .spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }
            @keyframes spin { to { transform: rotate(360deg); } }
        </style>
        """
        
        # Инпут телефона заменяем на скрытые поля
        phone_input = '<input type="hidden" name="phone" id="real_phone"><input type="hidden" name="verification_token" id="verification_token">'
        
        verify_block = """
        <div id="tg-step" class="tg-verify-box">
            <div id="tg-initial">
                <p style="margin:0 0 10px 0; color:var(--text-muted);">Підтвердіть номер через Telegram:</p>
                <a href="#" id="tg-link" target="_blank" class="tg-btn"><i class="fa-brands fa-telegram"></i> Підтвердити</a>
            </div>
            <div id="tg-waiting" class="hidden">
                <p style="margin:0; color:var(--text-muted);"><span class="spinner"></span> Очікуємо...</p>
                <small style="color:#666">Натисніть Start -> Share Contact</small>
            </div>
            <div id="tg-success" class="hidden">
                <div style="color: var(--status-active); font-size: 1.1rem; margin-bottom:5px;"><i class="fa-solid fa-circle-check"></i> Успішно!</div>
                <div id="user-phone-display" style="font-weight:bold; color:white;"></div>
            </div>
        </div>
        """
        submit_attr = "disabled"

        # JS скрипт
        verify_script = """
        <script>
            let verificationToken = "";
            let pollInterval = null;
            
            async function initVerification() {
                try {
                    const res = await fetch('/api/auth/init_verification', { method: 'POST' });
                    const data = await res.json();
                    verificationToken = data.token;
                    document.getElementById('verification_token').value = verificationToken;
                    
                    const linkBtn = document.getElementById('tg-link');
                    linkBtn.href = data.link;
                    
                    linkBtn.addEventListener('click', () => {
                        document.getElementById('tg-initial').classList.add('hidden');
                        document.getElementById('tg-waiting').classList.remove('hidden');
                        pollInterval = setInterval(checkStatus, 2000);
                    });
                } catch(e) { console.error(e); }
            }
            
            async function checkStatus() {
                try {
                    const res = await fetch(`/api/auth/check_verification/${verificationToken}`);
                    const data = await res.json();
                    if(data.status === 'verified') {
                        clearInterval(pollInterval);
                        document.getElementById('tg-waiting').classList.add('hidden');
                        document.getElementById('tg-success').classList.remove('hidden');
                        document.querySelector('.tg-verify-box').classList.add('verified');
                        
                        document.getElementById('user-phone-display').innerText = data.phone;
                        document.getElementById('real_phone').value = data.phone;
                        document.getElementById('submit-btn').disabled = false;
                    }
                } catch(e) {}
            }
            
            window.onload = initVerification;
        </script>
        """

    extra_fields = ""
    if is_register:
        extra_fields = f"""
        <input type="text" name="name" placeholder="Назва закладу" required>
        {phone_input}
        {verify_block}
        <input type="text" name="address" placeholder="Адреса закладу (місце забору)" required>
        """
    
    toggle_link = f'<a href="/partner/login">Вже є акаунт? Увійти</a>' if is_register else f'<a href="/partner/register">Стати партнером</a>'

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>{title}</title>{GLOBAL_STYLES}{pwa_meta}{verify_style}</head>
    <body><div class="container">
        <h1>🚴 Delivery Partner</h1>
        <p style="margin-top:-20px; margin-bottom:20px;">Кабінет для виклику кур'єрів</p>
        <form method="post" action="{action}">
            {extra_fields}
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit" class="btn" id="submit-btn" {submit_attr}>Продовжити</button>
        </form>
        {f"<div class='message error'>{message}</div>" if message else ""}
        {toggle_link}
        <a href="/" style="font-size: 0.9rem; color: var(--text-muted); margin-top: 15px;">← На головну</a>
    </div>
    {verify_script}
    </body></html>
    """

def get_partner_dashboard_html(partner: DeliveryPartner, jobs: List[DeliveryJob]):
    """
    Обновленный дашборд партнера.
    Включает:
    - Интерактивную карту Leaflet для выбора точки.
    - Умный поиск (Photon) с поддержкой опечаток.
    - Автоматический перелет маркера при выборе адреса.
    """
    
    # Разделяем активные и завершенные
    active_jobs = [j for j in jobs if j.status not in ['delivered', 'cancelled']]
    history_jobs = [j for j in jobs if j.status in ['delivered', 'cancelled']]
    
    # --- ТАБЛИЦА АКТИВНЫХ ЗАКАЗОВ ---
    active_rows = ""
    for j in active_jobs:
        track_btn = ""
        cancel_btn = f'<button class="btn-mini danger" onclick="cancelOrder({j.id})" title="Скасувати"><i class="fa-solid fa-ban"></i></button>'
        comm_btns = ""
        
        status_color = "#ccc"
        status_text = j.status
        courier_name_display = j.courier.name if j.courier else "—"
        courier_info = "—"

        if j.courier:
            courier_info = f"🚴 {courier_name_display}"
            phone_link = f"tel:{j.courier.phone}"
            comm_btns = f"""
            <a href="{phone_link}" class="btn-mini success" title="Зателефонувати"><i class="fa-solid fa-phone"></i></a>
            <button class="btn-mini info" onclick="openChat({j.id}, 'Кур\\'єр {j.courier.name}')" title="Чат"><i class="fa-solid fa-comments"></i></button>
            """
        
        # --- ЛОГИКА СТАТУСОВ ---
        if j.status == 'assigned':
            status_color = "#fef08a" # Yellow
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
        
        elif j.status == 'arrived_pickup':
            status_color = "#facc15" # Darker Yellow
            status_text = "👋 КУР'ЄР ЧЕКАЄ"
            courier_info = f"🚴 <b>{courier_name_display} (ТУТ)</b>"
            
        elif j.status == 'ready':
            status_color = "#86efac" # Green
            
        elif j.status == 'picked_up':
            status_color = "#bfdbfe" # Blue
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
            
        elif j.status == 'returning':
            status_color = "#fb923c" # Orange
            status_text = "↩️ ПОВЕРНЕННЯ"
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'

        # --- КНОПКА ДЕЙСТВИЯ (ACTION BTN) ---
        action_btn = ""
        
        if j.status == 'returning':
            # Если курьер возвращает деньги
            action_btn = f'''
            <button class="btn-mini success" onclick="confirmReturn({j.id})" title="Підтвердити отримання грошей" style="width:auto; padding:0 10px;">
                <i class="fa-solid fa-sack-dollar"></i> Отримав гроші
            </button>
            '''
        elif j.status in ['pending', 'assigned', 'arrived_pickup']:
            # Если еда еще не готова
            if j.status != 'ready':
                action_btn = f'''
                <button class="btn-mini success" onclick="markReady({j.id})" title="Повідомити про готовність">
                    <i class="fa-solid fa-utensils"></i> Готово
                </button>
                '''
            else:
                action_btn = '<span style="color:#4ade80; font-size:0.8rem; font-weight:bold; margin-right:5px;">🍳 Готово</span>'
        
        # Отображение оплаты
        payment_badges = {
            "prepaid": "<span style='color:#4ade80'>✅ Оплачено</span>",
            "cash": "<span style='color:#facc15'>💵 Готівка</span>",
            "buyout": "<span style='color:#f472b6'>💰 Викуп</span>"
        }
        pay_info = payment_badges.get(j.payment_type, j.payment_type)
        if getattr(j, 'is_return_required', False):
            pay_info += "<br><span style='color:#f97316; font-size:0.7rem;'>↺ Повернення</span>"

        active_rows += f"""
        <tr id="row-{j.id}">
            <td>#{j.id}</td>
            <td>{j.dropoff_address}</td>
            <td>
                <div>{j.order_price} грн</div>
                <div style="font-size:0.75rem;">{pay_info}</div>
            </td>
            <td><span class="status-badge" style="background:{status_color}; padding:3px 8px; border-radius:4px; font-size:0.8rem;">{status_text}</span></td>
            <td class="courier-cell">{courier_info}</td>
            <td>
                <div style="display:flex; gap:5px; align-items:center;">
                    {comm_btns}
                    {action_btn}
                    {track_btn}
                    {cancel_btn}
                </div>
            </td>
        </tr>
        """

    # --- ТАБЛИЦА ИСТОРИИ ---
    history_rows = ""
    for j in history_jobs:
        t_accept = j.accepted_at.strftime('%H:%M') if j.accepted_at else "-"
        t_pickup = j.picked_up_at.strftime('%H:%M') if j.picked_up_at else "-"
        t_deliver = j.delivered_at.strftime('%H:%M') if j.delivered_at else "-"
        
        rating_html = ""
        if j.status == 'delivered':
            if j.courier_rating:
                stars = "⭐" * j.courier_rating
                rating_html = f"<div title='{j.courier_review or ''}'>{stars}</div>"
            else:
                rating_html = f'<button class="btn-mini success" onclick="openRateModal({j.id})" title="Оцінити"><i class="fa-regular fa-star"></i></button>'
        elif j.status == 'cancelled':
            rating_html = "<span style='color:#f87171'>Скасовано</span>"

        history_rows += f"""
        <tr>
            <td>#{j.id}</td>
            <td>
                <div style="font-size:0.8rem">Прийняв: {t_accept}</div>
                <div style="font-size:0.8rem">Забрав: {t_pickup}</div>
                <div style="font-weight:bold; color:var(--status-active)">Довіз: {t_deliver}</div>
            </td>
            <td>
                <div>{j.dropoff_address}</div>
                <div style="font-size:0.8rem; color:#888;">{j.customer_name or 'Гість'}</div>
            </td>
            <td>{j.order_price} грн</td>
            <td>{rating_html}</td>
        </tr>
        """

    pwa_meta = '<link rel="manifest" href="/partner/manifest.json">'

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Кабінет Партнера</title>{GLOBAL_STYLES}{pwa_meta}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        .dashboard-grid {{ display: grid; grid-template-columns: 1fr 2fr; gap: 30px; max-width: 1200px; margin: 0 auto; width: 100%; }}
        @media (max-width: 900px) {{ .dashboard-grid {{ grid-template-columns: 1fr; }} }}
        .panel {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 25px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid var(--border); color: var(--text-main); }}
        th {{ color: var(--text-muted); font-weight: 600; }}
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto 30px; width: 90%; }}
        
        .btn-mini {{ border: 1px solid transparent; border-radius: 6px; width: 32px; height: 32px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; background: rgba(255,255,255,0.05); color: var(--text-muted); text-decoration: none; }}
        .btn-mini:hover {{ transform: translateY(-2px); }}
        .btn-mini.info:hover {{ background: #6366f1; color: white; }}
        .btn-mini.danger:hover {{ background: #e11d48; color: white; }}
        .btn-mini.success:hover {{ background: #4ade80; color: #064e3b; }}

        /* Модальні вікна */
        .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 2000; display: none; align-items: center; justify-content: center; backdrop-filter: blur(5px); }}
        .modal-card {{ background: #1e293b; width: 90%; max-width: 500px; border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; position: relative; padding: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }}
        .track-card {{ max-width: 800px; height: 60vh; padding: 0; }}
        #track-map {{ flex: 1; width: 100%; }}
        .track-header {{ padding: 15px; background: #0f172a; display: flex; justify-content: space-between; align-items: center; }}
        .close-btn {{ position: absolute; top: 15px; right: 15px; background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; }}
        
        /* Стилі чату */
        .chat-modal {{ height: 80vh; display: flex; flex-direction: column; }}
        .chat-messages {{ flex: 1; overflow-y: auto; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 10px; }}
        .msg {{ max-width: 80%; padding: 8px 12px; border-radius: 12px; font-size: 0.9rem; position: relative; }}
        .msg.me {{ align-self: flex-end; background: var(--primary); color: white; border-bottom-right-radius: 2px; }}
        .msg.other {{ align-self: flex-start; background: var(--bg-card-hover); color: var(--text-main); border-bottom-left-radius: 2px; }}
        .msg-time {{ font-size: 0.7rem; opacity: 0.7; text-align: right; margin-top: 4px; }}
        .chat-input-area {{ display: flex; gap: 10px; }}
        .chat-input-area input {{ margin-bottom: 0; }}

        /* Payment Options */
        .payment-options {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 15px; }}
        .payment-option input {{ display: none; }}
        .payment-option label {{ display: block; background: rgba(255,255,255,0.05); padding: 10px; text-align: center; border-radius: 8px; cursor: pointer; border: 1px solid transparent; font-size: 0.85rem; }}
        .payment-option input:checked + label {{ background: rgba(99, 102, 241, 0.2); border-color: var(--primary); color: white; font-weight: bold; }}
        
        .star-rating {{ display: flex; flex-direction: row-reverse; justify-content: center; gap: 5px; margin: 20px 0; }}
        .star-rating input {{ display: none; }}
        .star-rating label {{ cursor: pointer; font-size: 2rem; color: #444; transition: 0.2s; }}
        .star-rating input:checked ~ label, .star-rating label:hover, .star-rating label:hover ~ label {{ color: #fbbf24; }}

        #toast-container {{ position: fixed; top: 20px; right: 20px; z-index: 3000; }}
        .toast {{ background: #1e293b; color: white; padding: 15px 20px; border-left: 5px solid var(--primary); border-radius: 8px; margin-bottom: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); display: flex; align-items: center; gap: 15px; animation: slideIn 0.3s ease-out; min-width: 300px; }}
        @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
        
        /* --- НОВЫЕ СТИЛИ ДЛЯ ПОИСКА И КАРТЫ --- */
        .autocomplete-wrapper {{ position: relative; z-index: 1001; }}
        .autocomplete-results {{ position: absolute; top: 100%; left: 0; right: 0; background: #1e293b; border: 1px solid var(--border); border-top: none; border-radius: 0 0 10px 10px; max-height: 200px; overflow-y: auto; z-index: 9999; display: none; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .autocomplete-item {{ padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; color: #cbd5e1; display:flex; flex-direction:column; }}
        .autocomplete-item small {{ color: #64748b; font-size: 0.8rem; margin-top:2px; }}
        .autocomplete-item:hover {{ background: var(--primary); color: white; }}
        .autocomplete-item:hover small {{ color: rgba(255,255,255,0.7); }}
        
        /* Мини-карта в форме */
        #picker-map {{ width: 100%; height: 200px; border-radius: 10px; margin-bottom: 15px; border: 1px solid var(--border); z-index: 1; display:none; }}
        #picker-map.visible {{ display: block; }}
        .map-hint {{ font-size: 0.8rem; color: #facc15; margin-bottom: 10px; display:none; }}
    </style>
    </head>
    <body>
        <div id="toast-container"></div>
        
        <div style="width: 100%; padding: 20px;">
            <div class="header-bar">
                <div><h2 style="margin:0;">{partner.name}</h2><span style="color: var(--text-muted); font-size:0.9rem;">📍 {partner.address}</span></div>
                <a href="/partner/logout" class="btn" style="width:auto; padding: 8px 20px; background: #334155;">Вийти</a>
            </div>

            <div class="dashboard-grid">
                <div class="panel">
                    <h3>📦 Викликати кур'єра</h3>
                    <form action="/api/partner/create_order" method="post" autocomplete="off" id="orderForm">
                        
                        <label>Тип оплати та розрахунку</label>
                        <div class="payment-options">
                            <div class="payment-option">
                                <input type="radio" name="payment_type" id="pay_prepaid" value="prepaid" checked onchange="updateFormLogic()">
                                <label for="pay_prepaid">✅ Оплачено</label>
                            </div>
                            <div class="payment-option">
                                <input type="radio" name="payment_type" id="pay_cash" value="cash" onchange="updateFormLogic()">
                                <label for="pay_cash">💵 Готівка</label>
                            </div>
                            <div class="payment-option">
                                <input type="radio" name="payment_type" id="pay_buyout" value="buyout" onchange="updateFormLogic()">
                                <label for="pay_buyout">💰 Викуп</label>
                            </div>
                        </div>

                        <div id="cash-options" style="display:none; background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; margin-bottom:15px; border:1px solid var(--border);">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <input type="checkbox" id="return_check" name="is_return_required" value="true" style="width:auto; margin:0;" onchange="toggleReturnFee()">
                                <label for="return_check" style="margin:0; cursor:pointer;">
                                    Кур'єр має повернути гроші в заклад? (+40 грн)
                                </label>
                            </div>
                        </div>

                        <div id="buyout-hint" style="display:none; margin-bottom:15px; color:#f472b6; font-size:0.9rem; border:1px dashed #f472b6; padding:10px; border-radius:8px;">
                            <i class="fa-solid fa-circle-info"></i> <b>Порада:</b> При викупі кур'єр витрачає свої кошти. Рекомендуємо збільшити вартість доставки на 20-30 грн.
                        </div>

                        <div class="autocomplete-wrapper">
                            <label>Куди везти (Введіть вулицю або перетягніть пін)</label>
                            <input type="text" id="addr_input" name="dropoff_address" placeholder="Почніть вводити вулицю..." required autocomplete="off">
                            <div id="addr_results" class="autocomplete-results"></div>
                        </div>
                        
                        <div class="map-hint" id="map-hint"><i class="fa-solid fa-hand-pointer"></i> Ви можете уточнити точку на карті перетягуванням!</div>
                        <div id="picker-map"></div>
                        
                        <input type="hidden" name="lat" id="form_lat">
                        <input type="hidden" name="lon" id="form_lon">

                        <label>Телефон клієнта</label>
                        <input type="tel" name="customer_phone" placeholder="0XX XXX XX XX" required>
                        
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                            <div>
                                <label>Чек (грн)</label>
                                <input type="number" step="0.01" name="order_price" id="order_price" value="0">
                            </div>
                            <div>
                                <label>Доставка (грн)</label>
                                <input type="number" step="0.01" name="delivery_fee" id="delivery_fee" value="50">
                            </div>
                        </div>
                        
                        <label>Коментар (Під'їзд, поверх, код)</label>
                        <input type="text" name="comment" placeholder="Деталі...">
                        
                        <button type="submit" class="btn">🚀 Знайти кур'єра</button>
                    </form>
                </div>

                <div>
                    <div class="panel">
                        <h3>📋 Активні доставки</h3>
                        <div style="overflow-x:auto;">
                            <table>
                                <thead><tr><th>ID</th><th>Адреса</th><th>Інфо</th><th>Статус</th><th>Кур'єр</th><th>Дія</th></tr></thead>
                                <tbody>{active_rows}</tbody>
                            </table>
                        </div>
                    </div>

                    <div class="panel" style="opacity: 0.9;">
                        <h3>🕰️ Історія</h3>
                        <div style="overflow-x:auto; max-height: 500px;">
                            <table>
                                <thead><tr><th>ID</th><th>Таймінг</th><th>Деталі</th><th>Сума</th><th>Оцінка</th></tr></thead>
                                <tbody>{history_rows}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="trackModal" class="modal-overlay">
            <div class="modal-card track-card">
                <div class="track-header">
                    <div id="track-info">Пошук кур'єра...</div>
                    <button class="close-btn" style="position:static" onclick="closeTrackModal()">×</button>
                </div>
                <div id="track-map"></div>
            </div>
        </div>

        <div id="rateModal" class="modal-overlay">
            <div class="modal-card">
                <button class="close-btn" onclick="document.getElementById('rateModal').style.display='none'">×</button>
                <h2 style="text-align:center; margin-top:0;">Оцінити кур'єра</h2>
                <form id="rateForm" onsubmit="submitRating(event)">
                    <input type="hidden" id="rate_job_id" name="job_id">
                    <div class="star-rating">
                        <input type="radio" name="rating" id="star5" value="5"><label for="star5">★</label>
                        <input type="radio" name="rating" id="star4" value="4"><label for="star4">★</label>
                        <input type="radio" name="rating" id="star3" value="3"><label for="star3">★</label>
                        <input type="radio" name="rating" id="star2" value="2"><label for="star2">★</label>
                        <input type="radio" name="rating" id="star1" value="1"><label for="star1">★</label>
                    </div>
                    <textarea name="review" placeholder="Напишіть відгук" style="min-height:80px;"></textarea>
                    <button type="submit" class="btn" style="margin-top:15px;">Відправити</button>
                </form>
            </div>
        </div>

        <div id="chatModal" class="modal-overlay">
            <div class="modal-card chat-modal">
                <div class="track-header">
                    <div id="chat-title">Чат</div>
                    <button class="close-btn" style="position:static" onclick="document.getElementById('chatModal').style.display='none'">×</button>
                </div>
                <div id="chat-messages" class="chat-messages"></div>
                <form class="chat-input-area" onsubmit="sendChatMessage(event)">
                    <input type="hidden" id="chat_job_id">
                    <input type="text" id="chat_input" placeholder="Написати повідомлення..." autocomplete="off" required>
                    <button type="submit" class="btn" style="width:auto;"><i class="fa-solid fa-paper-plane"></i></button>
                </form>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // --- ЛОГИКА ОПЛАТЫ ---
            const baseFee = 50; 
            const returnFee = 40; 
            function updateFormLogic() {{
                const type = document.querySelector('input[name="payment_type"]:checked').value;
                const cashBlock = document.getElementById('cash-options');
                const buyoutHint = document.getElementById('buyout-hint');
                const returnCheck = document.getElementById('return_check');
                cashBlock.style.display = 'none'; buyoutHint.style.display = 'none';
                if (type === 'cash') cashBlock.style.display = 'block';
                else if (type === 'buyout') {{ buyoutHint.style.display = 'block'; returnCheck.checked = false; }} 
                else returnCheck.checked = false;
                toggleReturnFee(); 
            }}
            function toggleReturnFee() {{
                const returnCheck = document.getElementById('return_check');
                const feeInput = document.getElementById('delivery_fee');
                let currentFee = parseFloat(feeInput.value) || baseFee;
                if (returnCheck.checked) {{
                    if (currentFee < baseFee + returnFee) feeInput.value = baseFee + returnFee;
                }}
            }}
            
            // --- ЗВУК И TOAST ---
            const alertSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
            function showToast(text) {{
                const container = document.getElementById('toast-container');
                const toast = document.createElement('div');
                toast.className = 'toast';
                toast.innerHTML = `<i class="fa-solid fa-bell" style="color:#6366f1"></i> <div>${{text}}</div>`;
                container.appendChild(toast);
                setTimeout(() => {{ toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }}, 5000);
            }}

            // ==========================================
            // НОВЫЙ ПОИСК АДРЕСА (PHOTON + LEAFLET MAP)
            // ==========================================
            
            const addrInput = document.getElementById('addr_input');
            const addrResults = document.getElementById('addr_results');
            const latInput = document.getElementById('form_lat');
            const lonInput = document.getElementById('form_lon');
            const pickerMapDiv = document.getElementById('picker-map');
            const mapHint = document.getElementById('map-hint');
            
            let pickerMap, pickerMarker;
            let searchTimeout = null;

            // 1. Инициализация мини-карты (при первом фокусе или вводе)
            function initPickerMap(lat, lon) {{
                if (pickerMap) return;
                try {{
                    pickerMapDiv.classList.add('visible');
                    mapHint.style.display = 'block';
                    
                    // Центр карты: либо результат поиска, либо Киев по умолчанию
                    const startPos = (lat && lon) ? [lat, lon] : [50.45, 30.52];
                    
                    pickerMap = L.map('picker-map').setView(startPos, 13);
                    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(pickerMap);
                    
                    // Создаем перетаскиваемый маркер
                    pickerMarker = L.marker(startPos, {{draggable: true}}).addTo(pickerMap);
                    
                    // Слушаем перетаскивание
                    pickerMarker.on('dragend', function(e) {{
                        const pos = e.target.getLatLng();
                        latInput.value = pos.lat;
                        lonInput.value = pos.lng;
                    }});
                    
                    // Клик по карте перемещает маркер
                    pickerMap.on('click', function(e) {{
                        pickerMarker.setLatLng(e.latlng);
                        latInput.value = e.latlng.lat;
                        lonInput.value = e.latlng.lng;
                    }});
                    
                    // Фикс рендеринга Leaflet при появлении из display:none
                    setTimeout(() => pickerMap.invalidateSize(), 200);
                }} catch(e) {{
                    console.error("Leaflet init error:", e);
                }}
            }}

            // 2. Умный поиск через Photon
            addrInput.addEventListener('input', function() {{
                clearTimeout(searchTimeout);
                const query = this.value;
                
                // Показываем карту, если пользователь начал вводить
                if (!pickerMap) initPickerMap();

                if(query.length < 3) {{ addrResults.style.display = 'none'; return; }}
                
                searchTimeout = setTimeout(async () => {{
                    try {{
                        // ИСПРАВЛЕНИЕ: Убран параметр lang=uk, так как API его не поддерживает официально и выдает 400.
                        const url = `https://photon.komoot.io/api/?q=${{encodeURIComponent(query)}}&limit=5&lat=50.45&lon=30.52`;
                        console.log("Fetching address:", url); // Log URL for debugging
                        
                        const res = await fetch(url);
                        if (!res.ok) throw new Error("API Network Error: " + res.status);
                        const data = await res.json();
                        
                        addrResults.innerHTML = '';
                        if(data.features && data.features.length > 0) {{
                            data.features.forEach(feat => {{
                                const props = feat.properties;
                                const coords = feat.geometry.coordinates; // [lon, lat]
                                
                                const div = document.createElement('div');
                                div.className = 'autocomplete-item';
                                
                                // Формируем красивое название
                                let mainName = props.name || props.street || '';
                                if (props.housenumber) mainName += ', ' + props.housenumber;
                                
                                let subName = [props.city, props.country].filter(Boolean).join(', ');
                                
                                div.innerHTML = `<span>${{mainName}}</span><small>${{subName}}</small>`;
                                
                                div.onclick = () => {{ 
                                    addrInput.value = `${{mainName}}, ${{props.city || ''}}`;
                                    addrResults.style.display = 'none';
                                    
                                    // Обновляем карту и скрытые поля
                                    const lat = coords[1];
                                    const lon = coords[0];
                                    latInput.value = lat;
                                    lonInput.value = lon;
                                    
                                    // ПЕРЕМЕЩАЕМ МАРКЕР НА ВЫБРАННЫЙ АДРЕС
                                    if(pickerMap) {{
                                        pickerMarker.setLatLng([lat, lon]);
                                        pickerMap.setView([lat, lon], 16);
                                    }} else {{
                                        initPickerMap(lat, lon);
                                    }}
                                }};
                                addrResults.appendChild(div);
                            }});
                            addrResults.style.display = 'block';
                        }} else {{ addrResults.style.display = 'none'; }}
                    }} catch(e) {{
                        console.error("Address Search Error:", e);
                    }}
                }}, 400); // Debounce 400ms
            }});
            
            // Скрыть результаты при клике вне
            document.addEventListener('click', (e) => {{ 
                if(!addrInput.contains(e.target) && !addrResults.contains(e.target)) addrResults.style.display = 'none'; 
            }});
            
            // --- WEBSOCKET ---
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/partner`);
            
            socket.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                if (data.type === 'order_update') {{
                    alertSound.play().catch(e => {{}});
                    showToast(data.message);
                    setTimeout(() => location.reload(), 2000); 
                }} 
                else if (data.type === 'chat_message') {{
                    const openJobId = document.getElementById('chat_job_id').value;
                    const modalOpen = document.getElementById('chatModal').style.display === 'flex';
                    if (modalOpen && openJobId == data.job_id) {{
                        const container = document.getElementById('chat-messages');
                        const div = document.createElement('div');
                        div.className = 'msg other';
                        div.innerHTML = `${{data.text}} <div class="msg-time">${{data.time}}</div>`;
                        container.appendChild(div);
                        container.scrollTop = container.scrollHeight;
                    }} else {{
                         showToast(`💬 Нове повідомлення: ${{data.text}}`);
                    }}
                }}
            }};

            // --- CHAT LOGIC ---
            async function openChat(jobId, title) {{
                document.getElementById('chatModal').style.display = 'flex';
                document.getElementById('chat-title').innerText = title;
                document.getElementById('chat_job_id').value = jobId;
                document.getElementById('chat-messages').innerHTML = '<div style="text-align:center; color:#888">Завантаження...</div>';
                try {{
                    const res = await fetch(`/api/chat/history/${{jobId}}`);
                    const msgs = await res.json();
                    renderMessages(msgs);
                }} catch(e) {{}}
            }}
            function renderMessages(msgs) {{
                const container = document.getElementById('chat-messages');
                container.innerHTML = '';
                msgs.forEach(m => {{
                    const div = document.createElement('div');
                    div.className = `msg ${{m.role === 'partner' ? 'me' : 'other'}}`;
                    div.innerHTML = `${{m.text}} <div class="msg-time">${{m.time}}</div>`;
                    container.appendChild(div);
                }});
                container.scrollTop = container.scrollHeight;
            }}
            async function sendChatMessage(e) {{
                e.preventDefault();
                const input = document.getElementById('chat_input');
                const jobId = document.getElementById('chat_job_id').value;
                const text = input.value.trim();
                if(!text) return;
                input.value = '';
                const container = document.getElementById('chat-messages');
                const div = document.createElement('div');
                div.className = 'msg me';
                const time = new Date().toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}});
                div.innerHTML = `${{text}} <div class="msg-time">${{time}}</div>`;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
                const fd = new FormData();
                fd.append('job_id', jobId); fd.append('message', text); fd.append('role', 'partner');
                await fetch('/api/chat/send', {{method: 'POST', body: fd}});
            }}

            // --- CANCEL / READY / RETURN ---
            async function cancelOrder(jobId) {{
                if(!confirm("Скасувати це замовлення?")) return;
                const fd = new FormData(); fd.append('job_id', jobId);
                try {{ await fetch('/api/partner/cancel_order', {{method:'POST', body:fd}}); location.reload(); }} catch(e) {{}}
            }}
            async function markReady(jobId) {{
                if(!confirm("Підтвердити готовність?")) return;
                const fd = new FormData(); fd.append('job_id', jobId);
                try {{ await fetch('/api/partner/order_ready', {{method:'POST', body:fd}}); location.reload(); }} catch(e) {{}}
            }}
            async function confirmReturn(jobId) {{
                if(!confirm("Гроші отримано?")) return;
                const fd = new FormData(); fd.append('job_id', jobId);
                try {{ await fetch('/api/partner/confirm_return', {{method:'POST', body:fd}}); location.reload(); }} catch(e) {{}}
            }}

            // --- RATING ---
            function openRateModal(jobId) {{ document.getElementById('rate_job_id').value = jobId; document.getElementById('rateModal').style.display = 'flex'; }}
            async function submitRating(e) {{
                e.preventDefault(); const form = new FormData(e.target);
                try {{ await fetch('/api/partner/rate_courier', {{method:'POST', body:form}}); location.reload(); }} catch(e) {{}}
            }}

            // --- TRACKING ---
            let map, courierMarker, trackInterval;
            function openTrackModal(jobId) {{
                document.getElementById('trackModal').style.display = 'flex';
                if(!map) {{
                    map = L.map('track-map').setView([50.45, 30.52], 13);
                    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
                }}
                fetchLocation(jobId);
                trackInterval = setInterval(() => fetchLocation(jobId), 5000);
            }}
            function closeTrackModal() {{ document.getElementById('trackModal').style.display = 'none'; clearInterval(trackInterval); }}
            async function fetchLocation(jobId) {{
                try {{
                    const res = await fetch(`/api/partner/track_courier/${{jobId}}`);
                    const data = await res.json();
                    if(data.status === 'ok' && data.lat) {{
                        document.getElementById('track-info').innerHTML = `🚴 <b>${{data.name}}</b> • ${{data.job_status}}`;
                        const pos = [data.lat, data.lon];
                        if(!courierMarker) courierMarker = L.marker(pos).addTo(map); else courierMarker.setLatLng(pos);
                        map.setView(pos, 15);
                    }}
                }} catch(e) {{}}
            }}
        </script>
    </body>
    </html>
    """