from typing import List, Dict
from templates_saas import GLOBAL_STYLES

# Импорт моделей для типизации
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
    Обновленный дашборд партнера с картой трекинга, WebSocket уведомлениями и автоподстановкой адресов (OSM)
    """
    
    # Генерация таблицы с кнопкой "Следить"
    jobs_rows = ""
    for j in sorted(jobs, key=lambda x: x.id, reverse=True):
        track_btn = ""
        status_color = "#ccc"
        status_text = j.status
        
        if j.status == 'assigned' or j.status == 'picked_up':
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
            status_color = "#fef08a" if j.status == 'assigned' else "#bfdbfe"
        
        courier_name = f"ID {j.courier_id}" if j.courier_id else "—"

        jobs_rows += f"""
        <tr id="row-{j.id}">
            <td>#{j.id}</td>
            <td>{j.dropoff_address}</td>
            <td>{j.order_price} грн</td>
            <td><span class="status-badge" style="background:{status_color}; padding:3px 8px; border-radius:4px; font-size:0.8rem;">{status_text}</span></td>
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

        /* --- STYLES FOR AUTOCOMPLETE (OSM) --- */
        .autocomplete-wrapper {{ position: relative; }}
        .autocomplete-results {{
            position: absolute; top: 100%; left: 0; right: 0;
            background: #1e293b; border: 1px solid var(--border);
            border-top: none; border-radius: 0 0 10px 10px;
            max-height: 200px; overflow-y: auto; z-index: 1000;
            display: none; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .autocomplete-item {{
            padding: 10px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; color: #cbd5e1;
        }}
        .autocomplete-item:hover {{ background: var(--primary); color: white; }}
        .autocomplete-item:last-child {{ border-bottom: none; }}
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
                    <form action="/api/partner/create_order" method="post" autocomplete="off">
                        
                        <div class="autocomplete-wrapper">
                            <label>Куди везти (Адреса клієнта)</label>
                            <input type="text" id="addr_input" name="dropoff_address" placeholder="Вулиця, будинок, під'їзд" required>
                            <div id="addr_results" class="autocomplete-results"></div>
                        </div>
                        
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

            // --- AUTOCOMPLETE (OPENSTREETMAP) ---
            const addrInput = document.getElementById('addr_input');
            const addrResults = document.getElementById('addr_results');
            let searchTimeout = null;

            addrInput.addEventListener('input', function() {{
                clearTimeout(searchTimeout);
                const query = this.value;
                
                if(query.length < 3) {{
                    addrResults.style.display = 'none';
                    return;
                }}
                
                searchTimeout = setTimeout(async () => {{
                    try {{
                        // Шукаємо в Україні (countrycodes=ua)
                        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(query)}}&countrycodes=ua&limit=5&accept-language=uk`;
                        const res = await fetch(url);
                        const data = await res.json();
                        
                        addrResults.innerHTML = '';
                        if(data.length > 0) {{
                            data.forEach(item => {{
                                const div = document.createElement('div');
                                div.className = 'autocomplete-item';
                                // Беремо скорочену назву або повну
                                const displayName = item.display_name;
                                div.innerText = displayName; 
                                div.onclick = () => {{
                                    addrInput.value = displayName;
                                    addrResults.style.display = 'none';
                                }};
                                addrResults.appendChild(div);
                            }});
                            addrResults.style.display = 'block';
                        }} else {{
                            addrResults.style.display = 'none';
                        }}
                    }} catch(e) {{ console.error("OSM Error:", e); }}
                }}, 500); // Затримка 500мс (debounce)
            }});

            // Закриття списку при кліку поза ним
            document.addEventListener('click', (e) => {{
                if(!addrInput.contains(e.target) && !addrResults.contains(e.target)) {{
                    addrResults.style.display = 'none';
                }}
            }});

            // --- WEBSOCKET ДЛЯ ПАРТНЕРА ---
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const socket = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/partner`);

            socket.onopen = () => console.log("Connected to Partner WS");
            
            socket.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'order_update') {{
                    alertSound.play().catch(e => console.log('Audio error:', e));
                    showToast(data.message);
                    updateTableRow(data);
                }}
            }};

            function showToast(text) {{
                const container = document.getElementById('toast-container');
                const toast = document.createElement('div');
                toast.className = 'toast';
                toast.innerHTML = `<i class="fa-solid fa-bell" style="color:#6366f1"></i> <div>${{text}}</div>`;
                container.appendChild(toast);
                setTimeout(() => {{
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                }}, 5000);
            }}

            function updateTableRow(data) {{
                const row = document.getElementById(`row-${{data.job_id}}`);
                if (row) {{
                    const statusSpan = row.cells[3].querySelector('.status-badge');
                    if(statusSpan) {{
                        statusSpan.innerText = data.status_text;
                        statusSpan.style.background = data.status_color;
                    }}
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