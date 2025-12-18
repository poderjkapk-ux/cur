from templates_saas import GLOBAL_STYLES

# Импорт моделей для типизации
try:
    from models import Courier
except ImportError:
    class Courier: pass

# --- ОБНОВЛЕННЫЕ СТИЛИ (SUPER DESIGNER PWA) ---
PWA_STYLES = """
<style>
    :root {
        --bg-deep: #0f172a;
        --bg-glass: rgba(30, 41, 59, 0.7);
        --bg-card: #1e293b;
        --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        --accent-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
        --danger-gradient: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
        --glass-border: 1px solid rgba(255, 255, 255, 0.08);
        --shadow-soft: 0 10px 40px -10px rgba(0,0,0,0.5);
        --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.3);
        --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

    body, html { 
        height: 100%; width: 100%;
        overflow: hidden; overscroll-behavior: none;
        padding: 0 !important; margin: 0 !important;
        background: var(--bg-deep); font-family: 'Inter', sans-serif;
        color: #f8fafc;
    }
    
    /* Утилиты */
    .glass {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: var(--glass-border);
    }
    .icon-btn { 
        background: rgba(255,255,255,0.05); border: none; color: white; 
        width: 44px; height: 44px; border-radius: 12px; 
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2rem; cursor: pointer; transition: 0.2s;
    }
    .icon-btn:active { transform: scale(0.9); background: rgba(255,255,255,0.1); }

    /* Карта */
    #map { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
    #map.hidden { visibility: hidden; }

    /* HEADER */
    .app-header {
        position: absolute; top: 0; left: 0; right: 0;
        padding: 15px 20px; z-index: 100;
        display: flex; justify-content: space-between; align-items: center;
        padding-top: max(15px, env(safe-area-inset-top));
        background: linear-gradient(to bottom, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0) 100%);
        pointer-events: none; /* Чтобы кликать сквозь градиент */
    }
    .app-header > * { pointer-events: auto; } /* Возвращаем клики элементам */

    .status-capsule {
        display: flex; align-items: center; gap: 10px;
        background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(10px);
        padding: 8px 16px; border-radius: 30px; border: var(--glass-border);
        font-weight: 700; font-size: 0.85rem; cursor: pointer;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: 0.3s;
    }
    .status-capsule:active { transform: scale(0.95); }
    .dot { width: 8px; height: 8px; border-radius: 50%; box-shadow: 0 0 10px currentColor; transition: 0.3s; }
    .dot.online { background: #4ade80; color: #4ade80; box-shadow: 0 0 15px #4ade80; }
    .dot.offline { background: #f87171; color: #f87171; }

    /* BOTTOM NAV */
    .bottom-nav {
        position: fixed; bottom: 20px; left: 20px; right: 20px;
        height: 70px; border-radius: 24px;
        display: flex; justify-content: space-around; align-items: center;
        z-index: 500; padding-bottom: env(safe-area-inset-bottom);
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.1);
        overflow: hidden;
    }
    .nav-item {
        flex: 1; height: 100%; display: flex; flex-direction: column; 
        justify-content: center; align-items: center; gap: 4px;
        color: #94a3b8; font-size: 0.7rem; font-weight: 600;
        transition: 0.3s; cursor: pointer; position: relative;
    }
    .nav-item i { font-size: 1.4rem; transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .nav-item.active { color: white; }
    .nav-item.active i { transform: translateY(-3px); color: #818cf8; text-shadow: 0 0 15px rgba(99, 102, 241, 0.6); }
    /* Индикатор активной вкладки (Glow effect) */
    .nav-item.active::after {
        content: ''; position: absolute; bottom: 0; width: 40%; height: 3px;
        background: #818cf8; border-radius: 10px 10px 0 0;
        box-shadow: 0 -5px 15px #818cf8;
    }

    /* SCREENS */
    .screen { display: none; height: 100%; width: 100%; position: relative; }
    .screen.active { display: block; animation: fadeIn 0.3s ease; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    /* FEED (ORDERS) */
    .feed-container {
        position: absolute; inset: 0;
        padding: 90px 20px 100px 20px; /* Отступы под header и nav */
        overflow-y: auto; -webkit-overflow-scrolling: touch;
        background: var(--bg-deep);
        background-image: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.15), transparent 40%);
    }
    .feed-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 25px; }
    .feed-title { font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; margin: 0; }
    .loading-indicator { font-size: 0.85rem; color: #94a3b8; display: flex; align-items: center; gap: 6px; }
    .loading-indicator i { animation: spin 1s linear infinite; }

    /* ORDER CARD */
    .order-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 20px; padding: 20px; margin-bottom: 20px;
        position: relative; overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .order-card:active { transform: scale(0.98); }
    .order-card.high-price { border: 1px solid rgba(16, 185, 129, 0.3); background: linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, rgba(30, 41, 59, 0.6) 100%); }
    
    .oc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
    .oc-price { font-size: 1.5rem; font-weight: 800; color: white; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }
    .oc-dist { background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; color: #cbd5e1; }

    .oc-timeline { position: relative; padding-left: 24px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 15px; }
    .oc-timeline::before {
        content: ''; position: absolute; left: 7px; top: 8px; bottom: 8px; width: 2px;
        background: linear-gradient(to bottom, #facc15 0%, #4ade80 100%); opacity: 0.3;
    }
    .oc-point { position: relative; }
    .oc-point::after {
        content: ''; position: absolute; left: -24px; top: 4px; width: 10px; height: 10px; border-radius: 50%;
        border: 2px solid var(--bg-card); z-index: 2;
    }
    .oc-point.rest::after { background: #facc15; box-shadow: 0 0 10px rgba(250, 204, 21, 0.4); }
    .oc-point.client::after { background: #4ade80; box-shadow: 0 0 10px rgba(74, 222, 128, 0.4); }
    
    .oc-title { font-weight: 700; font-size: 1rem; color: #f1f5f9; line-height: 1.2; }
    .oc-sub { font-size: 0.85rem; color: #94a3b8; margin-top: 2px; }

    .btn-accept {
        width: 100%; border: none; padding: 14px; border-radius: 14px;
        background: var(--primary-gradient); color: white; font-weight: 700; font-size: 1rem;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); cursor: pointer;
        display: flex; justify-content: center; align-items: center; gap: 8px;
    }

    /* BOTTOM SHEET (JOB) */
    .bottom-sheet {
        position: absolute; bottom: 0; left: 0; right: 0;
        background: rgba(30, 41, 59, 0.9); backdrop-filter: blur(20px);
        border-radius: 30px 30px 0 0; border-top: 1px solid rgba(255,255,255,0.1);
        padding: 10px 20px 30px 20px; z-index: 200;
        box-shadow: 0 -10px 40px rgba(0,0,0,0.4);
        transform: translateY(110%); transition: transform 0.4s var(--ease-spring);
        max-height: 85vh; overflow-y: auto;
    }
    .bottom-sheet.active { transform: translateY(0); }
    .drag-pill { width: 40px; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; margin: 10px auto 25px; }

    /* STEPPER */
    .stepper { display: flex; gap: 6px; margin-bottom: 25px; }
    .step { flex: 1; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; transition: 0.3s; }
    .step.active { background: #818cf8; box-shadow: 0 0 10px #818cf8; }
    .step.done { background: #10b981; }

    /* JOB INFO */
    .job-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .job-id { font-size: 1.5rem; font-weight: 800; color: white; }
    .job-income { font-size: 1.2rem; font-weight: 700; color: #4ade80; background: rgba(74, 222, 128, 0.1); padding: 4px 10px; border-radius: 8px; }
    .job-status-text { color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; }

    .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px; }
    
    .btn-main {
        grid-column: span 2;
        background: var(--primary-gradient); color: white; border: none;
        padding: 16px; border-radius: 16px; font-weight: 700; font-size: 1.1rem;
        box-shadow: 0 5px 20px rgba(99, 102, 241, 0.4); cursor: pointer; transition: 0.2s;
    }
    .btn-main:active { transform: scale(0.97); }
    .btn-sec {
        background: rgba(255,255,255,0.05); color: white; border: none;
        padding: 14px; border-radius: 14px; font-weight: 600; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 8px;
    }

    /* MODALS */
    .full-modal {
        position: fixed; inset: 0; background: var(--bg-deep); z-index: 600;
        display: flex; flex-direction: column;
        transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .full-modal.open { transform: translateY(0); }
    .modal-header {
        padding: 20px; display: flex; align-items: center; gap: 15px;
        background: rgba(15,23,42,0.9); border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .modal-title { font-size: 1.2rem; font-weight: 700; flex: 1; }

    /* CHAT */
    .chat-area { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .msg { max-width: 80%; padding: 12px 16px; border-radius: 18px; font-size: 0.95rem; line-height: 1.4; position: relative; }
    .msg.me { align-self: flex-end; background: #6366f1; color: white; border-bottom-right-radius: 4px; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3); }
    .msg.other { align-self: flex-start; background: #334155; color: #f1f5f9; border-bottom-left-radius: 4px; }
    
    .chat-input-bar {
        padding: 15px; background: #1e293b; display: flex; gap: 10px;
        border-top: 1px solid rgba(255,255,255,0.05); padding-bottom: max(15px, env(safe-area-inset-bottom));
    }
    .chat-field {
        flex: 1; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 25px; padding: 12px 20px; color: white; outline: none; transition: 0.3s;
    }
    .chat-field:focus { border-color: #818cf8; background: rgba(99, 102, 241, 0.1); }
    .chat-send {
        width: 46px; height: 46px; border-radius: 50%; border: none;
        background: var(--primary-gradient); color: white; font-size: 1rem;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.4); cursor: pointer;
    }

    /* POPUP MODAL (NEW ORDER) */
    .popup-overlay {
        position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);
        z-index: 2000;
        display: none; /* Скрыт по умолчанию */
        align-items: center; justify-content: center;
    }
    /* ИСПРАВЛЕНИЕ: show добавляет flex для показа */
    .popup-overlay.show { display: flex; animation: fadeIn 0.3s ease-out; }
    
    .popup-card {
        background: #1e293b; width: 85%; max-width: 360px; border-radius: 24px;
        padding: 25px; text-align: center; border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 20px 60px rgba(0,0,0,0.6);
        transform: scale(0.9); transition: transform 0.3s var(--ease-spring);
    }
    .popup-overlay.show .popup-card { transform: scale(1); }

    .pulse-ring {
        width: 80px; height: 80px; border-radius: 50%; background: rgba(99, 102, 241, 0.2);
        margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;
        position: relative;
    }
    .pulse-ring::after {
        content: ''; position: absolute; inset: 0; border-radius: 50%;
        border: 2px solid #6366f1; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
    }
    @keyframes ping { 75%, 100% { transform: scale(1.6); opacity: 0; } }

    /* OFFLINE SCREEN */
    .offline-screen {
        display: none; position: absolute; inset: 0; z-index: 50;
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(10px);
        flex-direction: column; align-items: center; justify-content: center;
    }
    .btn-go-online {
        width: 180px; height: 180px; border-radius: 50%; border: none;
        background: var(--primary-gradient); color: white; font-weight: 800; font-size: 1.5rem;
        box-shadow: 0 0 50px rgba(99, 102, 241, 0.5); cursor: pointer;
        transition: 0.3s; text-transform: uppercase; letter-spacing: 1px;
    }
    .btn-go-online:active { transform: scale(0.95); box-shadow: 0 0 20px rgba(99, 102, 241, 0.8); }

    /* TOAST */
    #toast {
        position: fixed; top: 20px; left: 50%; transform: translateX(-50%) translateY(-100px);
        background: rgba(16, 185, 129, 0.9); backdrop-filter: blur(8px); color: white;
        padding: 12px 24px; border-radius: 50px; font-weight: 600;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 9999;
        transition: transform 0.4s var(--ease-spring); display: flex; align-items: center; gap: 10px;
    }
    #toast.show { transform: translateX(-50%) translateY(0); }

    /* Доп. стили статусов */
    .badge-ready { background: #10b981; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem; display: inline-block; margin-bottom: 8px; }
    .badge-cash { background: rgba(250, 204, 21, 0.15); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.3); padding: 10px; border-radius: 12px; margin-bottom: 15px; font-weight: 600; text-align: center; }
</style>
"""

def get_courier_login_page(message="", msg_type="error"):
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'
    return f"""
    <!DOCTYPE html><html lang="uk"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Вхід для кур'єрів</title>{GLOBAL_STYLES}{pwa_meta}</head>
    <body><div class="container glass">
        <h1 style="margin-bottom:10px;">🚴 Courier App</h1>
        <p style="color:#94a3b8; margin-bottom:30px;">Увійдіть, щоб почати зміну</p>
        <form method="post" action="/api/courier/login">
            <input type="tel" name="phone" placeholder="Телефон" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit" class="btn" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">Почати зміну</button>
        </form>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <a href="/courier/register" style="margin-top:20px; color:#94a3b8; font-size:0.9rem;">Немає акаунту? Реєстрація</a>
    </div></body></html>
    """

def get_courier_register_page():
    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Реєстрація</title>{GLOBAL_STYLES}
    <style>
        .tg-verify-box {{ border: 2px dashed rgba(255,255,255,0.2); padding: 20px; border-radius: 16px; margin-bottom: 20px; text-align: center; background: rgba(255,255,255,0.03); }}
        .tg-verify-box.verified {{ border-color: #4ade80; background: rgba(74, 222, 128, 0.1); }}
        .tg-btn {{ background: #24A1DE; color: white; padding: 12px 20px; border-radius: 10px; text-decoration: none; display: inline-flex; align-items: center; gap: 10px; font-weight: 600; margin-top: 10px; }}
        .hidden {{ display: none; }}
    </style>
    </head>
    <body><div class="container glass">
        <h1>Новий Кур'єр</h1>
        <form id="regForm" method="post" action="/api/courier/register">
            <input type="text" name="name" placeholder="Ваше Ім'я" required>
            <input type="password" name="password" placeholder="Придумайте пароль" required>
            <div id="tg-step" class="tg-verify-box">
                <div id="tg-initial">
                    <p style="margin:0 0 10px 0; color:#cbd5e1;">Підтвердіть телефон через Telegram:</p>
                    <a href="#" id="tg-link" target="_blank" class="tg-btn"><i class="fa-brands fa-telegram"></i> Відкрити бота</a>
                </div>
                <div id="tg-waiting" class="hidden">
                    <p style="margin:0; color:#cbd5e1;">Очікуємо...</p>
                    <small style="color:#64748b">Натисніть "Start" та "Share Contact"</small>
                </div>
                <div id="tg-success" class="hidden">
                    <div style="color: #4ade80; font-size: 1.2rem; margin-bottom: 5px;"><i class="fa-solid fa-circle-check"></i> Успішно!</div>
                    <div id="user-phone-display" style="font-weight:bold; color:white;"></div>
                </div>
            </div>
            <input type="hidden" name="phone" id="real_phone">
            <input type="hidden" name="verification_token" id="verification_token">
            <button type="submit" class="btn" id="submitBtn" disabled style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">Створити акаунт</button>
        </form>
        <div id="msg" class="message" style="display:none"></div>
    </div>
    <script>
        let verificationToken = ""; let pollInterval = null;
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
                    pollInterval = setInterval(async () => {{
                        try {{
                            const res = await fetch(`/api/auth/check_verification/${{verificationToken}}`);
                            const data = await res.json();
                            if(data.status === 'verified') {{
                                clearInterval(pollInterval);
                                document.getElementById('tg-waiting').classList.add('hidden');
                                document.getElementById('tg-success').classList.remove('hidden');
                                document.querySelector('.tg-verify-box').classList.add('verified');
                                document.getElementById('user-phone-display').innerText = data.phone;
                                document.getElementById('real_phone').value = data.phone;
                                document.getElementById('submitBtn').disabled = false;
                            }}
                        }} catch(e) {{ }}
                    }}, 2000);
                }});
            }} catch(e) {{ console.error(e); }}
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
                if(resp.ok) window.location.href='/courier/login?message=Успішно! Увійдіть.&type=success';
                else {{ msgEl.style.display = 'block'; msgEl.className = 'message error'; msgEl.innerText = resData.detail || 'Помилка'; btn.disabled = false; btn.innerText = "Зареєструватися"; }}
            }} catch (err) {{ msgEl.style.display = 'block'; msgEl.innerText = "Помилка мережі"; btn.disabled = false; btn.innerText = "Зареєструватися"; }}
        }});
    </script>
    </body></html>
    """

def get_courier_pwa_html(courier: Courier, firebase_config_json: str, vapid_key: str):
    """
    PREMIUM DESIGNER PWA INTERFACE
    """
    status_class = "online" if courier.is_online else "offline"
    status_text = "НА ЗМІНІ" if courier.is_online else "ОФЛАЙН"
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'
    safe_firebase_config = firebase_config_json if firebase_config_json else "{}"
    safe_vapid_key = vapid_key if vapid_key else ""

    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Courier Pro</title>
        {GLOBAL_STYLES}
        {PWA_STYLES}
        {pwa_meta}
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="app-header glass">
            <button class="icon-btn" onclick="toggleHistory(true)"><i class="fa-solid fa-clock-rotate-left"></i></button>
            
            <div class="status-capsule glass" onclick="toggleShift()">
                <div id="status-dot" class="dot {status_class}"></div>
                <span id="status-text">{status_text}</span>
            </div>
            
            <a href="/courier/logout" class="icon-btn"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>

        <div id="offline-msg" class="offline-screen" style="display: {'none' if courier.is_online else 'flex'};">
            <div style="opacity:0.6; margin-bottom:20px; font-size:4rem;"><i class="fa-solid fa-power-off"></i></div>
            <h2 style="margin-bottom:30px; font-weight:800;">Ви Офлайн</h2>
            <button class="btn-go-online" onclick="toggleShift()">GO</button>
        </div>

        <div id="screen-map" class="screen active">
            <div id="map"></div>
            
            <div id="job-sheet" class="bottom-sheet glass">
                <div class="drag-pill"></div>
                
                <div class="stepper">
                    <div id="step-1" class="step"></div>
                    <div id="step-2" class="step"></div>
                </div>

                <div class="job-header-row">
                    <div class="job-id" id="job-title">#...</div>
                    <div class="job-income" id="job-price">+0 ₴</div>
                </div>
                
                <div class="job-status-text" id="job-status-desc">Очікування...</div>

                <div style="background:rgba(255,255,255,0.03); border-radius:16px; padding:15px; margin-bottom:15px;">
                    <div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; margin-bottom:5px;" id="addr-label">Адреса</div>
                    <div style="font-size:1.1rem; font-weight:600; color:#fff; margin-bottom:5px;" id="current-target-addr">...</div>
                    <div style="font-size:0.9rem; color:#94a3b8;" id="current-target-name">...</div>
                </div>

                <div id="client-info-block" style="display:none; background:rgba(255,255,255,0.03); border-radius:16px; padding:15px; margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:0.75rem; color:#64748b; text-transform:uppercase;">Клієнт</div>
                            <div style="font-weight:600;" id="client-name">Name</div>
                            <div style="color:#var(--primary); font-size:0.9rem;" id="job-comment"></div>
                        </div>
                        <a href="#" id="client-phone" class="icon-btn" style="background:#10b981; border-radius:50%;"><i class="fa-solid fa-phone"></i></a>
                    </div>
                </div>
                
                <div class="action-grid">
                    <a href="#" id="btn-call" class="btn-sec" style="display:none;"><i class="fa-solid fa-phone"></i> Заклад</a>
                    <button id="btn-chat" class="btn-sec"><i class="fa-solid fa-comments"></i> Чат</button>
                    <a href="#" id="btn-nav" target="_blank" class="btn-sec"><i class="fa-solid fa-location-arrow"></i> Навігація</a>
                    <button id="btn-action" class="btn-main" onclick="advanceJobState()">ДІЯ</button>
                </div>
            </div>
        </div>

        <div id="screen-orders" class="screen">
            <div class="feed-container">
                <div class="feed-header">
                    <h1 class="feed-title">Актуальні</h1>
                    <div id="feed-loader" class="loading-indicator"><i class="fa-solid fa-circle-notch"></i> Пошук...</div>
                </div>
                <div id="orders-list"></div>
            </div>
        </div>

        <div class="bottom-nav glass">
            <div class="nav-item active" onclick="switchTab('map')" id="nav-map">
                <i class="fa-solid fa-map-location-dot"></i>
                <span>Карта</span>
            </div>
            <div class="nav-item" onclick="switchTab('orders')" id="nav-orders">
                <div style="position:relative;">
                    <i class="fa-solid fa-layer-group"></i>
                    <div id="orders-badge" style="display:none; position:absolute; top:-2px; right:-5px; width:8px; height:8px; background:#ef4444; border-radius:50%; box-shadow:0 0 5px #ef4444;"></div>
                </div>
                <span>Замовлення</span>
            </div>
        </div>

        <div id="chat-sheet" class="full-modal">
             <div class="modal-header">
                <button class="icon-btn" onclick="document.getElementById('chat-sheet').classList.remove('open')"><i class="fa-solid fa-chevron-down"></i></button>
                <div class="modal-title">Чат замовлення</div>
            </div>
            <div id="chat-body" class="chat-area"></div>
            <form class="chat-input-bar" onsubmit="sendChatMessage(event)">
                <input type="text" id="chat-input" class="chat-field" placeholder="Повідомлення..." autocomplete="off" required>
                <button type="submit" class="chat-send"><i class="fa-solid fa-paper-plane"></i></button>
            </form>
        </div>

        <div id="history-modal" class="full-modal">
            <div class="modal-header">
                <button class="icon-btn" onclick="toggleHistory(false)"><i class="fa-solid fa-chevron-down"></i></button>
                <div class="modal-title">Історія змін</div>
            </div>
            <div id="history-list" style="padding:20px; overflow-y:auto;"></div>
        </div>

        <div id="orderModal" class="popup-overlay">
             <div class="popup-card glass">
                <div class="pulse-ring">
                    <i class="fa-solid fa-bolt" style="font-size:2rem; color:#6366f1;"></i>
                </div>
                <h2 style="margin:0 0 5px 0; font-weight:800;">Нове Замовлення!</h2>
                <div id="modal-fee" style="font-size:2.5rem; font-weight:900; color:#10b981; margin-bottom:15px; text-shadow:0 0 20px rgba(16,185,129,0.3);">+50 ₴</div>
                
                <div id="warning-placeholder"></div>
                
                <div id="modal-route" style="text-align:left; background:rgba(255,255,255,0.05); padding:15px; border-radius:16px; margin-bottom:20px;"></div>
                
                <input type="hidden" id="modal-job-id">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <button onclick="closeOrderModal()" class="btn-sec" style="justify-content:center;">Пропустити</button>
                    <button onclick="acceptOrder()" class="btn-main" style="grid-column:auto; background:var(--accent-gradient);">ПРИЙНЯТИ</button>
                </div>
             </div>
        </div>

        <div id="toast">
            <i class="fa-solid fa-bell" style="color:#fbbf24;"></i> <span id="toast-text">Сповіщення</span>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js"></script>

        <script>
            // --- FIREBASE & PUSH ---
            const firebaseConfig = {safe_firebase_config};
            let messaging = null;
            try {{
                if (firebaseConfig.apiKey) {{ firebase.initializeApp(firebaseConfig); messaging = firebase.messaging(); }}
            }} catch(e) {{}}
            
            const VAPID_KEY = "{safe_vapid_key}";

            async function initPushNotifications() {{
                if (!messaging) return; 
                try {{
                    const permission = await Notification.requestPermission();
                    if (permission === 'granted') {{
                        const token = await messaging.getToken({{ vapidKey: VAPID_KEY }});
                        if (token) sendTokenToServer(token);
                    }}
                }} catch (err) {{}}
            }}

            if (messaging) {{
                messaging.onMessage((payload) => {{
                    const audio = new Audio('/static/notification.mp3'); audio.play().catch(e => {{}});
                    showToast(payload.notification?.title || "Нове замовлення!");
                    if (payload.data?.job_id && activeTab === 'orders') fetchOrders();
                }});
            }}

            async function sendTokenToServer(token) {{
                const fd = new FormData(); fd.append('token', token);
                try {{ await fetch('/api/courier/fcm_token', {{ method: 'POST', body: fd }}); }} catch(e) {{}}
            }}

            function showToast(text) {{
                const t = document.getElementById('toast');
                document.getElementById('toast-text').innerText = text;
                t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 4000);
            }}

            // --- WAKE LOCK ---
            document.addEventListener('click', () => {{
                initPushNotifications();
                // FIX: catch empty lambda syntax for py f-string
                if ('wakeLock' in navigator) navigator.wakeLock.request('screen').catch(()=>{{}});
            }}, {{ once: true }});

            // --- APP LOGIC ---
            let currentLat = null, currentLon = null;
            let isOnline = {str(courier.is_online).lower()};
            let currentJob = null;
            let activeTab = 'map';
            let socket = null, pingInterval = null;

            // INIT MAP (Dark Theme)
            const map = L.map('map', {{ zoomControl: false }}).setView([50.45, 30.52], 13);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '© OpenStreetMap', subdomains: 'abcd', maxZoom: 19
            }}).addTo(map);
            let marker = null, targetMarker = null, routeLine = null;

            function switchTab(tab) {{
                activeTab = tab;
                document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                
                // FIX: string interpolation with ${{}}
                document.getElementById(`screen-${{tab}}`).classList.add('active');
                document.getElementById(`nav-${{tab}}`).classList.add('active');
                
                if(tab === 'map') {{
                    document.getElementById('map').classList.remove('hidden');
                    setTimeout(() => map.invalidateSize(), 100);
                }} else {{
                    document.getElementById('map').classList.add('hidden');
                    if(currentLat && currentLon) fetchOrders();
                }}
            }}

            async function fetchOrders() {{
                if (!isOnline || !currentLat) return;
                const loader = document.getElementById('feed-loader'); loader.style.opacity = '1';
                try {{
                    const res = await fetch(`/api/courier/open_orders?lat=${{currentLat}}&lon=${{currentLon}}`);
                    const orders = await res.json();
                    renderOrders(orders);
                }} catch(e) {{}} finally {{ loader.style.opacity = '0'; }}
            }}

            function renderOrders(orders) {{
                const container = document.getElementById('orders-list');
                const badge = document.getElementById('orders-badge');
                
                if (orders.length === 0) {{
                    container.innerHTML = `<div style="text-align:center; padding:40px; color:#64748b;"><i class="fa-solid fa-mug-hot" style="font-size:3rem; margin-bottom:10px;"></i><p>Замовлень поки немає</p></div>`;
                    badge.style.display = 'none';
                    return;
                }}

                badge.style.display = 'block';
                container.innerHTML = orders.map(o => {{
                    const isHigh = o.fee > 100;
                    const cardClass = isHigh ? 'order-card high-price' : 'order-card';
                    
                    // --- ИСПРАВЛЕНО: Правильные ключи и отображение дистанции ---
                    // dist_to_rest - до ресторана
                    // dist_trip - от ресторана до клиента (это то, что приходит с сервера)
                    
                    // Безопасное отображение
                    let toRestText = (o.dist_to_rest !== null && o.dist_to_rest !== undefined) ? o.dist_to_rest.toFixed(1) + ' км' : '?';
                    let tripText = (o.dist_trip !== null && o.dist_trip !== undefined && o.dist_trip !== '?') ? parseFloat(o.dist_trip).toFixed(1) + ' км' : '?';

                    // --- NEW: Payment Badges in List ---
                    let badges = '';
                    if (o.payment_type === 'buyout') {{
                        badges += `<div class="badge-cash" style="color:#ec4899; border-color:#ec4899; background:rgba(236,72,153,0.15); margin-bottom:10px;">💰 Викуп: ${{o.price}} ₴</div>`;
                    }} else if (o.is_return) {{
                        badges += `<div class="badge-cash" style="color:#f97316; border-color:#f97316; background:rgba(249,115,22,0.15); margin-bottom:10px;">↩️ Повернути: ${{o.price}} ₴</div>`;
                    }} else if (o.payment_type === 'cash') {{
                        badges += `<div class="badge-cash" style="margin-bottom:10px;">💵 До сплати: ${{o.price}} ₴</div>`;
                    }}

                    return `
                    <div class="${{cardClass}}">
                        <div class="oc-header">
                            <div class="oc-price">+${{o.fee}} ₴</div>
                            <div class="oc-dist"><i class="fa-solid fa-person-walking"></i> ${{toRestText}}</div>
                        </div>
                        
                        ${{badges}}

                        <div class="oc-timeline">
                            <div class="oc-point rest">
                                <div class="oc-title">${{o.restaurant_name}}</div>
                                <div class="oc-sub">${{o.restaurant_address}}</div>
                            </div>
                            <div class="oc-point client">
                                <div class="oc-title">Клієнт</div>
                                <div class="oc-sub">${{o.dropoff_address}} <span style="color:#4ade80; font-weight:bold;">(${{tripText}})</span></div>
                            </div>
                        </div>
                        <button class="btn-accept" onclick="acceptOrderFromFeed(${{o.id}})">
                            <span>ПРИЙНЯТИ</span>
                        </button>
                    </div>`;
                }}).join('');
            }}

            async function acceptOrderFromFeed(id) {{
                if(!confirm("Прийняти замовлення?")) return;
                document.getElementById('modal-job-id').value = id;
                await acceptOrder();
                switchTab('map');
            }}

            function connectWS() {{
                if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/courier`);

                socket.onopen = () => {{
                    document.getElementById('status-dot').style.boxShadow = '0 0 15px #4ade80';
                    clearInterval(pingInterval);
                    pingInterval = setInterval(() => {{ if (socket.readyState === WebSocket.OPEN) socket.send("ping"); }}, 15000);
                }};
                socket.onmessage = (e) => {{
                    if (e.data === "pong") return; 
                    const msg = JSON.parse(e.data);
                    if(msg.type === 'new_order') {{
                        // Force Modal Show logic + audio play
                        if (activeTab === 'orders') fetchOrders(); 
                        showNewOrderModal(msg.data);
                        // FIX: catch empty lambda syntax for py f-string
                        new Audio('/static/notification.mp3').play().catch(()=>{{}});
                    }}
                    else if (msg.type === 'job_update') checkActiveJob();
                    else if (msg.type === 'job_ready') {{
                        if (currentJob) {{ currentJob.is_ready = true; renderJobSheet(); showToast("🍳 ЗАМОВЛЕННЯ ГОТОВЕ!"); }}
                    }}
                    else if (msg.type === 'chat_message') {{
                        if (document.getElementById('chat-sheet').classList.contains('open')) renderSingleMsg(msg);
                        else showToast("💬 Нове повідомлення");
                    }}
                }};
                socket.onclose = () => {{
                    if (isOnline) setTimeout(connectWS, 3000);
                }};
            }}
            
            // GEOLOCATION
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition((pos) => {{
                    const {{ latitude, longitude }} = pos.coords;
                    currentLat = latitude; currentLon = longitude;
                    if (!marker) {{ marker = L.marker([latitude, longitude]).addTo(map); map.setView([latitude, longitude], 15); }}
                    else marker.setLatLng([latitude, longitude]);
                    
                    if (activeTab === 'orders' && isOnline) fetchOrders();
                    
                    if(isOnline && socket?.readyState === WebSocket.OPEN) {{
                         const fd = new FormData(); fd.append('lat', latitude); fd.append('lon', longitude);
                         navigator.sendBeacon('/api/courier/location', fd);
                    }}
                }}, null, {{ enableHighAccuracy: true }});
            }}

            async function toggleShift() {{
                try {{
                    const res = await fetch('/api/courier/toggle_status', {{method:'POST'}});
                    const data = await res.json();
                    isOnline = data.is_online;
                    document.getElementById('offline-msg').style.display = isOnline ? 'none' : 'flex';
                    const dot = document.getElementById('status-dot');
                    const txt = document.getElementById('status-text');
                    
                    if(isOnline) {{ dot.className='dot online'; txt.innerText='НА ЗМІНІ'; connectWS(); }}
                    else {{ dot.className='dot offline'; txt.innerText='ОФЛАЙН'; socket?.close(); }}
                }} catch(e) {{}}
            }}
            if(isOnline) connectWS();

            async function checkActiveJob() {{
                try {{
                    const res = await fetch('/api/courier/active_job');
                    const data = await res.json();
                    if(data.active) {{
                        currentJob = data.job; renderJobSheet(); switchTab('map');
                        document.querySelector('.bottom-nav').style.display = 'none';
                        document.querySelector('.feed-container').style.paddingBottom = '0';
                    }} else {{
                        document.getElementById('job-sheet').classList.remove('active');
                        currentJob = null;
                        document.querySelector('.bottom-nav').style.display = 'flex';
                        if(targetMarker) {{ map.removeLayer(targetMarker); targetMarker = null; }}
                        if(routeLine) {{ map.removeLayer(routeLine); routeLine = null; }}
                    }}
                }} catch(e) {{}}
            }}
            checkActiveJob();

            function renderJobSheet() {{
                const sheet = document.getElementById('job-sheet'); sheet.classList.add('active');
                document.getElementById('job-title').innerText = `#${{currentJob.id}}`;
                document.getElementById('job-price').innerText = `+${{currentJob.delivery_fee}} ₴`;
                
                const statusDesc = document.getElementById('job-status-desc');
                statusDesc.innerHTML = '';
                
                if (currentJob.is_ready) statusDesc.innerHTML += '<div class="badge-ready">🍳 ГОТОВО</div> ';
                
                // --- NEW: Payment details in Active Job Sheet ---
                if (currentJob.payment_type === 'cash' && !currentJob.is_return_required) 
                    statusDesc.innerHTML += `<div class="badge-cash">💵 Клієнт платить: ${{currentJob.order_price}} ₴</div>`;

                if (currentJob.payment_type === 'buyout') 
                    statusDesc.innerHTML += `<div class="badge-cash" style="color:#ec4899; border-color:#ec4899">💰 Викуп: ${{currentJob.order_price}} ₴</div>`;

                if (currentJob.is_return_required) 
                    statusDesc.innerHTML += `<div class="badge-cash" style="color:#f97316; border-color:#f97316">↩️ Повернути: ${{currentJob.order_price}} ₴</div>`;
                // ------------------------------------------------

                document.getElementById('current-target-name').innerText = currentJob.partner_name;
                document.getElementById('client-name').innerText = currentJob.customer_name || 'Гість';
                document.getElementById('client-phone').href = `tel:${{currentJob.customer_phone}}`;
                
                const btnNav = document.getElementById('btn-nav');
                const btnAct = document.getElementById('btn-action');
                const btnCall = document.getElementById('btn-call');
                
                if (currentJob.partner_phone) {{ btnCall.href = `tel:${{currentJob.partner_phone}}`; btnCall.style.display = 'flex'; }} 
                else btnCall.style.display = 'none';
                
                document.getElementById('btn-chat').onclick = openChat;

                let destAddr = "";
                // Logic phases
                if (['assigned', 'ready', 'arrived_pickup'].includes(currentJob.status)) {{
                    destAddr = currentJob.partner_address;
                    document.getElementById('addr-label').innerText = 'ЗАБРАТИ ТУТ';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('client-info-block').style.display = 'none';
                    document.getElementById('step-1').className = 'step active'; document.getElementById('step-2').className = 'step';
                    
                    if (currentJob.status === 'arrived_pickup') {{
                        btnAct.innerText = 'ЗАБРАВ';
                        btnAct.style.background = 'var(--accent-gradient)';
                        btnAct.onclick = () => updateStatus('picked_up');
                    }} else {{
                        btnAct.innerText = 'Я НА МІСЦІ';
                        btnAct.style.background = 'var(--primary-gradient)';
                        btnAct.onclick = async () => {{
                             await fetch('/api/courier/arrived_pickup', {{method:'POST', body: new URLSearchParams({{job_id: currentJob.id}})}});
                             currentJob.status = 'arrived_pickup'; renderJobSheet();
                        }};
                    }}
                }} else {{
                    destAddr = currentJob.customer_address;
                    document.getElementById('addr-label').innerText = 'ВЕЗТИ СЮДИ';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('client-info-block').style.display = 'block';
                    document.getElementById('step-1').className = 'step done'; document.getElementById('step-2').className = 'step active';
                    
                    if (currentJob.is_return_required) {{
                        btnAct.innerText = 'ПОВЕРНЕННЯ';
                        btnAct.onclick = () => {{ if(confirm("Везти гроші в заклад?")) updateStatus('delivered'); }};
                    }} else if (currentJob.status === 'returning') {{
                         statusDesc.innerHTML = '<b style="color:#ef4444">↩️ ПОВЕРНІТЬ ГРОШІ!</b>';
                         document.getElementById('addr-label').innerText = 'ВЕЗТИ ГРОШІ СЮДИ';
                         document.getElementById('current-target-addr').innerText = currentJob.partner_address;
                         btnAct.innerText = 'ВІДДАВ';
                         btnAct.style.background = '#f97316';
                         btnAct.onclick = () => alert("Чекайте підтвердження закладу.");
                    }} else {{
                        btnAct.innerText = 'ДОСТАВИВ';
                        btnAct.style.background = 'var(--accent-gradient)';
                        btnAct.onclick = () => updateStatus('delivered');
                    }}
                    
                    // Draw Line on Map
                    if (currentJob.customer_lat && !targetMarker) {{
                        const pos = [currentJob.customer_lat, currentJob.customer_lon];
                        targetMarker = L.marker(pos).addTo(map);
                        if(marker) {{
                             routeLine = L.polyline([marker.getLatLng(), pos], {{color: '#818cf8', weight: 4, dashArray: '10, 10'}}).addTo(map);
                             map.fitBounds(routeLine.getBounds(), {{padding:[50,50]}});
                        }}
                    }}
                }}
                
                // FIX: Use Google Maps Search query with correctly encoded address
                btnNav.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(destAddr);
            }}

            async function updateStatus(s) {{
                const fd = new FormData(); fd.append('job_id', currentJob.id); fd.append('status', s);
                await fetch('/api/courier/update_job_status', {{method:'POST', body:fd}}); checkActiveJob();
            }}

            async function acceptOrder() {{
                const id = document.getElementById('modal-job-id').value;
                const fd = new FormData(); fd.append('job_id', id);
                try {{
                    const res = await fetch('/api/courier/accept_order', {{method:'POST', body:fd}});
                    const data = await res.json();
                    closeOrderModal();
                    if(data.status === 'ok') checkActiveJob(); else alert(data.message);
                }} catch(e) {{}}
            }}

            function showNewOrderModal(data) {{
                document.getElementById('modal-fee').innerText = `+${{data.fee}} ₴`;
                
                let warningHtml = '';
                
                // 1. Выкуп (Buyout)
                if (data.payment_type === 'buyout') {{
                    warningHtml += `<div class="badge-cash" style="color:#ec4899; border-color:#ec4899; background:rgba(236,72,153,0.15);">💰 ПОТРІБЕН ВИКУП: ${{data.price}} ₴</div>`;
                }}
                
                // 2. Повернення коштів (Return)
                if (data.is_return) {{
                    warningHtml += `<div class="badge-cash" style="color:#f97316; border-color:#f97316; background:rgba(249,115,22,0.15);">↩️ ТРЕБА ПОВЕРНУТИ КОШТИ</div>`;
                }}
                
                // 3. Готівка (Cash) - якщо не викуп і не повернення
                if (data.payment_type === 'cash' && !data.is_return) {{
                     warningHtml += `<div class="badge-cash">💵 ОПЛАТА ГОТІВКОЮ: ${{data.price}} ₴</div>`;
                }}

                document.getElementById('warning-placeholder').innerHTML = warningHtml;
                document.getElementById('modal-route').innerHTML = `<div>🏪 <b>${{data.restaurant}}</b></div><div style="margin-top:5px; color:#cbd5e1; font-size:0.9rem;">${{data.restaurant_address}}</div><div style="margin-top:10px;">📍 <b>Клієнт</b></div><div style="margin-top:5px; color:#cbd5e1; font-size:0.9rem;">${{data.address}}</div>`;
                document.getElementById('modal-job-id').value = data.id;
                document.getElementById('orderModal').classList.add('show');
            }}
            function closeOrderModal() {{ document.getElementById('orderModal').classList.remove('show'); }}

            // CHAT & HISTORY
            async function toggleHistory(show) {{
                const el = document.getElementById('history-modal');
                if(show) {{
                    const res = await fetch('/api/courier/history');
                    const jobs = await res.json();
                    document.getElementById('history-list').innerHTML = jobs.map(j => `
                        <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:15px; margin-bottom:10px; display:flex; justify-content:space-between;">
                            <div><div style="font-weight:700">#${{j.id}}</div><div style="font-size:0.8rem; color:#94a3b8">${{j.address}}</div></div>
                            <div style="color:#4ade80; font-weight:700">+${{j.price}}₴</div>
                        </div>`).join('');
                    el.classList.add('open');
                }} else el.classList.remove('open');
            }}
            
            async function openChat() {{
                if(!currentJob) return;
                document.getElementById('chat-sheet').classList.add('open');
                const res = await fetch(`/api/chat/history/${{currentJob.id}}`);
                const msgs = await res.json();
                const box = document.getElementById('chat-body'); box.innerHTML = '';
                msgs.forEach(renderSingleMsg);
            }}
            function renderSingleMsg(m) {{
                const box = document.getElementById('chat-body');
                const div = document.createElement('div');
                div.className = `msg ${{m.role === 'courier' ? 'me' : 'other'}}`;
                div.innerText = m.text; box.appendChild(div); box.scrollTop = box.scrollHeight;
            }}
            async function sendChatMessage(e) {{
                e.preventDefault(); const inp = document.getElementById('chat-input');
                const txt = inp.value.trim(); if(!txt || !currentJob) return;
                inp.value = ''; renderSingleMsg({{role:'courier', text:txt}});
                const fd = new FormData(); fd.append('job_id', currentJob.id); fd.append('message', txt); fd.append('role', 'courier');
                await fetch('/api/chat/send', {{method: 'POST', body: fd}});
            }}
        </script>
    </body>
    </html>
    """