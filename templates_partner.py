import pytz
from datetime import datetime
from typing import List, Dict
from templates_saas import GLOBAL_STYLES

# Импорт моделей для типизации (с заглушкой на случай циклических импортов)
try:
    from models import DeliveryPartner, DeliveryJob, Courier
except ImportError:
    class DeliveryPartner: pass
    class DeliveryJob: pass
    class Courier: pass

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

# --- Шаблоны для ПАРТНЕРОВ (Рестораны без сайта) ---

def get_partner_auth_html(is_register=False, message=""):
    """Страница входа/регистрации для Партнеров (с верификацией при регистрации)"""
    title = "Реєстрація Партнера" if is_register else "Вхід для Партнерів"
    action = "/partner/register" if is_register else "/partner/login"
    pwa_meta = '<link rel="manifest" href="/partner/manifest.json">'
    viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    
    leaflet_css = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>' if is_register else ""
    
    verify_script = ""
    verify_style = ""
    verify_block = ""
    phone_input = '<input type="text" name="phone" placeholder="Телефон" required>' 
    submit_attr = ""
    map_html = ""

    # Если регистрация - добавляем логику верификации И КАРТУ
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

            /* СТИЛИ ДЛЯ КАРТЫ И ПОИСКА */
            .autocomplete-wrapper { position: relative; }
            .autocomplete-results { position: absolute; top: 100%; left: 0; right: 0; background: #1e293b; border: 1px solid var(--border); border-top: none; border-radius: 0 0 10px 10px; max-height: 200px; overflow-y: auto; z-index: 9999; display: none; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: left; }
            .autocomplete-item { padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; color: #cbd5e1; display:flex; flex-direction:column; }
            .autocomplete-item small { color: #64748b; font-size: 0.8rem; margin-top:2px; }
            .autocomplete-item:hover { background: var(--primary); color: white; }
            
            /* Индикатор загрузки в поле ввода */
            .loading-input {
                background-image: url("data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cstyle%3E.spinner_P7sC%7Btransform-origin:center;animation:spinner_svv2 .75s infinite linear%7D@keyframes spinner_svv2%7B100%25%7Btransform:rotate(360deg)%7D%7D%3C/style%3E%3Cpath d='M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z' class='spinner_P7sC' fill='%236366f1'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-position: right 10px center;
                background-size: 20px 20px;
            }

            #picker-map { width: 100%; height: 250px; border-radius: 10px; margin-bottom: 15px; border: 1px solid var(--border); display:none; }
            #picker-map.visible { display: block; }
            .map-hint { font-size: 0.8rem; color: #facc15; margin-bottom: 10px; display:none; text-align: left; }
        </style>
        """
        
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

        map_html = """
        <div class="autocomplete-wrapper">
            <input type="text" id="addr_input" name="address" placeholder="Адреса закладу (почніть вводити)" required autocomplete="off">
            <div id="addr_results" class="autocomplete-results"></div>
        </div>
        <div class="map-hint" id="map-hint"><i class="fa-solid fa-hand-pointer"></i> Уточніть точку на карті (Одеса)</div>
        <div id="picker-map"></div>
        <input type="hidden" id="form_lat">
        <input type="hidden" id="form_lon">
        """

        verify_script = """
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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

            // --- КАРТА И ПОИСК ---
            const addrInput = document.getElementById('addr_input');
            const addrResults = document.getElementById('addr_results');
            const latInput = document.getElementById('form_lat');
            const lonInput = document.getElementById('form_lon');
            const pickerMapDiv = document.getElementById('picker-map');
            const mapHint = document.getElementById('map-hint');
            
            let pickerMap, pickerMarker;
            let searchTimeout = null;
            let latestReqId = 0; // Для отслеживания актуальности запроса

            // КООРДИНАТЫ ОДЕССЫ ПО УМОЛЧАНИЮ
            const ODESA_LAT = 46.4825;
            const ODESA_LON = 30.7233;

            function initPickerMap(lat, lon) {
                if (pickerMap) return;
                pickerMapDiv.classList.add('visible');
                mapHint.style.display = 'block';
                
                const startPos = (lat && lon) ? [lat, lon] : [ODESA_LAT, ODESA_LON];
                
                pickerMap = L.map('picker-map').setView(startPos, 13);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap contributors'
                }).addTo(pickerMap);
                
                pickerMarker = L.marker(startPos, {draggable: true}).addTo(pickerMap);
                
                pickerMarker.on('dragend', function(e) {
                    const pos = e.target.getLatLng();
                    if(latInput) latInput.value = pos.lat;
                    if(lonInput) lonInput.value = pos.lng;
                });
                
                pickerMap.on('click', function(e) {
                    pickerMarker.setLatLng(e.latlng);
                    if(latInput) latInput.value = e.latlng.lat;
                    if(lonInput) lonInput.value = e.latlng.lng;
                });
                
                setTimeout(() => pickerMap.invalidateSize(), 200);
            }

            if(addrInput) {
                addrInput.addEventListener('input', function() {
                    clearTimeout(searchTimeout);
                    const query = this.value.trim();
                    
                    if (!pickerMap) initPickerMap();
                    
                    if(query.length < 3) { 
                        addrResults.style.display = 'none';
                        addrInput.classList.remove('loading-input'); 
                        return; 
                    }
                    
                    addrInput.classList.add('loading-input');
                    
                    // Дебаунс 800мс
                    searchTimeout = setTimeout(async () => {
                        const reqId = ++latestReqId;
                        
                        try {
                            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&accept-language=uk&addressdetails=1&viewbox=30.6,46.6,30.8,46.3&bounded=0&limit=5`;
                            
                            const res = await fetch(url);
                            
                            if (reqId !== latestReqId) return;

                            if (!res.ok) throw new Error("API Error");
                            const data = await res.json();
                            
                            addrResults.innerHTML = '';
                            if(data && data.length > 0) {
                                data.forEach(item => {
                                    const div = document.createElement('div');
                                    div.className = 'autocomplete-item';
                                    
                                    const displayName = item.display_name;
                                    const parts = displayName.split(',');
                                    const mainName = parts[0];
                                    const subName = parts.slice(1).join(',').trim();
                                    
                                    div.innerHTML = `<span>${mainName}</span><small>${subName}</small>`;
                                    div.onclick = () => { 
                                        const a = item.address;
                                        const cleanParts = [];
                                        
                                        if (a.road) cleanParts.push(a.road);
                                        else if (a.pedestrian) cleanParts.push(a.pedestrian);
                                        else if (a.hamlet) cleanParts.push(a.hamlet);
                                        else cleanParts.push(mainName);
                                        
                                        if (a.house_number) cleanParts.push(a.house_number);
                                        
                                        if (a.city) cleanParts.push(a.city);
                                        else if (a.town) cleanParts.push(a.town);
                                        else if (a.village) cleanParts.push(a.village);
                                        
                                        addrInput.value = cleanParts.join(', ');
                                        addrResults.style.display = 'none';
                                        
                                        const lat = item.lat;
                                        const lon = item.lon;
                                        
                                        if(latInput) latInput.value = lat;
                                        if(lonInput) lonInput.value = lon;
                                        
                                        if(pickerMap) {
                                            pickerMarker.setLatLng([lat, lon]);
                                            pickerMap.setView([lat, lon], 16);
                                        } else {
                                            initPickerMap(lat, lon);
                                        }
                                    };
                                    addrResults.appendChild(div);
                                });
                                addrResults.style.display = 'block';
                            } else { 
                                addrResults.style.display = 'none'; 
                            }
                        } catch(e) {
                             console.error("Search error:", e);
                        } finally {
                             if (reqId === latestReqId) {
                                 addrInput.classList.remove('loading-input');
                             }
                        }
                    }, 800);
                });
                
                document.addEventListener('click', (e) => { 
                    if(!addrInput.contains(e.target) && !addrResults.contains(e.target)) addrResults.style.display = 'none'; 
                });
            }
        </script>
        """

    extra_fields = ""
    if is_register:
        extra_fields = f"""
        <input type="text" name="name" placeholder="Назва закладу" required>
        {phone_input}
        {verify_block}
        {map_html} """
    
    toggle_link = f'<a href="/partner/login">Вже є акаунт? Увійти</a>' if is_register else f'<a href="/partner/register">Стати партнером</a>'

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>{title}</title>{GLOBAL_STYLES}{pwa_meta}{viewport_meta}{leaflet_css}{verify_style}</head>
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


# =================================================================================
# CSS та JavaScript для Дашборду винесені у звичайні змінні, щоб уникнути помилок з `{` `}`
# =================================================================================

DASHBOARD_CSS = """
<style>
    body { background-color: #0f172a; padding: 20px; }
    
    /* Layout */
    .dashboard-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 30px; max-width: 1400px; margin: 0 auto; width: 100%; }
    @media (max-width: 1000px) { .dashboard-grid { grid-template-columns: 1fr; } }
    
    .panel { 
        background: #1e293b; 
        border: 1px solid rgba(255,255,255,0.05); 
        border-radius: 20px; 
        padding: 25px; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .header-bar { 
        display: flex; justify-content: space-between; align-items: center; 
        max-width: 1400px; margin: 0 auto 30px; width: 100%;
    }
    .header-bar h2 { color: white; margin: 0; font-size: 1.5rem; }
    
    /* Tables Default (Desktop) */
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }
    th, td { padding: 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); color: #e2e8f0; vertical-align: middle; }
    th { color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
    
    /* СТИЛІ ТАЙМЛАЙНУ (ХРОНОЛОГІЇ) */
    .timeline { display: flex; flex-direction: column; gap: 8px; margin-top: 15px; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 12px; }
    .tl-title { font-size: 0.75rem; color: #6366f1; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 0.05em; }
    .tl-step { display: flex; align-items: flex-start; gap: 10px; }
    .tl-icon-wrap { display: flex; flex-direction: column; align-items: center; width: 12px; }
    .tl-icon { width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.2); z-index: 2; margin-top: 3px; }
    .tl-icon.done { background: #6366f1; }
    .tl-line { width: 2px; background: rgba(255,255,255,0.1); flex-grow: 1; min-height: 15px; margin-top: 2px; }
    .tl-icon.done + .tl-line { background: rgba(99, 102, 241, 0.5); }
    .tl-content { flex: 1; display: flex; justify-content: space-between; align-items: flex-start; line-height: 1.2; }
    .tl-text { font-size: 0.85rem; color: #94a3b8; }
    .tl-text.done { color: #f8fafc; font-weight: 600; }
    .tl-time { font-size: 0.75rem; color: #64748b; margin-left: 10px; white-space: nowrap; }
    .tl-badge { background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 2px 5px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-left: 5px; }

    /* Status Badge */
    .status-badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Buttons */
    .btn-mini { 
        border: none; border-radius: 8px; width: 36px; height: 36px; cursor: pointer; 
        display: flex; align-items: center; justify-content: center; transition: 0.2s; 
        background: rgba(255,255,255,0.05); color: #94a3b8; text-decoration: none; font-size: 1rem;
    }
    .btn-mini:hover { transform: translateY(-2px); color: white; }
    .btn-mini.info:hover { background: #6366f1; }
    .btn-mini.danger:hover { background: #e11d48; }
    .btn-mini.success:hover { background: #22c55e; }
    .btn-mini.warn:hover { background: #f59e0b; }

    /* Forms */
    label { color: #94a3b8; font-size: 0.85rem; margin-bottom: 5px; display: block; }
    input, select, textarea {
        background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white;
        padding: 12px 15px; border-radius: 10px; width: 100%; box-sizing: border-box;
        font-size: 1rem; margin-bottom: 15px; transition: 0.3s;
    }
    input:focus, select:focus, textarea:focus {
        outline: none; border-color: #6366f1; background: rgba(99, 102, 241, 0.05);
    }

    /* --- MOBILE ADAPTATION (RESPONSIVE) --- */
    @media (max-width: 768px) {
        body { padding: 10px; }
        .header-bar { margin-bottom: 20px; }
        .header-bar h2 { font-size: 1.2rem; }
        .panel { padding: 15px; border-radius: 16px; }
        thead { display: none; }
        tr {
            display: block;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        td {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            text-align: right;
        }
        td:last-child { border-bottom: none; padding-bottom: 0; }
        td::before {
            content: attr(data-label);
            font-weight: 600;
            color: #64748b;
            font-size: 0.85rem;
            text-align: left;
            margin-right: 15px;
        }
        .actions-cell {
            display: block;
            margin-top: 10px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .actions-cell::before { display: none; }
        .actions-cell > div { justify-content: space-between; width: 100%; }
        .btn-mini { width: 42px; height: 42px; font-size: 1.1rem; }
        .payment-options { grid-template-columns: 1fr; gap: 8px; }
        .courier-cell { flex-direction: column; align-items: flex-end; text-align: right; }
        .courier-cell::before { align-self: flex-start; }
        .timeline { width: 100%; text-align: left; box-sizing: border-box; }
    }

    /* Modals */
    .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 2000; display: none; align-items: center; justify-content: center; backdrop-filter: blur(5px); }
    .modal-card { background: #1e293b; width: 95%; max-width: 500px; border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; position: relative; padding: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); max-height: 90vh; overflow-y: auto; }
    .track-card { max-width: 800px; height: 60vh; padding: 0; }
    #track-map { flex: 1; width: 100%; min-height: 300px; }
    
    .chat-modal { height: 80vh; }
    .chat-messages { flex: 1; overflow-y: auto; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 10px; }
    .msg { max-width: 80%; padding: 10px 14px; border-radius: 16px; font-size: 0.95rem; position: relative; line-height: 1.4; }
    .msg.me { align-self: flex-end; background: #6366f1; color: white; border-bottom-right-radius: 4px; }
    .msg.other { align-self: flex-start; background: #334155; color: white; border-bottom-left-radius: 4px; }
    .msg-time { font-size: 0.7rem; opacity: 0.7; text-align: right; margin-top: 4px; }

    .payment-options { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
    .payment-option input { display: none; }
    .payment-option label { display: block; background: rgba(255,255,255,0.05); padding: 12px; text-align: center; border-radius: 10px; cursor: pointer; border: 1px solid transparent; font-size: 0.9rem; transition: 0.2s; }
    .payment-option input:checked + label { background: rgba(99, 102, 241, 0.2); border-color: #6366f1; color: white; font-weight: bold; }
    
    .star-rating { display: flex; flex-direction: row-reverse; justify-content: center; gap: 5px; margin: 20px 0; }
    .star-rating input { display: none; }
    .star-rating label { cursor: pointer; font-size: 2.5rem; color: #444; transition: 0.2s; }
    .star-rating input:checked ~ label, .star-rating label:hover, .star-rating label:hover ~ label { color: #fbbf24; }

    #toast-container { position: fixed; top: 20px; right: 20px; z-index: 3000; pointer-events: none; }
    .toast { pointer-events: auto; background: #1e293b; color: white; padding: 15px 20px; border-left: 5px solid #6366f1; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); display: flex; align-items: center; gap: 15px; animation: slideIn 0.3s ease-out; min-width: 300px; }
    @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    
    /* Autocomplete & Loading */
    .autocomplete-wrapper { position: relative; z-index: 1001; }
    .autocomplete-results { position: absolute; top: 100%; left: 0; right: 0; background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-top: none; border-radius: 0 0 10px 10px; max-height: 250px; overflow-y: auto; z-index: 9999; display: none; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .autocomplete-item { padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.95rem; color: #cbd5e1; display:flex; flex-direction:column; }
    .autocomplete-item small { color: #64748b; font-size: 0.8rem; margin-top:2px; }
    .autocomplete-item:hover { background: #6366f1; color: white; }
    
    /* Spinner */
    .loading-input {
        background-image: url("data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cstyle%3E.spinner_P7sC{transform-origin:center;animation:spinner_svv2 .75s infinite linear}@keyframes spinner_svv2{100%{transform:rotate(360deg)}}%3C/style%3E%3Cpath d='M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z' class='spinner_P7sC' fill='%236366f1'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 10px center;
        background-size: 20px 20px;
    }

    #picker-map { width: 100%; height: 250px; border-radius: 12px; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1); z-index: 1; display:none; }
    #picker-map.visible { display: block; }
    .map-hint { font-size: 0.85rem; color: #facc15; margin-bottom: 10px; display:none; background: rgba(250, 204, 21, 0.1); padding: 8px; border-radius: 6px; }
</style>
"""

DASHBOARD_SCRIPT = """
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    // --- ЛОГИКА ОПЛАТЫ ---
    const baseFee = 80; 
    const returnFee = 40; 
    function updateFormLogic() {
        const type = document.querySelector('input[name="payment_type"]:checked').value;
        const buyoutBlock = document.getElementById('buyout-options');
        
        buyoutBlock.style.display = 'none';
        if (type === 'buyout') { 
            buyoutBlock.style.display = 'block'; 
        }
    }
    
    // --- ЗВУК И TOAST ---
    const alertSound = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
    function showToast(text) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<i class="fa-solid fa-bell" style="color:#6366f1"></i> <div>${text}</div>`;
        container.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 5000);
    }

    // --- BOOST ---
    async function boostOrder(id) {
        if(!confirm("Підняти ціну доставки на 10 грн, щоб пришвидшити пошук?")) return;
        const fd = new FormData(); fd.append('job_id', id); fd.append('amount', 10);
        try {
            const res = await fetch('/api/partner/boost_order', {method:'POST', body:fd});
            const data = await res.json();
            if(res.ok) { showToast(`💸 Ціну піднято! Нова сума: ${data.new_fee} грн`); setTimeout(() => location.reload(), 1500); }
            else { alert(data.message || "Помилка"); }
        } catch(e) { alert("Помилка з'єднання"); }
    }

    // ==========================================
    // ПОИСК АДРЕСА: ОБНОВЛЕН (Одесса + Nominatim + БЕЗ РАЙОНА)
    // ==========================================
    const addrInput = document.getElementById('addr_input');
    const addrResults = document.getElementById('addr_results');
    const latInput = document.getElementById('form_lat');
    const lonInput = document.getElementById('form_lon');
    const pickerMapDiv = document.getElementById('picker-map');
    const mapHint = document.getElementById('map-hint');
    
    let pickerMap, pickerMarker;
    let searchTimeout = null;
    let latestReqId = 0; // Счетчик запросов

    // КООРДИНАТЫ ОДЕССЫ ПО УМОЛЧАНИЮ
    const ODESA_LAT = 46.4825;
    const ODESA_LON = 30.7233;

    function initPickerMap(lat, lon) {
        if (pickerMap) return;
        try {
            pickerMapDiv.classList.add('visible');
            mapHint.style.display = 'block';
            const startPos = (lat && lon) ? [lat, lon] : [ODESA_LAT, ODESA_LON];
            
            pickerMap = L.map('picker-map').setView(startPos, 13);
            // Используем OpenStreetMap (Open Map)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(pickerMap);

            pickerMarker = L.marker(startPos, {draggable: true}).addTo(pickerMap);
            
            pickerMarker.on('dragend', function(e) {
                const pos = e.target.getLatLng();
                latInput.value = pos.lat; lonInput.value = pos.lng;
            });
            pickerMap.on('click', function(e) {
                pickerMarker.setLatLng(e.latlng);
                latInput.value = e.latlng.lat; lonInput.value = e.latlng.lng;
            });
            setTimeout(() => pickerMap.invalidateSize(), 200);
        } catch(e) { console.error("Leaflet init error:", e); }
    }

    if(addrInput) {
        addrInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (!pickerMap) initPickerMap();
            
            if(query.length < 3) { 
                addrResults.style.display = 'none'; 
                addrInput.classList.remove('loading-input');
                return; 
            }
            
            addrInput.classList.add('loading-input');
            
            // Дебаунс 800мс
            searchTimeout = setTimeout(async () => {
                const reqId = ++latestReqId;
                
                try {
                    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&accept-language=uk&addressdetails=1&viewbox=30.6,46.6,30.8,46.3&bounded=0&limit=5`;
                    
                    const res = await fetch(url);
                    
                    if (reqId !== latestReqId) return;

                    if (!res.ok) throw new Error("API Error");
                    const data = await res.json();
                    
                    addrResults.innerHTML = '';
                    if(data && data.length > 0) {
                        data.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'autocomplete-item';
                            
                            const displayName = item.display_name;
                            const parts = displayName.split(',');
                            const mainName = parts[0];
                            const subName = parts.slice(1).join(',').trim();
                            
                            div.innerHTML = `<span>${mainName}</span><small>${subName}</small>`;
                            div.onclick = () => { 
                                // --- СБОРКА КОРОТКОГО АДРЕСА ---
                                const a = item.address;
                                const cleanParts = [];
                                
                                if (a.road) cleanParts.push(a.road);
                                else if (a.pedestrian) cleanParts.push(a.pedestrian);
                                else if (a.hamlet) cleanParts.push(a.hamlet);
                                else cleanParts.push(mainName);
                                
                                if (a.house_number) cleanParts.push(a.house_number);
                                
                                if (a.city) cleanParts.push(a.city);
                                else if (a.town) cleanParts.push(a.town);
                                else if (a.village) cleanParts.push(a.village);
                                
                                addrInput.value = cleanParts.join(', ');
                                addrResults.style.display = 'none';
                                
                                const lat = parseFloat(item.lat);
                                const lon = parseFloat(item.lon);
                                
                                latInput.value = lat; lonInput.value = lon;
                                if(pickerMap) { 
                                    pickerMarker.setLatLng([lat, lon]); 
                                    pickerMap.setView([lat, lon], 16); 
                                } else { 
                                    initPickerMap(lat, lon); 
                                }
                            };
                            addrResults.appendChild(div);
                        });
                        addrResults.style.display = 'block';
                    } else { addrResults.style.display = 'none'; }
                } catch(e) { 
                    console.error("Search error:", e); 
                } finally { 
                    if (reqId === latestReqId) {
                        addrInput.classList.remove('loading-input'); 
                    }
                }
            }, 800);
        });
        document.addEventListener('click', (e) => { if(!addrInput.contains(e.target) && !addrResults.contains(e.target)) addrResults.style.display = 'none'; });
    }
    
    // --- WEBSOCKET ---
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/partner`);
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'order_update') {
            alertSound.play().catch(e => {});
            showToast(data.message);
            setTimeout(() => location.reload(), 2000); 
        } 
        else if (data.type === 'chat_message') {
            const openJobId = document.getElementById('chat_job_id').value;
            const modalOpen = document.getElementById('chatModal').style.display === 'flex';
            if (modalOpen && openJobId == data.job_id) {
                const container = document.getElementById('chat-messages');
                const div = document.createElement('div');
                div.className = 'msg other';
                div.innerHTML = `${data.text} <div class="msg-time">${data.time}</div>`;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            } else { showToast(`💬 Нове повідомлення: ${data.text}`); }
        }
    };

    // --- CHAT LOGIC ---
    async function openChat(jobId, title) {
        document.getElementById('chatModal').style.display = 'flex';
        document.getElementById('chat-title').innerText = title;
        document.getElementById('chat_job_id').value = jobId;
        document.getElementById('chat-messages').innerHTML = '<div style="text-align:center; color:#888">Завантаження...</div>';
        try {
            const res = await fetch(`/api/chat/history/${jobId}`);
            const msgs = await res.json();
            renderMessages(msgs);
        } catch(e) {}
    }
    function renderMessages(msgs) {
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        msgs.forEach(m => {
            const div = document.createElement('div');
            div.className = `msg ${m.role === 'partner' ? 'me' : 'other'}`;
            div.innerHTML = `${m.text} <div class="msg-time">${m.time}</div>`;
            container.appendChild(div);
        });
        container.scrollTop = container.scrollHeight;
    }
    async function sendChatMessage(e) {
        e.preventDefault();
        const input = document.getElementById('chat_input');
        const jobId = document.getElementById('chat_job_id').value;
        const text = input.value.trim();
        if(!text) return;
        input.value = '';
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'msg me';
        // Локальное время бразуера (пользователя) - здесь конвертация не нужна
        const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        div.innerHTML = `${text} <div class="msg-time">${time}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        const fd = new FormData();
        fd.append('job_id', jobId); fd.append('message', text); fd.append('role', 'partner');
        await fetch('/api/chat/send', {method: 'POST', body: fd});
    }

    // --- ACTIONS ---
    async function cancelOrder(jobId) { if(!confirm("Скасувати це замовлення?")) return; const fd = new FormData(); fd.append('job_id', jobId); try { await fetch('/api/partner/cancel_order', {method:'POST', body:fd}); location.reload(); } catch(e) {} }
    async function markReady(jobId) { if(!confirm("Підтвердити готовність?")) return; const fd = new FormData(); fd.append('job_id', jobId); try { await fetch('/api/partner/order_ready', {method:'POST', body:fd}); location.reload(); } catch(e) {} }
    async function confirmReturn(jobId) { if(!confirm("Гроші отримано?")) return; const fd = new FormData(); fd.append('job_id', jobId); try { await fetch('/api/partner/confirm_return', {method:'POST', body:fd}); location.reload(); } catch(e) {} }
    async function confirmBuyoutPaid(jobId) { if(!confirm("Підтвердити, що кур'єр оплатив своє замовлення на касі?")) return; const fd = new FormData(); fd.append('job_id', jobId); try { await fetch('/api/partner/confirm_buyout_paid', {method:'POST', body:fd}); location.reload(); } catch(e) {} }

    // --- RATING & TRACKING ---
    function openRateModal(jobId) { document.getElementById('rate_job_id').value = jobId; document.getElementById('rateModal').style.display = 'flex'; }
    async function submitRating(e) { e.preventDefault(); const form = new FormData(e.target); try { await fetch('/api/partner/rate_courier', {method:'POST', body:form}); location.reload(); } catch(e) {} }

    let map, courierMarker, trackInterval;
    function openTrackModal(jobId) {
        document.getElementById('trackModal').style.display = 'flex';
        if(!map) {
            map = L.map('track-map').setView([46.4825, 30.7233], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
        }
        fetchLocation(jobId);
        trackInterval = setInterval(() => fetchLocation(jobId), 5000);
    }
    function closeTrackModal() { document.getElementById('trackModal').style.display = 'none'; clearInterval(trackInterval); }
    async function fetchLocation(jobId) {
        try {
            const res = await fetch(`/api/partner/track_courier/${jobId}`);
            const data = await res.json();
            if(data.status === 'ok' && data.lat) {
                document.getElementById('track-info').innerHTML = `🚴 <b>${data.name}</b> • ${data.job_status}`;
                const pos = [data.lat, data.lon];
                if(!courierMarker) courierMarker = L.marker(pos).addTo(map); else courierMarker.setLatLng(pos);
                map.setView(pos, 15);
            }
        } catch(e) {}
    }
</script>
"""

def get_partner_dashboard_html(partner: DeliveryPartner, jobs: List[DeliveryJob], tz_string: str = "Europe/Kiev"):
    """
    Дашборд партнера з підтримкою часових поясів та візуальним таймлайном.
    """
    
    def calc_mins(start, end):
        if not start or not end: return None
        mins = int((end - start).total_seconds() / 60)
        return f"+{mins} хв" if mins > 0 else "< 1 хв"

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
        status_bg = "rgba(255,255,255,0.1)"
        status_fg = "#ccc"
        
        courier_info = "—"
        timeline_html = ""
        action_btn = ""

        # === ЗБІРКА ТАЙМЛАЙНУ ДЛЯ ЗАКАЗУ ===
        t_created = format_local_time(j.created_at, tz_string, '%H:%M')
        t_accepted = format_local_time(j.accepted_at, tz_string, '%H:%M') if j.accepted_at else None
        t_arrived = format_local_time(j.arrived_at_pickup_at, tz_string, '%H:%M') if j.arrived_at_pickup_at else None
        t_picked = format_local_time(j.picked_up_at, tz_string, '%H:%M') if j.picked_up_at else None

        timeline_html += f"""<div class="timeline"><div class="tl-title">Хронологія виконання</div>"""
        
        # Крок 1: Створено
        timeline_html += f"""
        <div class="tl-step">
            <div class="tl-icon-wrap"><div class="tl-icon done"></div><div class="tl-line"></div></div>
            <div class="tl-content"><div class="tl-text done">Створено</div><div class="tl-time">{t_created}</div></div>
        </div>
        """
        
        # Крок 2: Прийнято
        if j.accepted_at or j.status != 'pending':
            dur = calc_mins(j.created_at, j.accepted_at)
            is_done = j.accepted_at is not None
            is_last = j.arrived_at_pickup_at is None
            badge = f'<span class="tl-badge">{dur}</span>' if dur else ''
            icon_cls = "done" if is_done else ""
            txt_cls = "done" if is_done else ""
            line = '<div class="tl-line"></div>' if not is_last else ''
            
            timeline_html += f"""
            <div class="tl-step">
                <div class="tl-icon-wrap"><div class="tl-icon {icon_cls}"></div>{line}</div>
                <div class="tl-content"><div class="tl-text {txt_cls}">Кур'єр прийняв {badge}</div><div class="tl-time">{t_accepted or ''}</div></div>
            </div>
            """
            
        # Крок 3: Прибув у заклад
        if j.arrived_at_pickup_at or j.status in ['arrived_pickup', 'ready', 'picked_up', 'delivered']:
            dur = calc_mins(j.accepted_at, j.arrived_at_pickup_at)
            is_done = j.arrived_at_pickup_at is not None
            is_last = j.picked_up_at is None
            badge = f'<span class="tl-badge">{dur}</span>' if dur else ''
            icon_cls = "done" if is_done else ""
            txt_cls = "done" if is_done else ""
            line = '<div class="tl-line"></div>' if not is_last else ''
            
            timeline_html += f"""
            <div class="tl-step">
                <div class="tl-icon-wrap"><div class="tl-icon {icon_cls}"></div>{line}</div>
                <div class="tl-content"><div class="tl-text {txt_cls}">Прибув у заклад {badge}</div><div class="tl-time">{t_arrived or ''}</div></div>
            </div>
            """
            
        # Крок 4: Забрав замовлення
        if j.picked_up_at or j.status in ['picked_up', 'delivered', 'returning']:
            dur = calc_mins(j.arrived_at_pickup_at, j.picked_up_at)
            is_done = j.picked_up_at is not None
            badge = f'<span class="tl-badge">{dur}</span>' if dur else ''
            icon_cls = "done" if is_done else ""
            txt_cls = "done" if is_done else ""
            
            timeline_html += f"""
            <div class="tl-step">
                <div class="tl-icon-wrap"><div class="tl-icon {icon_cls}"></div></div>
                <div class="tl-content"><div class="tl-text {txt_cls}">Забрав замовлення {badge}</div><div class="tl-time">{t_picked or ''}</div></div>
            </div>
            """
            
        timeline_html += "</div>"
        # === КІНЕЦЬ ЗБІРКИ ТАЙМЛАЙНУ ===

        if j.courier:
            rating_val = j.courier.avg_rating
            rating_cnt = j.courier.rating_count
            rating_display = f"⭐ {rating_val:.1f}" if rating_cnt > 0 else "⭐ New"
            
            courier_info = f"""
            <div style="font-weight:600;">🚴 {j.courier.name}</div>
            <div style="font-size:0.75rem; color:#facc15;">{rating_display} <span style="color:#64748b">({rating_cnt})</span></div>
            """
            
            phone_link = f"tel:{j.courier.phone}"
            comm_btns = f"""
            <a href="{phone_link}" class="btn-mini success" title="Зателефонувати"><i class="fa-solid fa-phone"></i></a>
            <button class="btn-mini info" onclick="openChat({j.id}, 'Кур\\'єр {j.courier.name}')" title="Чат"><i class="fa-solid fa-comments"></i></button>
            """
        else:
            # Якщо кур'єра ще немає, показуємо тільки таймлайн "Створено"
            courier_info = "—"
        
        if j.status == 'assigned':
            status_bg = "rgba(254, 240, 138, 0.2)"
            status_fg = "#fef08a"
            status_text = "Прийнято"
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
        
        elif j.status == 'arrived_pickup':
            status_bg = "rgba(250, 204, 21, 0.2)"
            status_fg = "#facc15"
            status_text = "👋 Чекає"
            
        elif j.status == 'ready':
            status_bg = "rgba(134, 239, 172, 0.2)"
            status_fg = "#86efac"
            status_text = "Готово"
            
        elif j.status == 'picked_up':
            status_bg = "rgba(191, 219, 254, 0.2)"
            status_fg = "#bfdbfe"
            status_text = "В дорозі"
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'
            
        elif j.status == 'returning':
            status_bg = "rgba(251, 146, 60, 0.2)"
            status_fg = "#fb923c"
            status_text = "↩️ Повернення"
            track_btn = f'<button class="btn-mini info" onclick="openTrackModal({j.id})" title="Де кур\'єр?"><i class="fa-solid fa-map-location-dot"></i></button>'

        # --- КНОПКА ДЕЙСТВИЯ (ACTION BTN) ---
        if j.status == 'pending':
            action_btn = f"""
            <button class="btn-mini warn" onclick="boostOrder({j.id})" title="Підняти ціну (+10 грн)">
                <i class="fa-solid fa-fire"></i> +10
            </button>
            """
        elif j.status == 'returning':
            action_btn = f"""
            <button class="btn-mini success" onclick="confirmReturn({j.id})" title="Підтвердити отримання грошей">
                <i class="fa-solid fa-sack-dollar"></i> Гроші
            </button>
            """
        elif j.status in ['assigned', 'arrived_pickup']:
            is_ready = (j.ready_at is not None) or (j.status == 'ready')
            
            # --- НОВАЯ КНОПКА: Подтверждение оплаты выкупа (только если курьер уже прибыл) ---
            if j.payment_type == 'buyout' and not getattr(j, 'is_return_required', False) and j.status == 'arrived_pickup':
                action_btn += f"""
                <button class="btn-mini success" onclick="confirmBuyoutPaid({j.id})" title="Підтвердити оплату від кур'єра">
                    <i class="fa-solid fa-check-double"></i> Оплачено
                </button>
                """

            if not is_ready:
                action_btn += f"""
                <button class="btn-mini success" onclick="markReady({j.id})" title="Повідомити про готовність">
                    <i class="fa-solid fa-utensils"></i> Готово
                </button>
                """
            else:
                action_btn += '<span style="color:#4ade80; font-size:0.8rem; font-weight:bold; margin-right:5px;">🍳 Готово</span>'
        
        payment_badges = {
            "prepaid": "<span style='color:#4ade80'>✅ Оплачено</span>",
            "buyout": "<span style='color:#f472b6'>💰 Викуп</span>",
            "buyout_paid": "<span style='color:#4ade80'>✅ Оплачено</span>"
        }
        pay_info = payment_badges.get(j.payment_type, j.payment_type)
        if getattr(j, 'is_return_required', False):
            pay_info += "<br><span style='color:#f97316; font-size:0.7rem;'>↺ Повернення</span>"

        active_rows += f"""
        <tr id="row-{j.id}">
            <td data-label="ID">#{j.id}</td>
            <td data-label="Створено">
                <div style="font-size:0.85rem"><i class="fa-regular fa-clock"></i> {t_created}</div>
            </td>
            <td data-label="Адреса">{j.dropoff_address}</td>
            <td data-label="Клієнт (Чек)">
                <div style="font-weight:bold;">{j.order_price} грн</div>
                <div style="font-size:0.75rem;">{pay_info}</div>
            </td>
            <td data-label="Кур'єру (Fee)">
                <div style="font-weight:bold; color: #facc15;">{j.delivery_fee} грн</div>
            </td>
            <td data-label="Статус"><span class="status-badge" style="background:{status_bg}; color:{status_fg};">{status_text}</span></td>
            <td class="courier-cell" data-label="Кур'єр">
                {courier_info}
                {timeline_html} </td>
            <td class="actions-cell">
                <div style="display:flex; gap:8px; align-items:center; justify-content: flex-end;">
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
        # ЗАСТОСОВУЄМО ТАЙМЗОНУ ДО ЧАСУ ДОСТАВКИ
        t_deliver = format_local_time(j.delivered_at, tz_string, '%H:%M') if j.delivered_at else "-"
        
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
            <td data-label="ID">#{j.id}</td>
            <td data-label="Таймінг">
                <div style="font-size:0.85rem"><i class="fa-regular fa-clock"></i> {t_deliver}</div>
            </td>
            <td data-label="Клієнт">
                <div style="font-weight:600;">{j.dropoff_address}</div>
                <div style="font-size:0.8rem; color:#888;">{j.customer_name or 'Гість'}</div>
            </td>
            <td data-label="Сума">{j.order_price} грн</td>
            <td data-label="Оцінка">{rating_html}</td>
        </tr>
        """

    pwa_meta = '<link rel="manifest" href="/partner/manifest.json">'
    viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'

    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Кабінет Партнера</title>{GLOBAL_STYLES}{pwa_meta}{viewport_meta}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    {DASHBOARD_CSS}
    </head>
    <body>
        <div id="toast-container"></div>
        
        <div style="width: 100%;">
            <div class="header-bar">
                <div><h2>{partner.name}</h2><span style="color: #94a3b8; font-size:0.9rem;"><i class="fa-solid fa-location-dot"></i> {partner.address}</span></div>
                <a href="/partner/logout" class="btn" style="width:auto; padding: 8px 20px; background: #334155; font-size: 0.9rem;">Вийти</a>
            </div>

            <div class="dashboard-grid">
                <div class="panel">
                    <h3 style="margin-top:0; color:white;"><i class="fa-solid fa-rocket" style="color:var(--primary)"></i> Викликати кур'єра</h3>
                    <form action="/api/partner/create_order" method="post" autocomplete="off" id="orderForm">
                        
                        <label>Оплата та розрахунок</label>
                        <div class="payment-options">
                            <div class="payment-option">
                                <input type="radio" name="payment_type" id="pay_prepaid" value="prepaid" checked onchange="updateFormLogic()">
                                <label for="pay_prepaid">✅ Оплачено</label>
                            </div>
                            <div class="payment-option">
                                <input type="radio" name="payment_type" id="pay_buyout" value="buyout" onchange="updateFormLogic()">
                                <label for="pay_buyout">💰 Викуп</label>
                            </div>
                        </div>

                        <div id="buyout-options" style="display:none; background:rgba(255,255,255,0.05); padding:12px; border-radius:10px; margin-bottom:15px; border:1px solid rgba(255,255,255,0.1);">
                            <div style="color:#f472b6; font-size:0.85rem;">
                                <i class="fa-solid fa-circle-info"></i> <b>Увага:</b> Якщо ви не натиснете кнопку "Оплачено" під час передачі замовлення кур'єру, то після доставки клієнту автоматично увімкнеться логіка повернення грошей — кур'єр буде зобов'язаний повернутися і віддати вам гроші (статус "Повернення").
                            </div>
                        </div>

                        <div class="autocomplete-wrapper">
                            <label>Куди везти (Почніть вводити адресу)</label>
                            <input type="text" id="addr_input" name="dropoff_address" placeholder="Вулиця, номер будинку..." required autocomplete="off">
                            <div id="addr_results" class="autocomplete-results"></div>
                        </div>
                        
                        <div class="map-hint" id="map-hint"><i class="fa-solid fa-hand-pointer"></i> Ви можете уточнити точку на карті (Одеса)</div>
                        <div id="picker-map"></div>
                        
                        <input type="hidden" name="lat" id="form_lat">
                        <input type="hidden" name="lon" id="form_lon">

                        <label>Ім'я клієнта</label>
                        <input type="text" name="customer_name" placeholder="Ім'я" required>

                        <label>Телефон клієнта</label>
                        <input type="tel" name="customer_phone" placeholder="0XX XXX XX XX" required>
                        
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                            <div>
                                <label>Чек (грн)</label>
                                <input type="number" step="0.01" name="order_price" id="order_price" value="0">
                            </div>
                            <div>
                                <label>Доставка (грн)</label>
                                <input type="number" step="0.01" name="delivery_fee" id="delivery_fee" value="80" min="80">
                            </div>
                        </div>
                        
                        <label>Коментар (Під'їзд, поверх, код)</label>
                        <input type="text" name="comment" placeholder="Деталі...">
                        
                        <button type="submit" class="btn">🚀 Знайти кур'єра</button>
                    </form>
                </div>

                <div>
                    <div class="panel">
                        <h3 style="margin-top:0; color:white;"><i class="fa-solid fa-list-ul" style="color:#facc15"></i> Активні доставки</h3>
                        <div style="overflow-x:auto;">
                            <table>
                                <thead><tr><th>ID</th><th>Створено</th><th>Адреса</th><th>Клієнт (Чек)</th><th>Кур'єру (Fee)</th><th>Статус</th><th>Кур'єр</th><th>Дія</th></tr></thead>
                                <tbody>{active_rows}</tbody>
                            </table>
                        </div>
                        {f'<div style="text-align:center; color:#64748b; padding:20px;">Немає активних замовлень</div>' if not active_rows else ''}
                    </div>

                    <div class="panel" style="opacity: 0.9;">
                        <h3 style="margin-top:0; color:white;"><i class="fa-solid fa-clock-rotate-left" style="color:#94a3b8"></i> Історія</h3>
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
                <div style="padding: 15px; background: #0f172a; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <div id="track-info" style="font-weight:bold;">Пошук кур'єра...</div>
                    <button style="background:none; border:none; color:white; font-size:1.5rem; cursor:pointer;" onclick="closeTrackModal()">×</button>
                </div>
                <div id="track-map"></div>
            </div>
        </div>

        <div id="rateModal" class="modal-overlay">
            <div class="modal-card">
                <button style="position:absolute; top:15px; right:15px; background:none; border:none; color:white; font-size:1.5rem;" onclick="document.getElementById('rateModal').style.display='none'">×</button>
                <h2 style="text-align:center; margin-top:0; color:white;">Оцінити кур'єра</h2>
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
                <div style="padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center;">
                    <div id="chat-title" style="font-weight:bold; font-size:1.1rem;">Чат</div>
                    <button style="background:none; border:none; color:white; font-size:1.5rem; cursor:pointer;" onclick="document.getElementById('chatModal').style.display='none'">×</button>
                </div>
                <div id="chat-messages" class="chat-messages"></div>
                <form class="chat-input-area" onsubmit="sendChatMessage(event)" style="display:flex; gap:10px;">
                    <input type="hidden" id="chat_job_id">
                    <input type="text" id="chat_input" placeholder="Написати повідомлення..." autocomplete="off" required style="margin-bottom:0;">
                    <button type="submit" class="btn" style="width:auto; padding:0 20px;"><i class="fa-solid fa-paper-plane"></i></button>
                </form>
            </div>
        </div>

        {DASHBOARD_SCRIPT}
    </body>
    </html>
    """