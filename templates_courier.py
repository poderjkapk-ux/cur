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
    Полностью обновленный PWA интерфейс с защитой от потери заказов и авто-реконнектом.
    Включает отображение маркера клиента и маршрута, а также Push-уведомления (Firebase).
    """
    status_class = "online" if courier.is_online else "offline"
    status_text = "НА ЗМІНІ" if courier.is_online else "ОФЛАЙН"
    
    # --- PWA META (Manifest) ---
    pwa_meta = '<link rel="manifest" href="/courier/manifest.json">'

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
            <div class="status-indicator" onclick="toggleShift()" style="position: relative;">
                <div id="connection-dot" style="position: absolute; top:-2px; right:-2px; width:6px; height:6px; border-radius:50%; background:red; border:1px solid #0f172a;" title="Connection Status"></div>
                <div id="status-dot" class="dot {status_class}"></div>
                <span id="status-text">{status_text}</span>
            </div>
            <a href="/courier/logout" class="icon-btn"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>
        
        <div id="push-perm-request" style="display:none; position:fixed; top:70px; right:10px; z-index:999; background:#e11d48; padding:10px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.3);">
            <button onclick="requestPushPermission()" style="background:none; border:none; color:white; font-weight:bold;">
                <i class="fa-solid fa-bell"></i> Включити звук
            </button>
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
                <div style="margin-top:5px; color:var(--text-muted); font-size:0.9rem;" id="current-target-name">Ресторан</div>
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
            <div id="history-list"></div>
        </div>

        <div id="orderModal" class="order-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); z-index:2000; align-items:center; justify-content:center; backdrop-filter:blur(5px);">
             <div style="background:white; color:black; padding:30px; border-radius:20px; width:85%; max-width:350px; text-align:center;">
                <h2 style="margin-top:0;">🔥 Нове замовлення!</h2>
                <div style="font-size:2.5rem; font-weight:800; color:var(--primary);" id="modal-fee">50 ₴</div>
                <div id="modal-route" style="color:#555; margin:15px 0; text-align: left;"></div>
                <input type="hidden" id="modal-job-id">
                <button onclick="acceptOrder()" class="btn" style="background:var(--status-active); color:black; margin-bottom:10px;">ПРИЙНЯТИ</button>
                <button onclick="closeOrderModal()" style="background:none; border:none; color:#777; text-decoration:underline;">Закрити</button>
             </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js"></script>

        <script>
            // --- FIREBASE SETUP ---
            const firebaseConfig = {{
                apiKey: "AIzaSyC_amFOh032cBcaeo3f1woLmlwhe6Fyr_k",
                authDomain: "restifysite.firebaseapp.com",
                projectId: "restifysite",
                storageBucket: "restifysite.firebasestorage.app",
                messagingSenderId: "679234031594",
                appId: "1:679234031594:web:cc77807a88c5a03b72ec93"
            }};
            firebase.initializeApp(firebaseConfig);
            
            const messaging = firebase.messaging();
            
            // --- PUSH NOTIFICATION LOGIC (MANUAL REQUEST) ---
            
            // 1. Проверяем права при запуске
            function checkPushStatus() {{
                if (Notification.permission === 'default') {{
                    document.getElementById('push-perm-request').style.display = 'block';
                }} else if (Notification.permission === 'granted') {{
                    initPush(); // Если уже разрешено, инициализируем
                }}
            }}

            // 2. Функция, вызываемая ТОЛЬКО по клику
            async function requestPushPermission() {{
                try {{
                    const permission = await Notification.requestPermission();
                    if (permission === 'granted') {{
                        document.getElementById('push-perm-request').style.display = 'none';
                        initPush();
                    }} else {{
                        alert("Ви заборонили сповіщення. Увімкніть їх у налаштуваннях браузера.");
                    }}
                }} catch (err) {{
                    console.error("Permission error:", err);
                }}
            }}
            
            async function initPush() {{
                try {{
                    const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
                    console.log('Service Worker Registered');

                    // Используем VAPID ключ для получения токена
                    const token = await messaging.getToken({{ 
                        vapidKey: 'BP5-1Obs3DLFOEXn_H-Vopc2JTmVol72wJ8JmcA0dAYFy3YCozBxSn5hbYPkckt5F0T56kiKQYi01cw0hGMOvIU',
                        serviceWorkerRegistration: registration 
                    }});
                    
                    if (token) {{
                        console.log('FCM Token:', token);
                        // Відправляємо токен на сервер
                        const fd = new FormData();
                        fd.append('token', token);
                        await fetch('/api/courier/fcm_token', {{ method: 'POST', body: fd }});
                    }}
                }} catch (err) {{
                    console.error('Push Init Error:', err);
                }}
            }}
            
            // Запускаем проверку при загрузке
            checkPushStatus();
            
            // Обробка пушів, коли додаток відкритий
            messaging.onMessage((payload) => {{
                console.log('Foreground push:', payload);
                // Можна додати звук або тост
                const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                audio.play().catch(e => console.log("Audio play failed"));
            }});

            // --- State ---
            let currentJob = null;
            let isOnline = {str(courier.is_online).lower()};
            let socket = null;
            let pingInterval = null;
            let isReconnecting = false;
            
            // --- Map Init ---
            const map = L.map('map', {{ zoomControl: false }}).setView([50.45, 30.52], 13);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
            
            let marker = null;       // Маркер курьера
            let targetMarker = null; // Маркер назначения
            let routeLine = null;    // Линия маршрута

            // --- Wake Lock (Щоб екран не гас) ---
            async function requestWakeLock() {{
                try {{
                    if ('wakeLock' in navigator) {{
                        await navigator.wakeLock.request('screen');
                        console.log('Wake Lock active');
                    }}
                }} catch (err) {{ console.error(err); }}
            }}
            if(isOnline) requestWakeLock();

            // --- WebSocket Manager (Robust) ---
            function connectWS() {{
                if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/courier`);

                socket.onopen = () => {{
                    console.log("WS Connected");
                    document.getElementById('connection-dot').style.background = '#4ade80'; // Green
                    isReconnecting = false;
                    
                    // Start Heartbeat (Ping) каждые 15 сек
                    clearInterval(pingInterval);
                    pingInterval = setInterval(() => {{
                        if (socket.readyState === WebSocket.OPEN) socket.send("ping");
                    }}, 15000);
                }};

                socket.onmessage = (e) => {{
                    if (e.data === "pong") return; 
                    const msg = JSON.parse(e.data);
                    if(msg.type === 'new_order') {{
                        // Проверяем, не показываем ли мы уже этот заказ
                        const currentModalId = document.getElementById('modal-job-id').value;
                        if (currentModalId != msg.data.id) {{
                            showNewOrder(msg.data);
                        }}
                    }}
                }};

                socket.onclose = (e) => {{
                    console.log("WS Closed", e);
                    document.getElementById('connection-dot').style.background = 'red';
                    clearInterval(pingInterval);
                    
                    // Авто-реконнект, если мы на смене
                    if (isOnline) {{
                        isReconnecting = true;
                        setTimeout(connectWS, 3000); // Пробуем каждые 3 сек
                    }}
                }};
                
                socket.onerror = (err) => {{
                    console.error("WS Error", err);
                    socket.close();
                }};
            }}
            
            if(isOnline) connectWS();

            // --- UI Functions ---
            function showNewOrder(data) {{
                // Проигрываем звук (нужно взаимодействие с пользователем сначала)
                const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                audio.play().catch(e => console.log("Audio play failed (need interaction)"));

                // Вибрация (для Android)
                if (navigator.vibrate) navigator.vibrate([200, 100, 200]);

                document.getElementById('modal-fee').innerText = data.fee + ' ₴';
                // --- МОДИФИКАЦИЯ: Добавляем больше информации в модал ---
                document.getElementById('modal-route').innerHTML = `
                    <div style="font-weight: 700; color: #1e293b; margin-bottom: 5px;">Замовлення #${{data.id}}</div>
                    <div style="font-size: 0.9rem; color: #334155; margin-bottom: 5px;">
                        <i class="fa-solid fa-store" style="color: #6366f1;"></i> <b>${{data.restaurant}}</b>
                    </div>
                    <div style="font-size: 0.8rem; color: #555;">
                        <i class="fa-solid fa-location-dot" style="color: #ef4444;"></i> ${{data.restaurant_address}} ➝ ${{data.address}}
                    </div>
                    <div style="font-size: 1.2rem; font-weight: 600; color: #334155; margin-top: 10px;">
                         Чек клієнта: ${{data.price}} ₴
                    </div>
                `;
                // --------------------------------------------------------
                document.getElementById('modal-job-id').value = data.id;
                document.getElementById('orderModal').style.display = 'flex';
            }}
            
            function closeOrderModal() {{
                document.getElementById('orderModal').style.display = 'none';
                document.getElementById('modal-job-id').value = '';
            }}

            // --- Geolocation ---
            if (navigator.geolocation) {{
                navigator.geolocation.watchPosition((pos) => {{
                    const {{ latitude, longitude }} = pos.coords;
                    if (!marker) {{
                        marker = L.marker([latitude, longitude]).addTo(map);
                        map.setView([latitude, longitude], 15);
                    }} else {{
                        marker.setLatLng([latitude, longitude]);
                    }}
                    
                    // Отправляем локацию, если онлайн и сокет открыт
                    if(isOnline && socket && socket.readyState === WebSocket.OPEN) {{
                        const fd = new FormData();
                        fd.append('lat', latitude);
                        fd.append('lon', longitude);
                        navigator.sendBeacon('/api/courier/location', fd);
                    }}
                }}, console.error, {{ enableHighAccuracy: true }});
            }}

            // --- Shift Logic ---
            async function toggleShift() {{
                try {{
                    const res = await fetch('/api/courier/toggle_status', {{method:'POST'}});
                    const data = await res.json();
                    isOnline = data.is_online;
                    
                    document.getElementById('offline-msg').style.display = isOnline ? 'none' : 'flex';
                    document.getElementById('status-dot').className = isOnline ? 'dot online' : 'dot offline';
                    document.getElementById('status-text').innerText = isOnline ? 'НА ЗМІНІ' : 'ОФЛАЙН';
                    
                    if(isOnline) {{
                        requestWakeLock();
                        connectWS();
                    }} else {{
                        if(socket) socket.close();
                    }}
                }} catch(e) {{
                    alert("Помилка з'єднання. Перевірте інтернет.");
                }}
            }}

            // --- Job Logic (Existing) ---
            async function checkActiveJob() {{
                try {{
                    const res = await fetch('/api/courier/active_job');
                    if (!res.ok) throw new Error("Server Error");
                    const data = await res.json();
                    if(data.active) {{
                        currentJob = data.job;
                        renderJobSheet();
                    }} else {{
                        document.getElementById('job-sheet').classList.remove('active');
                        currentJob = null;
                        
                        // Очистка карты при отсутствии заказа
                        if(targetMarker) {{ map.removeLayer(targetMarker); targetMarker = null; }}
                        if(routeLine) {{ map.removeLayer(routeLine); routeLine = null; }}
                    }}
                }} catch(e) {{
                     console.error(e);
                     alert("Не вдалося завантажити деталі замовлення. Спробуйте оновити сторінку.");
                }}
            }}
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

                // --- ЛОГИКА ОТОБРАЖЕНИЯ НА КАРТЕ ---
                
                // 1. Очищаем старые маркеры назначения
                if (targetMarker) {{ map.removeLayer(targetMarker); targetMarker = null; }}
                if (routeLine) {{ map.removeLayer(routeLine); routeLine = null; }}

                let destLat = null;
                let destLon = null;
                let destAddr = "";

                if (currentJob.status === 'assigned') {{
                    // Едем в РЕСТОРАН.
                    destAddr = currentJob.partner_address;
                    
                    steps[0].className = 'step active'; steps[1].className = 'step';
                    document.getElementById('job-status-desc').innerText = 'Прямуйте до закладу';
                    document.getElementById('addr-label').innerText = 'ЗАБРАТИ ТУТ:';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('current-target-name').innerText = currentJob.partner_name;
                    document.getElementById('client-info-block').style.display = 'none';
                    
                    // Ссылка на навигатор (по адресу)
                    btnNav.href = `https://www.google.com/maps/search/?api=1&query=$?q=${{encodeURIComponent(destAddr)}}`;
                    
                    btnAct.innerText = 'Забрав замовлення';
                    btnAct.onclick = () => updateStatus('picked_up');
                    
                }} else if (currentJob.status === 'picked_up') {{
                    // Едем к КЛИЕНТУ.
                    destLat = currentJob.customer_lat;
                    destLon = currentJob.customer_lon;
                    destAddr = currentJob.customer_address;

                    steps[0].className = 'step done'; steps[1].className = 'step active';
                    document.getElementById('job-status-desc').innerText = 'Везіть до клієнта';
                    document.getElementById('addr-label').innerText = 'ВЕЗТИ СЮДИ:';
                    document.getElementById('current-target-addr').innerText = destAddr;
                    document.getElementById('current-target-name').innerText = 'Клієнт';
                    document.getElementById('client-info-block').style.display = 'block';
                    
                    // Если есть координаты - ставим маркер и строим линию
                    if (destLat && destLon) {{
                        const redIcon = new L.Icon({{
                            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                            iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
                        }});
                        
                        targetMarker = L.marker([destLat, destLon], {{icon: redIcon}}).addTo(map)
                            .bindPopup("Клієнт: " + destAddr).openPopup();

                        // Если курьер тоже на карте, рисуем линию
                        if (marker) {{
                            const courierPos = marker.getLatLng();
                            const targetPos = [destLat, destLon];
                            routeLine = L.polyline([courierPos, targetPos], {{color: '#6366f1', weight: 4, dashArray: '10, 10'}}).addTo(map);
                            map.fitBounds(routeLine.getBounds(), {{padding: [50, 50]}});
                        }} else {{
                             map.setView([destLat, destLon], 14);
                        }}

                        // Ссылка на навигатор (по координатам)
                        btnNav.href = `https://www.google.com/maps/search/?api=1&query=$?q=${{destLat}},${{destLon}}`;
                    }} else {{
                        // Если координат нет, используем адрес
                        btnNav.href = `https://www.google.com/maps/search/?api=1&query=$?q=${{encodeURIComponent(destAddr)}}`;
                    }}

                    btnAct.innerText = '✅ Доставив';
                    btnAct.onclick = () => updateStatus('delivered');
                }}
            }}

            async function acceptOrder() {{
                const jobId = document.getElementById('modal-job-id').value;
                const fd = new FormData(); fd.append('job_id', jobId);
                
                try {{
                    const res = await fetch('/api/courier/accept_order', {{method:'POST', body:fd}});
                    const data = await res.json();
                    closeOrderModal();
                    if(data.status === 'ok') checkActiveJob();
                    else alert(data.message);
                }} catch(e) {{
                    alert("Помилка при прийнятті. Можливо, замовлення вже забрав інший кур'єр.");
                    closeOrderModal();
                }}
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
                        // Удаляем маркеры
                        if(targetMarker) {{ map.removeLayer(targetMarker); targetMarker = null; }}
                        if(routeLine) {{ map.removeLayer(routeLine); routeLine = null; }}
                    }} else {{
                        renderJobSheet();
                    }}
                }}
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
        </script>
    </body>
    </html>
    """