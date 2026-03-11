import os
from typing import List, Dict

# Імпорт моделей для типізації (з заглушкою на випадок циклічних імпортів)
try:
    from models import User, Instance
except ImportError:
    class User: pass
    class Instance: pass

# --- 1. Глобальні стилі ---
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
    input, textarea, select { 
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
    select {
        appearance: none;
        background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%2394a3b8%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
        background-repeat: no-repeat;
        background-position: right 14px top 50%;
        background-size: 12px auto;
    }
    select option {
        background: var(--bg-card);
        color: var(--text-main);
    }
    textarea {
        min-height: 150px;
        line-height: 1.6;
    }
    input:focus, textarea:focus, select:focus {
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

# --- 2. Сторінки Авторизації ---

def get_login_page(message: str = "", msg_type: str = "error"):
    """HTML для сторінки входу /login"""
    return f"""
    <!DOCTYPE html><html lang="uk"><head><title>Вхід</title>{GLOBAL_STYLES}</head>
    <body><div class="container">
        <img src="/static/logo.png" alt="Restify Logo" class="logo-img">
        <h1>Вхід у систему</h1>
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
                
            }} catch(e) {{ console.error("Error init verification", e); }}
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
                }} catch(e) {{ console.error("Polling error", e); }}
            }}, 2000);
        }}

        function showSuccess(phone) {{
            document.getElementById('tg-waiting').classList.add('hidden');
            document.getElementById('tg-success').classList.remove('hidden');
            
            const box = document.querySelector('.tg-verify-box');
            box.classList.add('verified');
            
            document.getElementById('user-phone').innerText = phone;
            document.getElementById('submitBtn').disabled = false;
        }}

        initVerification();

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

# --- 3. Шаблон Дашборда ---

def get_dashboard_html(user: User, instances: List[Instance]):
    """HTML для Особистого Кабінету (/dashboard)"""
    
    project_cards_html = ""
    if not instances:
        project_cards_html = "<p style='text-align: center; color: var(--text-muted);'>У вас поки немає проектів. Створіть свій перший проект, використовуючи форму вище.</p>"
    else:
        for instance in sorted(instances, key=lambda x: x.created_at, reverse=True):
            status_color = "var(--status-active)" if instance.status == "active" else "var(--status-suspended)"
            
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
            .token-fields {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            @media (min-width: 600px) {{
                .token-fields {{ grid-template-columns: 1fr 1fr; }}
            }}

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

        async function deleteInstance(instanceId, subdomain) {{
            const message = `Ви впевнені, що хочете ПОВНІСТЮ видалити проект '${{subdomain}}'?\\n\\nЦя дія незворотна. Контейнер та база даних будуть видалені.`
            if (!confirm(message)) return;

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

# --- 4. Шаблони Адмін-панелі (ДЛЯ SUPER ADMIN) ---

def get_admin_dashboard_html(clients: list, message: str = "", msg_type: str = "success"):
    """HTML для Адмінки (/admin)"""
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
    """HTML для сторінки налаштувань (/settings)"""
    import os
    
    custom_btn_text = str(config.get('custom_btn_text', '')).replace('"', '&quot;')
    custom_btn_content = str(config.get('custom_btn_content', '')).replace('<', '&lt;').replace('>', '&gt;')
    
    fb_json_content = ""
    if os.path.exists("firebase_credentials.json"):
        try:
            with open("firebase_credentials.json", "r", encoding="utf-8") as f:
                fb_json_content = f.read()
        except: pass
        
    current_tz = config.get('timezone', 'Europe/Kiev')
    timezones = [
        "Europe/Kiev", "Europe/Warsaw", "Europe/London", "Europe/Berlin", 
        "Europe/Paris", "America/New_York", "UTC"
    ]
    tz_options = "".join([f'<option value="{tz}" {"selected" if tz == current_tz else ""}>{tz}</option>' for tz in timezones])
    
    return f"""
    <!DOCTYPE html><html><head><title>Restify Admin</title>{GLOBAL_STYLES}</head>
    <style>
        .container {{ max-width: 600px; text-align: left; margin: 40px auto; }}
        label {{ color: var(--text-muted); display: block; margin-bottom: 5px; font-size: 0.9rem; margin-top: 15px; font-weight: bold; }}
        h2 {{ border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 30px; }}
    </style>
    <body>
        <div class="container">
            <h1 style="text-align:center;">Налаштування Вітрини</h1>
            {f'<div class="message success" style="text-align:center">{message}</div>' if message else ''}
            <form method="post" action="/settings">
                <h2>Базові налаштування</h2>
                <label>Символ валюти</label><input type="text" name="currency" value="{config.get('currency', '$')}">
                
                <input type="hidden" name="price_light" value="{config.get('price_light', '300')}">
                <label>Ціна (Pro) / місяць</label><input type="number" name="price_full" value="{config.get('price_full', '600')}">
                
                <label>Admin Telegram ID (для заявок)</label><input type="text" name="admin_id" value="{config.get('admin_id', '')}">
                <label>Bot Token (для заявок)</label><input type="text" name="bot_token" value="{config.get('bot_token', '')}">
                
                <label>Часовий пояс (Timezone)</label>
                <select name="timezone">
                    {tz_options}
                </select>
                <p class="form-hint" style="margin-top: 5px;">Впливає на відображення часу в панелях партнерів та кур'єрів.</p>
                
                <h2>Push-сповіщення (Firebase)</h2>
                <label>Firebase API Key</label>
                <input type="text" name="firebase_api_key" value="{config.get('firebase_api_key', '')}" placeholder="AIzaSy...">
                
                <label>Firebase Project ID</label>
                <input type="text" name="firebase_project_id" value="{config.get('firebase_project_id', '')}" placeholder="restifysite">
                
                <label>Firebase Sender ID (messagingSenderId)</label>
                <input type="text" name="firebase_sender_id" value="{config.get('firebase_sender_id', '')}" placeholder="1234567890">
                
                <label>Firebase App ID</label>
                <input type="text" name="firebase_app_id" value="{config.get('firebase_app_id', '')}" placeholder="1:1234567890:web:abcd...">
                
                <label>VAPID Key (Web Push certificate)</label>
                <input type="text" name="firebase_vapid_key" value="{config.get('firebase_vapid_key', '')}" placeholder="BP5-1Obs3...">
                
                <label>Вміст файлу firebase_credentials.json (Серверний ключ)</label>
                <p class="form-hint" style="margin-top: 5px;">Вставте сюди весь текст із завантаженого JSON файлу Service Account.</p>
                <textarea name="firebase_credentials_json" style="font-family: monospace; font-size: 0.8rem; height: 200px;" placeholder='{{ "type": "service_account", ... }}'>{fb_json_content}</textarea>

                <h2>Додаткова кнопка в меню</h2>
                <label>Текст кнопки</label>
                <input type="text" name="custom_btn_text" value="{custom_btn_text}" placeholder="Напр: Політика">
                <p class="form-hint" style="margin-top: 5px;">Залиште порожнім, щоб приховати кнопку.</p>
                
                <label>Вміст вікна (HTML)</label>
                <textarea name="custom_btn_content" placeholder="<p>Ваш текст...</p>">{custom_btn_content}</textarea>
                
                <button type="submit" class="btn" style="margin-top: 20px;">Зберегти налаштування</button>
            </form>
            <a href="/admin" style="text-align:center;">← Назад до Клієнтів</a>
        </div>
    </body></html>
    """

# --- 5. ПРОФЕСІЙНА ГОЛОВНА СТОРІНКА (Тільки Кур'єри та Ресторани) ---

def get_landing_page_html(config: Dict[str, str]):
    """
    ПРОФЕСІЙНА ГОЛОВНА СТОРІНКА (SEO, MOBILE-FIRST, PREMIUM UI, БЕЗ ТОЧНИХ ЦИФР)
    """
    
    custom_button_html = ""
    mobile_custom_button_html = ""
    if config.get("custom_btn_text"):
        button_text = str(config["custom_btn_text"]).replace('<', '&lt;').replace('>', '&gt;')
        custom_button_html = f'<a href="#" class="nav-link custom-modal-btn">{button_text}</a>'
        mobile_custom_button_html = f'<a href="#" class="mobile-nav-link custom-modal-btn">{button_text}</a>'
        
    modal_content_html = str(config.get("custom_btn_content", ""))

    return f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    
    <title>Restify Delivery | Інноваційна платформа для ресторанів та кур'єрів</title>
    <meta name="description" content="Restify Delivery - надійна логістична B2B платформа. Швидкий пошук верифікованих кур'єрів для ресторанів та вигідна робота з гнучким графіком для кур'єрів. Без абонплат!">
    <meta name="keywords" content="доставка їжі, кур'єри, для ресторанів, логістика, B2B доставка, Restify, робота кур'єром, виклик кур'єра, кур'єрська служба">
    <meta name="author" content="Restify">
    
    <meta property="og:type" content="website">
    <meta property="og:title" content="Restify Delivery | Платформа для ресторанів та кур'єрів">
    <meta property="og:description" content="Прозора та надійна система доставки без абонплати за софт. Викликайте кур'єрів в один клік!">
    <meta property="og:url" content="https://restify.site/">
    <meta property="og:image" content="/static/og-image.jpg">
    
    <link rel="icon" href="/static/favicon.ico" type="image/x-icon">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">

    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {{ 
            --bg: #07090e; 
            --bg-card: rgba(22, 31, 51, 0.4);
            --bg-glass: rgba(15, 20, 35, 0.7);
            --text: #f8fafc; 
            --text-muted: #94a3b8;
            --primary: #6366f1; 
            --primary-hover: #4f46e5;
            --accent: #facc15; 
            --accent-hover: #eab308;
            --border: rgba(255, 255, 255, 0.08);
            --font: 'Manrope', sans-serif;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ scroll-behavior: smooth; }}
        body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; overflow-x: hidden; -webkit-font-smoothing: antialiased; }}
        a {{ text-decoration: none; color: inherit; transition: 0.3s ease; }}
        ul {{ list-style: none; }}
        
        .container {{ max-width: 1240px; margin: 0 auto; padding: 0 24px; }}
        
        /* --- ANIMATIONS --- */
        @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes float {{ 0% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-15px); }} 100% {{ transform: translateY(0px); }} }}
        @keyframes pulseGlow {{ 0% {{ box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }} 70% {{ box-shadow: 0 0 0 20px rgba(99, 102, 241, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }} }}

        .animate-up {{ animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; }}
        .delay-1 {{ animation-delay: 0.1s; }}
        .delay-2 {{ animation-delay: 0.2s; }}
        .delay-3 {{ animation-delay: 0.3s; }}

        /* --- NAVBAR --- */
        .navbar {{ position: fixed; top: 0; left: 0; width: 100%; padding: 18px 0; background: rgba(7, 9, 14, 0.7); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-bottom: 1px solid var(--border); z-index: 1000; transition: 0.3s; }}
        .nav-inner {{ display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-weight: 800; font-size: 1.6rem; display: flex; align-items: center; gap: 10px; color: white; letter-spacing: -0.5px; }}
        .logo i {{ color: var(--accent); font-size: 1.8rem; }}
        
        .nav-links {{ display: flex; gap: 32px; align-items: center; }}
        .nav-link {{ font-weight: 600; color: var(--text-muted); font-size: 0.95rem; transition: 0.3s; }}
        .nav-link:hover {{ color: white; text-shadow: 0 0 15px rgba(255,255,255,0.4); }}
        
        .auth-btns {{ display: flex; gap: 12px; align-items: center; }}
        .btn {{ padding: 14px 28px; border-radius: 14px; font-weight: 700; font-size: 0.95rem; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 10px; border: none; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-align: center; }}
        .btn-outline {{ border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.03); color: white; backdrop-filter: blur(10px); }}
        .btn-outline:hover {{ border-color: var(--primary); background: rgba(99, 102, 241, 0.1); transform: translateY(-2px); }}
        .btn-primary {{ background: var(--primary); color: white; box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4); }}
        .btn-primary:hover {{ background: var(--primary-hover); transform: translateY(-3px); box-shadow: 0 12px 30px rgba(99, 102, 241, 0.6); }}
        .btn-accent {{ background: var(--accent); color: #0f172a; box-shadow: 0 8px 25px rgba(250, 204, 21, 0.3); }}
        .btn-accent:hover {{ background: var(--accent-hover); transform: translateY(-3px); box-shadow: 0 12px 30px rgba(250, 204, 21, 0.5); }}

        /* --- MOBILE MENU --- */
        .mobile-menu-btn {{ display: none; color: white; font-size: 1.8rem; background: none; border: none; cursor: pointer; z-index: 1001; transition: 0.3s; }}
        .mobile-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100vh; background: rgba(7, 9, 14, 0.98); z-index: 999; display: flex; flex-direction: column; justify-content: center; align-items: center; opacity: 0; pointer-events: none; transition: 0.4s ease; backdrop-filter: blur(15px); }}
        .mobile-overlay.active {{ opacity: 1; pointer-events: all; }}
        .mobile-nav-links {{ display: flex; flex-direction: column; gap: 25px; text-align: center; margin-bottom: 40px; }}
        .mobile-nav-link {{ font-size: 1.5rem; font-weight: 700; color: white; }}
        .mobile-auth-btns {{ display: flex; flex-direction: column; gap: 15px; width: 80%; max-width: 300px; }}

        /* --- HERO SECTION --- */
        .hero {{ padding: 200px 0 140px; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
        .hero-bg-glow1 {{ position: absolute; top: 10%; left: 10%; width: 50vw; height: 50vw; background: var(--primary); filter: blur(150px); opacity: 0.15; border-radius: 50%; z-index: -1; animation: float 10s infinite alternate; }}
        .hero-bg-glow2 {{ position: absolute; bottom: 10%; right: 10%; width: 40vw; height: 40vw; background: var(--accent); filter: blur(150px); opacity: 0.1; border-radius: 50%; z-index: -1; animation: float 12s infinite alternate-reverse; }}
        
        .hero-content {{ text-align: center; max-width: 900px; margin: 0 auto; position: relative; z-index: 2; }}
        .hero-badge {{ display: inline-flex; align-items: center; gap: 8px; background: rgba(250, 204, 21, 0.1); border: 1px solid rgba(250, 204, 21, 0.2); color: var(--accent); padding: 8px 20px; border-radius: 30px; font-size: 0.9rem; font-weight: 700; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 1px; backdrop-filter: blur(5px); }}
        .hero-badge i {{ font-size: 1.1rem; }}
        .hero h1 {{ font-size: clamp(2.5rem, 6vw, 5rem); font-weight: 800; line-height: 1.1; margin-bottom: 25px; color: white; letter-spacing: -1px; }}
        .hero h1 span {{ background: linear-gradient(135deg, #fff, var(--text-muted)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .hero p {{ font-size: clamp(1.1rem, 2vw, 1.3rem); color: var(--text-muted); margin-bottom: 50px; font-weight: 400; max-width: 750px; margin-inline: auto; }}
        
        .hero-actions {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }}
        
        /* --- STATS BAR --- */
        .stats-wrapper {{ margin-top: -80px; position: relative; z-index: 10; padding: 0 20px; }}
        .stats-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; background: var(--bg-glass); backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px); border: 1px solid var(--border); padding: 40px; border-radius: 30px; box-shadow: 0 25px 50px rgba(0,0,0,0.4); }}
        .stat-item {{ text-align: center; border-right: 1px solid var(--border); display: flex; flex-direction: column; align-items: center; justify-content: center; }}
        .stat-item:last-child {{ border-right: none; }}
        .stat-icon {{ font-size: 2.2rem; color: var(--accent); margin-bottom: 15px; animation: float 6s infinite ease-in-out; }}
        .stat-val {{ font-size: 1.6rem; font-weight: 800; color: white; margin-bottom: 5px; line-height: 1.2; }}
        .stat-label {{ color: var(--text-muted); font-size: 0.95rem; font-weight: 500; }}

        /* --- SPLIT SECTION (RESTAURANTS & COURIERS) --- */
        .section {{ padding: 140px 0; }}
        .section-header {{ text-align: center; margin-bottom: 70px; }}
        .section-header h2 {{ font-size: clamp(2rem, 4vw, 3rem); color: white; margin-bottom: 20px; font-weight: 800; letter-spacing: -0.5px; }}
        .section-header p {{ color: var(--text-muted); font-size: 1.2rem; max-width: 600px; margin: 0 auto; }}
        
        .split-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
        
        .service-card {{ background: linear-gradient(160deg, var(--bg-card) 0%, rgba(10, 15, 25, 0.8) 100%); border: 1px solid var(--border); border-radius: 32px; padding: 50px; position: relative; overflow: hidden; transition: all 0.4s ease; backdrop-filter: blur(10px); }}
        .service-card:hover {{ transform: translateY(-10px); border-color: rgba(99, 102, 241, 0.3); box-shadow: 0 30px 60px rgba(0,0,0,0.5); }}
        .sc-courier:hover {{ border-color: rgba(250, 204, 21, 0.3); }}
        
        .sc-icon-wrapper {{ width: 90px; height: 90px; border-radius: 28px; display: flex; align-items: center; justify-content: center; font-size: 2.8rem; margin-bottom: 35px; transition: 0.4s; position: relative; }}
        .sc-partner .sc-icon-wrapper {{ background: rgba(99, 102, 241, 0.1); color: var(--primary); border: 1px solid rgba(99, 102, 241, 0.2); box-shadow: 0 10px 30px rgba(99, 102, 241, 0.2); }}
        .sc-courier .sc-icon-wrapper {{ background: rgba(250, 204, 21, 0.1); color: var(--accent); border: 1px solid rgba(250, 204, 21, 0.2); box-shadow: 0 10px 30px rgba(250, 204, 21, 0.2); }}
        
        .service-card h3 {{ font-size: 2.2rem; color: white; margin-bottom: 25px; font-weight: 800; }}
        .service-card > p {{ color: var(--text-muted); font-size: 1.15rem; margin-bottom: 40px; line-height: 1.7; }}
        
        .feature-list {{ display: grid; gap: 20px; }}
        .feature-list li {{ display: flex; align-items: flex-start; gap: 18px; font-size: 1.05rem; color: #e2e8f0; line-height: 1.6; }}
        .feature-list i {{ font-size: 1.4rem; margin-top: 4px; }}
        .sc-partner .feature-list i {{ color: var(--primary); text-shadow: 0 0 10px rgba(99, 102, 241, 0.5); }}
        .sc-courier .feature-list i {{ color: var(--accent); text-shadow: 0 0 10px rgba(250, 204, 21, 0.5); }}
        .feature-list b {{ color: white; font-weight: 700; }}
        
        .service-actions {{ margin-top: 50px; display: flex; gap: 16px; flex-wrap: wrap; }}

        /* --- HOW IT WORKS --- */
        .process-section {{ background: linear-gradient(to bottom, transparent, rgba(22, 31, 51, 0.3), transparent); padding: 120px 0; border-top: 1px solid rgba(255,255,255,0.03); border-bottom: 1px solid rgba(255,255,255,0.03); }}
        .process-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px; position: relative; margin-top: 60px; }}
        .process-step {{ text-align: center; position: relative; z-index: 2; padding: 20px; }}
        .step-icon {{ width: 100px; height: 100px; background: var(--bg-glass); border: 2px solid var(--border); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; color: white; margin: 0 auto 30px; transition: 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); box-shadow: 0 15px 35px rgba(0,0,0,0.3); backdrop-filter: blur(10px); }}
        .process-step:hover .step-icon {{ background: var(--primary); border-color: var(--primary); transform: scale(1.1) translateY(-10px); box-shadow: 0 20px 40px rgba(99, 102, 241, 0.4); color: white; }}
        .process-step h4 {{ font-size: 1.35rem; color: white; margin-bottom: 15px; font-weight: 800; }}
        .process-step p {{ color: var(--text-muted); font-size: 1rem; line-height: 1.6; }}
        
        .process-grid::before {{ content: ''; position: absolute; top: 70px; left: 12%; right: 12%; height: 2px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1) 20%, rgba(255,255,255,0.1) 80%, transparent); z-index: 1; }}

        /* --- FOOTER --- */
        footer {{ background: #050609; padding: 80px 0 40px; text-align: center; position: relative; }}
        .footer-logo {{ font-size: 2rem; font-weight: 800; color: white; display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 25px; }}
        .footer-logo i {{ color: var(--accent); }}
        .footer-links {{ display: flex; justify-content: center; gap: 35px; margin-bottom: 40px; flex-wrap: wrap; }}
        .footer-links a {{ color: var(--text-muted); font-weight: 600; font-size: 1rem; transition: 0.3s; }}
        .footer-links a:hover {{ color: white; transform: translateY(-2px); }}
        .footer-bottom {{ border-top: 1px solid rgba(255,255,255,0.05); padding-top: 30px; color: #475569; font-size: 0.95rem; font-weight: 500; display: flex; flex-direction: column; align-items: center; gap: 10px; }}

        /* --- MODAL --- */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 2000; justify-content: center; align-items: center; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); padding: 20px; }}
        .modal-overlay.visible {{ display: flex; animation: fadeIn 0.3s ease; }}
        .modal-content {{ background: rgba(15, 20, 35, 0.95); padding: 50px 40px; border-radius: 30px; max-width: 650px; width: 100%; color: #fff; position: relative; border: 1px solid var(--border); box-shadow: 0 30px 60px rgba(0,0,0,0.6); animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); max-height: 90vh; overflow-y: auto; }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; cursor: pointer; font-size: 1.5rem; color: var(--text-muted); transition: 0.3s; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: rgba(255,255,255,0.05); }}
        .close-btn:hover {{ color: white; background: rgba(225, 29, 72, 0.8); transform: rotate(90deg); }}

        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        @keyframes slideUp {{ from {{ transform: translateY(50px) scale(0.95); opacity: 0; }} to {{ transform: translateY(0) scale(1); opacity: 1; }} }}

        /* --- RESPONSIVE / MOBILE OPTIMIZATION --- */
        @media (max-width: 1024px) {{
            .stats-bar {{ grid-template-columns: repeat(2, 1fr); padding: 30px; gap: 30px; border-radius: 24px; }}
            .stat-item:nth-child(2) {{ border-right: none; }}
            .stat-item:nth-child(3), .stat-item:nth-child(4) {{ border-top: 1px solid var(--border); padding-top: 30px; }}
            .hero h1 {{ font-size: clamp(2.5rem, 5vw, 4rem); }}
        }}
        
        @media (max-width: 992px) {{
            .split-grid {{ grid-template-columns: 1fr; gap: 50px; }}
            .process-grid {{ grid-template-columns: repeat(2, 1fr); gap: 40px; }}
            .process-grid::before {{ display: none; }}
            .hero {{ padding: 160px 0 100px; min-height: auto; }}
        }}
        
        @media (max-width: 768px) {{
            .nav-links, .auth-btns {{ display: none; }}
            .mobile-menu-btn {{ display: block; }}
            
            .hero {{ padding: 140px 0 80px; }}
            .hero-badge {{ font-size: 0.8rem; padding: 6px 16px; }}
            .hero h1 {{ font-size: 2.4rem; }}
            .hero p {{ font-size: 1.05rem; padding: 0 10px; }}
            
            .hero-actions {{ flex-direction: column; width: 100%; padding: 0 20px; }}
            .hero-actions .btn {{ width: 100%; }}
            
            .stats-bar {{ grid-template-columns: 1fr; gap: 25px; padding: 30px 20px; }}
            .stat-item {{ border-right: none !important; border-top: 1px solid var(--border); padding-top: 25px; }}
            .stat-item:first-child {{ border-top: none; padding-top: 0; margin-top: 0; }}
            .stat-icon {{ font-size: 2rem; margin-bottom: 10px; }}
            .stat-val {{ font-size: 1.4rem; }}
            
            .section {{ padding: 80px 0; }}
            .service-card {{ padding: 35px 25px; border-radius: 24px; }}
            .sc-icon-wrapper {{ width: 70px; height: 70px; font-size: 2.2rem; margin-bottom: 25px; }}
            .service-card h3 {{ font-size: 1.8rem; }}
            .service-card > p {{ font-size: 1rem; margin-bottom: 30px; }}
            .feature-list li {{ font-size: 0.95rem; align-items: flex-start; }}
            .service-actions {{ flex-direction: column; width: 100%; }}
            .service-actions .btn {{ width: 100%; justify-content: center; }}
            
            .process-section {{ padding: 80px 0; }}
            .process-grid {{ grid-template-columns: 1fr; gap: 30px; margin-top: 40px; }}
            .step-icon {{ width: 80px; height: 80px; font-size: 2rem; margin-bottom: 20px; }}
            
            .footer-links {{ flex-direction: column; gap: 20px; }}
            .modal-content {{ padding: 40px 25px; }}
        }}
    </style>
</head>
<body>

    <nav class="navbar" id="navbar">
        <div class="container nav-inner">
            <a href="/" class="logo">
    		<img src="/static/logo.png" alt="Restify" style="height: 38px; width: auto; object-fit: contain;"> 
    		Restify
	</a>
            
            <div class="nav-links">
                <a href="#restaurants" class="nav-link">Закладам</a>
                <a href="#couriers" class="nav-link">Кур'єрам</a>
                <a href="#how-it-works" class="nav-link">Як працює</a>
                {custom_button_html}
            </div>

            <div class="auth-btns">
                <a href="/partner/login" class="btn btn-outline"><i class="fa-solid fa-store"></i> Вхід для закладів</a>
                <a href="/courier/login" class="btn btn-primary"><i class="fa-solid fa-helmet-safety"></i> Вхід кур'єра</a>
            </div>
            
            <button class="mobile-menu-btn" id="mobile-menu-toggle">
                <i class="fa-solid fa-bars"></i>
            </button>
        </div>
    </nav>

    <div class="mobile-overlay" id="mobile-overlay">
        <button class="close-btn" id="mobile-menu-close" style="top: 25px; right: 25px; position: absolute;"><i class="fa-solid fa-xmark"></i></button>
        
        <div class="mobile-nav-links">
            <a href="#restaurants" class="mobile-nav-link mobile-link-item">Для закладів</a>
            <a href="#couriers" class="mobile-nav-link mobile-link-item">Для кур'єрів</a>
            <a href="#how-it-works" class="mobile-nav-link mobile-link-item">Як це працює</a>
            {mobile_custom_button_html}
        </div>
        
        <div class="mobile-auth-btns">
            <a href="/partner/login" class="btn btn-outline mobile-link-item" style="padding: 16px;"><i class="fa-solid fa-store"></i> Вхід закладу</a>
            <a href="/courier/login" class="btn btn-primary mobile-link-item" style="padding: 16px;"><i class="fa-solid fa-helmet-safety"></i> Вхід кур'єра</a>
        </div>
    </div>

    <section class="hero">
        <div class="hero-bg-glow1"></div>
        <div class="hero-bg-glow2"></div>
        <div class="container hero-content">
            <div class="hero-badge animate-up"><i class="fa-solid fa-rocket"></i> B2B Платформа для HoReCa</div>
            <h1 class="animate-up delay-1"><span>Новий стандарт доставки</span> <br>для вашого бізнесу</h1>
            <p class="animate-up delay-2">Прозора та сучасна система логістики. Викликайте верифікованих кур'єрів в один клік, керуйте викупами, відстежуйте замовлення на Live-карті та спілкуйтеся у вбудованому чаті.</p>
            
            <div class="hero-actions animate-up delay-3">
                <a href="/partner/register" class="btn btn-primary" style="padding: 18px 36px; font-size: 1.1rem;">Підключити заклад</a>
                <a href="/courier/register" class="btn btn-outline" style="padding: 18px 36px; font-size: 1.1rem; border-color: rgba(255,255,255,0.2);">Стати кур'єром</a>
            </div>
        </div>
    </section>

    <div class="container stats-wrapper">
        <div class="stats-bar animate-up delay-3">
            <div class="stat-item">
                <div class="stat-icon"><i class="fa-solid fa-infinity"></i></div>
                <div class="stat-val">Без абонплат</div>
                <div class="stat-label">Оплата лише за результат</div>
            </div>
            <div class="stat-item">
                <div class="stat-icon" style="color: var(--primary);"><i class="fa-solid fa-handshake-angle"></i></div>
                <div class="stat-val">Чесна комісія</div>
                <div class="stat-label">Мінімальний % платформи</div>
            </div>
            <div class="stat-item">
                <div class="stat-icon"><i class="fa-solid fa-location-crosshairs"></i></div>
                <div class="stat-val">Live трекінг</div>
                <div class="stat-label">Контроль на кожному кроці</div>
            </div>
            <div class="stat-item">
                <div class="stat-icon" style="color: var(--primary);"><i class="fa-solid fa-wallet"></i></div>
                <div class="stat-val">Гідна оплата</div>
                <div class="stat-label">Вигідні тарифи для кур'єрів</div>
            </div>
        </div>
    </div>

    <section class="section" id="restaurants">
        <div class="container">
            <div class="section-header">
                <h2>Ідеальне рішення для всіх</h2>
                <p>Ми об'єднуємо кращі заклади міста з надійними кур'єрами на єдиній сучасній платформі.</p>
            </div>
            
            <div class="split-grid">
                <div class="service-card sc-partner">
                    <div class="sc-icon-wrapper"><i class="fa-solid fa-store"></i></div>
                    <h3>Ресторанам та Кафе</h3>
                    <p>Повний контроль над логістикою без утримання власного штату. Створюйте заявки, мотивуйте кур'єрів преміями та відстежуйте кожну доставку онлайн.</p>
                    
                    <ul class="feature-list">
                        <li><i class="fa-solid fa-bolt"></i> <div><b>Миттєвий виклик & Boost:</b> Створення заявки за секунди. Функція Boost для термінового пошуку вільного кур'єра.</div></li>
                        <li><i class="fa-solid fa-money-bill-transfer"></i> <div><b>Гнучкі розрахунки:</b> Підтримка передоплати, готівки, "Викупу" (кур'єр платить на касі) та автоматичне повернення коштів.</div></li>
                        <li><i class="fa-solid fa-comments"></i> <div><b>Прямий зв'язок:</b> Вбудований чат у реальному часі та система прозорих рейтингів після кожної доставки.</div></li>
                    </ul>
                    
                    <div class="service-actions">
                        <a href="/partner/register" class="btn btn-primary">Почати роботу</a>
                        <a href="/partner/login" class="btn btn-outline">Увійти в кабінет</a>
                    </div>
                </div>

                <div class="service-card sc-courier" id="couriers">
                    <div class="sc-icon-wrapper"><i class="fa-solid fa-helmet-safety"></i></div>
                    <h3>Професійним Кур'єрам</h3>
                    <p>Доставляйте замовлення з кращих закладів міста через зручний PWA додаток. Чесний розподіл замовлень, безпека та високий стабільний дохід.</p>
                    
                    <ul class="feature-list">
                        <li><i class="fa-solid fa-shield-halved"></i> <div><b>Безпека & Довіра:</b> Легка реєстрація через Telegram з обов'язковою верифікацією гарантує безпеку всіх учасників.</div></li>
                        <li><i class="fa-solid fa-sack-dollar"></i> <div><b>Високий дохід:</b> Отримуйте гідну оплату за кожну доставку з мінімальною прозорою комісією платформи.</div></li>
                        <li><i class="fa-solid fa-bell-concierge"></i> <div><b>Smart-система:</b> Push-сповіщення про нові замовлення поблизу, вбудована навігація та прямий чат із закладом.</div></li>
                    </ul>
                    
                    <div class="service-actions">
                        <a href="/courier/register" class="btn btn-accent">Стати кур'єром</a>
                        <a href="/courier/login" class="btn btn-outline">Увійти в додаток</a>
                    </div>
                </div>

            </div>
        </div>
    </section>

    <section class="process-section" id="how-it-works">
        <div class="container">
            <div class="section-header" style="margin-bottom: 30px;">
                <h2>Як це працює?</h2>
                <p>Абсолютно прозорий процес взаємодії від передачі пакунка на кухні до вручення щасливому клієнту.</p>
            </div>
            
            <div class="process-grid">
                <div class="process-step">
                    <div class="step-icon"><i class="fa-solid fa-file-invoice"></i></div>
                    <h4>1. Заявка</h4>
                    <p>Менеджер вказує адресу, тип оплати та за потреби вмикає опцію "Повернення коштів".</p>
                </div>
                <div class="process-step">
                    <div class="step-icon"><i class="fa-solid fa-satellite-dish"></i></div>
                    <h4>2. Smart-Пошук</h4>
                    <p>Система миттєво відправляє Push-сповіщення найближчим вільним верифікованим кур'єрам.</p>
                </div>
                <div class="process-step">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <h4>3. Пікап</h4>
                    <p>Кур'єр приймає замовлення, прибуває в заклад, забирає пакунок (відбувається викуп, якщо вказано).</p>
                </div>
                <div class="process-step">
                    <div class="step-icon"><i class="fa-solid fa-location-crosshairs"></i></div>
                    <h4>4. Доставка</h4>
                    <p>Ресторан бачить рух кур'єра на Live-карті. Після успішного вручення списується мінімальна комісія.</p>
                </div>
            </div>
        </div>
    </section>

    <footer>
        <div class="container">
            <div class="footer-logo">
    		<img src="/static/logo.png" alt="Restify" style="height: 45px; width: auto; object-fit: contain;"> 
    			Restify Delivery
		</div>
            <p style="color: var(--text-muted); margin-bottom: 35px; font-size: 1.05rem; max-width: 500px; margin-inline: auto;">Ваш надійний технологічний партнер у сфері ресторанної логістики.</p>
            
            <div class="footer-links">
                <a href="/partner/register">Підключити ресторан</a>
                <a href="/courier/register">Робота для кур'єрів</a>
                {custom_button_html}
            </div>
            
            <div class="footer-bottom">
                <span>© 2026 Restify SaaS. Всі права захищені.</span>
                <span style="font-size: 0.85rem; opacity: 0.7;">Розроблено для розвитку вашого бізнесу</span>
            </div>
        </div>
    </footer>

    <div id="customModal" class="modal-overlay">
        <div class="modal-content">
            <span class="close-btn" id="close-modal-btn"><i class="fa-solid fa-xmark"></i></span>
            <div class="modal-body" style="line-height: 1.8; font-size: 1.05rem;">
                {modal_content_html}
            </div>
        </div>
    </div>

    <script>
        // Navbar scroll effect
        window.addEventListener('scroll', () => {{
            const nav = document.getElementById('navbar');
            if (window.scrollY > 20) {{
                nav.style.background = 'rgba(7, 9, 14, 0.95)';
                nav.style.padding = '12px 0';
            }} else {{
                nav.style.background = 'rgba(7, 9, 14, 0.7)';
                nav.style.padding = '18px 0';
            }}
        }});

        // Mobile Menu Logic
        const mobileToggle = document.getElementById('mobile-menu-toggle');
        const mobileClose = document.getElementById('mobile-menu-close');
        const mobileOverlay = document.getElementById('mobile-overlay');
        const mobileLinks = document.querySelectorAll('.mobile-link-item');

        function toggleMobileMenu() {{
            mobileOverlay.classList.toggle('active');
            document.body.style.overflow = mobileOverlay.classList.contains('active') ? 'hidden' : '';
        }}

        mobileToggle.addEventListener('click', toggleMobileMenu);
        mobileClose.addEventListener('click', toggleMobileMenu);
        
        mobileLinks.forEach(link => {{
            link.addEventListener('click', () => {{
                if(!link.classList.contains('custom-modal-btn')) {{
                    toggleMobileMenu();
                }}
            }});
        }});

        // Modal Logic
        const modalBtns = document.querySelectorAll('.custom-modal-btn');
        const modalOverlay = document.getElementById('customModal');
        const closeModalBtn = document.getElementById('close-modal-btn');

        modalBtns.forEach(btn => {{
            btn.addEventListener('click', (e) => {{
                e.preventDefault();
                if(mobileOverlay.classList.contains('active')) toggleMobileMenu();
                modalOverlay.classList.add('visible');
                document.body.style.overflow = 'hidden';
            }});
        }});

        const closeModal = () => {{
            modalOverlay.classList.remove('visible');
            document.body.style.overflow = '';
        }};

        closeModalBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', (e) => {{
            if(e.target === modalOverlay) closeModal();
        }});
        
        // Scroll Animation Observer
        const observerOptions = {{ threshold: 0.1, rootMargin: "0px 0px -50px 0px" }};
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }}
            }});
        }}, observerOptions);
        
        // Pause animation initially for elements below fold
        document.querySelectorAll('.service-card, .process-step').forEach(el => {{
            el.classList.add('animate-up');
            el.style.animationPlayState = 'paused';
            observer.observe(el);
        }});
    </script>
</body>
</html>
    """