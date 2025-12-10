import os
from typing import List, Dict

# Импорт моделей для типизации (с заглушкой на случай циклических импортов)
try:
    from models import User, Instance, Courier, DeliveryPartner, DeliveryJob
except ImportError:
    class User: pass
    class Instance: pass
    class Courier: pass
    class DeliveryPartner: pass
    class DeliveryJob: pass

# --- 1. Глобальные стили ---
GLOBAL_STYLES = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    :root {
        --bg-body: #0f172a;
        --bg-card: #1e293b;
        --bg-card-hover: #334155;
        --primary: #6366f1;
        --primary-hover: #4f46e5;
        --accent: #ec4899;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border: rgba(255, 255, 255, 0.1);
        --radius: 16px;
        --font: 'Inter', sans-serif;
        --transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        --status-active: #4ade80; 
        --status-suspended: #f87171; 
        --status-delete: #e11d48; 
    }
    body { 
        font-family: var(--font); 
        display: grid; 
        place-items: center; 
        min-height: 100vh; 
        background-color: var(--bg-body); 
        color: var(--text-main); 
        margin: 0; 
        padding: 20px 0; 
    }
    .container { 
        background: var(--bg-card); 
        border: 1px solid var(--border);
        border-radius: var(--radius); 
        box-shadow: 0 10px 40px rgba(0,0,0,0.3); 
        padding: 40px; 
        max-width: 420px; 
        width: 90%; 
        text-align: center; 
    }
    .logo-img {
        width: 150px;
        height: 150px;
        margin: 0 auto 20px;
        filter: invert(0.8);
    }
    h1 {
        color: var(--text-main);
        font-weight: 700;
        margin-bottom: 30px;
    }
    input, textarea { 
        width: 100%; 
        padding: 14px; 
        margin-bottom: 15px; 
        border: 1px solid var(--border); 
        border-radius: 10px; 
        box-sizing: border-box; 
        background: rgba(255,255,255,0.03);
        color: var(--text-main);
        font-family: var(--font);
        transition: 0.3s;
    }
    textarea {
        min-height: 150px;
        line-height: 1.6;
    }
    input:focus, textarea:focus {
        outline: none; 
        border-color: var(--primary); 
        background: rgba(99, 102, 241, 0.05); 
    }
    label {
        display: block;
        text-align: left;
        color: var(--text-muted);
        font-size: 0.9rem;
        margin-bottom: 5px;
    }
    .btn { 
        background: linear-gradient(135deg, var(--primary), var(--accent)); 
        color: white; 
        padding: 15px; 
        border: none; 
        border-radius: 10px; 
        cursor: pointer; 
        font-size: 16px; 
        font-weight: 600; 
        width: 100%; 
        transition: var(--transition);
        box-shadow: 0 4px 20px -5px rgba(99, 102, 241, 0.5);
        text-align: center;
        display: inline-block;
        text-decoration: none;
    }
    .btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px -5px rgba(99, 102, 241, 0.7);
    }
    .btn:disabled {
        background: #555;
        box-shadow: none;
        transform: none;
        cursor: not-allowed; 
    }
    a { 
        color: var(--primary); 
        text-decoration: none; 
        display: block; 
        margin-top: 25px; 
        font-weight: 500;
    }
    a:hover {
        text-decoration: underline;
    }
    .message { margin-top: 20px; font-weight: 600; padding: 10px; border-radius: 8px; }
    .error { color: #f87171; background: rgba(248, 113, 113, 0.1); border: 1px solid rgba(248, 113, 113, 0.3); }
    .success { color: #4ade80; background: rgba(74, 222, 128, 0.1); border: 1px solid rgba(74, 222, 128, 0.3); }
    hr { border:none; border-top: 1px solid var(--border); margin: 25px 0; }
    p { color: var(--text-muted); line-height: 1.6; }
    
    .form-hint {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-align: left;
        margin-top: -10px; 
        margin-bottom: 15px; 
    }
    .form-hint code {
        background: var(--bg-body);
        color: var(--accent);
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .form-hint strong {
        color: var(--text-main);
        font-weight: 500;
    }
</style>
"""

# Добавляем стили специально для карты и PWA
PWA_STYLES = """
<style>
    /* Отключаем скролл страницы, чтобы ощущалось как Native App */
    body, html { height: 100%; overflow: hidden; overscroll-behavior: none; }
    
    /* Карта на весь фон */
    #map { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
    
    /* Верхняя панель (Header) */
    .app-header {
        position: absolute; top: 0; left: 0; right: 0;
        background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(10px);
        padding: 15px 20px; z-index: 100;
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid var(--border);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .status-indicator { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 0.9rem; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #ccc; box-shadow: 0 0 10px currentColor; }
    .dot.online { background: var(--status-active); color: var(--status-active); }
    .dot.offline { background: var(--status-delete); color: var(--status-delete); }

    /* Кнопки меню */
    .icon-btn { background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer; padding: 5px; }

    /* ШТОРКА ЗАКАЗА (Bottom Sheet) */
    .bottom-sheet {
        position: absolute; bottom: 0; left: 0; right: 0;
        background: var(--bg-card);
        border-radius: 20px 20px 0 0;
        padding: 25px;
        z-index: 200;
        box-shadow: 0 -5px 30px rgba(0,0,0,0.4);
        transform: translateY(110%); /* Скрыта по умолчанию */
        transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        max-height: 80vh;
        overflow-y: auto;
    }
    .bottom-sheet.active { transform: translateY(0); }
    
    .drag-handle { width: 40px; height: 5px; background: rgba(255,255,255,0.2); border-radius: 5px; margin: 0 auto 20px; }

    /* Этапы заказа */
    .stepper { display: flex; margin-bottom: 20px; }
    .step { flex: 1; height: 4px; background: #334155; margin-right: 5px; border-radius: 2px; }
    .step.active { background: var(--primary); }
    .step.done { background: var(--status-active); }

    .sheet-title { font-size: 1.4rem; font-weight: 800; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
    .sheet-subtitle { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; }
    
    .info-block { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 15px; margin-bottom: 15px; border: 1px solid var(--border); }
    .info-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
    .info-value { font-size: 1.1rem; font-weight: 600; color: #f8fafc; }
    .info-value i { color: var(--primary); width: 20px; }

    /* Большие кнопки действий */
    .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
    .btn-nav { background: #3b82f6; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: 600; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; font-size: 1rem; }
    .btn-main { background: var(--status-active); color: #0f172a; border: none; padding: 15px; border-radius: 12px; font-weight: 700; width: 100%; font-size: 1.1rem; cursor: pointer; }
    
    /* Модалка истории */
    .history-modal {
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: var(--bg-body); z-index: 300;
        padding: 20px;
        transform: translateX(100%); transition: 0.3s;
        overflow-y: auto;
    }
    .history-modal.open { transform: translateX(0); }
    .history-item { padding: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; }
    .history-price { color: var(--status-active); font-weight: bold; }
</style>
"""

# --- 2. Шаблоны страниц Авторизации (ДЛЯ ВЛАДЕЛЬЦЕВ SaaS) ---

def get_login_page(message: str = "", msg_type: str = "error"):
    """HTML для страницы входа /login"""
    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Вхід</title>{GLOBAL_STYLES}</head>
    <body><div class="container">
        <img src="/static/logo.png" alt="Restify Logo" class="logo-img">
        <h1>Вхід у Restify</h1>
        <form method="post" action="/token">
            <input type="email" name="username" placeholder="Ваш Email" required>
            <input type="password" name="password" placeholder="Ваш пароль" required>
            <button type="submit" class="btn">Увійти</button>
        </form>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <a href="/register">У мене немає акаунта</a>
        <a href="/" style="font-size: 0.9rem; color: var(--text-muted); margin-top: 15px;">← На головну</a>
    </div></body></html>
    """

def get_register_page():
    """HTML для сторінки реєстрації з Telegram Verification"""
    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Реєстрація</title>{GLOBAL_STYLES}
    <style>
        .tg-verify-box {{
            border: 2px dashed var(--border);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
            background: rgba(255,255,255,0.02);
            transition: 0.3s;
        }}
        .tg-verify-box.verified {{
            border-color: var(--status-active);
            background: rgba(74, 222, 128, 0.1);
        }}
        .tg-btn {{
            background: #24A1DE;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            margin-top: 10px;
            transition: 0.2s;
        }}
        .tg-btn:hover {{ background: #1b8bbf; transform: translateY(-2px); }}
        .hidden {{ display: none; }}
        
        .spinner {{ display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
    </head>
    <body><div class="container">
        <img src="/static/logo.png" alt="Restify Logo" class="logo-img">
        <h1>Створити акаунт</h1>
        
        <form id="registerForm" method="post" action="/api/register">
            <input type="email" name="email" placeholder="Ваш Email" required>
            <input type="password" name="password" placeholder="Придумайте пароль" required>
            
            <div id="tg-step" class="tg-verify-box">
                <div id="tg-initial">
                    <p style="margin:0 0 10px 0; color:var(--text-muted);">Для захисту від ботів, підтвердіть номер:</p>
                    <a href="#" id="tg-link" target="_blank" class="tg-btn">
                        <i class="fa-brands fa-telegram"></i> Підтвердити в Telegram
                    </a>
                </div>
                
                <div id="tg-waiting" class="hidden">
                    <p style="margin:0; color:var(--text-muted);">
                        <span class="spinner"></span> Очікуємо підтвердження...
                    </p>
                    <small style="color:#666">Натисніть "Start" та "Share Contact" у боті</small>
                </div>

                <div id="tg-success" class="hidden">
                    <div style="color: var(--status-active); font-size: 1.2rem; margin-bottom: 5px;">
                        <i class="fa-solid fa-circle-check"></i> Підтверджено!
                    </div>
                    <div id="user-phone" style="font-weight:bold; color:white;"></div>
                </div>
            </div>

            <input type="hidden" name="verification_token" id="verification_token">

            <button type="submit" class="btn" id="submitBtn" disabled>Зареєструватися</button>
            <div id="response-msg" class="message" style="display: none;"></div>
        </form>
        <a href="/login">У мене вже є акаунт</a>
    </div>
    
    <script>
        let verificationToken = "";
        let pollInterval = null;

        // 1. Ініціалізація: Отримуємо токен і посилання на бота
        async function initVerification() {{
            try {{
                const res = await fetch('/api/auth/init_verification', {{ method: 'POST' }});
                const data = await res.json();
                
                verificationToken = data.token;
                document.getElementById('verification_token').value = verificationToken;
                
                const linkBtn = document.getElementById('tg-link');
                linkBtn.href = data.link;
                
                // Коли юзер клікає на посилання -> починаємо опитування
                linkBtn.addEventListener('click', () => {{
                    document.getElementById('tg-initial').classList.add('hidden');
                    document.getElementById('tg-waiting').classList.remove('hidden');
                    startPolling();
                }});
                
            }} catch(e) {{ console.error("Error init verification", e); }}
        }}

        // 2. Опитування статусу (Polling)
        function startPolling() {{
            pollInterval = setInterval(async () => {{
                try {{
                    const res = await fetch(`/api/auth/check_verification/${{verificationToken}}`);
                    const data = await res.json();
                    
                    if(data.status === 'verified') {{
                        clearInterval(pollInterval);
                        showSuccess(data.phone);
                    }}
                }} catch(e) {{ console.error("Polling error", e); }}
            }}, 2000); // Перевіряємо кожні 2 секунди
        }}

        // 3. Успіх
        function showSuccess(phone) {{
            document.getElementById('tg-waiting').classList.add('hidden');
            document.getElementById('tg-success').classList.remove('hidden');
            
            const box = document.querySelector('.tg-verify-box');
            box.classList.add('verified');
            
            document.getElementById('user-phone').innerText = phone;
            document.getElementById('submitBtn').disabled = false; // Розблокуємо кнопку
        }}

        // Запускаємо при завантаженні
        initVerification();

        // 4. Стандартна відправка форми
        document.getElementById('registerForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const form = e.target;
            const btn = document.getElementById('submitBtn');
            const msgEl = document.getElementById('response-msg');
            btn.disabled = true; btn.textContent = 'Реєстрація...';
            msgEl.style.display = 'none';
            
            try {{
                const response = await fetch('/api/register', {{
                    method: 'POST',
                    body: new FormData(form)
                }});
                const result = await response.json();
                msgEl.style.display = 'block';
                
                if (response.ok) {{
                    msgEl.className = 'message success';
                    msgEl.innerHTML = `✅ <strong>Успішно!</strong> Перенаправляємо...`;
                    setTimeout(() => {{ window.location.href = '/login?message=Акаунт створено!&type=success'; }}, 2000);
                }} else {{
                    msgEl.className = 'message error';
                    msgEl.textContent = result.detail || 'Помилка.';
                    btn.disabled = false; btn.textContent = 'Зареєструватися';
                }}
            }} catch (err) {{
                msgEl.style.display = 'block'; msgEl.className = 'message error';
                msgEl.textContent = 'Помилка мережі.';
                btn.disabled = false; btn.textContent = 'Зареєструватися';
            }}
        }});
    </script>
    </body></html>
    """

# --- 3. Шаблоны для ПАРТНЕРОВ (Рестораны без сайта) ---

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
    Обновленный дашборд партнера с картой трекинга, WebSocket уведомлениями и звуком
    """
    
    # Генерация таблицы с кнопкой "Следить"
    jobs_rows = ""
    for j in sorted(jobs, key=lambda x: x.id, reverse=True):
        track_btn = ""
        status_color = "#ccc"
        
        if j.status == 'assigned' or j.status == 'picked_up':
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
            status_color = "#fef08a" if j.status == 'assigned' else "#bfdbfe"
        
        courier_name = f"ID {j.courier_id}" if j.courier_id else "—"

        jobs_rows += f"""
        <tr id="row-{j.id}">
            <td>#{j.id}</td>
            <td>{j.dropoff_address}</td>
            <td>{j.order_price} грн</td>
            <td><span class="status-badge" style="background:{status_color}; padding:3px 8px; border-radius:4px; font-size:0.8rem;">{j.status}</span></td>
            <td class="courier-cell">{courier_name}</td>
            <td>{track_btn}</td>
        </tr>
        """

    # --- PWA META (Manifest) ---
    pwa_meta = '<link rel="manifest" href="/partner/manifest.json">'
    # ---------------------------

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Кабінет Партнера</title>{GLOBAL_STYLES}{pwa_meta}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        .dashboard-grid {{ display: grid; grid-template-columns: 1fr 2fr; gap: 30px; max-width: 1200px; margin: 0 auto; width: 100%; }}
        @media (max-width: 768px) {{ .dashboard-grid {{ grid-template-columns: 1fr; }} }}
        .panel {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 25px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid var(--border); color: var(--text-main); }}
        th {{ color: var(--text-muted); font-weight: 600; }}
        .header-bar {{ display: flex; justify-content: space-between; align-items: center; max-width: 1200px; margin: 0 auto 30px; width: 90%; }}
        
        .btn-mini {{
            border: 1px solid transparent;
            border-radius: 6px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
            background: rgba(255,255,255,0.05);
            color: var(--text-muted);
        }}
        .btn-mini:hover {{ transform: translateY(-2px); }}
        .btn-mini.info:hover {{ background: #6366f1; color: white; }}

        /* Модальное окно карты */
        .track-modal {{
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); z-index: 2000;
            display: none; align-items: center; justify-content: center;
        }}
        .track-card {{
            background: #1e293b; width: 90%; max-width: 800px; height: 60vh;
            border-radius: 16px; overflow: hidden; display: flex; flex-direction: column;
            position: relative;
        }}
        #track-map {{ flex: 1; width: 100%; }}
        .track-header {{ padding: 15px; background: #0f172a; display: flex; justify-content: space-between; align-items: center; }}
        .close-btn {{ background: none; border: none; color: white; font-size: 1.5rem; cursor: pointer; }}
        
        /* Стилі для спливаючих повідомлень (Toasts) */
        #toast-container {{
            position: fixed; top: 20px; right: 20px; z-index: 3000;
        }}
        .toast {{
            background: #1e293b; color: white; padding: 15px 20px; 
            border-left: 5px solid var(--primary);
            border-radius: 8px; margin-bottom: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            display: flex; align-items: center; gap: 15px;
            animation: slideIn 0.3s ease-out;
            min-width: 300px;
        }}
        @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
    </style>
    </head>
    <body>
        <div id="toast-container"></div>
        
        <div style="width: 100%; padding: 20px;">
            <div class="header-bar">
                <div>
                    <h2 style="margin:0;">{partner.name}</h2>
                    <span style="color: var(--text-muted); font-size:0.9rem;">📍 {partner.address}</span>
                </div>
                <a href="/partner/logout" class="btn" style="width:auto; padding: 8px 20px; background: #334155;">Вийти</a>
            </div>

            <div class="dashboard-grid">
                <div class="panel">
                    <h3>📦 Викликати кур'єра</h3>
                    <form action="/api/partner/create_order" method="post">
                        <label>Куди везти (Адреса клієнта)</label>
                        <input type="text" name="dropoff_address" placeholder="Вулиця, будинок, під'їзд" required>
                        
                        <label>Телефон клієнта</label>
                        <input type="tel" name="customer_phone" placeholder="0XX XXX XX XX" required>
                        
                        <label>Ім'я клієнта</label>
                        <input type="text" name="customer_name" placeholder="Ім'я">
                        
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                            <div>
                                <label>Сума чеку (грн)</label>
                                <input type="number" step="0.01" name="order_price" value="0">
                            </div>
                            <div>
                                <label>Доставка (грн)</label>
                                <input type="number" step="0.01" name="delivery_fee" value="50">
                            </div>
                        </div>
                        
                        <label>Коментар для кур'єра</label>
                        <input type="text" name="comment" placeholder="Код домофону, поверх...">
                        
                        <button type="submit" class="btn">🚀 Знайти кур'єра</button>
                    </form>
                </div>

                <div class="panel">
                    <h3>📋 Активні доставки</h3>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr><th>ID</th><th>Адреса</th><th>Сума</th><th>Статус</th><th>Кур'єр</th><th>Дія</th></tr>
                            </thead>
                            <tbody>
                                {jobs_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div id="trackModal" class="track-modal">
            <div class="track-card">
                <div class="track-header">
                    <div id="track-info">Пошук курь'єра...</div>
                    <button class="close-btn" onclick="closeTrackModal()">×</button>
                </div>
                <div id="track-map"></div>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // --- ЗВУК ПОВІДОМЛЕННЯ ---
            const alertSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');

            // --- WEBSOCKET ДЛЯ ПАРТНЕРА ---
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/partner`);

            socket.onopen = () => console.log("Connected to Partner WS");
            
            socket.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'order_update') {{
                    // 1. Програти звук
                    alertSound.play().catch(e => console.log('Audio error:', e));

                    // 2. Показати тост
                    showToast(data.message);

                    // 3. Оновити рядок таблиці
                    updateTableRow(data);
                }}
            }};

            function showToast(text) {{
                const container = document.getElementById('toast-container');
                const toast = document.createElement('div');
                toast.className = 'toast';
                toast.innerHTML = `<i class="fa-solid fa-bell" style="color:#6366f1"></i> <div>${{text}}</div>`;
                container.appendChild(toast);
                
                // Видалити через 5 секунд
                setTimeout(() => {{
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                }}, 5000);
            }}

            function updateTableRow(data) {{
                const row = document.getElementById(`row-${{data.job_id}}`);
                if (row) {{
                    // Оновлюємо статус (4-й стовпчик)
                    const statusSpan = row.cells[3].querySelector('.status-badge');
                    if(statusSpan) {{
                        statusSpan.innerText = data.status_text;
                        statusSpan.style.background = data.status_color;
                    }}
                    
                    // Оновлюємо ім'я кур'єра (5-й стовпчик)
                    if(data.courier_name) {{
                         const courierCell = row.cells[4];
                         if (courierCell) courierCell.innerText = `🚴 ${{data.courier_name}}`;
                    }}
                }}
            }}

            let map, courierMarker;
            let trackInterval;

            function openTrackModal(jobId) {{
                document.getElementById('trackModal').style.display = 'flex';
                
                if(!map) {{
                    map = L.map('track-map').setView([50.45, 30.52], 13);
                    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
                }}
                
                // Запускаем опрос
                fetchLocation(jobId);
                trackInterval = setInterval(() => fetchLocation(jobId), 5000);
            }}

            function closeTrackModal() {{
                document.getElementById('trackModal').style.display = 'none';
                clearInterval(trackInterval);
            }}

            async function fetchLocation(jobId) {{
                try {{
                    const res = await fetch(`/api/partner/track_courier/${{jobId}}`);
                    const data = await res.json();
                    
                    const infoDiv = document.getElementById('track-info');
                    
                    if(data.status === 'waiting') {{
                        infoDiv.innerText = "Кур'єр ще не призначений";
                        return;
                    }}
                    
                    if(data.status === 'ok' && data.lat) {{
                        infoDiv.innerHTML = `🚴 <b>${{data.name}}</b> (${{data.phone}}) • Статус: ${{data.job_status}}`;
                        const pos = [data.lat, data.lon];
                        
                        if(!courierMarker) {{
                            courierMarker = L.marker(pos).addTo(map).bindPopup("Кур'єр тут");
                        }} else {{
                            courierMarker.setLatLng(pos);
                        }}
                        map.setView(pos, 15);
                    }}
                }} catch(e) {{ console.error(e); }}
            }}
        </script>
    </body>
    </html>
    """

# --- 4. Шаблон Дашборда (ДЛЯ ВЛАДЕЛЬЦЕВ SaaS) ---

def get_dashboard_html(user: User, instances: List[Instance]):
    """HTML для Личного Кабинета Клиента SaaS (/dashboard)"""
    
    project_cards_html = ""
    if not instances:
        project_cards_html = "<p style='text-align: center; color: var(--text-muted);'>У вас поки немає проектів. Створіть свій перший проект, використовуючи форму вище.</p>"
    else:
        # Сортируем: сначала новые
        for instance in sorted(instances, key=lambda x: x.created_at, reverse=True):
            status_color = "var(--status-active)" if instance.status == "active" else "var(--status-suspended)"
            
            # Кнопки управления
            stop_disabled = "disabled" if instance.status != "active" else ""
            start_disabled = "disabled" if instance.status == "active" else ""

            project_cards_html += f"""
            <div class="project-card" id="instance-card-{instance.id}">
                <div class="project-header">
                    <a href="{instance.url}" target="_blank">{instance.subdomain}</a>
                    <span class="project-status" style="background-color: {status_color};" id="status-badge-{instance.id}">
                        {instance.status}
                    </span>
                </div>
                <div class="project-body">
                    <p><strong>Адмінка:</strong> <a href="{instance.url}/admin" target="_blank">{instance.url}/admin</a></p>
                    <p><strong>Логін:</strong> admin</p>
                    <p><strong>Пароль:</strong> {instance.admin_pass}</p>
                    <p><strong>Оплачено до:</strong> {instance.next_payment_due.strftime('%Y-%m-%d')}</p>
                </div>
                <div class="project-footer">
                    <button class="btn-action" onclick="controlInstance({instance.id}, 'stop')" id="btn-stop-{instance.id}" {stop_disabled}>
                        <i class="fa-solid fa-stop"></i> Stop
                    </button>
                    <button class="btn-action btn-start" onclick="controlInstance({instance.id}, 'start')" id="btn-start-{instance.id}" {start_disabled}>
                        <i class="fa-solid fa-play"></i> Start
                    </button>
                    <button class="btn-action btn-renew" disabled>
                        <i class="fa-solid fa-credit-card"></i> Продовжити
                    </button>
                    <button class="btn-action btn-delete" onclick="deleteInstance({instance.id}, '{instance.subdomain}')">
                        <i class="fa-solid fa-trash"></i> Видалити
                    </button>
                </div>
            </div>
            """

    return f"""
    <!DOCTYPE html><html lang="uk">
    <head>
        <title>Особистий кабінет</title>
        {GLOBAL_STYLES}
        <style>
            /* Перевизначення стилів для дашборда */
            body {{ display: block; padding: 20px; }}
            .dashboard-container {{
                margin: 0 auto;
                max-width: 900px;
                width: 100%;
            }}
            .dashboard-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}
            .dashboard-header h1 {{ margin: 0; font-size: 1.8rem; }}
            .dashboard-header a {{ margin: 0; font-size: 0.9rem; color: #f87171; }}
            
            /* Стилі для картки створення */
            .create-card {{
                background: var(--bg-card); 
                border: 1px solid var(--border);
                border-radius: var(--radius); 
                padding: 30px; 
                margin-bottom: 30px;
            }}
            .create-card h2 {{ margin-top: 0; }}
            .create-card form {{ text-align: left; }}
            .create-card .btn {{ margin-top: 15px; }}
            /* Поділ полів токенів */
            .token-fields {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            @media (min-width: 600px) {{
                .token-fields {{ grid-template-columns: 1fr 1fr; }}
            }}

            /* Стилі для списку проектів */
            .projects-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
            }}
            .project-card {{
                background: var(--bg-card); 
                border: 1px solid var(--border);
                border-radius: var(--radius); 
                display: flex;
                flex-direction: column;
                transition: var(--transition);
            }}
            .project-card:hover {{ border-color: var(--primary); }}
            .project-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 25px;
                border-bottom: 1px solid var(--border);
            }}
            .project-header a {{
                font-size: 1.2rem;
                font-weight: 600;
                margin: 0;
            }}
            .project-status {{
                font-size: 0.8rem;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 20px;
                color: #0f172a;
                text-transform: capitalize;
            }}
            .project-body {{
                padding: 25px;
                flex-grow: 1;
            }}
            .project-body p {{
                margin: 0 0 10px 0;
                color: var(--text-muted);
                font-size: 0.95rem;
            }}
            .project-body p strong {{ color: var(--text-main); font-weight: 500; }}
            .project-body p a {{ display: inline; margin: 0; }}

            .project-footer {{
                display: flex;
                gap: 10px;
                padding: 0 25px 25px 25px;
                border-top: 1px solid var(--border);
                padding-top: 20px;
            }}
            .btn-action {{
                flex-grow: 1;
                background: var(--bg-card-hover);
                border: 1px solid var(--border);
                color: var(--text-muted);
                padding: 10px;
                border-radius: 8px;
                cursor: pointer;
                font-family: var(--font);
                font-size: 0.9rem;
                font-weight: 600;
                transition: var(--transition);
            }}
            .btn-action:hover:not(:disabled) {{
                background: var(--bg-body);
                color: var(--text-main);
                border-color: #444;
            }}
            .btn-action.btn-start:hover:not(:disabled) {{ color: var(--status-active); border-color: var(--status-active); }}
            .btn-action:disabled {{
                opacity: 0.4;
                cursor: not-allowed;
            }}
            .btn-action.btn-renew {{
                background: var(--primary);
                border-color: var(--primary);
                color: white;
            }}
            .btn-action.btn-renew:hover:not(:disabled) {{ background: var(--primary-hover); }}
            
            .btn-action.btn-delete {{
                background: rgba(225, 29, 72, 0.1);
                border-color: rgba(225, 29, 72, 0.3);
                color: var(--status-delete);
                flex-grow: 0;
                padding: 10px 15px;
            }}
            .btn-action.btn-delete:hover:not(:disabled) {{
                background: var(--status-delete);
                border-color: var(--status-delete);
                color: white;
            }}
            .btn-action i {{ margin-right: 8px; }}
        </style>
    </head>
    <body>
        <div class="dashboard-container">
            <div class="dashboard-header">
                <h1>Вітаю, {user.email}!</h1>
                <a href="/logout">Вийти</a>
            </div>

            <div class="create-card">
                <h2><i class="fa-solid fa-plus" style="color: var(--primary);"></i> Створити новий проект</h2>
                <form id="createInstanceForm" method="post" action="/api/create-instance">
                    
                    <label for="name">Назва проекту (Тільки латиниця, без пробілів)</label>
                    <input type="text" name="name" id="name" placeholder="Наприклад: 'moybiznes' або 'romashka'" required>
                    <p class="form-hint">Ця назва буде використана для створення вашого унікального домену: <code>moybiznes.restify.site</code></p>
                    
                    <label for="phone">Ваш контактний телефон</label>
                    <input type="tel" name="phone" id="phone" placeholder="Ми повідомимо, коли проект буде готовий" required>
                    <p class="form-hint">Використовується тільки для повідомлень вам про статус створення.</p>

                    <hr>
                    <h3>Налаштування Telegram Ботів</h3>
                    <p class="form-hint" style="margin-top: 0; margin-bottom: 20px;">Введіть токени ваших ботів, отримані від <code>@BotFather</code>. Ви зможете змінити їх пізніше в адмін-панелі вашого проекту.</p>
                    
                    <div class="token-fields">
                        <div>
                            <label for="client_bot_token">Токен Клієнт-Бота (для замовлень)</label>
                            <input type="text" name="client_bot_token" id="client_bot_token" placeholder="123456:ABC-..." required>
                        </div>
                        <div>
                            <label for="admin_bot_token">Токен Адмін-Бота (для персоналу)</label>
                            <input type="text" name="admin_bot_token" id="admin_bot_token" placeholder="789123:XYZ-..." required>
                        </div>
                    </div>
                    
                    <label for="admin_chat_id">Admin Chat ID (для сповіщень)</label>
                    <input type="text" name="admin_chat_id" id="admin_chat_id" placeholder="-100123..." required>
                    <p class="form-hint">ID вашого Telegram-каналу або групи, куди будуть приходити замовлення. (Дізнайтеся у <code>@GetMyID_bot</code>)</p>
                    
                    <button type="submit" class="btn" id="submitBtn">🚀 Запустити проект</button>
                    <div id="response-msg" class="message" style="display: none; margin-top: 20px;"></div>
                </form>
            </div>

            <hr>
            
            <h2 style="margin-bottom: 20px;">Ваші проекти</h2>
            <div class="projects-grid" id="projects-grid-container">
                {project_cards_html}
            </div>
        </div>

        <script>
        // --- JS для форми створення ---
        const form = document.getElementById('createInstanceForm');
        if (form) {{
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                const msgEl = document.getElementById('response-msg');
                btn.disabled = true;
                btn.textContent = 'Запускаємо... (Це може зайняти 2-3 хвилини)';
                msgEl.style.display = 'none'; msgEl.textContent = '';
                
                try {{
                    const response = await fetch('/api/create-instance', {{
                        method: 'POST', body: new FormData(form)
                    }});
                    const result = await response.json();
                    
                    if (response.ok) {{
                        msgEl.style.display = 'block';
                        msgEl.className = 'message success';
                        msgEl.innerHTML = `✅ <strong>УСПІХ! Ваш сайт створено.</strong><br>Адреса: <strong>${{result.url}}</strong><br>Пароль: <strong>${{result.password}}</strong><br><br>Перезавантажуємо сторінку...`;
                        // Перезавантажуємо сторінку, щоб показати нову картку
                        setTimeout(() => {{ window.location.reload(); }}, 3000);
                    }} else {{
                        msgEl.style.display = 'block';
                        msgEl.className = 'message error';
                        msgEl.textContent = `Помилка: ${{result.detail || 'Не вдалося створити сайт.'}}`;
                        btn.disabled = false; btn.textContent = '🚀 Запустити проект';
                    }}
                }} catch (err) {{
                    msgEl.style.display = 'block';
                    msgEl.className = 'message error';
                    msgEl.textContent = 'Помилка мережі. Спробуйте ще раз.';
                    btn.disabled = false; btn.textContent = '🚀 Запустити проект';
                }}
            }});
        }}

        // --- JS для управління (Stop/Start) ---
        async function controlInstance(instanceId, action) {{
            const stopBtn = document.getElementById(`btn-stop-${{instanceId}}`);
            const startBtn = document.getElementById(`btn-start-${{instanceId}}`);
            const statusBadge = document.getElementById(`status-badge-${{instanceId}}`);
            const currentStatus = statusBadge.textContent.trim(); 

            stopBtn.disabled = true;
            startBtn.disabled = true;
            statusBadge.textContent = 'обробка...';
            
            const formData = new FormData();
            formData.append('instance_id', instanceId);
            formData.append('action', action);

            try {{
                const response = await fetch('/api/instance/control', {{
                    method: 'POST',
                    body: formData
                }});
                const result = await response.json();

                if (response.ok) {{
                    statusBadge.textContent = result.new_status;
                    if (result.new_status === 'active') {{
                        stopBtn.disabled = false;
                        startBtn.disabled = true;
                        statusBadge.style.backgroundColor = 'var(--status-active)';
                    }} else {{
                        stopBtn.disabled = true;
                        startBtn.disabled = false;
                        statusBadge.style.backgroundColor = 'var(--status-suspended)';
                    }}
                    if (result.message) {{
                         alert(result.message);
                    }}
                }} else {{
                    alert(`Помилка: ${{result.detail}}`);
                    statusBadge.textContent = currentStatus; 
                    if (currentStatus === 'active') {{
                         stopBtn.disabled = false;
                         statusBadge.style.backgroundColor = 'var(--status-active)';
                    }} else {{
                         startBtn.disabled = false;
                         statusBadge.style.backgroundColor = 'var(--status-suspended)';
                    }}
                }}
            }} catch (err) {{
                alert('Мережева помилка. Не вдалося виконати дію.');
                statusBadge.textContent = currentStatus;
                if (currentStatus === 'active') {{
                     stopBtn.disabled = false;
                     statusBadge.style.backgroundColor = 'var(--status-active)';
                }} else {{
                     startBtn.disabled = false;
                     statusBadge.style.backgroundColor = 'var(--status-suspended)';
                }}
            }}
        }}

        // --- JS: Управління Видаленням ---
        async function deleteInstance(instanceId, subdomain) {{
            const message = `Ви впевнені, що хочете ПОВНІСТЮ видалити проект '${{subdomain}}'?\\n\\nЦя дія незворотна. Контейнер та база даних будуть видалені.`
            if (!confirm(message)) {{
                return;
            }}

            const card = document.getElementById(`instance-card-${{instanceId}}`);
            const deleteBtn = card.querySelector('.btn-delete');
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Видалення...';
            
            const formData = new FormData();
            formData.append('instance_id', instanceId);

            try {{
                const response = await fetch('/api/instance/delete', {{
                    method: 'POST',
                    body: formData
                }});
                const result = await response.json();

                if (response.ok) {{
                    alert(result.message || 'Проект успішно видалений.');
                    card.style.transition = 'opacity 0.5s, transform 0.5s';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    setTimeout(() => {{ 
                        card.remove();
                        const grid = document.getElementById('projects-grid-container');
                        if (grid.children.length === 0) {{
                            grid.innerHTML = "<p style='text-align: center; color: var(--text-muted);'>У вас поки немає проектів. Створіть свій перший проект, використовуючи форму вище.</p>";
                        }}
                    }}, 500);
                }} else {{
                    alert(`Помилка видалення: ${{result.detail}}`);
                    deleteBtn.disabled = false;
                    deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Видалити';
                }}
            }} catch (err) {{
                alert('Мережева помилка. Не вдалося видалити проект.');
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Видалити';
            }}
        }}
        </script>
    </body></html>
    """

# --- 5. Шаблоны Админ-панели (ДЛЯ SUPER ADMIN) ---

def get_admin_dashboard_html(clients: list, message: str = "", msg_type: str = "success"):
    """HTML для Админки (/admin)"""
    rows = ""
    for user, instance in clients:
        if instance:
            url_link = f"<a href='{instance.url}' target='_blank'>{instance.subdomain}</a>" if instance.url else instance.subdomain
            rows += f"""
            <tr>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>{url_link}</td>
                <td>{instance.container_name}</td>
                <td>
                    <span style="padding: 4px 8px; border-radius: 4px; background: {'rgba(74, 222, 128, 0.1)' if instance.status == 'active' else 'rgba(248, 113, 113, 0.1)'}; color: {'#4ade80' if instance.status == 'active' else '#f87171'}; font-size: 0.85rem;">
                        {instance.status}
                    </span>
                </td>
                <td>{instance.next_payment_due.strftime('%Y-%m-%d')}</td>
                <td>
                    <form action="/admin/control" method="post" style="display:flex; gap: 10px; align-items: center;">
                        <input type="hidden" name="instance_id" value="{instance.id}">
                        {
                            '<button type="submit" name="action" value="stop" class="btn-mini warn" title="Зупинити"><i class="fa-solid fa-pause"></i></button>' 
                            if instance.status == 'active' else 
                            '<button type="submit" name="action" value="start" class="btn-mini success" title="Запустити"><i class="fa-solid fa-play"></i></button>'
                        }
                        
                        <button type="submit" name="action" value="update" class="btn-mini info" title="Оновити код контейнера" onclick="return confirm('Ви перезібрали образ crm-template? Контейнер буде перезапущено.');">
                            <i class="fa-solid fa-rotate"></i>
                        </button>

                        <button type="submit" name="action" value="force_delete" class="btn-mini danger" title="Видалити назавжди" onclick="return confirm('УВАГА: Це видалить базу даних клієнта та контейнер НАЗАВЖДИ. Продовжити?');">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </form>
                </td>
            </tr>
            """
        else:
            rows += f"<tr><td>{user.id}</td><td>{user.email}</td><td colspan='5'><i>(Екземпляр не створено)</i></td></tr>"

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Admin Panel</title>{GLOBAL_STYLES}</head>
    <style>
        body {{ display: block; padding: 20px; }}
        .container {{ max-width: 1200px; width: 100%; text-align: left; margin: 0 auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 15px; border: 1px solid var(--border); text-align: left; font-size: 0.9rem; }}
        th {{ background: var(--bg-card-hover); font-weight: 600; }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
        
        .btn-mini {{
            border: 1px solid transparent;
            border-radius: 6px;
            width: 32px;
            height: 32px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
            background: rgba(255,255,255,0.05);
            color: var(--text-muted);
        }}
        .btn-mini:hover {{ transform: translateY(-2px); }}
        .btn-mini.warn:hover {{ background: #f59e0b; color: white; }}
        .btn-mini.success:hover {{ background: #4ade80; color: white; }}
        .btn-mini.info:hover {{ background: #6366f1; color: white; }}
        .btn-mini.danger:hover {{ background: #e11d48; color: white; }}

        .header-nav {{ display: flex; justify-content: space-between; align-items: center; }}
        .nav-link {{ background: var(--primary); color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 0.9rem; margin-top: 0; }}
        .nav-link:hover {{ background: var(--primary-hover); }}
    </style>
    <body><div class="container">
        <div class="header-nav">
            <h1>Панель Адміністратора</h1>
            <a href="/settings" class="nav-link">Налаштування Вітрини</a>
        </div>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <h2>Клієнти SaaS</h2>
        <table>
            <thead>
                <tr><th>ID Юзера</th><th>Email</th><th>Піддомен</th><th>Контейнер</th><th>Статус</th><th>Оплачено до</th><th>Дія</th></tr>
            </thead>
            <tbody>
                {rows or "<tr><td colspan='7'>Немає клієнтів</td></tr>"}
            </tbody>
        </table>
    </div></body></html>
    """

def get_settings_page_html(config, message=""):
    """HTML для настройки витрины (/settings)"""
    custom_btn_text = config.get('custom_btn_text', '').replace('"', '"')
    custom_btn_content = config.get('custom_btn_content', '').replace('<', '<').replace('>', '>')
    
    return f"""
    <!DOCTYPE html><html><head><title>Restify Admin</title>{GLOBAL_STYLES}</head>
    <style>
        .container {{ max-width: 500px; text-align: left; }}
        label {{ color: var(--text-muted); display: block; margin-bottom: 5px; font-size: 0.9rem; }}
    </style>
    <body>
        <div class="container">
            <h1 style="text-align:center;">Налаштування Вітрини</h1>
            {f'<div class="message success" style="text-align:center">{message}</div>' if message else ''}
            <form method="post" action="/settings">
                <label>Символ валюти</label><input type="text" name="currency" value="{config.get('currency', '$')}">
                
                <input type="hidden" name="price_light" value="{config.get('price_light', '300')}">
                <label>Ціна (Pro) / місяць</label><input type="number" name="price_full" value="{config.get('price_full', '600')}">
                
                <hr>
                <label>Admin Telegram ID (для заявок)</label><input type="text" name="admin_id" value="{config.get('admin_id', '')}">
                <label>Bot Token (для заявок)</label><input type="text" name="bot_token" value="{config.get('bot_token', '')}">
                
                <hr>
                <label>Текст кнопки (в меню)</label>
                <input type="text" name="custom_btn_text" value="{custom_btn_text}" placeholder="Напр: Політика">
                <p class="form-hint" style="margin-top: 5px; margin-bottom: 15px;">Залиште порожнім, щоб приховати кнопку.</p>
                
                <label>Вміст вікна (HTML)</label>
                <textarea name="custom_btn_content" placeholder="<p>Ваш текст...</p>">{custom_btn_content}</textarea>
                <button type="submit" class="btn">Зберегти</button>
            </form>
            <a href="/admin" style="text-align:center;">← Назад до Клієнтів</a>
        </div>
    </body></html>
    """

# --- 6. Шаблоны для КУРЬЕРОВ ---

def get_courier_login_page(message="", msg_type="error"):
    """Страница входа для курьеров"""
    
    # --- PWA META (Manifest) ---
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'
    # ---------------------------

    return f"""
    <!DOCTYPE html><html lang="uk"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Вхід для кур'єрів</title>{GLOBAL_STYLES}{pwa_meta}</head>
    <body><div class="container">
        <h1>🚴 Courier App</h1>
        <form method="post" action="/api/courier/login">
            <input type="tel" name="phone" placeholder="Телефон" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit" class="btn">Почати зміну</button>
        </form>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <a href="/courier/register">Стати кур'єром</a>
    </div></body></html>
    """

def get_courier_register_page():
    """Страница регистрации для курьеров с Telegram Verification"""
    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Реєстрація кур'єра</title>{GLOBAL_STYLES}
    <style>
        .tg-verify-box {{
            border: 2px dashed var(--border);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
            background: rgba(255,255,255,0.02);
            transition: 0.3s;
        }}
        .tg-verify-box.verified {{
            border-color: var(--status-active);
            background: rgba(74, 222, 128, 0.1);
        }}
        .tg-btn {{
            background: #24A1DE;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            margin-top: 10px;
            transition: 0.2s;
        }}
        .tg-btn:hover {{ background: #1b8bbf; transform: translateY(-2px); }}
        .hidden {{ display: none; }}
        
        .spinner {{ display: inline-block; width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
    </head>
    <body><div class="container">
        <h1>Реєстрація Кур'єра</h1>
        <form id="regForm" method="post" action="/api/courier/register">
            <input type="text" name="name" placeholder="Ваше Ім'я" required>
            <input type="password" name="password" placeholder="Пароль" required>
            
            <div id="tg-step" class="tg-verify-box">
                <div id="tg-initial">
                    <p style="margin:0 0 10px 0; color:var(--text-muted);">Підтвердіть телефон через Telegram:</p>
                    <a href="#" id="tg-link" target="_blank" class="tg-btn">
                        <i class="fa-brands fa-telegram"></i> Підтвердити
                    </a>
                </div>
                
                <div id="tg-waiting" class="hidden">
                    <p style="margin:0; color:var(--text-muted);">
                        <span class="spinner"></span> Очікуємо підтвердження...
                    </p>
                    <small style="color:#666">Натисніть "Start" та "Share Contact" у боті</small>
                </div>

                <div id="tg-success" class="hidden">
                    <div style="color: var(--status-active); font-size: 1.2rem; margin-bottom: 5px;">
                        <i class="fa-solid fa-circle-check"></i> Підтверджено!
                    </div>
                    <div id="user-phone-display" style="font-weight:bold; color:white;"></div>
                </div>
            </div>

            <input type="hidden" name="phone" id="real_phone">
            <input type="hidden" name="verification_token" id="verification_token">

            <button type="submit" class="btn" id="submitBtn" disabled>Зареєструватися</button>
        </form>
        <div id="msg" class="message" style="display:none"></div>
    </div>
    <script>
        let verificationToken = "";
        let pollInterval = null;

        async function initVerification() {{
            try {{
                const res = await fetch('/api/auth/init_verification', {{ method: 'POST' }});
                const data = await res.json();
                verificationToken = data.token;
                document.getElementById('verification_token').value = verificationToken;
                
                const linkBtn = document.getElementById('tg-link');
                linkBtn.href = data.link;
                
                linkBtn.addEventListener('click', () => {{
                    document.getElementById('tg-initial').classList.add('hidden');
                    document.getElementById('tg-waiting').classList.remove('hidden');
                    startPolling();
                }});
            }} catch(e) {{ console.error(e); }}
        }}

        function startPolling() {{
            pollInterval = setInterval(async () => {{
                try {{
                    const res = await fetch(`/api/auth/check_verification/${{verificationToken}}`);
                    const data = await res.json();
                    if(data.status === 'verified') {{
                        clearInterval(pollInterval);
                        showSuccess(data.phone);
                    }}
                }} catch(e) {{ }}
            }}, 2000);
        }}

        function showSuccess(phone) {{
            document.getElementById('tg-waiting').classList.add('hidden');
            document.getElementById('tg-success').classList.remove('hidden');
            document.querySelector('.tg-verify-box').classList.add('verified');
            
            document.getElementById('user-phone-display').innerText = phone;
            document.getElementById('real_phone').value = phone;
            document.getElementById('submitBtn').disabled = false;
        }}

        initVerification();

        document.getElementById('regForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const btn = document.getElementById('submitBtn');
            btn.disabled = true; btn.innerText = "Обробка...";
            
            const form = new FormData(e.target);
            const msgEl = document.getElementById('msg');
            msgEl.style.display = 'none';

            try {{
                const resp = await fetch('/api/courier/register', {{ method: 'POST', body: form }});
                const resData = await resp.json();

                if(resp.ok) {{
                    window.location.href='/courier/login?message=Успішно! Увійдіть.&type=success';
                }} else {{
                    msgEl.style.display = 'block';
                    msgEl.className = 'message error';
                    msgEl.innerText = resData.detail || 'Помилка реєстрації';
                    btn.disabled = false; btn.innerText = "Зареєструватися";
                }}
            }} catch (err) {{
                 msgEl.style.display = 'block'; msgEl.innerText = "Помилка мережі";
                 btn.disabled = false; btn.innerText = "Зареєструватися";
            }}
        }});
    </script>
    </body></html>
    """

def get_courier_pwa_html(courier: Courier):
    """
    Полностью переработанный PWA интерфейс
    """
    status_class = "online" if courier.is_online else "offline"
    status_text = "НА ЗМІНІ" if courier.is_online else "ОФЛАЙН"
    
    # --- PWA META (Manifest) ---
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'
    # ---------------------------

    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Courier App</title>
        {GLOBAL_STYLES}
        {PWA_STYLES}
        {pwa_meta}
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    </head>
    <body>
        <div id="map"></div>

        <div class="app-header">
            <button class="icon-btn" onclick="toggleHistory(true)"><i class="fa-solid fa-clock-rotate-left"></i></button>
            <div class="status-indicator" onclick="toggleShift()">
                <div id="status-dot" class="dot {status_class}"></div>
                <span id="status-text">{status_text}</span>
            </div>
            <a href="/courier/logout" class="icon-btn"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>

        <div id="offline-msg" style="display: { 'none' if courier.is_online else 'flex' }; position: absolute; inset:0; background:rgba(15,23,42,0.8); z-index: 50; align-items:center; justify-content:center; flex-direction:column; backdrop-filter:blur(3px);">
            <h2>Ви зараз офлайн</h2>
            <button class="btn" style="width:200px" onclick="toggleShift()">Вийти на лінію</button>
        </div>

        <div id="job-sheet" class="bottom-sheet">
            <div class="drag-handle"></div>
            
            <div class="stepper">
                <div id="step-1" class="step"></div> <div id="step-2" class="step"></div> </div>

            <div class="sheet-title">
                <span id="job-title">Замовлення #000</span>
                <span id="job-price" style="color: var(--status-active)">+0 ₴</span>
            </div>
            <div class="sheet-subtitle" id="job-status-desc">Прямуйте до закладу</div>

            <div class="info-block">
                <div class="info-label" id="addr-label">Забрати тут:</div>
                <div class="info-value" id="current-target-addr">вул. Прикладна, 10</div>
                <div style="margin-top:5px; color:var(--text-muted); font-size:0.9rem;" id="current-target-name">Ресторан "Ромашка"</div>
            </div>

            <div class="info-block" id="client-info-block" style="display:none;">
                <div class="info-label">Клієнт</div>
                <div class="info-value"><i class="fa-solid fa-user"></i> <span id="client-name">Іван</span></div>
                <div class="info-value"><i class="fa-solid fa-phone"></i> <a href="#" id="client-phone" style="color:white; text-decoration:none;">000</a></div>
                <div style="margin-top:5px; color:var(--accent);" id="job-comment">Код 123</div>
            </div>

            <div class="action-grid">
                <a href="#" id="btn-nav" target="_blank" class="btn-nav">
                    <i class="fa-solid fa-location-arrow"></i> Маршрут
                </a>
                <button id="btn-action" class="btn-main" onclick="advanceJobState()">Прибув</button>
            </div>
        </div>
        
        <div id="history-modal" class="history-modal">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h2>Історія замовлень</h2>
                <button class="icon-btn" onclick="toggleHistory(false)"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div id="history-list">
                </div>
        </div>

        <div id="orderModal" class="order-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); z-index:2000; align-items:center; justify-content:center; backdrop-filter:blur(5px);">
             <div style="background:white; color:black; padding:30px; border-radius:20px; width:85%; max-width:350px; text-align:center;">
                <h2 style="margin-top:0;">🔥 Нове замовлення!</h2>
                <div style="font-size:2.5rem; font-weight:800; color:var(--primary);" id="modal-fee">50 ₴</div>
                <p id="modal-route" style="color:#555; margin:15px 0;">Ресторан -> Адреса</p>
                <input type="hidden" id="modal-job-id">
                <button onclick="acceptOrder()" class="btn" style="background:var(--status-active); color:black; margin-bottom:10px;">ПРИЙНЯТИ</button>
                <button onclick="document.getElementById('orderModal').style.display='none'" style="background:none; border:none; color:#777; text-decoration:underline;">Пропустити</button>
             </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // --- State ---
            let currentJob = null;
            let isOnline = {str(courier.is_online).lower()};
            
            // --- Map Init ---
            const map = L.map('map', {{ zoomControl: false }}).setView([50.45, 30.52], 13);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
            let marker = null;

            // --- Geolocation & Tracking ---
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition((pos) => {{
                    const {{ latitude, longitude }} = pos.coords;
                    if (!marker) {{
                        marker = L.marker([latitude, longitude]).addTo(map);
                        map.setView([latitude, longitude], 15);
                    }} else {{
                        marker.setLatLng([latitude, longitude]);
                    }}
                    
                    if(isOnline) {{
                        const fd = new FormData();
                        fd.append('lat', latitude);
                        fd.append('lon', longitude);
                        navigator.sendBeacon('/api/courier/location', fd);
                    }}
                }}, console.error, {{ enableHighAccuracy: true }});
            }}

            // --- WebSocket ---
            let socket;
            function connectWS() {{
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/courier`);
                socket.onmessage = (e) => {{
                    const msg = JSON.parse(e.data);
                    if(msg.type === 'new_order') showNewOrder(msg.data);
                }};
            }}
            if(isOnline) connectWS();

            // --- UI Functions ---
            function showNewOrder(data) {{
                document.getElementById('modal-fee').innerText = data.fee + ' ₴';
                document.getElementById('modal-route').innerText = `${{data.restaurant}} ➝ ${{data.address}}`;
                document.getElementById('modal-job-id').value = data.id;
                document.getElementById('orderModal').style.display = 'flex';
                // Try play sound
                new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3').play().catch(e=>{{}});
            }}

            async function toggleShift() {{
                const res = await fetch('/api/courier/toggle_status', {{method:'POST'}});
                const data = await res.json();
                isOnline = data.is_online;
                document.getElementById('offline-msg').style.display = isOnline ? 'none' : 'flex';
                document.getElementById('status-dot').className = isOnline ? 'dot online' : 'dot offline';
                document.getElementById('status-text').innerText = isOnline ? 'НА ЗМІНІ' : 'ОФЛАЙН';
                if(isOnline) connectWS();
            }}

            async function toggleHistory(show) {{
                const modal = document.getElementById('history-modal');
                if(show) {{
                    const res = await fetch('/api/courier/history');
                    const jobs = await res.json();
                    const list = document.getElementById('history-list');
                    list.innerHTML = jobs.map(j => `
                        <div class="history-item">
                            <div>
                                <div style="font-weight:bold;">#${{j.id}} - ${{j.address}}</div>
                                <div style="font-size:0.8rem; color:#888;">${{j.date}}</div>
                            </div>
                            <div class="history-price">+${{j.price}}₴</div>
                        </div>
                    `).join('');
                    modal.classList.add('open');
                }} else {{
                    modal.classList.remove('open');
                }}
            }}

            // --- JOB LOGIC ---
            
            async function checkActiveJob() {{
                const res = await fetch('/api/courier/active_job');
                const data = await res.json();
                if(data.active) {{
                    currentJob = data.job;
                    renderJobSheet();
                }} else {{
                    document.getElementById('job-sheet').classList.remove('active');
                    currentJob = null;
                }}
            }}
            
            // Check on load
            checkActiveJob();

            function renderJobSheet() {{
                const sheet = document.getElementById('job-sheet');
                const btnNav = document.getElementById('btn-nav');
                const btnAct = document.getElementById('btn-action');
                const steps = [document.getElementById('step-1'), document.getElementById('step-2')];
                
                sheet.classList.add('active');
                document.getElementById('job-title').innerText = `Замовлення #${{currentJob.id}}`;
                document.getElementById('job-price').innerText = `+${{currentJob.delivery_fee}} ₴`;
                document.getElementById('client-name').innerText = currentJob.customer_name || 'Гість';
                document.getElementById('client-phone').innerText = currentJob.customer_phone;
                document.getElementById('client-phone').href = `tel:${{currentJob.customer_phone}}`;
                document.getElementById('job-comment').innerText = currentJob.comment || '';

                // Logic based on status
                if (currentJob.status === 'assigned') {{
                    // Phase 1: Go to Restaurant
                    steps[0].className = 'step active'; steps[1].className = 'step';
                    document.getElementById('job-status-desc').innerText = 'Прямуйте до закладу';
                    document.getElementById('addr-label').innerText = 'ЗАБРАТИ ТУТ:';
                    document.getElementById('current-target-addr').innerText = currentJob.partner_address;
                    document.getElementById('current-target-name').innerText = currentJob.partner_name;
                    
                    document.getElementById('client-info-block').style.display = 'none';
                    
                    // Maps Link to Restaurant
                    btnNav.href = `https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(currentJob.partner_address)}}`;
                    btnAct.innerText = 'Забрав замовлення';
                    btnAct.onclick = () => updateStatus('picked_up');
                    
                }} else if (currentJob.status === 'picked_up') {{
                    // Phase 2: Go to Client
                    steps[0].className = 'step done'; steps[1].className = 'step active';
                    document.getElementById('job-status-desc').innerText = 'Везіть до клієнта';
                    document.getElementById('addr-label').innerText = 'ВЕЗТИ СЮДИ:';
                    document.getElementById('current-target-addr').innerText = currentJob.customer_address;
                    document.getElementById('current-target-name').innerText = 'Клієнт';
                    
                    document.getElementById('client-info-block').style.display = 'block';

                    // Maps Link to Client
                    btnNav.href = `https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(currentJob.customer_address)}}`;
                    btnAct.innerText = '✅ Доставив';
                    btnAct.onclick = () => updateStatus('delivered');
                }}
            }}

            async function acceptOrder() {{
                const jobId = document.getElementById('modal-job-id').value;
                const fd = new FormData(); fd.append('job_id', jobId);
                
                const res = await fetch('/api/courier/accept_order', {{method:'POST', body:fd}});
                const data = await res.json();
                
                document.getElementById('orderModal').style.display = 'none';
                if(data.status === 'ok') checkActiveJob();
                else alert(data.message);
            }}

            async function updateStatus(newStatus) {{
                if(!currentJob) return;
                const fd = new FormData();
                fd.append('job_id', currentJob.id);
                fd.append('status', newStatus);
                
                const res = await fetch('/api/courier/update_job_status', {{method:'POST', body:fd}});
                if(res.ok) {{
                    currentJob.status = newStatus;
                    if(newStatus === 'delivered') {{
                        alert("Чудова робота! Замовлення завершено.");
                        currentJob = null;
                        document.getElementById('job-sheet').classList.remove('active');
                        // Можно показать конфетти
                    }} else {{
                        renderJobSheet();
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """

# --- 7. Landing Page (SaaS + Partner) ---

def get_landing_page_html(config: Dict[str, str]):
    """
    ОБНОВЛЕННАЯ Главная страница (Lander).
    Содержит две основные опции: Создать SaaS проект или Стать Партнером.
    """
    
    custom_button_html = ""
    if config.get("custom_btn_text"):
        button_text = config["custom_btn_text"].replace('<', '<').replace('>', '>')
        custom_button_html = f'<a href="#" id="custom-modal-btn">{button_text}</a>'
        
    modal_content_html = config.get("custom_btn_content", "")

    return f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restify | Платформа для ресторанів</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #0f172a; --text: #f8fafc; --primary: #6366f1; --accent: #ec4899; }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        a {{ text-decoration: none; color: inherit; transition: 0.3s; }}
        
        /* Nav */
        .navbar {{ padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); position: sticky; top: 0; background: rgba(15,23,42,0.9); backdrop-filter: blur(10px); z-index: 100; }}
        .nav-inner {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-weight: 800; font-size: 1.5rem; display: flex; align-items: center; gap: 10px; }}
        .auth-btns {{ display: flex; gap: 15px; }}
        .btn-sm {{ padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 600; }}
        .btn-outline {{ border: 1px solid rgba(255,255,255,0.3); }}
        .btn-outline:hover {{ border-color: var(--primary); color: var(--primary); }}
        
        /* Hero */
        .hero {{ text-align: center; padding: 100px 0 60px; }}
        h1 {{ font-size: clamp(2.5rem, 5vw, 4rem); font-weight: 800; margin-bottom: 20px; line-height: 1.1; }}
        .gradient-text {{ background: linear-gradient(135deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ font-size: 1.2rem; color: #94a3b8; max-width: 600px; margin: 0 auto 50px; }}
        
        /* Split Section */
        .split-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px; }}
        @media(max-width: 768px) {{ .split-container {{ grid-template-columns: 1fr; }} }}
        
        .choice-card {{ 
            background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; padding: 40px; 
            text-align: left; transition: 0.4s; position: relative; overflow: hidden;
        }}
        .choice-card:hover {{ transform: translateY(-10px); border-color: var(--primary); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }}
        .card-icon {{ width: 60px; height: 60px; background: rgba(99, 102, 241, 0.1); color: var(--primary); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin-bottom: 25px; }}
        .choice-card h3 {{ font-size: 1.8rem; margin: 0 0 15px; }}
        .choice-card p {{ color: #94a3b8; margin-bottom: 30px; min-height: 80px; }}
        
        .btn-block {{ display: block; width: 100%; text-align: center; padding: 15px; border-radius: 12px; font-weight: 700; background: var(--primary); color: white; border: none; cursor: pointer; }}
        .btn-block:hover {{ background: #4f46e5; }}
        .btn-secondary {{ background: #334155; }}
        .btn-secondary:hover {{ background: #475569; }}
        
        /* Features List */
        .features li {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: #cbd5e1; }}
        .features i {{ color: var(--accent); }}
        
        /* Modal */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 2000; justify-content: center; align-items: center; backdrop-filter: blur(5px); }}
        .modal-overlay.visible {{ display: flex; }}
        .modal-content {{ background: #1e293b; padding: 40px; border-radius: 20px; max-width: 600px; width: 90%; color: #fff; position: relative; }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; cursor: pointer; font-size: 1.5rem; color: #94a3b8; }}
    </style>
</head>
<body>

    <nav class="navbar">
        <div class="container nav-inner">
            <div class="logo"><img src="/static/logo.png" height="40" style="filter:invert(1)"> Restify</div>
            <div class="auth-btns">
                <a href="/login" class="btn-sm btn-outline">Вхід (SaaS)</a>
                <a href="/partner/login" class="btn-sm btn-outline" style="border-color: var(--accent); color: var(--accent);">Вхід (Партнер)</a>
            </div>
        </div>
    </nav>

    <div class="container hero">
        <h1>Оберіть свій формат <br><span class="gradient-text">роботи з доставкою</span></h1>
        <p class="subtitle">Ми пропонуємо два рішення: повна автоматизація закладу "під ключ" або просто швидкий виклик наших кур'єрів.</p>
        
        <div class="split-container">
            <div class="choice-card">
                <div class="card-icon"><i class="fa-solid fa-rocket"></i></div>
                <h3>Власний Сайт + Бот</h3>
                <p>Повне рішення: свій сайт доставки, Telegram-бот, QR-меню в залі, CRM система та адмін-панель. Ідеально для побудови бренду.</p>
                <ul class="features">
                    <li><i class="fa-solid fa-check"></i> Персональний домен та сайт</li>
                    <li><i class="fa-solid fa-check"></i> Власна база клієнтів</li>
                    <li><i class="fa-solid fa-check"></i> QR-меню та виклик офіціанта</li>
                </ul>
                <a href="/register" class="btn-block">Створити проект (SaaS)</a>
            </div>

            <div class="choice-card" style="border-color: rgba(236, 72, 153, 0.3);">
                <div class="card-icon" style="background: rgba(236, 72, 153, 0.1); color: var(--accent);"><i class="fa-solid fa-motorcycle"></i></div>
                <h3>Тільки Кур'єри</h3>
                <p>Вам не потрібен сайт? Просто викликайте наших кур'єрів, коли у вас з'являється замовлення. Швидка реєстрація та прозорі тарифи.</p>
                <ul class="features">
                    <li><i class="fa-solid fa-check"></i> Виклик кур'єра в 1 клік</li>
                    <li><i class="fa-solid fa-check"></i> Без абонплати за софт</li>
                    <li><i class="fa-solid fa-check"></i> Трекінг доставки</li>
                </ul>
                <a href="/partner/register" class="btn-block btn-secondary">Стати Партнером</a>
            </div>
        </div>
    </div>

    <footer style="text-align:center; padding: 40px; color: #64748b; font-size: 0.9rem;">
        © 2025 Restify. {custom_button_html}
    </footer>

    <div id="customModal" class="modal-overlay">
        <div class="modal-content">
            <span class="close-btn" onclick="document.getElementById('customModal').classList.remove('visible')">×</span>
            <div class="modal-body">{modal_content_html}</div>
        </div>
    </div>

    <script>
        const btn = document.getElementById('custom-modal-btn');
        if(btn) btn.onclick = (e) => {{ e.preventDefault(); document.getElementById('customModal').classList.add('visible'); }};
    </script>
</body>
</html>
    """