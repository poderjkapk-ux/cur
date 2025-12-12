from templates_saas import GLOBAL_STYLES

# Импорт моделей для типизации
try:
    from models import Courier
except ImportError:
    class Courier: pass

# --- Добавляем стили специально для карты и PWA ---
PWA_STYLES = """
<style>
    /* Отключаем скролл страницы, чтобы ощущалось как Native App */
    body, html { height: 100%; overflow: hidden; overscroll-behavior: none; }
    
    /* Карта на весь фон */
    #map { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
    #map.hidden { visibility: hidden; } /* Скрываем карту, когда активна лента */

    /* Верхняя панель (Header) */
    .app-header {
        position: absolute; top: 0; left: 0; right: 0;
        background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px);
        padding: 15px 20px; z-index: 100;
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid var(--border);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .status-indicator { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 0.9rem; cursor: pointer; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #ccc; box-shadow: 0 0 10px currentColor; }
    .dot.online { background: var(--status-active); color: var(--status-active); }
    .dot.offline { background: var(--status-delete); color: var(--status-delete); }
    .icon-btn { background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer; padding: 5px; }

    /* --- НИЖНЯЯ НАВИГАЦИЯ (TABS) --- */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; right: 0;
        height: 70px; background: #1e293b;
        display: flex; justify-content: space-around; align-items: center;
        border-top: 1px solid var(--border);
        z-index: 500; padding-bottom: env(safe-area-inset-bottom);
        box-shadow: 0 -5px 20px rgba(0,0,0,0.3);
    }
    .nav-item {
        color: var(--text-muted); text-align: center;
        font-size: 0.75rem; flex: 1; height: 100%;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        gap: 5px; transition: 0.3s; cursor: pointer;
    }
    .nav-item i { font-size: 1.4rem; transition: 0.3s; }
    .nav-item.active { color: var(--primary); }
    .nav-item.active i { transform: translateY(-2px); text-shadow: 0 0 10px var(--primary); }

    /* Контейнеры экранов */
    .screen { display: none; height: 100%; width: 100%; padding-bottom: 80px; }
    .screen.active { display: block; }

    /* --- ЛЕНТА ЗАКАЗОВ (FEED) --- */
    .feed-container {
        padding: 80px 15px 20px 15px; /* Отступ сверху для хедера */
        overflow-y: auto; height: 100%;
        background: var(--bg-body);
    }
    .feed-header {
        margin-bottom: 20px; display: flex; justify-content: space-between; align-items: end;
    }
    .feed-title { font-size: 1.5rem; font-weight: 800; color: white; margin: 0; }
    
    .loading-indicator { font-size: 0.8rem; color: var(--text-muted); animation: pulse 1s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

    .empty-state { text-align: center; padding: 40px 20px; color: var(--text-muted); margin-top: 50px; }
    .empty-state i { font-size: 3rem; margin-bottom: 15px; opacity: 0.3; }

    /* Карточка заказа в ленте */
    .order-card {
        background: #1e293b; border-radius: 16px; padding: 20px; margin-bottom: 15px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        position: relative; overflow: hidden;
    }
    .order-card::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: var(--primary);
    }
    .order-card.high-price::before { background: var(--status-active); } /* Зеленая полоска для дорогих */

    .oc-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
    .oc-dist-badge { 
        background: rgba(99, 102, 241, 0.15); color: #818cf8; 
        padding: 4px 10px; border-radius: 8px; font-weight: 600; font-size: 0.85rem; 
        display: flex; align-items: center; gap: 5px;
    }
    .oc-price { font-size: 1.4rem; font-weight: 800; color: white; }

    .oc-route { display: flex; flex-direction: column; gap: 10px; position: relative; padding-left: 20px; margin-bottom: 15px; }
    .oc-route::after {
        content: ''; position: absolute; left: 6px; top: 5px; bottom: 5px; width: 2px;
        background: #334155; z-index: 0;
    }
    .oc-point { position: relative; z-index: 1; font-size: 0.95rem; color: #cbd5e1; }
    .oc-point::before {
        content: ''; position: absolute; left: -20px; top: 6px; width: 10px; height: 10px; border-radius: 50%;
    }
    .oc-point.rest::before { background: #facc15; border: 2px solid #1e293b; }
    .oc-point.client::before { background: #22c55e; border: 2px solid #1e293b; }

    .oc-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px; }
    .oc-tags { display: flex; gap: 5px; flex-wrap: wrap; }
    .oc-tag { font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; background: #334155; color: #94a3b8; text-transform: uppercase; }

    .btn-accept {
        background: var(--primary); color: white; border: none; 
        padding: 10px 20px; border-radius: 10px; font-weight: 600; cursor: pointer;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    .btn-accept:active { transform: scale(0.95); }

    /* --- ШТОРКА АКТИВНОГО ЗАКАЗА (Bottom Sheet) --- */
    .bottom-sheet {
        position: absolute; bottom: 0; left: 0; right: 0;
        background: var(--bg-card);
        border-radius: 20px 20px 0 0;
        padding: 25px;
        z-index: 200;
        box-shadow: 0 -5px 30px rgba(0,0,0,0.4);
        transform: translateY(110%); /* Скрыта по умолчанию */
        transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        max-height: 85vh;
        overflow-y: auto;
        /* Отступ снизу, чтобы не перекрываться навбаром, если он есть (но мы его скрываем при активном заказе) */
    }
    .bottom-sheet.active { transform: translateY(0); }
    
    .drag-handle { width: 40px; height: 5px; background: rgba(255,255,255,0.2); border-radius: 5px; margin: 0 auto 20px; }
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

    .action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
    .btn-nav { background: #3b82f6; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: 600; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; font-size: 1rem; }
    .btn-main { background: var(--status-active); color: #0f172a; border: none; padding: 15px; border-radius: 12px; font-weight: 700; width: 100%; font-size: 1.1rem; cursor: pointer; transition: 0.2s; }
    
    /* Модалки (История, Чат) */
    .history-modal, .chat-sheet {
        position: fixed; inset: 0; background: var(--bg-body); z-index: 600;
        padding: 20px; transform: translateX(100%); transition: 0.3s; overflow-y: auto;
    }
    .history-modal.open, .chat-sheet.open { transform: translateX(0); }

    /* Чат (стили) */
    .chat-header { padding-bottom: 15px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
    .chat-body { flex: 1; padding: 15px 0; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; height: calc(100% - 130px); }
    .chat-footer { position: absolute; bottom: 0; left: 0; right: 0; padding: 15px; background: var(--bg-card); display: flex; gap: 10px; }
    .msg { max-width: 80%; padding: 10px 14px; border-radius: 16px; font-size: 0.95rem; color: white; }
    .msg.me { align-self: flex-end; background: var(--primary); border-bottom-right-radius: 4px; }
    .msg.other { align-self: flex-start; background: #334155; border-bottom-left-radius: 4px; }
    .chat-input { flex: 1; background: #1e293b; border: 1px solid var(--border); padding: 12px; border-radius: 25px; color: white; }
</style>
"""

def get_courier_login_page(message="", msg_type="error"):
    """Страница входа для курьеров"""
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'
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
        .tg-verify-box {{ border: 2px dashed var(--border); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; background: rgba(255,255,255,0.02); }}
        .tg-verify-box.verified {{ border-color: var(--status-active); background: rgba(74, 222, 128, 0.1); }}
        .tg-btn {{ background: #24A1DE; color: white; padding: 12px 20px; border-radius: 8px; text-decoration: none; display: inline-flex; align-items: center; gap: 10px; font-weight: 600; margin-top: 10px; }}
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
                    <a href="#" id="tg-link" target="_blank" class="tg-btn"><i class="fa-brands fa-telegram"></i> Підтвердити</a>
                </div>
                <div id="tg-waiting" class="hidden">
                    <p style="margin:0; color:var(--text-muted);"><span class="spinner"></span> Очікуємо...</p>
                    <small style="color:#666">Натисніть "Start" та "Share Contact"</small>
                </div>
                <div id="tg-success" class="hidden">
                    <div style="color: var(--status-active); font-size: 1.2rem; margin-bottom: 5px;"><i class="fa-solid fa-circle-check"></i> Підтверджено!</div>
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

def get_courier_pwa_html(courier: Courier):
    """
    Полностью обновленный PWA интерфейс с Feed (Лентой заказов).
    """
    status_class = "online" if courier.is_online else "offline"
    status_text = "НА ЗМІНІ" if courier.is_online else "ОФЛАЙН"
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'

    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Courier App</title>
        {GLOBAL_STYLES}
        {PWA_STYLES}
        {pwa_meta}
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    </head>
    <body>
        <div class="app-header">
            <button class="icon-btn" onclick="toggleHistory(true)"><i class="fa-solid fa-clock-rotate-left"></i></button>
            <div class="status-indicator" onclick="toggleShift()" style="position: relative;">
                <div id="connection-dot" style="position: absolute; top:-2px; right:-2px; width:6px; height:6px; border-radius:50%; background:red; border:1px solid #0f172a;" title="Connection Status"></div>
                <div id="status-dot" class="dot {status_class}"></div>
                <span id="status-text">{status_text}</span>
            </div>
            <a href="/courier/logout" class="icon-btn"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>

        <div id="offline-msg" style="display: {'none' if courier.is_online else 'flex'}; position: absolute; inset:0; background:rgba(15,23,42,0.8); z-index: 50; align-items:center; justify-content:center; flex-direction:column; backdrop-filter:blur(3px);">
            <h2>Ви зараз офлайн</h2>
            <button class="btn" style="width:200px" onclick="toggleShift()">Вийти на лінію</button>
        </div>

        <div id="screen-map" class="screen active">
            <div id="map"></div>
            
            <div id="job-sheet" class="bottom-sheet">
                <div class="drag-handle"></div>
                <div class="stepper"><div id="step-1" class="step"></div><div id="step-2" class="step"></div></div>
                <div class="sheet-title">
                    <span id="job-title">Замовлення #...</span>
                    <span id="job-price" style="color: var(--status-active)">+0 ₴</span>
                </div>
                <div class="sheet-subtitle" id="job-status-desc">Статус...</div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                    <a href="#" id="btn-call" class="btn-nav" style="background: #334155; display:none;"><i class="fa-solid fa-phone"></i> Дзвінок</a>
                    <button id="btn-chat" class="btn-nav" style="background: #334155; cursor: pointer;"><i class="fa-solid fa-comments"></i> Чат</button>
                </div>
                <div class="info-block">
                    <div class="info-label" id="addr-label">Адреса:</div>
                    <div class="info-value" id="current-target-addr">...</div>
                    <div style="margin-top:5px; color:var(--text-muted); font-size:0.9rem;" id="current-target-name">...</div>
                </div>
                <div class="info-block" id="client-info-block" style="display:none;">
                    <div class="info-label">Клієнт</div>
                    <div class="info-value"><i class="fa-solid fa-user"></i> <span id="client-name"></span></div>
                    <div class="info-value"><i class="fa-solid fa-phone"></i> <a href="#" id="client-phone" style="color:white; text-decoration:none;"></a></div>
                    <div style="margin-top:5px; color:var(--accent);" id="job-comment"></div>
                </div>
                <div class="action-grid">
                    <a href="#" id="btn-nav" target="_blank" class="btn-nav"><i class="fa-solid fa-location-arrow"></i> Навігація</a>
                    <button id="btn-action" class="btn-main" onclick="advanceJobState()">Дія</button>
                </div>
            </div>
        </div>

        <div id="screen-orders" class="screen">
            <div class="feed-container">
                <div class="feed-header">
                    <h1 class="feed-title">Стрічка замовлень</h1>
                    <div id="feed-loader" class="loading-indicator"><i class="fa-solid fa-satellite-dish"></i> Пошук...</div>
                </div>
                <div id="orders-list"></div>
            </div>
        </div>

        <div class="bottom-nav">
            <div class="nav-item active" onclick="switchTab('map')" id="nav-map">
                <i class="fa-solid fa-map-location-dot"></i>
                <span>Карта</span>
            </div>
            <div class="nav-item" onclick="switchTab('orders')" id="nav-orders">
                <div style="position:relative;">
                    <i class="fa-solid fa-list-ul"></i>
                    <div id="orders-badge" style="display:none; position:absolute; top:-2px; right:-8px; width:10px; height:10px; background:var(--accent); border-radius:50%; border:2px solid #1e293b;"></div>
                </div>
                <span>Замовлення</span>
            </div>
        </div>

        <div id="chat-sheet" class="chat-sheet">
             <div class="chat-header">
                <button class="icon-btn" onclick="document.getElementById('chat-sheet').classList.remove('open')" style="color:white;"><i class="fa-solid fa-arrow-left"></i></button>
                <div style="font-weight:bold;">Чат</div><div style="width:24px"></div>
            </div>
            <div id="chat-body" class="chat-body"></div>
            <form class="chat-footer" onsubmit="sendChatMessage(event)">
                <input type="text" id="chat-input" class="chat-input" placeholder="..." autocomplete="off" required>
                <button type="submit" class="icon-btn" style="background:var(--primary); border-radius:50%; width:40px; height:40px;"><i class="fa-solid fa-paper-plane"></i></button>
            </form>
        </div>

        <div id="history-modal" class="history-modal">
            <div style="display:flex; justify-content:space-between; margin-bottom:20px;"><h2>Історія</h2><button class="icon-btn" onclick="toggleHistory(false)">×</button></div>
            <div id="history-list"></div>
        </div>

        <div id="orderModal" class="order-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); z-index:2000; align-items:center; justify-content:center; backdrop-filter:blur(5px);">
             <div style="background:white; color:black; padding:30px; border-radius:20px; width:85%; max-width:350px; text-align:center;">
                <h2 style="margin-top:0;">🔥 Нове замовлення!</h2>
                <div style="font-size:2.5rem; font-weight:800; color:var(--primary);" id="modal-fee">50 ₴</div>
                <div id="warning-placeholder"></div>
                <div id="modal-route" style="color:#555; margin:15px 0;"></div>
                <input type="hidden" id="modal-job-id">
                <button onclick="acceptOrder()" class="btn" style="background:var(--status-active); color:black; margin-bottom:10px;">ПРИЙНЯТИ</button>
                <button onclick="closeOrderModal()" style="background:none; border:none; color:#777; text-decoration:underline;">Закрити</button>
             </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // --- GLOBAL STATE ---
            let currentLat = null, currentLon = null;
            let isOnline = {str(courier.is_online).lower()};
            let currentJob = null;
            let activeTab = 'map';
            let socket = null, pingInterval = null;

            // --- MAP INIT ---
            const map = L.map('map', {{ zoomControl: false }}).setView([50.45, 30.52], 13);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
            let marker = null, targetMarker = null, routeLine = null;

            // --- TABS LOGIC ---
            function switchTab(tab) {{
                activeTab = tab;
                document.querySelectorAll('.screen').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                
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

            // --- FETCH ORDERS LOGIC ---
            async function fetchOrders() {{
                if (!isOnline || !currentLat) return;
                const loader = document.getElementById('feed-loader');
                loader.style.opacity = '1';
                try {{
                    const res = await fetch(`/api/courier/open_orders?lat=${{currentLat}}&lon=${{currentLon}}`);
                    const orders = await res.json();
                    renderOrders(orders);
                }} catch(e) {{ console.error(e); }} finally {{ loader.style.opacity = '0.5'; }}
            }}

            function renderOrders(orders) {{
                const container = document.getElementById('orders-list');
                const badge = document.getElementById('orders-badge');
                
                if (orders.length === 0) {{
                    container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-mug-hot"></i><h3>Поки тихо...</h3><p>Немає доступних замовлень поблизу.</p></div>`;
                    badge.style.display = 'none';
                    return;
                }}

                badge.style.display = 'block';
                container.innerHTML = orders.map(o => {{
                    const isHighPrice = o.fee > 100;
                    const cardClass = isHighPrice ? 'order-card high-price' : 'order-card';
                    let badgesHtml = '';
                    if (o.payment_type === 'cash') badgesHtml += '<span class="oc-tag" style="color:#facc15">Готівка</span>';
                    if (o.payment_type === 'buyout') badgesHtml += '<span class="oc-tag" style="color:#ec4899">Викуп</span>';
                    if (o.is_return) badgesHtml += '<span class="oc-tag" style="color:#f97316">Повернення</span>';
                    
                    let distText = o.dist_to_rest !== null ? o.dist_to_rest.toFixed(1) + ' км' : '?';

                    return `
                    <div class="${{cardClass}}">
                        <div class="oc-header">
                            <div class="oc-dist-badge"><i class="fa-solid fa-person-walking"></i> ${{distText}}</div>
                            <div class="oc-price">+${{o.fee}} ₴</div>
                        </div>
                        <div class="oc-route">
                            <div class="oc-point rest"><div style="font-weight:600; color:white;">${{o.restaurant_name}}</div><div style="font-size:0.8rem;">${{o.restaurant_address}}</div></div>
                            <div class="oc-point client"><div style="font-weight:600; color:white;">Клієнт</div><div style="font-size:0.8rem;">${{o.dropoff_address}}</div></div>
                        </div>
                        ${{o.comment ? `<div style="font-size:0.85rem; color:#94a3b8; margin-bottom:10px; background:rgba(255,255,255,0.03); padding:8px; border-radius:8px;">💬 ${{o.comment}}</div>` : ''}}
                        <div class="oc-footer">
                            <div class="oc-tags">${{badgesHtml}}</div>
                            <button class="btn-accept" onclick="acceptOrderFromFeed(${{o.id}})">ПРИЙНЯТИ</button>
                        </div>
                    </div>`;
                }}).join('');
            }}
            
            async function acceptOrderFromFeed(id) {{
                if(!confirm("Прийняти це замовлення?")) return;
                document.getElementById('modal-job-id').value = id;
                await acceptOrder();
                switchTab('map');
            }}

            // --- GEOLOCATION & SOCKET ---
            function connectWS() {{
                if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/courier`);

                socket.onopen = () => {{
                    document.getElementById('connection-dot').style.background = '#4ade80';
                    clearInterval(pingInterval);
                    pingInterval = setInterval(() => {{ if (socket.readyState === WebSocket.OPEN) socket.send("ping"); }}, 15000);
                }};
                socket.onmessage = (e) => {{
                    if (e.data === "pong") return; 
                    const msg = JSON.parse(e.data);
                    
                    if(msg.type === 'new_order') {{
                        if (activeTab === 'orders') fetchOrders(); // Обновляем ленту
                        else {{
                            // Показываем модалку, только если не в ленте
                            showNewOrderModal(msg.data);
                        }}
                    }}
                    else if (msg.type === 'job_update') checkActiveJob();
                    else if (msg.type === 'chat_message') {{
                        const sheetOpen = document.getElementById('chat-sheet').classList.contains('open');
                        if (sheetOpen && currentJob && currentJob.id == msg.job_id) renderSingleMsg(msg);
                        else alert(`💬 Повідомлення: ${{msg.text}}`);
                    }}
                }};
                socket.onclose = () => {{
                    document.getElementById('connection-dot').style.background = 'red';
                    if (isOnline) setTimeout(connectWS, 3000);
                }};
            }}
            
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition((pos) => {{
                    const {{ latitude, longitude }} = pos.coords;
                    currentLat = latitude; currentLon = longitude;

                    if (!marker) {{ marker = L.marker([latitude, longitude]).addTo(map); map.setView([latitude, longitude], 15); }}
                    else marker.setLatLng([latitude, longitude]);
                    
                    if (activeTab === 'orders' && isOnline) fetchOrders();

                    if(isOnline && socket && socket.readyState === WebSocket.OPEN) {{
                        const fd = new FormData(); fd.append('lat', latitude); fd.append('lon', longitude);
                        navigator.sendBeacon('/api/courier/location', fd);
                    }}
                }}, console.error, {{ enableHighAccuracy: true }});
            }}
            
            // Периодическое обновление ленты
            setInterval(() => {{
                if (activeTab === 'orders' && isOnline && currentLat) fetchOrders();
            }}, 15000);

            async function toggleShift() {{
                try {{
                    const res = await fetch('/api/courier/toggle_status', {{method:'POST'}});
                    const data = await res.json();
                    isOnline = data.is_online;
                    
                    document.getElementById('offline-msg').style.display = isOnline ? 'none' : 'flex';
                    document.getElementById('status-dot').className = isOnline ? 'dot online' : 'dot offline';
                    document.getElementById('status-text').innerText = isOnline ? 'НА ЗМІНІ' : 'ОФЛАЙН';
                    
                    if(isOnline) connectWS(); else if(socket) socket.close();
                }} catch(e) {{ alert("Помилка з'єднання"); }}
            }}
            if(isOnline) connectWS();

            // --- JOB LOGIC ---
            async function checkActiveJob() {{
                try {{
                    const res = await fetch('/api/courier/active_job');
                    const data = await res.json();
                    if(data.active) {{
                        currentJob = data.job;
                        renderJobSheet();
                        switchTab('map');
                        document.querySelector('.bottom-nav').style.display = 'none'; // Скрываем табы
                    }} else {{
                        document.getElementById('job-sheet').classList.remove('active');
                        currentJob = null;
                        document.querySelector('.bottom-nav').style.display = 'flex'; // Показываем табы
                        if(targetMarker) {{ map.removeLayer(targetMarker); targetMarker = null; }}
                        if(routeLine) {{ map.removeLayer(routeLine); routeLine = null; }}
                    }}
                }} catch(e) {{}}
            }}
            checkActiveJob();

            function renderJobSheet() {{
                const sheet = document.getElementById('job-sheet');
                sheet.classList.add('active');
                
                document.getElementById('job-title').innerText = `Замовлення #${{currentJob.id}}`;
                document.getElementById('job-price').innerText = `+${{currentJob.delivery_fee}} ₴`;
                document.getElementById('current-target-name').innerText = currentJob.partner_name;
                document.getElementById('client-name').innerText = currentJob.customer_name || 'Гість';
                document.getElementById('client-phone').innerText = currentJob.customer_phone;
                document.getElementById('client-phone').href = `tel:${{currentJob.customer_phone}}`;
                
                const btnNav = document.getElementById('btn-nav');
                const btnAct = document.getElementById('btn-action');
                const btnCall = document.getElementById('btn-call');
                
                if (currentJob.partner_phone) {{ btnCall.href = `tel:${{currentJob.partner_phone}}`; btnCall.style.display = 'flex'; }} 
                else btnCall.style.display = 'none';
                
                document.getElementById('btn-chat').onclick = openChat;

                let destAddr = "";
                if (['assigned', 'ready', 'arrived_pickup'].includes(currentJob.status)) {{
                    destAddr = currentJob.partner_address;
                    document.getElementById('addr-label').innerText = 'ЗАБРАТИ ТУТ:';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('client-info-block').style.display = 'none';
                    document.getElementById('step-1').className = 'step active'; document.getElementById('step-2').className = 'step';
                    
                    if (currentJob.status === 'arrived_pickup') {{
                        btnAct.innerText = '📦 Забрав замовлення';
                        btnAct.style.background = 'var(--status-active)';
                        btnAct.onclick = () => updateStatus('picked_up');
                        document.getElementById('job-status-desc').innerText = 'Чекайте видачі замовлення';
                    }} else {{
                        btnAct.innerText = '👋 Я на місці';
                        btnAct.style.background = 'var(--status-active)';
                        btnAct.onclick = async () => {{
                             await fetch('/api/courier/arrived_pickup', {{method:'POST', body: new URLSearchParams({{job_id: currentJob.id}})}});
                             currentJob.status = 'arrived_pickup'; renderJobSheet();
                        }};
                        document.getElementById('job-status-desc').innerText = 'Прямуйте до закладу';
                    }}
                }} else {{
                    destAddr = currentJob.customer_address;
                    document.getElementById('addr-label').innerText = 'ВЕЗТИ СЮДИ:';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('client-info-block').style.display = 'block';
                    document.getElementById('step-1').className = 'step done'; document.getElementById('step-2').className = 'step active';
                    
                    document.getElementById('job-status-desc').innerText = 'Везіть до клієнта';
                    if (currentJob.payment_type === 'cash') document.getElementById('job-status-desc').innerText = '💵 ОТРИМАЙТЕ ГОТІВКУ!';
                    if (currentJob.payment_type === 'buyout') document.getElementById('job-status-desc').innerText = '💰 ВІЗЬМІТЬ ГРОШІ!';

                    if (currentJob.is_return_required) {{
                        btnAct.innerText = '💰 Забрав гроші (Везу назад)';
                        btnAct.onclick = () => {{ if(confirm("Везти гроші в заклад?")) updateStatus('delivered'); }};
                    }} else if (currentJob.status === 'returning') {{
                         document.getElementById('job-status-desc').innerHTML = '<b style="color:red">↩️ ПОВЕРНІТЬ ГРОШІ!</b>';
                         document.getElementById('addr-label').innerText = 'ВЕЗТИ ГРОШІ СЮДИ:';
                         document.getElementById('current-target-addr').innerText = currentJob.partner_address;
                         btnAct.innerText = '💵 Гроші віддав';
                         btnAct.style.background = '#fb923c';
                         btnAct.onclick = () => alert("Чекайте підтвердження від закладу.");
                    }} else {{
                        btnAct.innerText = '✅ Доставив';
                        btnAct.onclick = () => updateStatus('delivered');
                    }}
                    
                    // Рисуем маршрут к клиенту
                    if (currentJob.customer_lat && currentJob.customer_lon && !targetMarker) {{
                        const pos = [currentJob.customer_lat, currentJob.customer_lon];
                        targetMarker = L.marker(pos).addTo(map);
                        if(marker) {{
                             routeLine = L.polyline([marker.getLatLng(), pos], {{color: '#6366f1', weight: 4, dashArray: '10, 10'}}).addTo(map);
                             map.fitBounds(routeLine.getBounds(), {{padding:[50,50]}});
                        }}
                    }}
                }}
                btnNav.href = `https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(destAddr)}}`;
            }}

            async function updateStatus(newStatus) {{
                const fd = new FormData(); fd.append('job_id', currentJob.id); fd.append('status', newStatus);
                await fetch('/api/courier/update_job_status', {{method:'POST', body:fd}});
                checkActiveJob();
            }}

            async function acceptOrder() {{
                const jobId = document.getElementById('modal-job-id').value;
                const fd = new FormData(); fd.append('job_id', jobId);
                try {{
                    const res = await fetch('/api/courier/accept_order', {{method:'POST', body:fd}});
                    const data = await res.json();
                    closeOrderModal();
                    if(data.status === 'ok') checkActiveJob(); else alert(data.message);
                }} catch(e) {{ alert("Помилка"); }}
            }}

            function showNewOrderModal(data) {{
                document.getElementById('modal-fee').innerText = data.fee + ' ₴';
                let warning = "";
                if (data.payment_type === 'buyout') warning = `<div style="background:#fce7f3; color:#db2777; padding:10px; border-radius:8px; margin-bottom:10px; font-weight:bold;">💰 ПОТРІБЕН ВИКУП: ${{data.price}} грн</div>`;
                document.getElementById('warning-placeholder').innerHTML = warning;
                document.getElementById('modal-route').innerHTML = `<b>${{data.restaurant}}</b> <i class="fa-solid fa-arrow-right"></i> Клієнт`;
                document.getElementById('modal-job-id').value = data.id;
                document.getElementById('orderModal').style.display = 'flex';
            }}
            function closeOrderModal() {{ document.getElementById('orderModal').style.display = 'none'; }}

            // --- CHAT & HISTORY ---
            async function toggleHistory(show) {{
                const modal = document.getElementById('history-modal');
                if(show) {{
                    const res = await fetch('/api/courier/history');
                    const jobs = await res.json();
                    document.getElementById('history-list').innerHTML = jobs.map(j => `
                        <div style="padding:15px; border-bottom:1px solid #333; display:flex; justify-content:space-between">
                            <div><b>#${{j.id}}</b> ${{j.address}}<br><small style="color:#888">${{j.date}}</small></div>
                            <div style="color:#4ade80">+${{j.price}}₴</div>
                        </div>`).join('');
                    modal.classList.add('open');
                }} else modal.classList.remove('open');
            }}
            
            async function openChat() {{
                if(!currentJob) return;
                document.getElementById('chat-sheet').classList.add('open');
                const res = await fetch(`/api/chat/history/${{currentJob.id}}`);
                const msgs = await res.json();
                const container = document.getElementById('chat-body');
                container.innerHTML = '';
                msgs.forEach(renderSingleMsg);
            }}
            function renderSingleMsg(m) {{
                const container = document.getElementById('chat-body');
                const div = document.createElement('div');
                div.className = `msg ${{m.role === 'courier' ? 'me' : 'other'}}`;
                div.innerText = m.text;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }}
            async function sendChatMessage(e) {{
                e.preventDefault();
                const input = document.getElementById('chat-input');
                const text = input.value.trim();
                if(!text || !currentJob) return;
                input.value = '';
                renderSingleMsg({{role:'courier', text:text}}); // optimistic
                const fd = new FormData(); fd.append('job_id', currentJob.id); fd.append('message', text); fd.append('role', 'courier');
                await fetch('/api/chat/send', {{method: 'POST', body: fd}});
            }}
        </script>
    </body>
    </html>
    """