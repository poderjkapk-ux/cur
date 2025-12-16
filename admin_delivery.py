import json
import os
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

# FIREBASE ADMIN IMPORTS
import firebase_admin
from firebase_admin import credentials, get_app, delete_app

# Импортируем auth вместо app, чтобы избежать циклического импорта
from models import get_db, Courier, DeliveryPartner, SystemSetting
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

# --- HTML TEMPLATE ---
def get_delivery_admin_html(couriers, partners, pwa_config, fb_config_str, vapid_key, service_account_str, message=""):
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

        /* --- STYLES FOR FIREBASE PANEL --- */
        .settings-box {{ background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px; border: 1px solid var(--border); }}
        textarea {{ width: 100%; background: rgba(0,0,0,0.3); color: #fff; font-family: monospace; font-size: 0.85rem; min-height: 100px; border: 1px solid #475569; border-radius: 6px; padding: 8px; box-sizing: border-box; resize: vertical; }}
        .section-label {{ color: var(--primary); font-weight: bold; margin-bottom: 5px; display: block; margin-top: 15px; }}
    </style>
    </head>
    <body>
        <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <h1>🚴 Delivery Control</h1>
                <a href="/admin" class="btn" style="width:auto; padding: 10px 20px;">← Назад в SaaS Admin</a>
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

            <div class="grid" style="margin-top: 20px;">
                <div class="panel">
                    <h2>📱 Налаштування PWA (для встановлення)</h2>
                    <form method="post" action="/admin/delivery/pwa_save" class="pwa-settings">
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

                        <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px; margin-top: 10px;">
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
                        
                        <button type="submit" class="btn" style="margin-top: 15px; width: 100%;">💾 Зберегти налаштування PWA</button>
                    </form>
                </div>

                <div class="panel">
                    <h2>🔥 Firebase Cloud Messaging</h2>
                    <form method="post" action="/admin/delivery/firebase_save">
                        <div class="settings-box">
                            <span class="section-label">1. Client Config (для браузера)</span>
                            <p style="font-size:0.8rem; color:#888; margin-bottom:5px;">Project Settings -> General -> Your apps</p>
                            <textarea name="firebase_config_json" placeholder='{{ "apiKey": "...", ... }}' required>{fb_config_str}</textarea>
                            
                            <span class="section-label">2. VAPID Key (для прав доступу)</span>
                            <p style="font-size:0.8rem; color:#888; margin-bottom:5px;">Cloud Messaging -> Web configuration (Key Pair)</p>
                            <input type="text" name="vapid_key" value="{vapid_key}" required>

                            <span class="section-label">3. Service Account JSON (для сервера)</span>
                            <p style="font-size:0.8rem; color:#888; margin-bottom:5px;">Project Settings -> Service accounts -> Generate new private key. Відкрийте файл і скопіюйте сюди ВЕСЬ вміст.</p>
                            <textarea name="service_account_json" placeholder='{{ "type": "service_account", ... }}' style="min-height:150px;">{service_account_str}</textarea>
                        </div>
                        <button type="submit" class="btn" style="margin-top:15px; width: 100%;">💾 Зберегти і Перезапустити Firebase</button>
                    </form>
                </div>
            </div>
        </div>
    </body></html>
    """

# ОБНОВЛЕНО: Получение настроек из БД и передача в шаблон
@router.get("/admin/delivery", response_class=HTMLResponse)
async def admin_delivery_page(
    message: str = "",
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    couriers = (await db.execute(select(Courier).order_by(Courier.id.desc()))).scalars().all()
    partners = (await db.execute(select(DeliveryPartner).order_by(DeliveryPartner.id.desc()))).scalars().all()
    pwa_config = load_pwa_config()
    
    # Загружаем настройки Firebase из базы
    fb_conf = await db.get(SystemSetting, "firebase_config")
    vapid = await db.get(SystemSetting, "vapid_key")
    sa_conf = await db.get(SystemSetting, "firebase_service_account")
    
    fb_val = fb_conf.value if fb_conf else ""
    vapid_val = vapid.value if vapid else ""
    sa_val = sa_conf.value if sa_conf else ""
    
    return get_delivery_admin_html(couriers, partners, pwa_config, fb_val, vapid_val, sa_val, message)

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

# НОВЫЙ РОУТ: Сохранение настроек Firebase
@router.post("/admin/delivery/firebase_save")
async def save_firebase_settings(
    firebase_config_json: str = Form(...),
    vapid_key: str = Form(...),
    service_account_json: str = Form(""),
    user: str = Depends(check_admin_auth),
    db: AsyncSession = Depends(get_db)
):
    # 1. Сохраняем Client Config
    conf_setting = await db.get(SystemSetting, "firebase_config")
    if not conf_setting:
        conf_setting = SystemSetting(key="firebase_config")
        db.add(conf_setting)
    conf_setting.value = firebase_config_json.strip()

    # 2. Сохраняем VAPID
    vapid_setting = await db.get(SystemSetting, "vapid_key")
    if not vapid_setting:
        vapid_setting = SystemSetting(key="vapid_key")
        db.add(vapid_setting)
    vapid_setting.value = vapid_key.strip()

    # 3. Сохраняем Service Account (Server) и перезагружаем
    msg_extra = ""
    if service_account_json.strip():
        sa_setting = await db.get(SystemSetting, "firebase_service_account")
        if not sa_setting:
            sa_setting = SystemSetting(key="firebase_service_account")
            db.add(sa_setting)
        sa_setting.value = service_account_json.strip()
        
        # --- МГНОВЕННАЯ ПЕРЕЗАГРУЗКА FIREBASE ADMIN ---
        try:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
            
            # Удаляем старое приложение, если есть
            try:
                app = get_app()
                delete_app(app)
            except ValueError:
                pass # Не было инициализировано
            
            firebase_admin.initialize_app(cred)
            msg_extra = " (Server Creds Reloaded!)"
            logging.info("Firebase Admin re-initialized via Admin Panel")
        except Exception as e:
            msg_extra = f" (ERROR Reloading: {e})"
            logging.error(f"Error reloading Firebase: {e}")

    await db.commit()
    return RedirectResponse(f"/admin/delivery?message=Налаштування Firebase оновлено!{msg_extra}", status_code=302)

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