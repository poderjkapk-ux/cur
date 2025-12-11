import os
from typing import List, Dict
# Эти модели нужны для подсказок типов в функциях
try:
    from models import User, Instance
except ImportError:
    # Простая заглушка, если models.py еще не доступен
    class User: pass
    class Instance: pass

# --- 1. Глобальные стили (Из app.py) ---
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
        --status-active: #4ade80; /* Зеленый */
        --status-suspended: #f87171; /* Красный */
        --status-delete: #e11d48; /* Ярко-красный */
    }
    body { 
        font-family: var(--font); 
        display: grid; 
        place-items: center; 
        min-height: 100vh; 
        background-color: var(--bg-body); 
        color: var(--text-main); 
        margin: 0; 
        padding: 20px 0; /* Добавлен отступ для дашборда */
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
    input, textarea { /* Добавлена textarea */
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
    }
    .btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px -5px rgba(99, 102, 241, 0.7);
    }
    .btn:disabled {
        background: #555;
        box-shadow: none;
        transform: none;
        cursor: not-allowed; /* Курсор "недоступно" */
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
    
    /* Стили для подсказок в форме дашборда */
    .form-hint {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-align: left;
        margin-top: -10px; /* Ближе к input'у */
        margin-bottom: 15px; /* Отступ до следующего label */
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

# --- 2. Шаблоны страниц Авторизации (Из app.py) ---

def get_login_page(message: str = "", msg_type: str = "error"):
    """HTML для страницы входа /login"""
    return f"""
    <!DOCTYPE html><html lang="ru"><head><title>Вход</title>{GLOBAL_STYLES}</head>
    <body><div class="container">
        <img src="/static/logo.png" alt="Restify Logo" class="logo-img">
        <h1>Вход в Restify</h1>
        <form method="post" action="/token">
            <input type="email" name="username" placeholder="Ваш Email" required>
            <input type="password" name="password" placeholder="Ваш пароль" required>
            <button type="submit" class="btn">Войти</button>
        </form>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <a href="/register">У меня нет аккаунта</a>
        <a href="/" style="font-size: 0.9rem; color: var(--text-muted); margin-top: 15px;">&larr; На главную</a>
    </div></body></html>
    """

def get_register_page():
    """HTML для страницы регистрации /register"""
    return f"""
    <!DOCTYPE html><html lang="ru"><head><title>Регистрация</title>{GLOBAL_STYLES}</head>
    <body><div class="container">
        <img src="/static/logo.png" alt="Restify Logo" class="logo-img">
        <h1>Регистрация</h1>
        <p style="margin-top: -20px; margin-bottom: 20px;">Создайте свой аккаунт для входа в дашборд.</p>
        
        <form id="registerForm" method="post" action="/api/register">
            <input type="email" name="email" placeholder="Ваш Email (это будет ваш логин)" required>
            <input type="password" name="password" placeholder="Придумайте пароль" required>
            <button type="submit" class="btn" id="submitBtn">Зарегистрироваться</button>
            <div id="response-msg" class="message" style="display: none;"></div>
        </form>
        <a href="/login">У меня уже есть аккаунт</a>
    </div>
    
    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const form = e.target;
            const btn = document.getElementById('submitBtn');
            const msgEl = document.getElementById('response-msg');
            btn.disabled = true; btn.textContent = 'Регистрация...';
            msgEl.style.display = 'none'; msgEl.textContent = '';
            
            try {{
                const response = await fetch('/api/register', {{
                    method: 'POST',
                    body: new FormData(form)
                }});
                const result = await response.json();
                msgEl.style.display = 'block';
                
                if (response.ok) {{
                    msgEl.className = 'message success';
                    msgEl.innerHTML = `✅ <strong>Регистрация успешна!</strong><br>Перенаправляем на страницу входа...`;
                    form.reset();
                    setTimeout(() => {{
                        window.location.href = '/login?message=Регистрация прошла успешно! Теперь вы можете войти.&type=success';
                    }}, 2000);
                }} else {{
                    msgEl.className = 'message error';
                    msgEl.textContent = `Ошибка: ${{result.detail || 'Не удалось создать аккаунт.'}}`;
                    btn.disabled = false; btn.textContent = 'Зарегистрироваться';
                }}
            }} catch (err) {{
                msgEl.style.display = 'block';
                msgEl.className = 'message error';
                msgEl.textContent = 'Ошибка сети. Попробуйте снова.';
                btn.disabled = false; btn.textContent = 'Зарегистрироваться';
            }}
        }});
    </script>
    </body></html>
    """
    
# --- 3. Шаблон Дашборда (Из app.py) ---

def get_dashboard_html(user: User, instances: List[Instance]):
    """HTML для Личного Кабинета Клиента (/dashboard)"""
    
    project_cards_html = ""
    if not instances:
        project_cards_html = "<p style='text-align: center; color: var(--text-muted);'>У вас пока нет проектов. Создайте свой первый проект, используя форму выше.</p>"
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
                    <p><strong>Админка:</strong> <a href="{instance.url}/admin" target="_blank">{instance.url}/admin</a></p>
                    <p><strong>Логин:</strong> admin</p>
                    <p><strong>Пароль:</strong> {instance.admin_pass}</p>
                    <p><strong>Оплачен до:</strong> {instance.next_payment_due.strftime('%Y-%m-%d')}</p>
                </div>
                <div class="project-footer">
                    <button class="btn-action" onclick="controlInstance({instance.id}, 'stop')" id="btn-stop-{instance.id}" {stop_disabled}>
                        <i class="fa-solid fa-stop"></i> Stop
                    </button>
                    <button class="btn-action btn-start" onclick="controlInstance({instance.id}, 'start')" id="btn-start-{instance.id}" {start_disabled}>
                        <i class="fa-solid fa-play"></i> Start
                    </button>
                    <button class="btn-action btn-renew" disabled>
                        <i class="fa-solid fa-credit-card"></i> Продлить
                    </button>
                    <button class="btn-action btn-delete" onclick="deleteInstance({instance.id}, '{instance.subdomain}')">
                        <i class="fa-solid fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
            """

    return f"""
    <!DOCTYPE html><html lang="ru">
    <head>
        <title>Личный кабинет</title>
        {GLOBAL_STYLES}
        <style>
            /* Переопределяем стили для дашборда */
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
            
            /* Стили для карточки создания */
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
            /* Разделение полей токенов */
            .token-fields {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            @media (min-width: 600px) {{
                .token-fields {{ grid-template-columns: 1fr 1fr; }}
            }}

            /* Стили для списка проектов */
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
                background: rgba(225, 29, 72, 0.1); /* bg-rose-900/10 */
                border-color: rgba(225, 29, 72, 0.3);
                color: var(--status-delete);
                flex-grow: 0; /* Не растягивать */
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
                <h1>Здравствуйте, {user.email}!</h1>
                <a href="/logout">Выйти</a>
            </div>

            <div class="create-card">
                <h2><i class="fa-solid fa-plus" style="color: var(--primary);"></i> Создать новый проект</h2>
                <form id="createInstanceForm" method="post" action="/api/create-instance">
                    
                    <label for="name">Название проекта (Только латиница, без пробелов)</label>
                    <input type="text" name="name" id="name" placeholder="Например: 'moybiznes' или 'romashka'" required>
                    <p class="form-hint">Это название будет использовано для создания вашего уникального домена: <code>moybiznes.restify.site</code></p>
                    
                    <label for="phone">Ваш контактный телефон</label>
                    <input type="tel" name="phone" id="phone" placeholder="Мы сообщим, когда проект будет готов" required>
                    <p class="form-hint">Используется только для уведомлений вам о статусе создания.</p>

                    <hr>
                    <h3>Настройка Telegram Ботов</h3>
                    <p class="form-hint" style="margin-top: 0; margin-bottom: 20px;">Введите токены ваших ботов, полученные от <code>@BotFather</code>. Вы сможете изменить их позже в админ-панели вашего проекта.</p>
                    
                    <div class="token-fields">
                        <div>
                            <label for="client_bot_token">Токен Клиент-Бота (для заказов)</label>
                            <input type="text" name="client_bot_token" id="client_bot_token" placeholder="123456:ABC-..." required>
                        </div>
                        <div>
                            <label for="admin_bot_token">Токен Админ-Бота (для персонала)</label>
                            <input type="text" name="admin_bot_token" id="admin_bot_token" placeholder="789123:XYZ-..." required>
                        </div>
                    </div>
                    
                    <label for="admin_chat_id">Admin Chat ID (для уведомлений)</label>
                    <input type="text" name="admin_chat_id" id="admin_chat_id" placeholder="-100123..." required>
                    <p class="form-hint">ID вашего Telegram-канала или группы, куда будут приходить заказы. (Узнайте у <code>@GetMyID_bot</code>)</p>
                    
                    <button type="submit" class="btn" id="submitBtn">🚀 Запустить проект</button>
                    <div id="response-msg" class="message" style="display: none; margin-top: 20px;"></div>
                </form>
            </div>

            <hr>
            
            <h2 style="margin-bottom: 20px;">Ваши проекты</h2>
            <div class="projects-grid" id="projects-grid-container">
                {project_cards_html}
            </div>
        </div>

        <script>
        // --- JS для формы создания ---
        const form = document.getElementById('createInstanceForm');
        if (form) {{
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                const msgEl = document.getElementById('response-msg');
                btn.disabled = true;
                btn.textContent = 'Запускаем... (Это может занять 2-3 минуты)';
                msgEl.style.display = 'none'; msgEl.textContent = '';
                
                try {{
                    const response = await fetch('/api/create-instance', {{
                        method: 'POST', body: new FormData(form)
                    }});
                    const result = await response.json();
                    
                    if (response.ok) {{
                        msgEl.style.display = 'block';
                        msgEl.className = 'message success';
                        msgEl.innerHTML = `✅ <strong>УСПЕХ! Ваш сайт создан.</strong><br>Адрес: <strong>${{result.url}}</strong><br>Пароль: <strong>${{result.password}}</strong><br><br>Перезагружаем страницу...`;
                        // Перезагружаем страницу, чтобы показать новую карточку
                        setTimeout(() => {{ window.location.reload(); }}, 3000);
                    }} else {{
                        msgEl.style.display = 'block';
                        msgEl.className = 'message error';
                        msgEl.textContent = `Ошибка: ${{result.detail || 'Не удалось создать сайт.'}}`;
                        btn.disabled = false; btn.textContent = '🚀 Запустить проект';
                    }}
                }} catch (err) {{
                    msgEl.style.display = 'block';
                    msgEl.className = 'message error';
                    msgEl.textContent = 'Ошибка сети. Попробуйте снова.';
                    btn.disabled = false; btn.textContent = '🚀 Запустить проект';
                }}
            }});
        }}

        // --- JS для управления (Stop/Start) ---
        async function controlInstance(instanceId, action) {{
            const stopBtn = document.getElementById(`btn-stop-${{instanceId}}`);
            const startBtn = document.getElementById(`btn-start-${{instanceId}}`);
            const statusBadge = document.getElementById(`status-badge-${{instanceId}}`);
            const currentStatus = statusBadge.textContent.trim(); 

            stopBtn.disabled = true;
            startBtn.disabled = true;
            statusBadge.textContent = 'обработка...';
            
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
                    alert(`Ошибка: ${{result.detail}}`);
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
                alert('Сетевая ошибка. Не удалось выполнить действие.');
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

        // --- JS: Управление Удалением ---
        async function deleteInstance(instanceId, subdomain) {{
            const message = `Вы уверены, что хотите ПОЛНОСТЬЮ удалить проект '${{subdomain}}'?\n\nЭто действие необратимо. Контейнер и база данных будут стерты.`
            if (!confirm(message)) {{
                return;
            }}

            const card = document.getElementById(`instance-card-${{instanceId}}`);
            const deleteBtn = card.querySelector('.btn-delete');
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Удаление...';
            
            const formData = new FormData();
            formData.append('instance_id', instanceId);

            try {{
                const response = await fetch('/api/instance/delete', {{
                    method: 'POST',
                    body: formData
                }});
                const result = await response.json();

                if (response.ok) {{
                    alert(result.message || 'Проект успешно удален.');
                    card.style.transition = 'opacity 0.5s, transform 0.5s';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.9)';
                    setTimeout(() => {{ 
                        card.remove();
                        const grid = document.getElementById('projects-grid-container');
                        if (grid.children.length === 0) {{
                            grid.innerHTML = "<p style='text-align: center; color: var(--text-muted);'>У вас пока нет проектов. Создайте свой первый проект, используя форму выше.</p>";
                        }}
                    }}, 500);
                }} else {{
                    alert(`Ошибка удаления: ${{result.detail}}`);
                    deleteBtn.disabled = false;
                    deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Удалить';
                }}
            }} catch (err) {{
                alert('Сетевая ошибка. Не удалось удалить проект.');
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Удалить';
            }}
        }}
        </script>
    </body></html>
    """

# --- 4. Шаблоны Админ-панели (Из app.py) ---

def get_admin_dashboard_html(clients: list, message: str = "", msg_type: str = "success"):
    """HTML для Вашей Админки (/admin)"""
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
                <td>{instance.status}</td>
                <td>{instance.next_payment_due.strftime('%Y-%m-%d')}</td>
                <td>
                    <form action="/admin/control" method="post" style="display:inline;">
                        <input type="hidden" name="instance_id" value="{instance.id}">
                        {
                            '<button type="submit" name="action" value="stop" class="btn-link error">Отключить</button>' 
                            if instance.status == 'active' else 
                            '<button type="submit" name="action" value="start" class="btn-link success">Включить</button>'
                        }
                    </form>
                </td>
            </tr>
            """
        else:
            rows += f"<tr><td>{user.id}</td><td>{user.email}</td><td colspan='5'><i>(Экземпляр не создан)</i></td></tr>"

    return f"""
    <!DOCTYPE html><html lang="ru"><head><title>Admin Panel</title>{GLOBAL_STYLES}</head>
    <style>
        body {{ display: block; padding: 20px; }}
        .container {{ max-width: 1200px; width: 100%; text-align: left; margin: 0 auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 15px; border: 1px solid var(--border); text-align: left; font-size: 0.9rem; }}
        th {{ background: var(--bg-card-hover); font-weight: 600; }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
        .btn-link {{ background:none; border:none; cursor:pointer; padding: 0; margin: 0; text-decoration: underline; font-family: var(--font); font-size: 0.9rem; }}
        .btn-link.error {{ color: #f87171; }}
        .btn-link.success {{ color: #4ade80; }}
        .header-nav {{ display: flex; justify-content: space-between; align-items: center; }}
        .nav-link {{ background: var(--primary); color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 0.9rem; margin-top: 0; }}
        .nav-link:hover {{ background: var(--primary-hover); }}
    </style>
    <body><div class="container">
        <div class="header-nav">
            <h1>Панель Администратора</h1>
            <a href="/settings" class="nav-link">Настройки Витрины</a>
        </div>
        {f"<div class='message {msg_type}'>{message}</div>" if message else ""}
        <h2>Клиенты SaaS</h2>
        <table>
            <thead>
                <tr><th>ID Юзера</th><th>Email</th><th>Поддомен</th><th>Контейнер</th><th>Статус</th><th>Оплачен до</th><th>Действие</th></tr>
            </thead>
            <tbody>
                {rows or "<tr><td colspan='7'>Нет клиентов</td></tr>"}
            </tbody>
        </table>
    </div></body></html>
    """

def get_settings_page_html(config, message=""):
    """
    HTML для страницы настроек витрины (/settings)
    ИЗМЕНЕНИЕ: Добавлены поля для custom_btn_text и custom_btn_content
    """
    # Экранируем кавычки и HTML-сущности для безопасного встраивания в value="" и <textarea>
    custom_btn_text = config.get('custom_btn_text', '').replace('"', '&quot;')
    custom_btn_content = config.get('custom_btn_content', '').replace('<', '&lt;').replace('>', '&gt;')
    
    return f"""
    <!DOCTYPE html><html><head><title>Restify Admin</title>{GLOBAL_STYLES}</head>
    <style>
        .container {{ max-width: 500px; text-align: left; }}
        label {{ color: var(--text-muted); display: block; margin-bottom: 5px; font-size: 0.9rem; }}
    </style>
    <body>
        <div class="container">
            <h1 style="text-align:center;">Настройки Витрины</h1>
            {f'<div class="message success" style="text-align:center">{message}</div>' if message else ''}
            <form method="post" action="/settings">
                <label>Currency Symbol</label><input type="text" name="currency" value="{config.get('currency', '$')}">
                
                <input type="hidden" name="price_light" value="{config.get('price_light', '300')}">
                <label>Price (Pro) / month</label><input type="number" name="price_full" value="{config.get('price_full', '600')}">
                
                <hr>
                <label>Admin Telegram ID (для заявок)</label><input type="text" name="admin_id" value="{config.get('admin_id', '')}">
                <label>Bot Token (для заявок)</label><input type="text" name="bot_token" value="{config.get('bot_token', '')}">
                
                <hr>
                <label>Текст кнопки (в меню)</label>
                <input type="text" name="custom_btn_text" value="{custom_btn_text}" placeholder="Напр: Политика">
                <p class="form-hint" style="margin-top: 5px; margin-bottom: 15px;">Оставьте пустым, чтобы скрыть кнопку.</p>
                
                <label>Содержимое окна (HTML)</label>
                <textarea name="custom_btn_content" placeholder="<p>Ваш текст...</p>">{custom_btn_content}</textarea>
                <button type="submit" class="btn">Сохранить</button>
            </form>
            <a href="/admin" style="text-align:center;">&larr; Назад к Клиентам</a>
        </div>
    </body></html>
    """


# --- 5. Шаблон Главной Страницы (С ИЗМЕНЕНИЯМИ) ---

def get_landing_page_html(config: Dict[str, str]):
    """
    HTML для главной страницы (витрины).
    ВКЛЮЧАЕТ ИЗМЕНЕНИЯ:
    1. Тексты "48 часов" заменены на "мгновенный запуск".
    2. Добавлена кастомная кнопка в меню и модальное окно (HTML/CSS/JS).
    """
    
    # Готовим кастомную кнопку. Она будет добавлена, только если текст для нее задан в config.
    custom_button_html = ""
    if config.get("custom_btn_text"):
        # Экранируем текст для безопасного встраивания
        button_text = config["custom_btn_text"].replace('<', '&lt;').replace('>', '&gt;')
        custom_button_html = f"""
            <a href="#" id="custom-modal-btn">{button_text}</a>
        """
        
    # Готовим контент для модального окна.
    # Здесь мы доверяем HTML-контенту из админки.
    modal_content_html = config.get("custom_btn_content", "")

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restify | Digital Restaurant System</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --primary: #6366f1; /* Indigo */
            --primary-hover: #4f46e5;
            --accent: #ec4899; /* Pink */
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
            --radius: 16px;
            --font: 'Inter', sans-serif;
            --transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            font-family: var(--font);
            background-color: var(--bg-body);
            color: var(--text-main);
            line-height: 1.6;
            overflow-x: hidden;
            display: block;
            min-height: auto;
            padding: 0;
        }}
        
        .container {{ 
            width: 100%; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 0 20px; 
            background: none;
            border: none;
            box-shadow: none;
            max-width: 1200px;
        }}
        
        h1, h2, h3 {{ line-height: 1.2; font-weight: 800; letter-spacing: -0.02em; }}
        h1 {{ margin-bottom: 0; }}
        
        .gradient-text {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-size: 200% 200%;
            animation: gradientMove 5s ease infinite;
        }}
        @keyframes gradientMove {{ 0% {{background-position:0% 50%}} 50% {{background-position:100% 50%}} 100% {{background-position:0% 50%}} }}

        /* Buttons */
        .btn {{
            display: inline-flex; align-items: center; justify-content: center; gap: 10px;
            padding: 14px 28px; border-radius: 12px; font-weight: 600; cursor: pointer;
            text-decoration: none; transition: var(--transition); border: none; font-size: 1rem;
            position: relative; overflow: hidden;
            width: auto; 
            margin-bottom: 0;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--primary), var(--accent)); color: white;
            box-shadow: 0 4px 20px -5px rgba(99, 102, 241, 0.5);
        }}
        .btn-primary:hover {{ transform: translateY(-3px) scale(1.02); box-shadow: 0 15px 30px -5px rgba(99, 102, 241, 0.7); }}
        .btn-outline {{
            background: transparent; border: 1px solid var(--border); color: white;
        }}
        .btn-outline:hover {{ border-color: var(--primary); background: rgba(255,255,255,0.05); transform: translateY(-3px); }}

        /* Navbar */
        .navbar {{
            position: fixed; top: 0; width: 100%; z-index: 1000;
            background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border); transition: all 0.3s;
        }}
        .nav-inner {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            height: 80px; 
        }}
        .logo {{ 
            font-size: 1.5rem; 
            font-weight: 800; 
            color: white; 
            text-decoration: none; 
            display: flex; 
            align-items: center; 
            gap: 8px; 
        }}
        .logo img {{
            height: 60px; 
            width: 60px;
            filter: invert(0.9);
            margin-right: 5px;
        }}
        
        .nav-links {{ 
            display: flex; 
            gap: 25px; 
            align-items: center; 
        }}
        .nav-links a {{ 
            color: var(--text-muted); text-decoration: none; font-weight: 500; font-size: 0.95rem; 
            transition: var(--transition); position: relative; 
            display: inline; margin: 0;
            cursor: pointer; /* Для кастомной кнопки */
        }}
        .nav-links a:hover {{ color: white; transform: translateY(-2px); text-decoration: none; }}
        .nav-links a::after {{
            content: ''; position: absolute; width: 0; height: 2px; bottom: -4px; left: 0;
            background-color: var(--primary); transition: width 0.3s;
        }}
        .nav-links a:hover::after {{ width: 100%; }}

        .nav-right {{ display: flex; align-items: center; gap: 20px; }}
        
        .lang-dropdown {{ position: relative; }}
        .lang-btn {{ 
            background: transparent; color: var(--text-muted); border: 1px solid var(--border); 
            padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 0.9rem; 
            display: flex; align-items: center; gap: 6px; transition: var(--transition);
        }}
        .lang-btn:hover {{ color: white; border-color: var(--text-muted); background: rgba(255,255,255,0.05); }}
        .lang-menu {{
            display: none; position: absolute; top: 100%; right: 0; margin-top: 10px;
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            width: 180px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); overflow: hidden;
            transform-origin: top right; animation: scaleIn 0.2s ease;
        }}
        @keyframes scaleIn {{ from {{ opacity: 0; transform: scale(0.9); }} to {{ opacity: 1; transform: scale(1); }} }}
        .lang-dropdown:hover .lang-menu {{ display: block; }}
        .lang-item {{
            display: flex; align-items: center; gap: 10px; padding: 10px 15px; color: var(--text-muted);
            text-decoration: none; transition: 0.2s; cursor: pointer; font-size: 0.9rem;
        }}
        .lang-item:hover {{ background: var(--bg-card-hover); color: white; padding-left: 20px; }}
        .flag {{ font-size: 1.2rem; }}

        /* Hero */
        .hero {{ padding: 180px 0 120px; text-align: center; position: relative; overflow: hidden; perspective: 1000px; }}
        .hero-bg {{
            position: absolute; width: 120%; height: 120%; top: -10%; left: -10%; z-index: -1;
            background: radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 60%);
            transition: transform 0.1s ease-out;
        }}
        .hero-content {{ position: relative; z-index: 1; }}
        .hero h1 {{ font-size: clamp(2.5rem, 6vw, 4.5rem); margin-bottom: 24px; opacity: 0; animation: fadeUp 0.8s ease forwards 0.2s; }}
        .hero p {{ font-size: 1.2rem; color: var(--text-muted); max-width: 600px; margin: 0 auto 40px; opacity: 0; animation: fadeUp 0.8s ease forwards 0.4s; }}
        .hero-btns {{ opacity: 0; animation: fadeUp 0.8s ease forwards 0.6s; display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }}

        /* Features */
        .section {{ padding: 100px 0; }}
        .section-header {{ text-align: center; margin-bottom: 60px; max-width: 700px; margin-inline: auto; opacity: 0; transform: translateY(20px); transition: all 0.8s ease; }}
        .section-header.visible {{ opacity: 1; transform: translateY(0); }}
        .section-header h2 {{ font-size: 2.5rem; margin-bottom: 16px; }}
        
        .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }}
        
        .feature-card {{
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(10px);
            padding: 40px; border-radius: var(--radius);
            border: 1px solid var(--border); transition: var(--transition);
            opacity: 0; transform: translateY(30px);
            position: relative; overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        .feature-card::after {{
            content: ""; position: absolute; inset: 0; border-radius: var(--radius); padding: 2px;
            background: linear-gradient(45deg, transparent, rgba(99, 102, 241, 0.3), transparent);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none;
        }}
        .feature-card:hover {{ transform: translateY(-10px); border-color: rgba(99, 102, 241, 0.5); box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.2); }}
        
        .icon-box {{
            width: 60px; height: 60px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(236, 72, 153, 0.1)); 
            border-radius: 16px; display: flex; align-items: center; justify-content: center; color: var(--primary);
            font-size: 1.8rem; margin-bottom: 24px; transition: var(--transition); border: 1px solid rgba(255,255,255,0.05);
        }}
        .feature-card:hover .icon-box {{ transform: scale(1.1) rotate(5deg); background: var(--primary); color: white; border-color: var(--primary); }}
        .feature-card h3 {{ font-size: 1.25rem; margin-bottom: 10px; }}
        .feature-card p {{ color: var(--text-muted); line-height: 1.6; }}

        /* Process */
        .process-section {{ background: #0b0f19; position: relative; }}
        .process-steps {{
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 30px;
            position: relative; margin-top: 60px;
        }}
        .process-steps::before {{
            content: ''; position: absolute; top: 40px; left: 50px; right: 50px; height: 2px;
            background: linear-gradient(90deg, var(--bg-card), var(--primary), var(--bg-card));
            z-index: 0; opacity: 0.3; width: 0; transition: width 1.5s ease;
        }}
        .process-steps.visible::before {{ width: calc(100% - 100px); }}
        
        .step-card {{
            position: relative; z-index: 1; background: var(--bg-card);
            border: 1px solid var(--border); border-radius: var(--radius);
            padding: 30px; text-align: center; transition: var(--transition);
            opacity: 0; transform: translateX(-30px);
        }}
        .step-card:hover {{ transform: translateY(-10px) scale(1.05); border-color: var(--primary); box-shadow: 0 10px 30px rgba(99, 102, 241, 0.15); }}
        .step-icon {{
            width: 80px; height: 80px; margin: 0 auto 20px; background: var(--bg-body);
            border: 2px solid var(--border); border-radius: 50%; display: flex;
            align-items: center; justify-content: center; font-size: 1.8rem;
            color: var(--primary); position: relative; z-index: 2; transition: var(--transition);
        }}
        .step-card:hover .step-icon {{ background: var(--primary); color: white; border-color: var(--primary); transform: rotateY(180deg); }}
        .step-card:hover .step-icon i {{ transform: rotateY(-180deg); }} 
        
        .step-num {{
            position: absolute; top: -5px; right: -5px; width: 30px; height: 30px;
            background: var(--accent); color: white; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-weight: bold;
            border: 4px solid var(--bg-card); box-shadow: 0 5px 15px rgba(236, 72, 153, 0.4);
        }}

        /* Стили Тарифа */
        .pro-pricing-card {{
            display: grid;
            grid-template-columns: 2fr 1fr; /* 2/3 под фичи, 1/3 под цену */
            background: var(--bg-card);
            border: 1px solid var(--primary); /* Сразу выделяем */
            border-radius: var(--radius);
            margin: 0 auto;
            max-width: 900px;
            overflow: hidden;
            box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.2);
            opacity: 0; 
            transform: scale(0.9); /* Для анимации */
        }}
        .pro-features {{
            padding: 50px;
        }}
        .pro-features h3 {{
            font-size: 1.8rem;
            margin-bottom: 30px;
            color: white;
        }}
        .pro-check-list {{
            list-style: none;
            text-align: left;
        }}
        .pro-check-list li {{
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 1.1rem;
            color: var(--text-muted);
            margin-bottom: 20px;
        }}
        .pro-check-list li i {{
            color: var(--accent);
            font-size: 1.3rem;
        }}
        .pro-check-list li span {{
            color: var(--text-main);
        }}
        .pro-check-list li i.fa-bolt {{ 
            color: #f59e0b; /* yellow */
        }}

        .pro-price-box {{
            background: linear-gradient(180deg, rgba(99, 102, 241, 0.05), var(--bg-card));
            border-left: 1px solid var(--border);
            padding: 50px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
        }}
        .pro-price-box .price {{
            font-size: 3.5rem; /* Крупнее */
            font-weight: 800;
            margin-bottom: 10px;
            color: white; /* Убедимся, что цвет белый */
        }}
        .pro-price-box .price span {{
            font-size: 1.1rem;
            color: var(--text-muted);
            font-weight: 400;
        }}
        .pro-price-box .price-note {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 30px;
            line-height: 1.4;
        }}
        .pro-price-box .btn {{
            width: 100%; /* Растянуть кнопку */
        }}


        /* FAQ */
        .faq-container {{ max-width: 800px; margin: 0 auto; }}
        .faq-item {{
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            margin-bottom: 15px; overflow: hidden; transition: all 0.3s ease;
            opacity: 0; transform: translateY(20px);
        }}
        .faq-item:hover {{ border-color: var(--primary); }}
        .faq-question {{
            padding: 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;
            font-weight: 600; font-size: 1.1rem; color: white; transition: background 0.3s;
        }}
        .faq-question:hover {{ background: rgba(255,255,255,0.02); }}
        .faq-question i {{ transition: transform 0.3s ease; color: var(--primary); }}
        .faq-answer {{
            max-height: 0; overflow: hidden; transition: max-height 0.3s ease;
            padding: 0 20px; color: var(--text-muted); font-size: 0.95rem; line-height: 1.6;
        }}
        .faq-item.active {{ border-color: var(--primary); box-shadow: 0 4px 20px rgba(99, 102, 241, 0.1); }}
        .faq-item.active .faq-question i {{ transform: rotate(180deg); color: var(--accent); }}
        .faq-item.active .faq-answer {{ padding-bottom: 20px; max-height: 200px; }}

        /* Contact */
        .contact-wrap {{ 
            background: var(--bg-card); padding: 50px; border-radius: var(--radius); 
            border: 1px solid var(--border); max-width: 600px; margin: 0 auto; 
            opacity: 0; transform: translateY(50px);
        }}
        .form-input {{
            width: 100%; padding: 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--border);
            border-radius: 10px; color: white; margin-bottom: 15px; font-family: var(--font); transition: 0.3s;
        }}
        .form-input:focus {{ outline: none; border-color: var(--primary); background: rgba(99, 102, 241, 0.05); transform: scale(1.02); }}
        .form-input.btn {{
            background: linear-gradient(135deg, var(--primary), var(--accent));
            box-shadow: 0 4px 20px -5px rgba(99, 102, 241, 0.5);
            width: 100%;
        }}
        
        input {{
            width: auto;
            padding: 0;
            margin-bottom: 0;
            border: none;
            border-radius: 0;
            background: none;
            color: inherit;
        }}
        /* Восстанавливаем стили для input и textarea в формах */
        .form-input, .container textarea {{
            width: 100%; padding: 14px; background: rgba(255,255,255,0.03); border: 1px solid var(--border);
            border-radius: 10px; color: white; margin-bottom: 15px; font-family: var(--font); transition: 0.3s;
        }}
        .form-input:focus, .container textarea:focus {{ 
            outline: none; border-color: var(--primary); background: rgba(99, 102, 241, 0.05); 
        }}
        .container textarea {{ min-height: 150px; line-height: 1.6; }}


        /* === ИЗМЕНЕНИЕ: Стили для модального окна === */
        .modal-overlay {{
            display: none; /* Скрыто по умолчанию */
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(10px);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }}
        .modal-content {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 40px;
            max-width: 700px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            /* Анимация появления */
            transform: scale(0.9);
            opacity: 0;
            transition: all 0.3s ease;
        }}
        .modal-overlay.visible {{
            display: flex;
        }}
        .modal-overlay.visible .modal-content {{
            transform: scale(1);
            opacity: 1;
        }}
        .modal-close-btn {{
            position: absolute;
            top: 15px; right: 20px;
            font-size: 2rem;
            color: var(--text-muted);
            cursor: pointer;
            transition: var(--transition);
        }}
        .modal-close-btn:hover {{
            color: var(--text-main);
            transform: rotate(90deg);
        }}
        /* Стили для контента внутри окна */
        .modal-body p {{
            margin-bottom: 15px;
            line-height: 1.7;
        }}
        .modal-body h1, .modal-body h2, .modal-body h3 {{
            color: var(--text-main);
            margin-bottom: 15px;
        }}
        .modal-body ul {{
            margin-left: 20px;
            margin-bottom: 15px;
        }}
        /* === КОНЕЦ СТИЛЕЙ МОДАЛЬНОГО ОКНА === */
        
        @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        
        .visible {{ opacity: 1 !important; transform: none !important; }}

        /* Мобильная навигация */
        @media (max-width: 1024px) {{ 
            .process-steps {{ grid-template-columns: repeat(2, 1fr); }} 
            .process-steps::before {{ display: none; }} 
        }}
        @media (max-width: 768px) {{ 
            .hero h1 {{ font-size: 2.5rem; }} 
            .process-steps {{ grid-template-columns: 1fr; }} 
            .nav-right {{ gap: 10px; }} 
            .nav-inner {{ 
                flex-wrap: wrap; 
                height: auto; 
                padding: 15px 0; 
            }}
            .nav-links {{ 
                order: 3; 
                width: 100%; 
                justify-content: center; 
                margin-top: 15px; 
                border-top: 1px solid var(--border); 
                padding-top: 15px; 
                gap: 20px; 
            }}
            .logo {{ order: 1; }}
            .nav-right {{ order: 2; }}
            
            .pro-pricing-card {{
                grid-template-columns: 1fr; /* Стек */
            }}
            .pro-price-box {{
                border-left: none;
                border-top: 1px solid var(--border);
            }}
            .pro-features {{ padding: 30px; }}
            .pro-price-box {{ padding: 40px 30px; }}
            .pro-check-list li {{ font-size: 1rem; }}
        }}
    </style>
</head>
<body>

    <nav class="navbar">
        <div class="container nav-inner">
            <a href="#" class="logo">
                <img src="/static/logo.png" alt="Restify Logo">
                Restify
            </a>
            
            <div class="nav-links">
                <a href="#features" data-i18n="nav_feat">Features</a>
                <a href="#process" data-i18n="nav_proc">Process</a>
                <a href="#pricing" data-i18n="nav_price">Pricing</a>
                <a href="#faq" data-i18n="nav_faq">FAQ</a>
                <a href="#contact" data-i18n="nav_contact">Contact</a>
                {custom_button_html}
            </div>

            <div class="nav-right">
                <div class="lang-dropdown">
                    <button class="lang-btn"><span class="flag" id="cur-flag">🇬🇧</span> <span id="cur-lang">EN</span> <i class="fa-solid fa-chevron-down" style="font-size: 0.7rem;"></i></button>
                    <div class="lang-menu">
                        <div class="lang-item" onclick="setLang('en')"><span class="flag">🇬🇧</span> English</div>
                        <div class="lang-item" onclick="setLang('uk')"><span class="flag">🇺🇦</span> Українська</div>
                        <div class="lang-item" onclick="setLang('ru')"><span class="flag">🇷🇺</span> Русский</div>
                        <div class="lang-item" onclick="setLang('ro')"><span class="flag">🇷🇴</span> Română</div>
                        <div class="lang-item" onclick="setLang('fr')"><span class="flag">🇫🇷</span> Français</div>
                        <div class="lang-item" onclick="setLang('es')"><span class="flag">🇪🇸</span> Español</div>
                        <div class="lang-item" onclick="setLang('it')"><span class="flag">🇮🇹</span> Italiano</div>
                    </div>
                </div>
                <a href="/login" class="btn btn-outline login-btn" style="padding: 8px 20px; font-size: 0.9rem;" data-i18n="login">Login</a>
            </div>
        </div>
    </nav>

    <section class="hero">
        <div class="hero-bg" id="hero-bg"></div>
        <div class="container hero-content">
            <h1 data-i18n="title" style="margin-top: 40px;">Your Restaurant in Smartphone <br><span class="gradient-text">Turnkey Automation</span></h1>
            <p data-i18n="subtitle">Own delivery system, QR-menu for dine-in, and staff management. No commissions. Instant project launch.</p>
            <div class="hero-btns">
                <a href="/register" class="btn btn-primary" data-i18n="btn_start">Start Project</a>
                <a href="#process" class="btn btn-outline" data-i18n="btn_how">How it works?</a>
            </div>
        </div>
    </section>

    <section id="features" class="section">
        <div class="container">
            <div class="section-header">
                <h2 data-i18n="feat_h">A Complete Ecosystem</h2>
                <p data-i18n="feat_sub">Four key modules for full automation of your restaurant.</p>
            </div>
            <div class="grid-3">
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-solid fa-store"></i></div>
                    <h3 data-i18n="f1_t">Multi-Channel Orders</h3>
                    <p data-i18n="f1_d">Website and Telegram bot for delivery and pickup orders.</p>
                </div>
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-solid fa-qrcode"></i></div>
                    <h3 data-i18n="f2_t">QR-Menu for Dine-In</h3>
                    <p data-i18n="f2_d">Guest can scan QR, call waiter, ask for bill, or send order to kitchen.</p>
                </div>
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-brands fa-telegram"></i></div>
                    <h3 data-i18n="f3_t">Mobile Hub for Staff</h3>
                    <p data-i18n="f3_d">Waiters and couriers manage orders directly in their Telegram bot.</p>
                </div>
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-solid fa-laptop-code"></i></div>
                    <h3 data-i18n="f4_t">Powerful Admin Panel</h3>
                    <p data-i18n="f4_d">Full management of menu, clients (CRM), staff, and site design.</p>
                </div>
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-solid fa-users-gear"></i></div>
                    <h3 data-i18n="f5_t">Flexible Roles & Shifts</h3>
                    <p data-i18n="f5_d">Assign roles (Courier, Waiter) and track who is on shift.</p>
                </div>
                <div class="feature-card stagger-card">
                    <div class="icon-box"><i class="fa-solid fa-paint-roller"></i></div>
                    <h3 data-i18n="f6_t">Branding & Customization</h3>
                    <p data-i18n="f6_d">Change colors, logos, and fonts directly from the admin panel.</p>
                </div>
            </div>
        </div>
    </section>

    <section id="process" class="process-section section">
        <div class="container">
            <div class="section-header">
                <h2 data-i18n="proc_h">Order Process</h2>
                <p data-i18n="proc_sub">Automated path from guest to staff.</p>
            </div>
            <div class="process-steps">
                <div class="step-card">
                    <div class="step-icon"><i class="fa-solid fa-mobile-screen"></i></div>
                    <div class="step-num">1</div>
                    <h3 data-i18n="s1_t">Choice</h3>
                    <p data-i18n="s1_d">Guest scans QR or enters bot. Views menu.</p>
                </div>
                <div class="step-card">
                    <div class="step-icon"><i class="fa-solid fa-cart-shopping"></i></div>
                    <div class="step-num">2</div>
                    <h3 data-i18n="s2_t">Order</h3>
                    <p data-i18n="s2_d">Places order, selects payment and delivery.</p>
                </div>
                <div class="step-card">
                    <div class="step-icon"><i class="fa-solid fa-server"></i></div>
                    <div class="step-num">3</div>
                    <h3 data-i18n="s3_t">System</h3>
                    <p data-i18n="s3_d">Order created in Admin and saved to DB.</p>
                </div>
                <div class="step-card">
                    <div class="step-icon"><i class="fa-solid fa-bell"></i></div>
                    <div class="step-num">4</div>
                    <h3 data-i18n="s4_t">Notification</h3>
                    <p data-i18n="s4_d">Staff gets instant Telegram message.</p>
                </div>
            </div>
        </div>
    </section>

    <section id="pricing" class="section">
        <div class="container">
            <div class="section-header">
                <h2 data-i18n="price_h">All-Inclusive Plan</h2>
                <p data-i18n="price_sub">Get all features for one monthly price.</p>
            </div>
            
            <div class="pro-pricing-card stagger-card">
                <div class="pro-features">
                    <h3 data-i18n="p2_t">Pro System</h3>
                    <ul class="pro-check-list">
                        <li><i class="fa-solid fa-check"></i> <span data-i18n="p2_1">Telegram Bot + Website</span></li>
                        <li><i class="fa-solid fa-check"></i> <span data-i18n="p2_2">QR-Menu (In-House)</span></li>
                        <li><i class="fa-solid fa-check"></i> <span data-i18n="p2_3">Staff & Courier Apps</span></li>
                        <li><i class="fa-solid fa-check"></i> <span data-i18n="p2_4">Advanced CRM & Stats</span></li>
                        <li><i class="fa-solid fa-bolt"></i> <span data-i18n="p2_5">Instant project launch</span></li>
                    </ul>
                </div>
                
                <div class="pro-price-box">
                    <div class="price">
                        {config['currency']}{config['price_full']}
                        <span>/ <span data-i18n="month">month</span></span>
                    </div>
                    <p class="price-note" data-i18n="price_note">Price is set in the admin panel</p>
                    <a href="/register" class="btn btn-primary" data-i18n="btn_ord">Order Pro</a>
                </div>
            </div>
        </div>
    </section>

    <section id="faq" class="section" style="background: #0b0f19;">
        <div class="container">
            <div class="section-header">
                <h2 data-i18n="faq_h">Common Questions</h2>
            </div>
            <div class="faq-container">
                <div class="faq-item stagger-card">
                    <div class="faq-question" onclick="toggleFaq(this)">
                        <span data-i18n="faq_q1">Do I need expensive hardware?</span>
                        <i class="fa-solid fa-chevron-down"></i>
                    </div>
                    <div class="faq-answer">
                        <p data-i18n="faq_a1">No, the system works on any smartphone or tablet. You don't need to buy expensive POS terminals. Everything is in the cloud.</p>
                    </div>
                </div>
                <div class="faq-item stagger-card">
                    <div class="faq-question" onclick="toggleFaq(this)">
                        <span data-i18n="faq_q2">How fast is the launch?</span>
                        <i class="fa-solid fa-chevron-down"></i>
                    </div>
                    <div class="faq-answer">
                        <p data-i18n="faq_a2">Launch is instant. After registration and filling in the data, your project is immediately ready to work.</p>
                    </div>
                </div>
                <div class="faq-item stagger-card">
                    <div class="faq-question" onclick="toggleFaq(this)">
                        <span data-i18n="faq_q3">Can I update the menu myself?</span>
                        <i class="fa-solid fa-chevron-down"></i>
                    </div>
                    <div class="faq-answer">
                        <p data-i18n="faq_a3">Yes, you get a full Admin Panel where you can change prices, add dishes, and manage staff instantly.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="contact" class="section contact-section">
        <div class="container">
            <div class="section-header">
                <h2 data-i18n="form_h">Discuss Project</h2>
                <p data-i18n="form_sub">Leave a request, we will contact you.</p>
            </div>
            <div class="contact-wrap">
                <form id="leadForm">
                    <label style="display:block; margin-bottom:8px; color:var(--text-muted); font-size:0.9rem;" data-i18n="lbl_name">Your Name</label>
                    <input type="text" name="name" class="form-input" required>
                    
                    <label style="display:block; margin-bottom:8px; color:var(--text-muted); font-size:0.9rem;" data-i18n="lbl_phone">Phone / Telegram</label>
                    <input type="text" name="phone" class="form-input" required>
                    
                    <label style="display:block; margin-bottom:8px; color:var(--text-muted); font-size:0.9rem;" data-i18n="lbl_int">Interest</label>
                    <select name="interest" class="form-input" style="background: var(--bg-body);">
                        <option value="Pro">Pro System</option>
                        <option value="Consultation">Consultation</option>
                    </select>
                    
                    <button type="submit" class="btn btn-primary form-input" data-i18n="btn_send">Send Request</button>
                    <div id="leadResponse" style="text-align: center; margin-top: 15px;"></div>
                </form>
            </div>
        </div>
    </section>

    <footer style="text-align: center; padding: 40px 0; color: var(--text-muted); border-top: 1px solid var(--border); margin-top: 50px;">
        <p>&copy; 2025 Restify. <span data-i18n="foot">IT Solutions for HoReCa.</span></p>
    </footer>

    <div id="customModal" class="modal-overlay">
        <div class="modal-content">
            <span id="custom-modal-close-btn" class="modal-close-btn">&times;</span>
            <div class="modal-body">
                {modal_content_html}
            </div>
        </div>
    </div>
    <script>
        // === ИЗМЕНЕНИЕ: Обновлен блок i18n ===
        const flags = {{
            en: "🇬🇧", uk: "🇺🇦", ru: "🇷🇺", ro: "🇷🇴", 
            fr: "🇫🇷", es: "🇪🇸", it: "🇮🇹"
        }};
        
        const i18n = {{
            en: {{
                nav_feat: "Features", nav_proc: "Process", nav_price: "Pricing", nav_faq: "FAQ", nav_contact: "Contact", login: "Login",
                title: "Your Restaurant in Smartphone <br><span class='gradient-text'>Turnkey Automation</span>",
                subtitle: "Own delivery system, QR-menu for dine-in, and staff management. No commissions. Instant project launch.",
                btn_start: "Start Project", btn_how: "How it works?",
                feat_h: "A Complete Ecosystem", feat_sub: "Four key modules for full automation of your restaurant.",
                f1_t: "Multi-Channel Orders", f1_d: "Website and Telegram bot for delivery and pickup orders.",
                f2_t: "QR-Menu for Dine-In", f2_d: "Guest can scan QR, call waiter, ask for bill, or send order to kitchen.",
                f3_t: "Mobile Hub for Staff", f3_d: "Waiters and couriers manage orders directly in their Telegram bot.",
                f4_t: "Powerful Admin Panel", f4_d: "Full management of menu, clients (CRM), staff, and site design.",
                f5_t: "Flexible Roles & Shifts", f5_d: "Assign roles (Courier, Waiter) and track who is on shift.",
                f6_t: "Branding & Customization", f6_d: "Change colors, logos, and fonts directly from the admin panel.",
                proc_h: "Order Process", proc_sub: "Automated path from guest to staff.",
                s1_t: "Choice", s1_d: "Guest scans QR or enters bot. Views menu.",
                s2_t: "Order", s2_d: "Places order, selects payment and delivery.",
                s3_t: "System", s3_d: "Order created in Admin and saved to DB.",
                s4_t: "Notification", s4_d: "Staff gets instant Telegram message.",
                price_h: "All-Inclusive Plan", price_sub: "Get all features for one monthly price.",
                p2_t: "Pro System", p2_1: "Telegram Bot + Website", p2_2: "QR-Menu (In-House)", p2_3: "Staff & Courier Apps", p2_4: "Advanced CRM & Stats", p2_5: "Instant project launch",
                btn_ord: "Order Pro", month: "month", price_note: "Price is set in the admin panel",
                faq_h: "Common Questions",
                faq_q1: "Do I need expensive hardware?", faq_a1: "No, the system works on any smartphone or tablet. You don't need to buy expensive POS terminals. Everything is in the cloud.",
                faq_q2: "How fast is the launch?", faq_a2: "Launch is instant. After registration and filling in the data, your project is immediately ready to work.",
                faq_q3: "Can I update the menu myself?", faq_a3: "Yes, you get a full Admin Panel where you can change prices, add dishes, and manage staff instantly.",
                form_h: "Discuss Project", form_sub: "Leave a request, we will contact you.",
                lbl_name: "Your Name", lbl_phone: "Phone / Telegram", lbl_int: "Interest", btn_send: "Send Request",
                foot: "IT Solutions for HoReCa."
            }},
            uk: {{
                nav_feat: "Переваги", nav_proc: "Процес", nav_price: "Тариф", nav_faq: "FAQ", nav_contact: "Контакти", login: "Увійти",
                title: "Ваш ресторан у смартфоні <br><span class='gradient-text'>Автоматизація під ключ</span>",
                subtitle: "Власна система доставки, QR-меню для залу та управління персоналом. Без комісій. Миттєвий запуск проекту.",
                btn_start: "Почати проект", btn_how: "Як це працює?",
                feat_h: "Повноцінна Екосистема", feat_sub: "Чотири ключові модулі для повної автоматизації вашого ресторану.",
                f1_t: "Прийом Замовлень", f1_d: "Веб-сайт та Telegram-бот для прийому замовлень на доставку та самовивіз.",
                f2_t: "QR-Меню в Залі", f2_d: "Гість сканує QR, викликає офіціанта, просить рахунок або сам відправляє замовлення на кухню.",
                f3_t: "Хаб для Персоналу", f3_d: "Офіціанти та кур'єри керують замовленнями прямо у своєму Telegram-боті.",
                f4_t: "Потужна Веб-Панель", f4_d: "Повне керування меню, клієнтами (CRM), персоналом та дизайном сайту.",
                f5_t: "Гнучкі Ролі та Зміни", f5_d: "Призначайте ролі (Кур'єр, Офіціант) та відстежуйте, хто на зміні.",
                f6_t: "Брендинг та Кастомізація", f6_d: "Змінюйте кольори, логотипи та шрифти прямо з адмін-панелі.",
                proc_h: "Як відбувається замовлення?", proc_sub: "Автоматизований шлях від гостя до персоналу.",
                s1_t: "Вибір", s1_d: "Гість сканує QR або заходить у бот. Бачить меню.",
                s2_t: "Замовлення", s2_d: "Оформляє замовлення, обирає оплату та доставку.",
                s3_t: "Система", s3_d: "Замовлення створюється в Адмінці та зберігається в базі.",
                s4_t: "Сповіщення", s4_d: "Персонал отримує миттєве повідомлення в Telegram.",
                price_h: "Єдиний Тариф", price_sub: "Отримайте всі функції за єдину місячну плату.",
                p2_t: "Pro System", p2_1: "Telegram Бот + Веб-сайт", p2_2: "QR-Меню (в залі)", p2_3: "Додатки для персоналу", p2_4: "Розширена CRM та статистика", p2_5: "Миттєвий запуск проекту",
                btn_ord: "Замовити Pro", month: "місяць", price_note: "Вартість налаштовується в адмін-панелі",
                faq_h: "Часті запитання",
                faq_q1: "Чи потрібне дороге обладнання?", faq_a1: "Ні, система працює на будь-якому смартфоні чи планшеті. Не потрібно купувати дорогі POS-термінали.",
                faq_q2: "Як швидко запуск?", faq_a2: "Запуск миттєвий. Після реєстрації та заповнення даних ваш проект одразу готовий до роботи.",
                faq_q3: "Чи можу я змінювати меню?", faq_a3: "Так, у вас є повна Адмін-панель, де ви можете змінювати ціни, додавати страви та керувати персоналом.",
                form_h: "Обговорити проект", form_sub: "Залиште заявку, ми зв'яжемося з вами.",
                lbl_name: "Ваше Ім'я", lbl_phone: "Телефон / Telegram", lbl_int: "Інтерес", btn_send: "Відправити заявку",
                foot: "IT рішення для HoReCa."
            }},
            ru: {{
                nav_feat: "Возможности", nav_proc: "Процесс", nav_price: "Тариф", nav_faq: "FAQ", nav_contact: "Контакты", login: "Вход",
                title: "Ваш ресторан в смартфоне <br><span class='gradient-text'>Автоматизация под ключ</span>",
                subtitle: "Собственная система доставки, QR-меню для зала и управление персоналом. Без комиссий. Моментальный запуск проекта.",
                btn_start: "Начать проект", btn_how: "Как это работает?",
                feat_h: "Полноценная Экосистема", feat_sub: "Четыре ключевых модуля для полной автоматизации вашего ресторана.",
                f1_t: "Прием Заказов", f1_d: "Веб-сайт и Telegram-бот для приема заказов на доставку и самовывоз.",
                f2_t: "QR-Меню в Зале", f2_d: "Гость сканирует QR, вызывает официанта, просит счет или отправляет заказ на кухню.",
                f3_t: "Хаб для Персонала", f3_d: "Официанты и курьеры управляют заказами прямо в своем Telegram-боте.",
                f4_t: "Мощная Админ-Панель", f4_d: "Полное управление меню, клиентами (CRM), персоналом и дизайном сайта.",
                f5_t: "Гибкие Роли и Смены", f5_d: "Назначайте роли (Курьер, Официант) и отслеживайте, кто на смене.",
                f6_t: "Брендинг и Настройка", f6_d: "Меняйте цвета, логотипы и шрифты прямо из админ-панели.",
                proc_h: "Процесс Заказа", proc_sub: "Автоматизированный путь от гостя до персонала.",
                s1_t: "Выбор", s1_d: "Гость сканирует QR или заходит в бот. Видит меню.",
                s2_t: "Заказ", s2_d: "Оформляет заказ, выбирает оплату и доставку.",
                s3_t: "Система", s3_d: "Заказ создается в Админке и сохраняется в базе.",
                s4_t: "Уведомление", s4_d: "Персонал получает мгновенное сообщение в Telegram.",
                price_h: "Единый Тариф", price_sub: "Получите все функции за единую месячную плату.",
                p2_t: "Pro System", p2_1: "Telegram Бот + Веб-сайт", p2_2: "QR-Меню (в зале)", p2_3: "Приложения для персонала", p2_4: "Расширенная CRM и статистика", p2_5: "Моментальный запуск проекта",
                btn_ord: "Заказать Pro", month: "месяц", price_note: "Стоимость настраивается в админ-панели",
                faq_h: "Частые Вопросы",
                faq_q1: "Нужно ли дорогое оборудование?", faq_a1: "Нет, система работает на любом смартфоне или планшете. Не нужно покупать дорогие POS-терминалы. Все в облаке.",
                faq_q2: "Как быстро происходит запуск?", faq_a2: "Запуск моментальный. После регистрации и заполнения данных ваш проект сразу готов к работе.",
                faq_q3: "Я могу сам обновлять меню?", faq_a3: "Да, вы получаете полную Админ-панель, где можете мгновенно менять цены, добавлять блюда и управлять персоналом.",
                form_h: "Обсудить проект", form_sub: "Оставьте заявку, мы свяжемся с вами.",
                lbl_name: "Ваше Имя", lbl_phone: "Телефон / Telegram", lbl_int: "Интерес", btn_send: "Отправить заявку",
                foot: "IT-решения для HoReCa."
            }},
            ro: {{
                nav_feat: "Avantaje", nav_proc: "Proces", nav_price: "Preț", nav_faq: "FAQ", nav_contact: "Contact", login: "Intrare",
                title: "Restaurantul tău în smartphone <br><span class='gradient-text'>Automatizare la cheie</span>",
                subtitle: "Sistem propriu de livrare, meniu QR și gestionare personal. Fără comisioane. Lansare instantanee a proiectului.",
                btn_start: "Începe", btn_how: "Cum funcționează?",
                feat_h: "Ecosistem Complet", feat_sub: "Patru module cheie pentru automatizarea completă.",
                f1_t: "Comenzi Multi-Canal", f1_d: "Site web și bot Telegram pentru comenzi de livrare și preluare.",
                f2_t: "Meniu QR", f2_d: "Oaspetele scanează QR, cheamă chelnerul, cere nota sau trimite comanda.",
                f3_t: "Hub Mobil Personal", f3_d: "Chelnerii și curierii gestionează comenzile direct în Telegram.",
                f4_t: "Panou Admin Puternic", f4_d: "Management complet al meniului, clienților (CRM), personalului și designului.",
                f5_t: "Roluri Flexibile", f5_d: "Atribuiți roluri (Curier, Chelner) și urmăriți cine este în tură.",
                f6_t: "Branding", f6_d: "Schimbați culorile, logo-urile și fonturile din panoul de administrare.",
                proc_h: "Procesul de comandă", proc_sub: "Automatizat de la oaspete la personal.",
                s1_t: "Alegere", s1_d: "Oaspetele scanează QR або intră în bot.",
                s2_t: "Comandă", s2_d: "Face comanda, alege plata.",
                s3_t: "Sistem", s3_d: "Comanda apare în Admin și bază.",
                s4_t: "Notificare", s4_d: "Personalul primește mesaj instant.",
                price_h: "Plan Unic", price_sub: "Obțineți toate funcțiile la un singur preț lunar.",
                p2_t: "Pro System", p2_1: "Bot Telegram + Site", p2_2: "Meniu QR", p2_3: "Aplicații Personal", p2_4: "CRM Avansat", p2_5: "Lansare instantanee a proiectului",
                btn_ord: "Comandă Pro", month: "lună", price_note: "Prețul este stabilit în panoul de administrare",
                faq_h: "Întrebări frecvente",
                faq_q1: "Trebuie echipament scump?", faq_a1: "Nu, sistemul funcționează pe orice telefon. Nu ai nevoie de terminale POS scumpe.",
                faq_q2: "Cât durează lansarea?", faq_a2: "Lansarea este instantanee. După înregistrare și completarea datelor, proiectul dvs. este imediat gata de lucru.",
                faq_q3: "Pot schimba meniul?", faq_a3: "Da, ai panou Admin complet pentru a gestiona prețurile și personalul.",
                form_h: "Discută proiectul", form_sub: "Lasă o cerere, te contactăm.",
                lbl_name: "Nume", lbl_phone: "Telefon", lbl_int: "Interes", btn_send: "Trimite",
                foot: "Soluții IT HoReCa."
            }},
            fr: {{
                nav_feat: "Fonctions", nav_proc: "Processus", nav_price: "Tarif", nav_faq: "FAQ", nav_contact: "Contact", login: "Connexion",
                title: "Votre Restaurant sur Smartphone <br><span class='gradient-text'>Automatisation</span>",
                subtitle: "Système de livraison, menu QR et gestion du personnel. Sans commissions. Lancement instantané du projet.",
                btn_start: "Commencer", btn_how: "Comment ça marche?",
                feat_h: "Écosystème Complet", feat_sub: "Quatre modules clés pour une automatisation complète.",
                f1_t: "Commandes Multi-Canaux", f1_d: "Site web et bot Telegram pour les commandes à livrer et à emporter.",
                f2_t: "Menu QR sur Place", f2_d: "Le client scanne le QR, appelle le serveur, demande l'addition ou envoie la commande.",
                f3_t: "Hub Mobil pour Staff", f3_d: "Les serveurs et coursiers gèrent les commandes dans Telegram.",
                f4_t: "Panel Admin Puissant", f4_d: "Gestion complète du menu, des clients (CRM), du personnel et du design.",
                f5_t: "Rôles & Services Flexibles", f5_d: "Attribuez des rôles (Coursier, Serveur) et suivez qui est en service.",
                f6_t: "Branding & Personnalisation", f6_d: "Modifiez les couleurs, logos et polices depuis le panel admin.",
                proc_h: "Processus", proc_sub: "Automatisé.",
                s1_t: "Choix", s1_d: "Client scanne QR.",
                s2_t: "Commande", s2_d: "Client valide.",
                s3_t: "Traitement", s3_d: "Système enregistre.",
                s4_t: "Notification", s4_d: "Staff informé.",
                price_h: "Plan Unique", price_sub: "Obtenez toutes les fonctionnalités pour un seul prix mensuel.",
                p2_t: "Système Pro", p2_1: "Bot + Site Web", p2_2: "Menu QR", p2_3: "Apps Staff", p2_4: "CRM Avancé", p2_5: "Lancement instantané du projet",
                btn_ord: "Commander", month: "mois", price_note: "Le prix est défini dans le panneau d'administration",
                faq_h: "FAQ",
                faq_q1: "Matériel coûteux ?", faq_a1: "Non, tout smartphone.",
                faq_q2: "Délai ?", faq_a2: "Le lancement est instantané. Après l'inscription et la saisie des données, votre projet est immédiatement prêt à fonctionner.",
                faq_q3: "Modifier menu ?", faq_a3: "Oui, via Admin.",
                form_h: "Contactez-nous", form_sub: "Envoyez une demande.",
                lbl_name: "Nom", lbl_phone: "Téléphone", lbl_int: "Intérêt", btn_send: "Envoyer",
                foot: "Solutions HoReCa."
            }},
            es: {{
                nav_feat: "Funciones", nav_proc: "Proceso", nav_price: "Precio", nav_faq: "FAQ", nav_contact: "Contacto", login: "Entrar",
                title: "Tu Restaurante en Smartphone <br><span class='gradient-text'>Automatización</span>",
                subtitle: "Sistema de entrega, menú QR y gestión de personal. Sin comisiones. Lanzamiento instantáneo del proyecto.",
                btn_start: "Empezar", btn_how: "¿Cómo funciona?",
                feat_h: "Ecosistema Completo", feat_sub: "Cuatro módulos clave para la automatización total.",
                f1_t: "Pedidos Multicanal", f1_d: "Sitio web y bot de Telegram para pedidos de entrega y recogida.",
                f2_t: "Menú QR en Local", f2_d: "El cliente escanea QR, llama al camarero, pide la cuenta o envía el pedido.",
                f3_t: "Hub Móvil Personal", f3_d: "Camareros y repartidores gestionan pedidos en Telegram.",
                f4_t: "Potente Panel Admin", f4_d: "Gestión total de menú, clientes (CRM), personal y diseño.",
                f5_t: "Roles y Turnos Flexibles", f5_d: "Asigna roles (Repartidor, Camarero) y sigue quién está de turno.",
                f6_t: "Branding", f6_d: "Cambia colores, logos y fuentes desde el panel de admin.",
                proc_h: "Proceso", proc_sub: "Automatizado.",
                s1_t: "Elección", s1_d: "Cliente escanea QR.",
                s2_t: "Pedido", s2_d: "Cliente confirma.",
                s3_t: "Procesamiento", s3_d: "Sistema guarda.",
                s4_t: "Notificación", s4_d: "Personal informado.",
                price_h: "Plan Único", price_sub: "Obtenga todas las funciones por un único precio mensual.",
                p2_t: "Sistema Pro", p2_1: "Bot + Web", p2_2: "Menú QR", p2_3: "Apps Personal", p2_4: "CRM Avanzado", p2_5: "Lanzamiento instantáneo del proyecto",
                btn_ord: "Pedir", month: "mes", price_note: "El precio se establece en el panel de administración",
                faq_h: "Preguntas",
                faq_q1: "¿Hardware caro?", faq_a1: "No, cualquier móvil.",
                faq_q2: "¿Tiempo?", faq_a2: "El lanzamiento es instantáneo. Después de registrarse e ingresar los datos, su proyecto está listo para funcionar de inmediato.",
                faq_q3: "¿Editar menú?", faq_a3: "Sí, panel completo.",
                form_h: "Hablemos", form_sub: "Envía solicitud.",
                lbl_name: "Nombre", lbl_phone: "Teléfono", lbl_int: "Interés", btn_send: "Enviar",
                foot: "Soluciones HoReCa."
            }},
            it: {{
                nav_feat: "Funzioni", nav_proc: "Processo", nav_price: "Prezzo", nav_faq: "FAQ", nav_contact: "Contatto", login: "Entra",
                title: "Il tuo Ristorante su Smartphone <br><span class='gradient-text'>Automazione</span>",
                subtitle: "Sistema di consegna, menu QR e gestione del personale. Senza commissioni. Avvio immediato del progetto.",
                btn_start: "Inizia", btn_how: "Come funziona?",
                feat_h: "Ecosistema Completo", feat_sub: "Quattro moduli chiave per l'automazione completa.",
                f1_t: "Ordini Multicanale", f1_d: "Sito web e bot Telegram per ordini di consegna e ritiro.",
                f2_t: "Menu QR", f2_d: "Il cliente scansiona QR, chiama il cameriere, chiede il conto o invia l'ordine.",
                f3_t: "Hub Mobile Staff", f3_d: "Camerieri e rider gestiscono gli ordini su Telegram.",
                f4_t: "Pannello Admin", f4_d: "Gestione completa di menu, clienti (CRM), staff e design.",
                f5_t: "Ruoli e Turni Flessibili", f5_d: "Assegna ruoli (Rider, Cameriere) e traccia chi è in turno.",
                f6_t: "Branding", f6_d: "Modifica colori, loghi e font dal pannello di amministrazione.",
                proc_h: "Processo", proc_sub: "Automatizzato.",
                s1_t: "Scelta", s1_d: "Cliente scansiona QR.",
                s2_t: "Ordine", s2_d: "Cliente conferma.",
                s3_t: "Elaborazione", s3_d: "Sistema salva.",
                s4_t: "Notifica", s4_d: "Staff informato.",
                price_h: "Piano Unico", price_sub: "Ottieni tutte le funzionalità a un unico prezzo mensile.",
                p2_t: "Sistema Pro", p2_1: "Bot + Sito", p2_2: "Menu QR", p2_3: "App Staff", p2_4: "CRM Avanzato", p2_5: "Avvio immediato del progetto",
                btn_ord: "Ordinare", month: "mese", price_note: "Il prezzo è impostato nel pannello di amministrazione",
                faq_h: "Domande",
                faq_q1: "Hardware costoso?", faq_a1: "No, qualsiasi smartphone.",
                faq_q2: "Tempo?", faq_a2: "L'avvio è immediato. Dopo la registrazione e l'inserimento dei dati, il tuo progetto è subito pronto per funzionare.",
                faq_q3: "Modificare menu?", faq_a3: "Sì, pannello admin.",
                form_h: "Parliamone", form_sub: "Invia richiesta.",
                lbl_name: "Nome", lbl_phone: "Telefono", lbl_int: "Interesse", btn_send: "Inviare",
                foot: "Soluzioni HoReCa."
            }}
        }};
        // === КОНЕЦ БЛОКА i18n ===

        function setLang(lang) {{
            localStorage.setItem('restify_lang', lang);
            document.getElementById('cur-lang').innerText = lang.toUpperCase();
            document.getElementById('cur-flag').innerText = flags[lang];
            const t = i18n[lang] || i18n.en;
            for (const key in t) {{
                const el = document.querySelector(`[data-i18n="${{key}}"]`);
                if (el) el.innerHTML = t[key];
            }}
        }}
        const savedLang = localStorage.getItem('restify_lang') || 'ru'; // По умолчанию русский
        setLang(savedLang);

        const observerOptions = {{ threshold: 0.1 }}; 
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('visible');
                    if (entry.target.classList.contains('process-steps')) {{
                        const steps = entry.target.querySelectorAll('.step-card');
                        steps.forEach((step, index) => {{
                            setTimeout(() => {{ step.classList.add('visible'); }}, index * 200);
                        }});
                    }}
                    
                    if (entry.target.classList.contains('grid-3') || entry.target.classList.contains('faq-container') || entry.target.classList.contains('pro-pricing-card')) {{
                        const cards = entry.target.querySelectorAll('.stagger-card, .faq-item');
                        if (cards.length > 0) {{
                             cards.forEach((card, index) => {{
                                setTimeout(() => {{ card.classList.add('visible'); }}, index * 150);
                            }});
                        }} else {{
                            // Для одиночной карты тарифа
                            entry.target.classList.add('visible');
                        }}
                    }}
                }}
            }});
        }}, observerOptions);

        document.querySelectorAll('.section-header, .contact-wrap, .process-steps, .grid-3, .faq-container, .pro-pricing-card').forEach(el => observer.observe(el));
        
        document.addEventListener('mousemove', (e) => {{
            const x = (window.innerWidth - e.pageX) / 50;
            const y = (window.innerHeight - e.pageY) / 50;
            const bg = document.getElementById('hero-bg');
            if(bg) bg.style.transform = `translate(${{x}}px, ${{y}}px)`;
        }});
        document.querySelectorAll('.feature-card').forEach(card => {{
            card.addEventListener('mousemove', e => {{
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty('--x', `${{x}}px`);
                card.style.setProperty('--y', `${{y}}px`);
            }});
        }});
        
        document.querySelectorAll('.tilt-card').forEach(card => {{
            card.addEventListener('mousemove', e => {{
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = ((y - centerY) / centerY) * -5;
                const rotateY = ((x - centerX) / centerX) * 5;
                card.style.transform = `perspective(1000px) rotateX(${{rotateX}}deg) rotateY(${{rotateY}}deg) scale(1.05)`;
            }});
            card.addEventListener('mouseleave', () => {{
                card.style.transform = `perspective(1000px) rotateX(0) rotateY(0) scale(1)`;
            }});
        }});

        function toggleFaq(element) {{
            const item = element.parentElement;
            item.classList.toggle('active');
        }}

        document.getElementById('leadForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const oldText = btn.innerText;
            const responseEl = document.getElementById('leadResponse');
            btn.innerText = '...'; btn.disabled = true;
            responseEl.style.color = 'var(--text-muted)';
            responseEl.innerText = 'Отправка...';
            const formData = new FormData(e.target);
            try {{
                const response = await fetch('/api/lead', {{ method: 'POST', body: formData }});
                if (response.ok) {{
                    responseEl.style.color = 'var(--accent)';
                    responseEl.innerText = 'Успешно! Мы скоро свяжемся с вами.';
                    e.target.reset();
                }} else {{
                    throw new Error('Server error');
                }}
            }} catch(e) {{ 
                responseEl.style.color = '#f87171';
                responseEl.innerText = 'Ошибка. Попробуйте позже.';
            }}
            btn.innerText = oldText; btn.disabled = false;
        }});
        
        // === ИЗМЕНЕНИЕ: JS для модального окна ===
        const modalBtn = document.getElementById('custom-modal-btn');
        const modal = document.getElementById('customModal');
        const closeModalBtn = document.getElementById('custom-modal-close-btn');

        if (modalBtn && modal && closeModalBtn) {{
            // Открыть окно по клику на кнопку в меню
            modalBtn.addEventListener('click', (e) => {{
                e.preventDefault();
                modal.classList.add('visible');
            }});
            
            // Закрыть окно по клику на "крестик"
            closeModalBtn.addEventListener('click', () => {{
                modal.classList.remove('visible');
            }});
            
            // Закрыть окно по клику на темный фон
            modal.addEventListener('click', (e) => {{
                if (e.target === modal) {{
                    modal.classList.remove('visible');
                }}
            }});
        }}
        // === КОНЕЦ JS ===
    </script>
</body>
</html>
    """