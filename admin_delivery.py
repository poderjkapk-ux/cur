import json
import os
import logging
import httpx
from urllib.parse import quote
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

# Импортируем auth вместо app, чтобы избежать циклического импорта
from models import get_db, Courier, DeliveryPartner, DeliveryJob
from auth import check_admin_auth 

# Импортируем GLOBAL_STYLES
from templates_saas import GLOBAL_STYLES

router = APIRouter()

# --- КОНФІГУРАЦІЯ PWA ---
PWA_CONFIG_FILE = "pwa_config.json"
DEFAULT_PWA_CONFIG = {
    "courier": {
        "name": "Restify Courier",
        "short_name": "Courier",
        "theme_color": "#0f172a",
        "background_color": "#0f172a",
        "display": "standalone",
        "icon_url": "https://cdn-icons-png.flaticon.com/512/7542/7542190.png"
    },
    "partner": {
        "name": "Restify Partner",
        "short_name": "Partner",
        "theme_color": "#1e293b",
        "background_color": "#1e293b",
        "display": "standalone",
        "icon_url": "https://cdn-icons-png.flaticon.com/512/2936/2936886.png"
    }
}

def load_pwa_config():
    if not os.path.exists(PWA_CONFIG_FILE):
        with open(PWA_CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_PWA_CONFIG, f)
        return DEFAULT_PWA_CONFIG
    with open(PWA_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_pwa_config(config):
    with open(PWA_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# --- ГЕОКОДИНГ ДЛЯ КАРТЫ (КЕШИРОВАННЫЙ) ---
GEOCODE_CACHE = {}

async def get_coords(address: str):
    """Шукає координати для адреси закладу, якщо їх немає в БД."""
    if not address: return None, None
    if address in GEOCODE_CACHE: return GEOCODE_CACHE[address]
    
    url = f"https://nominatim.openstreetmap.org/search?q={quote(address)}&format=json&limit=1"
    headers = {"User-Agent": "RestifyAdminMap/1.0"}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=3.0)
            data = resp.json()
            if data and len(data) > 0:
                res = (float(data[0]["lat"]), float(data[0]["lon"]))
                GEOCODE_CACHE[address] = res
                return res
        except Exception as e:
            logging.error(f"Map Geocoding Error for {address}: {e}")
            
    return None, None


# --- HTML ШАБЛОН: Карта Операцій ---
def get_ops_map_html(message=""):
    """HTML для сторінки Real-time Ops Map."""
    
    return f"""
    <!DOCTYPE html><html><head><title>Карта Операцій</title>{GLOBAL_STYLES}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ padding: 0; margin: 0; height: 100vh; overflow: hidden; display: block; background: #0f172a; }}
        #map {{ height: 100vh; width: 100%; z-index: 1; }}
        .map-header {{ 
            position: absolute; top: 0; left: 0; right: 0; 
            padding: 15px 20px; background: rgba(15, 23, 42, 0.9); 
            backdrop-filter: blur(10px); z-index: 1000; color: white;
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            height: 60px;
        }}
        .map-header h1 {{ margin: 0; font-size: 1.5rem; }}
        .map-info {{ font-size: 0.9rem; color: #94a3b8; }}
        .map-info span {{ color: #4ade80; font-weight: bold; margin-right: 15px; }}
        .leaflet-popup-content-wrapper {{ background: #1e293b; color: white; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }}
        .leaflet-popup-tip {{ background: #1e293b; border-top: 1px solid rgba(255,255,255,0.1); }}
        .job-popup h4 {{ margin-top: 0; color: #facc15; }}
        .job-popup p {{ margin: 5px 0; font-size: 0.9rem; }}
        .courier-popup h4 {{ margin-top: 0; color: #6366f1; }}
        .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }}
        
        .legend {{ 
            position: absolute; bottom: 10px; right: 10px; z-index: 1000; 
            background: rgba(30, 41, 59, 0.8); padding: 10px; border-radius: 8px; 
            color: white; font-size: 0.85rem; border: 1px solid rgba(255,255,255,0.1);
        }}
        .legend div {{ margin-bottom: 5px; display: flex; align-items: center; }}
        
        /* Custom Icons */
        .courier-icon {{ 
            background: #6366f1; width: 30px; height: 30px; border-radius: 50%; 
            color: white; text-align: center; line-height: 30px; font-size: 14px; 
            border: 2px solid white; font-weight: bold; box-shadow: 0 0 0 3px #6366f1; 
        }}
        .job-dropoff-icon {{ 
            background: #facc15; width: 20px; height: 20px; border-radius: 50%; 
            border: 2px solid white; box-shadow: 0 0 0 3px #facc15; 
        }}
        .rest-icon {{ 
            background: #94a3b8; width: 25px; height: 25px; border-radius: 50%; 
            border: 2px solid white; box-shadow: 0 0 0 3px #94a3b8; 
            font-size: 12px; color: white; line-height: 21px; text-align: center;
        }}
    </style>
    </head>
    <body>
        <div class="map-header">
            <h1>Карта Операцій <i class="fa-solid fa-map-location-dot"></i></h1>
            <div class="map-info">
                <span id="courier-count">Кур'єрів: 0</span>
                <span id="job-count">Замовлень: 0</span>
                <a href="/admin/delivery" class="btn" style="width:auto; padding: 5px 15px; font-size:0.9rem; margin:0; background: #334155;">← Список</a>
            </div>
        </div>
        <div id="map"></div>
        
        <div class="legend">
            <div><span class="dot" style="background:#6366f1;"></span> Кур'єр на зміні</div>
            <div><span class="dot" style="background:#94a3b8;"></span> Заклад (Pickup)</div>
            <div><span class="dot" style="background:#facc15;"></span> Адреса Доставки (Dropoff)</div>
            <div style="margin-top: 10px; color:#facc15;">Очікує -> Призначено: Жовтий</div>
            <div style="color:#4ade80;">В дорозі -> Повернення: Зелений</div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // --- JS Map Logic ---
            const map = L.map('map', {{ zoomControl: false }}).setView([50.45, 30.52], 12);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);

            let courierLayer = L.layerGroup().addTo(map);
            let jobLayer = L.layerGroup().addTo(map);
            let jobLinesLayer = L.layerGroup().addTo(map);
            let bounds = new L.LatLngBounds();

            const statusColors = {{
                "pending": "#facc15",
                "assigned": "#facc15",
                "arrived_pickup": "#facc15",
                "ready": "#facc15",
                "picked_up": "#4ade80",
                "returning": "#4ade80",
            }};
            
            const jobStatusText = {{
                "pending": "Очікує призначення",
                "assigned": "Кур'єр прийняв",
                "arrived_pickup": "Кур'єр прибув в заклад",
                "ready": "Замовлення готове",
                "picked_up": "В дорозі до клієнта",
                "returning": "Повернення коштів",
            }};
            
            function timeSince(dateString) {{
                if (!dateString) return '-';
                const seconds = Math.floor((new Date() - new Date(dateString)) / 1000);
                if (seconds < 60) return `щойно`;
                const minutes = Math.floor(seconds / 60);
                if (minutes < 60) return `${{minutes}} хв. тому`;
                const hours = Math.floor(minutes / 60);
                if (hours < 24) return `${{hours}} год. тому`;
                return `більше 1 доби тому`;
            }}

            async function fetchMapData() {{
                try {{
                    const res = await fetch('/api/admin/delivery/map_data');
                    const data = await res.json();
                    
                    document.getElementById('courier-count').innerText = `Кур'єрів онлайн: ${{data.couriers.length}}`;
                    document.getElementById('job-count').innerText = `Активних замовлень: ${{data.jobs.length}}`;

                    updateMapMarkers(data.couriers, data.jobs);
                    
                }} catch (e) {{
                    console.error("Error fetching map data:", e);
                }}
            }}

            function updateMapMarkers(couriers, jobs) {{
                courierLayer.clearLayers();
                jobLayer.clearLayers();
                jobLinesLayer.clearLayers();
                bounds = new L.LatLngBounds();

                // 1. Courier Markers
                couriers.forEach(c => {{
                    if (c.lat && c.lon) {{
                        const iconHtml = `<div class="courier-icon" title="${{c.name}}">
                                            <i class="fa-solid fa-motorcycle"></i>
                                         </div>`;
                        const courierIcon = L.divIcon({{ className: 'custom-icon', html: iconHtml, iconSize: [30, 30], iconAnchor: [15, 15] }});
                        
                        let jobStatus = c.job_id ? `Замовлення #${{c.job_id}}` : 'Вільний';
                        
                        const popupContent = `
                            <div class="courier-popup">
                                <h4>🚴 ${{c.name}}</h4>
                                <p><b>Статус:</b> ${{jobStatus}}</p>
                                <p><b>Телефон:</b> ${{c.phone}}</p>
                                <p><b>Рейтинг:</b> ⭐ ${{c.avg_rating}}</p>
                                <p><b>Оновлено:</b> ${{timeSince(c.last_seen)}}</p>
                            </div>
                        `;
                        const marker = L.marker([c.lat, c.lon], {{ icon: courierIcon }}).bindPopup(popupContent);
                        courierLayer.addLayer(marker);
                        bounds.extend([c.lat, c.lon]);
                    }}
                }});

                // 2. Job Markers and Lines
                jobs.forEach(j => {{
                    // A. Restaurant / Pickup Marker
                    if (j.partner.lat && j.partner.lon) {{
                        const restIconHtml = `<div class="rest-icon"><i class="fa-solid fa-shop"></i></div>`;
                        const restIcon = L.divIcon({{ 
                            className: 'custom-icon', 
                            html: restIconHtml, 
                            iconSize: [25, 25], 
                            iconAnchor: [12, 12] 
                        }});
                        
                        const restPopupContent = `
                            <div class="job-popup">
                                <h4>🏪 ${{j.partner.name}} (#${{j.id}})</h4>
                                <p><b>Адреса:</b> ${{j.partner.address}}</p>
                                <p><b>Створено:</b> ${{timeSince(j.created_at)}}</p>
                                <p><b>Статус:</b> <span style="color:${{statusColors[j.status] || '#94a3b8'}}">${{jobStatusText[j.status] || j.status}}</span></p>
                                <p><b>Кур'єр:</b> ${{j.courier.name || 'Очікується'}}</p>
                            </div>
                        `;
                        const restMarker = L.marker([j.partner.lat, j.partner.lon], {{ icon: restIcon }}).bindPopup(restPopupContent);
                        jobLayer.addLayer(restMarker);
                        bounds.extend([j.partner.lat, j.partner.lon]);

                        // B. Dropoff Marker
                        if (j.dropoff.lat && j.dropoff.lon) {{
                            let dropoffColor = statusColors[j.status] || '#94a3b8';
                            let dropoffIconHtml = `<div class="job-dropoff-icon" style="background:${{dropoffColor}}; box-shadow: 0 0 0 3px ${{dropoffColor}};"></div>`;
                            let dropoffIcon = L.divIcon({{ className: 'custom-icon', html: dropoffIconHtml, iconSize: [20, 20], iconAnchor: [10, 10] }});
                            
                            const dropoffPopupContent = `
                                <div class="job-popup">
                                    <h4>📍 ${{j.dropoff.address}} (#${{j.id}})</h4>
                                    <p><b>Клієнт:</b> ${{j.dropoff.customer_phone}}</p>
                                    <p><b>Сума:</b> ${{j.order_price}} грн (+${{j.delivery_fee}} грн)</p>
                                    <p><b>Статус:</b> <span style="color:${{dropoffColor}}">${{jobStatusText[j.status] || j.status}}</span></p>
                                </div>
                            `;
                            const dropoffMarker = L.marker([j.dropoff.lat, j.dropoff.lon], {{ icon: dropoffIcon }}).bindPopup(dropoffPopupContent);
                            jobLayer.addLayer(dropoffMarker);
                            bounds.extend([j.dropoff.lat, j.dropoff.lon]);

                            // C. Draw Line (Pickup to Dropoff)
                            const line = L.polyline([
                                [j.partner.lat, j.partner.lon], 
                                [j.dropoff.lat, j.dropoff.lon]
                            ], {{ color: dropoffColor, weight: 3, dashArray: '8, 8' }});
                            jobLinesLayer.addLayer(line);
                            
                            // D. Draw line from Courier to Pickup/Dropoff
                            const courier = couriers.find(c => c.id === j.courier.id);
                            if (courier && courier.lat && courier.lon) {{
                                let target_lat = j.partner.lat;
                                let target_lon = j.partner.lon;
                                let line_color = '#94a3b8';

                                if (['picked_up', 'returning'].includes(j.status)) {{
                                    target_lat = j.dropoff.lat;
                                    target_lon = j.dropoff.lon;
                                    line_color = '#6366f1'; 
                                }}

                                const courierLine = L.polyline([
                                    [courier.lat, courier.lon], 
                                    [target_lat, target_lon]
                                ], {{ color: line_color, weight: 2 }});
                                jobLinesLayer.addLayer(courierLine);
                            }}
                        }}
                    }}
                }});

                // 3. Auto-fit map
                if (bounds.isValid()) {{
                    map.fitBounds(bounds, {{ padding: [50, 50] }});
                }} else {{
                     map.setView([50.45, 30.52], 12);
                }}
            }}

            fetchMapData();
            setInterval(fetchMapData, 10000); // Оновлення кожні 10 секунд
        </script>
    </body></html>
    """

# --- HTML TEMPLATE: Управління ---
def get_delivery_admin_html(couriers, partners, pwa_config, message=""):
    courier_rows = ""
    for c in couriers:
        status_color = "#4ade80" if c.is_active else "#f87171"
        btn_action = "ban" if c.is_active else "unban"
        btn_icon = "fa-ban" if c.is_active else "fa-check"
        btn_class = "warn" if c.is_active else "success"
        
        courier_rows += f"""
        <tr>
            <td>{c.id}</td>
            <td><b>{c.name}</b><br><small>{c.phone}</small></td>
            <td><span class="dot" style="background:{status_color}"></span> {'Активний' if c.is_active else 'Заблокований'}</td>
            <td>{c.last_seen.strftime('%d.%m %H:%M') if c.last_seen else '-'}</td>
            <td style="display:flex; gap:5px;">
                <form action="/admin/delivery/courier/control" method="post" style="margin:0;">
                    <input type="hidden" name="id" value="{c.id}">
                    <input type="hidden" name="action" value="{btn_action}">
                    <button class="btn-mini {btn_class}"><i class="fa-solid {btn_icon}"></i></button>
                </form>
                <form action="/admin/delivery/courier/control" method="post" style="margin:0;" onsubmit="return confirm('Видалити кур\'єра назавжди?');">
                    <input type="hidden" name="id" value="{c.id}">
                    <input type="hidden" name="action" value="delete">
                    <button class="btn-mini danger"><i class="fa-solid fa-trash"></i></button>
                </form>
            </td>
        </tr>"""

    partner_rows = ""
    for p in partners:
        is_active = getattr(p, 'is_active', True)
        status_color = "#4ade80" if is_active else "#f87171"
        btn_action = "ban" if is_active else "unban"
        btn_icon = "fa-ban" if is_active else "fa-check"
        btn_class = "warn" if is_active else "success"

        partner_rows += f"""
        <tr>
            <td>{p.id}</td>
            <td><b>{p.name}</b><br><small>{p.address}</small></td>
            <td>{p.email}<br><small>{p.phone}</small></td>
            <td><span class="dot" style="background:{status_color}"></span></td>
            <td style="display:flex; gap:5px;">
                <form action="/admin/delivery/partner/control" method="post" style="margin:0;">
                    <input type="hidden" name="id" value="{p.id}">
                    <input type="hidden" name="action" value="{btn_action}">
                    <button class="btn-mini {btn_class}"><i class="fa-solid {btn_icon}"></i></button>
                </form>
                <form action="/admin/delivery/partner/control" method="post" style="margin:0;" onsubmit="return confirm('Видалити заклад назавжди?');">
                    <input type="hidden" name="id" value="{p.id}">
                    <input type="hidden" name="action" value="delete">
                    <button class="btn-mini danger"><i class="fa-solid fa-trash"></i></button>
                </form>
            </td>
        </tr>"""

    return f"""
    <!DOCTYPE html><html><head><title>Delivery Admin</title>{GLOBAL_STYLES}
    <style>
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        @media(max-width:900px){{ .grid {{ grid-template-columns: 1fr; }} }}
        .panel {{ background: #1e293b; padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        td, th {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; vertical-align: middle; }}
        .btn-mini {{ padding: 5px 10px; border-radius: 6px; border: none; cursor: pointer; color: white; }}
        .btn-mini.danger {{ background: #e11d48; }}
        .btn-mini.warn {{ background: #f59e0b; }}
        .btn-mini.success {{ background: #4ade80; color: #064e3b; }}
        .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }}
        h2 {{ margin-top: 0; display: flex; align-items: center; gap: 10px; }}
        
        .pwa-settings input {{ background: rgba(0,0,0,0.2); padding: 8px; border: 1px solid #475569; border-radius: 6px; color: white; width: 100%; margin-bottom: 10px; }}
        .pwa-settings label {{ font-size: 0.8rem; color: #94a3b8; margin-bottom: 2px; display: block; }}
    </style>
    </head>
    <body>
        <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h1>🚴 Delivery Control</h1>
                <div>
                    <a href="/admin/delivery/map" class="btn" style="width:auto; padding: 10px 20px; margin-right: 10px; background: #6366f1;">Реалтайм Карта</a>
                    <a href="/admin" class="btn" style="width:auto; padding: 10px 20px;">← Назад в SaaS Admin</a>
                </div>
            </div>
            
            {f'<div class="message success">{message}</div>' if message else ''}

            <div class="grid">
                <div class="panel">
                    <h2>🚴 Кур'єри ({len(couriers)})</h2>
                    <div style="max-height: 400px; overflow-y: auto;">
                        <table>
                            <thead><tr><th>ID</th><th>Інфо</th><th>Статус</th><th>Online</th><th>Дії</th></tr></thead>
                            <tbody>{courier_rows}</tbody>
                        </table>
                    </div>
                </div>

                <div class="panel">
                    <h2>🏪 Партнери / Заклади ({len(partners)})</h2>
                    <div style="max-height: 400px; overflow-y: auto;">
                        <table>
                            <thead><tr><th>ID</th><th>Заклад</th><th>Контакти</th><th>Статус</th><th>Дії</th></tr></thead>
                            <tbody>{partner_rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="panel" style="margin-top: 20px;">
                <h2>📱 Налаштування PWA (для встановлення додатків)</h2>
                <form method="post" action="/admin/delivery/pwa_save" class="pwa-settings grid">
                    <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px;">
                        <h3 style="margin-top:0">Courier App</h3>
                        <label>Назва додатка</label>
                        <input type="text" name="c_name" value="{pwa_config['courier']['name']}">
                        <label>Коротка назва (під іконкою)</label>
                        <input type="text" name="c_short_name" value="{pwa_config['courier']['short_name']}">
                        <label>URL іконки (PNG, 512x512)</label>
                        <input type="text" name="c_icon" value="{pwa_config['courier']['icon_url']}">
                        <label>Колір теми (HEX)</label>
                        <input type="color" name="c_color" value="{pwa_config['courier']['theme_color']}" style="height:40px;">
                    </div>

                    <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px;">
                        <h3 style="margin-top:0">Partner App</h3>
                        <label>Назва додатка</label>
                        <input type="text" name="p_name" value="{pwa_config['partner']['name']}">
                        <label>Коротка назва</label>
                        <input type="text" name="p_short_name" value="{pwa_config['partner']['short_name']}">
                        <label>URL іконки</label>
                        <input type="text" name="p_icon" value="{pwa_config['partner']['icon_url']}">
                        <label>Колір теми</label>
                        <input type="color" name="p_color" value="{pwa_config['partner']['theme_color']}" style="height:40px;">
                    </div>
                    
                    <button type="submit" class="btn" style="grid-column: 1 / -1; margin-top: 15px;">💾 Зберегти налаштування PWA</button>
                </form>
            </div>
            
        </div>
    </body></html>
    """

# --- РОУТИ ПАНЕЛІ ---

@router.get("/admin/delivery", response_class=HTMLResponse)
async def admin_delivery_page(
    message: str = "",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    couriers = (await db.execute(select(Courier).order_by(Courier.id.desc()))).scalars().all()
    partners = (await db.execute(select(DeliveryPartner).order_by(DeliveryPartner.id.desc()))).scalars().all()
    pwa_config = load_pwa_config()
    
    return get_delivery_admin_html(couriers, partners, pwa_config, message)

@router.get("/admin/delivery/map", response_class=HTMLResponse)
async def admin_delivery_map_page(
    user: str = Depends(check_admin_auth)
):
    return get_ops_map_html() 

# --- НОВИЙ АПІ ЕНДПОІНТ ДЛЯ ОТРИМАННЯ ДАНИХ ДЛЯ КАРТИ ---
@router.get("/api/admin/delivery/map_data")
async def get_map_data(user: str = Depends(check_admin_auth), db: AsyncSession = Depends(get_db)):
    
    # 1. Отримуємо онлайн кур'єрів
    couriers = (await db.execute(select(Courier).where(Courier.is_online == True))).scalars().all()
    courier_list = []
    
    for c in couriers:
        # Перевіряємо чи є у кур'єра активне замовлення
        active_job = (await db.execute(
            select(DeliveryJob.id)
            .where(DeliveryJob.courier_id == c.id)
            .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
        )).scalar()
        
        courier_list.append({
            "id": c.id, 
            "name": c.name, 
            "phone": c.phone,
            "lat": c.lat, 
            "lon": c.lon,
            "avg_rating": getattr(c, 'avg_rating', 5.0),
            "last_seen": c.last_seen.isoformat() if c.last_seen else None,
            "job_id": active_job
        })
        
    # 2. Отримуємо активні замовлення та їхні координати
    jobs_query = await db.execute(
        select(DeliveryJob)
        .options(joinedload(DeliveryJob.partner))
        .options(joinedload(DeliveryJob.courier))
        .where(DeliveryJob.status.notin_(["delivered", "cancelled"]))
    )
    jobs = jobs_query.scalars().all()
    
    jobs_list = []
    for j in jobs:
        p_lat, p_lon = None, None
        if j.partner:
            # Кешований геокодинг адреси закладу
            p_lat, p_lon = await get_coords(j.partner.address)
            
        jobs_list.append({
            "id": j.id,
            "status": j.status,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "order_price": j.order_price,
            "delivery_fee": j.delivery_fee,
            "partner": {
                "id": j.partner.id if j.partner else None,
                "name": j.partner.name if j.partner else "Невідомо",
                "address": j.partner.address if j.partner else "",
                "lat": p_lat,
                "lon": p_lon
            },
            "dropoff": {
                "address": j.dropoff_address,
                "lat": j.dropoff_lat,
                "lon": j.dropoff_lon,
                "customer_phone": j.customer_phone
            },
            "courier": {
                "id": j.courier.id if j.courier else None,
                "name": j.courier.name if j.courier else None
            }
        })
        
    return JSONResponse({"couriers": courier_list, "jobs": jobs_list})

# --- УПРАВЛІННЯ КУР'ЄРАМИ ТА ПАРТНЕРАМИ ---
@router.post("/admin/delivery/courier/control")
async def courier_control(
    id: int = Form(...),
    action: str = Form(...),
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    courier = await db.get(Courier, id)
    if not courier:
        return RedirectResponse("/admin/delivery?message=Кур'єра не знайдено", status_code=302)
    
    if action == "ban":
        courier.is_active = False
        msg = f"Кур'єр {courier.name} заблокований."
    elif action == "unban":
        courier.is_active = True
        msg = f"Кур'єр {courier.name} розблокований."
    elif action == "delete":
        await db.delete(courier)
        msg = "Кур'єр видалений."
    
    await db.commit()
    return RedirectResponse(f"/admin/delivery?message={msg}", status_code=302)

@router.post("/admin/delivery/partner/control")
async def partner_control(
    id: int = Form(...),
    action: str = Form(...),
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    partner = await db.get(DeliveryPartner, id)
    if not partner:
        return RedirectResponse("/admin/delivery?message=Партнера не знайдено", status_code=302)
    
    if not hasattr(partner, 'is_active'):
        return RedirectResponse("/admin/delivery?message=ПОМИЛКА: Оновіть models.py", status_code=302)

    if action == "ban":
        partner.is_active = False
        msg = f"Партнер {partner.name} заблокований."
    elif action == "unban":
        partner.is_active = True
        msg = f"Партнер {partner.name} розблокований."
    elif action == "delete":
        await db.delete(partner)
        msg = "Партнер видалений."
    
    await db.commit()
    return RedirectResponse(f"/admin/delivery?message={msg}", status_code=302)

# --- НАЛАШТУВАННЯ PWA ТА МАНІФЕСТИ ---
@router.post("/admin/delivery/pwa_save")
async def pwa_save_settings(
    c_name: str = Form(...), c_short_name: str = Form(...), c_icon: str = Form(...), c_color: str = Form(...),
    p_name: str = Form(...), p_short_name: str = Form(...), p_icon: str = Form(...), p_color: str = Form(...),
    user: str = Depends(check_admin_auth)
):
    config = {
        "courier": {
            "name": c_name, "short_name": c_short_name, "icon_url": c_icon, 
            "theme_color": c_color, "background_color": c_color, "display": "standalone"
        },
        "partner": {
            "name": p_name, "short_name": p_short_name, "icon_url": p_icon, 
            "theme_color": p_color, "background_color": p_color, "display": "standalone"
        }
    }
    save_pwa_config(config)
    return RedirectResponse("/admin/delivery?message=Налаштування PWA збережено", status_code=302)


@router.get("/courier/manifest.json")
async def get_courier_manifest():
    conf = load_pwa_config()["courier"]
    return JSONResponse({
        "name": conf["name"],
        "short_name": conf["short_name"],
        "start_url": "/courier/app", 
        "display": conf["display"],
        "background_color": conf["background_color"],
        "theme_color": conf["theme_color"],
        "icons": [{"src": conf["icon_url"], "sizes": "512x512", "type": "image/png"}]
    })

@router.get("/partner/manifest.json")
async def get_partner_manifest():
    conf = load_pwa_config()["partner"]
    return JSONResponse({
        "name": conf["name"],
        "short_name": conf["short_name"],
        "start_url": "/partner/login",
        "display": conf["display"],
        "background_color": conf["background_color"],
        "theme_color": conf["theme_color"],
        "icons": [{"src": conf["icon_url"], "sizes": "512x512", "type": "image/png"}]
    })