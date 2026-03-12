import json

def get_courier_login_page(message=None):
    msg_html = f"<div class='error-msg'>{message}</div>" if message else ""
    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Вхід для Кур'єрів | Restify</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --bg: #0f172a; --panel: #1e293b; --text: #f8fafc; --primary: #3b82f6; }}
            body {{
                margin: 0; padding: 0; background-color: var(--bg); color: var(--text);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex; justify-content: center; align-items: center; min-height: 100vh;
            }}
            .login-container {{
                background: var(--panel); padding: 30px; border-radius: 16px;
                width: 90%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                box-sizing: border-box;
            }}
            h1 {{ text-align: center; margin-top: 0; color: var(--primary); }}
            p.subtitle {{ text-align: center; color: #94a3b8; margin-bottom: 25px; }}
            .input-group {{ margin-bottom: 15px; }}
            .input-group label {{ display: block; margin-bottom: 5px; color: #cbd5e1; font-size: 0.9rem; }}
            .input-group input {{
                width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155;
                background: #0f172a; color: white; box-sizing: border-box; font-size: 1rem;
            }}
            .input-group input:focus {{ outline: none; border-color: var(--primary); }}
            .btn {{
                width: 100%; padding: 14px; background: var(--primary); color: white;
                border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold;
                cursor: pointer; margin-top: 10px; transition: background 0.3s;
            }}
            .btn:hover {{ background: #2563eb; }}
            .error-msg {{
                background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #ef4444;
                padding: 10px; border-radius: 8px; margin-bottom: 15px; text-align: center;
                font-size: 0.9rem;
            }}
            .links {{ text-align: center; margin-top: 20px; font-size: 0.9rem; }}
            .links a {{ color: var(--primary); text-decoration: none; }}
            .links a:hover {{ text-decoration: underline; }}
            
            /* Скидання пароля */
            .reset-btn {{
                background: none; border: none; color: #94a3b8; cursor: pointer;
                font-size: 0.85rem; padding: 0; text-decoration: underline; margin-top: 15px;
                display: block; width: 100%; text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1><i class="fa-solid fa-motorcycle"></i> Restify Кур'єр</h1>
            <p class="subtitle">Увійдіть, щоб почати доставку</p>
            {msg_html}
            <form action="/api/courier/login" method="post">
                <div class="input-group">
                    <label>Номер телефону</label>
                    <input type="tel" name="phone" placeholder="+380..." required>
                </div>
                <div class="input-group">
                    <label>Пароль</label>
                    <input type="password" name="password" placeholder="Ваш пароль" required>
                </div>
                <button type="submit" class="btn">Увійти</button>
            </form>
            
            <button class="reset-btn" onclick="resetPassword()">Забули пароль? Відновити через Telegram</button>

            <div class="links">
                Ще немає акаунту? <a href="/courier/register">Зареєструватися</a>
            </div>
        </div>

        <script>
            async function resetPassword() {{
                const phone = prompt("Введіть ваш номер телефону (напр. 380...):");
                if(!phone) return;
                
                try {{
                    const fd = new FormData();
                    fd.append('phone', phone);
                    const res = await fetch('/api/courier/reset_password', {{
                        method: 'POST', body: fd
                    }});
                    const data = await res.json();
                    
                    if(res.ok) {{
                        alert("Новий пароль відправлено у ваш Telegram!");
                    }} else {{
                        alert("Помилка: " + (data.detail || "Невідома помилка"));
                    }}
                }} catch(e) {{
                    alert("Помилка з'єднання з сервером.");
                }}
            }}
        </script>
    </body>
    </html>
    """

def get_courier_register_page():
    return """
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Реєстрація Кур'єра | Restify</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root { --bg: #0f172a; --panel: #1e293b; --text: #f8fafc; --primary: #3b82f6; --success: #22c55e; }
            body {
                margin: 0; padding: 0; background-color: var(--bg); color: var(--text);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex; justify-content: center; align-items: center; min-height: 100vh;
            }
            .register-container {
                background: var(--panel); padding: 30px; border-radius: 16px;
                width: 90%; max-width: 450px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                box-sizing: border-box; margin: 20px 0;
            }
            h1 { text-align: center; margin-top: 0; color: var(--primary); font-size: 1.5rem; }
            p.subtitle { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; }
            
            .step { display: none; }
            .step.active { display: block; animation: fadeIn 0.3s; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            
            .input-group { margin-bottom: 15px; }
            .input-group label { display: block; margin-bottom: 5px; color: #cbd5e1; font-size: 0.9rem; }
            .input-group input {
                width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155;
                background: #0f172a; color: white; box-sizing: border-box; font-size: 1rem;
            }
            .input-group input:focus { outline: none; border-color: var(--primary); }
            
            .file-upload {
                border: 2px dashed #334155; border-radius: 8px; padding: 20px;
                text-align: center; cursor: pointer; margin-bottom: 15px;
                background: rgba(0,0,0,0.2); transition: 0.3s;
            }
            .file-upload:hover { border-color: var(--primary); background: rgba(59, 130, 246, 0.1); }
            .file-upload i { font-size: 2rem; color: var(--primary); margin-bottom: 10px; }
            .file-upload input[type="file"] { display: none; }
            .file-name { margin-top: 10px; font-size: 0.85rem; color: var(--success); word-break: break-all; }

            .btn {
                width: 100%; padding: 14px; background: var(--primary); color: white;
                border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold;
                cursor: pointer; margin-top: 10px; transition: background 0.3s;
            }
            .btn:hover { background: #2563eb; }
            .btn:disabled { background: #475569; cursor: not-allowed; }
            .btn-outline {
                background: transparent; border: 1px solid var(--primary); color: var(--primary);
            }
            .btn-outline:hover { background: rgba(59, 130, 246, 0.1); }

            .tg-btn {
                background: #0088cc; display: flex; align-items: center; justify-content: center; gap: 10px;
            }
            .tg-btn:hover { background: #0077b3; }

            .links { text-align: center; margin-top: 20px; font-size: 0.9rem; }
            .links a { color: var(--primary); text-decoration: none; }
            
            #errorMsg { color: #ef4444; font-size: 0.9rem; text-align: center; margin-bottom: 15px; display: none; }
        </style>
    </head>
    <body>
        <div class="register-container">
            <h1>Реєстрація Кур'єра</h1>
            <p class="subtitle">Пройдіть 3 кроки для початку роботи</p>
            
            <div id="errorMsg"></div>

            <div id="step1" class="step active">
                <div style="text-align:center; margin-bottom: 20px;">
                    <i class="fa-brands fa-telegram" style="font-size: 4rem; color: #0088cc;"></i>
                    <p>Для зв'язку та безпеки нам потрібен ваш Telegram та номер телефону.</p>
                </div>
                <button class="btn tg-btn" onclick="startTelegramAuth()">
                    <i class="fa-brands fa-telegram"></i> Підтвердити через Telegram
                </button>
            </div>

            <div id="step2" class="step">
                <p style="text-align:center;">Завантажте фото для верифікації</p>
                
                <label class="file-upload" onclick="document.getElementById('docFile').click()">
                    <i class="fa-solid fa-id-card"></i>
                    <div>Натисніть, щоб завантажити фото паспорта або прав</div>
                    <input type="file" id="docFile" accept="image/*" onchange="showFileName(this, 'docName')">
                    <div id="docName" class="file-name"></div>
                </label>

                <label class="file-upload" onclick="document.getElementById('selfieFile').click()">
                    <i class="fa-solid fa-camera-retro"></i>
                    <div>Натисніть, щоб зробити селфі з документом</div>
                    <input type="file" id="selfieFile" accept="image/*" capture="user" onchange="showFileName(this, 'selfieName')">
                    <div id="selfieName" class="file-name"></div>
                </label>

                <div style="display:flex; gap:10px;">
                    <button class="btn btn-outline" onclick="showStep(1)">Назад</button>
                    <button class="btn" onclick="goToStep3()">Далі</button>
                </div>
            </div>

            <div id="step3" class="step">
                <form id="registerForm" onsubmit="submitRegistration(event)">
                    <div class="input-group">
                        <label>Ваше ПІБ</label>
                        <input type="text" id="regName" required placeholder="Іванов Іван">
                    </div>
                    <div class="input-group">
                        <label>Придумайте пароль для входу</label>
                        <input type="password" id="regPassword" required minlength="6" placeholder="Мінімум 6 символів">
                    </div>
                    
                    <div style="display:flex; gap:10px;">
                        <button type="button" class="btn btn-outline" onclick="showStep(2)">Назад</button>
                        <button type="submit" class="btn" id="submitBtn">Завершити реєстрацію</button>
                    </div>
                </form>
            </div>

            <div class="links" id="loginLink">
                Вже є акаунт? <a href="/courier/login">Увійти</a>
            </div>
        </div>

        <script>
            let verificationToken = "";
            let checkInterval = null;

            function showStep(num) {
                document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
                document.getElementById('step' + num).classList.add('active');
                if(num === 3) document.getElementById('loginLink').style.display = 'none';
                else document.getElementById('loginLink').style.display = 'block';
            }

            function showError(msg) {
                const el = document.getElementById('errorMsg');
                el.innerText = msg;
                el.style.display = 'block';
                setTimeout(() => el.style.display = 'none', 5000);
            }

            async function startTelegramAuth() {
                try {
                    const res = await fetch('/api/auth/init_verification', { method: 'POST' });
                    const data = await res.json();
                    verificationToken = data.token;
                    window.open(data.link, '_blank');
                    
                    const btn = document.querySelector('.tg-btn');
                    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Очікування підтвердження...';
                    btn.disabled = true;

                    checkInterval = setInterval(checkVerification, 2000);
                } catch(e) {
                    showError("Помилка з'єднання з сервером");
                }
            }

            async function checkVerification() {
                if(!verificationToken) return;
                try {
                    const res = await fetch('/api/auth/check_verification/' + verificationToken);
                    const data = await res.json();
                    if(data.status === 'verified') {
                        clearInterval(checkInterval);
                        showStep(2); // Переходимо до документів
                    }
                } catch(e) {}
            }

            function showFileName(input, targetId) {
                const target = document.getElementById(targetId);
                if(input.files && input.files[0]) {
                    target.innerText = "✅ " + input.files[0].name;
                } else {
                    target.innerText = "";
                }
            }

            function goToStep3() {
                const doc = document.getElementById('docFile').files[0];
                const selfie = document.getElementById('selfieFile').files[0];
                if(!doc || !selfie) {
                    showError("Будь ласка, завантажте обидва фото!");
                    return;
                }
                showStep(3);
            }

            async function submitRegistration(e) {
                e.preventDefault();
                const name = document.getElementById('regName').value;
                const pwd = document.getElementById('regPassword').value;
                const doc = document.getElementById('docFile').files[0];
                const selfie = document.getElementById('selfieFile').files[0];
                const btn = document.getElementById('submitBtn');

                if(!verificationToken || !name || !pwd || !doc || !selfie) {
                    showError("Заповніть всі поля!"); return;
                }

                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Реєстрація...';

                const fd = new FormData();
                fd.append('name', name);
                fd.append('password', pwd);
                fd.append('verification_token', verificationToken);
                fd.append('document_photo', doc);
                fd.append('selfie_photo', selfie);

                try {
                    const res = await fetch('/api/courier/register', {
                        method: 'POST', body: fd
                    });
                    
                    if(res.ok) {
                        document.querySelector('.register-container').innerHTML = `
                            <div style="text-align:center;">
                                <i class="fa-solid fa-circle-check" style="font-size: 5rem; color: var(--success); margin-bottom:20px;"></i>
                                <h2>Реєстрація успішна!</h2>
                                <p style="color:#94a3b8;">Ваші дані відправлені на перевірку адміністратору. Ми повідомимо вас у Telegram, коли акаунт буде активовано.</p>
                                <a href="/courier/login" class="btn" style="display:inline-block; text-decoration:none; margin-top:20px;">Перейти до входу</a>
                            </div>
                        `;
                    } else {
                        const data = await res.json();
                        showError(data.detail || "Помилка реєстрації");
                        btn.disabled = false;
                        btn.innerText = "Завершити реєстрацію";
                    }
                } catch(e) {
                    showError("Помилка з'єднання з сервером");
                    btn.disabled = false;
                    btn.innerText = "Завершити реєстрацію";
                }
            }
        </script>
    </body>
    </html>
    """

def get_courier_pwa_html(courier, config):
    PWA_STYLES = """
    :root {
        --bg: #0f172a; --panel: #1e293b; --text: #f8fafc;
        --primary: #3b82f6; --success: #22c55e; --danger: #ef4444; --warning: #facc15;
        --border: #334155; --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    body, html {
        margin: 0; padding: 0; width: 100%; height: 100%;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: var(--bg); color: var(--text); overflow: hidden;
    }
    
    .app-header {
        position: absolute; top: 0; left: 0; right: 0; height: 60px;
        background: rgba(15, 23, 42, 0.95); backdrop-filter: blur(10px);
        display: flex; justify-content: space-between; align-items: center;
        padding: 0 15px; z-index: 100; border-bottom: 1px solid var(--border);
    }
    .header-title { font-size: 1.1rem; font-weight: bold; color: white; display:flex; align-items:center; gap:8px; }
    
    .status-toggle {
        display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.1);
        padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 0.9rem;
    }
    .toggle-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--danger); transition: 0.3s; }
    .status-toggle.online .toggle-dot { background: var(--success); box-shadow: 0 0 8px var(--success); }
    
    /* --- СИСТЕМА ОГОЛОШЕНЬ (АККУРАТНІ ПЛАШКИ ПІД ХЕДЕРОМ) --- */
    #announcements-wrapper {
        position: absolute;
        top: 60px; /* Одразу під хедером */
        left: 0;
        right: 0;
        z-index: 95; /* Поверх карти, але під модалками */
        display: flex;
        flex-direction: column;
    }
    .announcement-bar {
        padding: 10px 15px;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        animation: slideDownAnn 0.3s ease-out;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .ann-info { background: rgba(30, 64, 175, 0.95); backdrop-filter: blur(5px); }
    .ann-warning { background: rgba(161, 98, 7, 0.95); backdrop-filter: blur(5px); }
    .ann-danger { background: rgba(153, 27, 27, 0.95); backdrop-filter: blur(5px); }
    .ann-success { background: rgba(22, 101, 52, 0.95); backdrop-filter: blur(5px); }
    
    .ann-content { flex: 1; display: flex; flex-direction: column; gap: 4px; }
    .ann-title { font-weight: 800; font-size: 0.95rem; display: flex; align-items: center; gap: 6px; }
    .ann-text { font-size: 0.85rem; line-height: 1.3; opacity: 0.9; }
    
    .ann-close { 
        background: rgba(255,255,255,0.2); border: none; width: 30px; height: 30px; 
        border-radius: 50%; color: white; display: flex; align-items: center; 
        justify-content: center; cursor: pointer; flex-shrink: 0; transition: 0.2s;
    }
    .ann-close:active { background: rgba(255,255,255,0.4); transform: scale(0.9); }
    
    @keyframes slideDownAnn { from { transform: translateY(-100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

    #map {
        position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1;
        background-color: #0f172a;
    }
    /* Темна тема для Leaflet */
    .leaflet-layer, .leaflet-control-zoom-in, .leaflet-control-zoom-out, .leaflet-control-attribution {
        filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
    }
    
    .bottom-sheet {
        position: absolute; bottom: 0; left: 0; right: 0;
        background: var(--panel); border-radius: 20px 20px 0 0;
        z-index: 100; display: flex; flex-direction: column;
        box-shadow: 0 -5px 20px rgba(0,0,0,0.5);
        transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
        max-height: 85vh;
    }
    
    .drag-handle {
        width: 100%; height: 25px; display: flex; justify-content: center; align-items: center; cursor: grab;
    }
    .drag-pill { width: 40px; height: 5px; background: #475569; border-radius: 3px; }
    
    .tabs-nav {
        display: flex; border-bottom: 1px solid var(--border); padding: 0 10px;
    }
    .tab-btn {
        flex: 1; background: none; border: none; color: var(--text-muted);
        padding: 12px 0; font-size: 0.95rem; font-weight: 600; cursor: pointer;
        border-bottom: 3px solid transparent; transition: 0.2s;
    }
    .tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }
    
    .tab-content {
        flex: 1; overflow-y: auto; padding: 15px; display: none;
    }
    .tab-content.active { display: block; }
    
    /* Картки замовлень */
    .job-card {
        background: rgba(0,0,0,0.2); border: 1px solid var(--border);
        border-radius: 12px; padding: 15px; margin-bottom: 15px;
    }
    .job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .job-price { font-size: 1.2rem; font-weight: bold; color: var(--success); }
    .job-dist { font-size: 0.85rem; color: var(--text-muted); background: var(--bg); padding: 3px 8px; border-radius: 12px;}
    
    .job-route { position: relative; padding-left: 20px; margin: 10px 0; }
    .job-route::before {
        content: ''; position: absolute; left: 6px; top: 10px; bottom: 10px;
        width: 2px; background: #334155;
    }
    .route-point { position: relative; margin-bottom: 10px; font-size: 0.9rem; }
    .route-point i {
        position: absolute; left: -20px; top: 2px; font-size: 14px;
        background: var(--panel); padding: 2px; border-radius: 50%;
    }
    .point-rest i { color: var(--warning); }
    .point-client i { color: var(--primary); }
    
    .job-comment { background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--warning); padding: 8px; font-size: 0.85rem; margin-bottom: 10px; border-radius: 0 4px 4px 0;}
    
    .btn {
        width: 100%; padding: 14px; background: var(--primary); color: white;
        border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold;
        cursor: pointer; transition: 0.2s; display: flex; justify-content: center; align-items: center; gap: 8px;
    }
    .btn:active { transform: scale(0.98); }
    .btn.success { background: var(--success); }
    .btn.warning { background: var(--warning); color: #000; }
    .btn.danger { background: var(--danger); }
    .btn.outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
    
    .empty-state { text-align: center; padding: 40px 20px; color: var(--text-muted); }
    .empty-state i { font-size: 3rem; margin-bottom: 15px; opacity: 0.5; }
    
    /* Профіль */
    .profile-header { text-align: center; margin-bottom: 20px; }
    .avatar-circle {
        width: 80px; height: 80px; background: var(--border); border-radius: 50%;
        display: flex; justify-content: center; align-items: center; font-size: 2rem;
        margin: 0 auto 10px; color: var(--primary);
    }
    .profile-stat {
        background: rgba(0,0,0,0.2); border: 1px solid var(--border); border-radius: 12px;
        padding: 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
    }
    .stat-val { font-size: 1.2rem; font-weight: bold; color: var(--success); }
    
    /* History */
    .history-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px; border-bottom: 1px solid var(--border); font-size: 0.9rem;
    }
    .history-item:last-child { border: none; }
    
    /* ЧАТ */
    #chat-container { display: flex; flex-direction: column; height: 300px; background: #0f172a; border-radius: 8px; margin-bottom: 15px; overflow: hidden; border: 1px solid var(--border);}
    #chat-messages { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
    .msg-bubble { max-width: 80%; padding: 8px 12px; border-radius: 12px; font-size: 0.9rem; position: relative; }
    .msg-courier { align-self: flex-end; background: var(--primary); color: white; border-bottom-right-radius: 2px; }
    .msg-partner { align-self: flex-start; background: #334155; color: white; border-bottom-left-radius: 2px; }
    .msg-time { font-size: 0.65rem; opacity: 0.7; display: block; text-align: right; margin-top: 4px; }
    .chat-input-area { display: flex; padding: 8px; background: var(--panel); border-top: 1px solid var(--border); }
    .chat-input-area input { flex: 1; padding: 10px; border-radius: 20px; border: 1px solid #334155; background: #0f172a; color: white; outline: none; }
    .chat-input-area button { background: var(--primary); color: white; border: none; width: 40px; height: 40px; border-radius: 50%; margin-left: 8px; display: flex; justify-content: center; align-items: center; cursor: pointer; }
    
    .spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: white; animation: spin 1s ease-in-out infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    
    /* Модалка на весь екран */
    .full-modal {
        position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--bg);
        z-index: 200; display: none; flex-direction: column;
    }
    .full-modal.active { display: flex; animation: slideUp 0.3s forwards; }
    @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
    .modal-header {
        padding: 15px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 15px;
    }
    .modal-back { background: none; border: none; color: white; font-size: 1.2rem; cursor: pointer; }
    .modal-body { flex: 1; overflow-y: auto; padding: 15px; }

    /* FAB Recenter */
    .fab-recenter {
        position: absolute; right: 15px; bottom: calc(85vh + 15px); z-index: 90;
        width: 45px; height: 45px; background: var(--panel); border: 2px solid var(--border);
        border-radius: 50%; display: flex; justify-content: center; align-items: center;
        color: var(--primary); font-size: 1.2rem; box-shadow: 0 4px 10px rgba(0,0,0,0.5); cursor: pointer;
        transition: bottom 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }
    """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <meta name="theme-color" content="#0f172a">
        <link rel="manifest" href="/courier/manifest.json">
        <title>Кур'єр | Restify</title>
        
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        
        <style>
            {PWA_STYLES}
        </style>
    </head>
    <body>

        <div class="app-header">
            <div class="header-title"><i class="fa-solid fa-motorcycle"></i> Restify</div>
            <div class="status-toggle {'online' if courier.is_online else ''}" id="statusBtn" onclick="toggleStatus()">
                <div class="toggle-dot"></div>
                <span id="statusText">{'На зміні' if courier.is_online else 'Офлайн'}</span>
            </div>
        </div>

        <div id="announcements-wrapper"></div>

        <div id="map"></div>
        <button class="fab-recenter" id="fabRecenter" onclick="recenterMap()"><i class="fa-solid fa-location-crosshairs"></i></button>

        <div class="bottom-sheet" id="bottomSheet">
            <div class="drag-handle" id="dragHandle">
                <div class="drag-pill"></div>
            </div>
            
            <div class="tabs-nav">
                <button class="tab-btn active" onclick="switchTab('orders')" id="tab-orders">Вільні</button>
                <button class="tab-btn" onclick="switchTab('active')" id="tab-active" style="display:none;">Активне <i class="fa-solid fa-circle-exclamation" style="color:var(--warning);font-size:10px;"></i></button>
                <button class="tab-btn" onclick="switchTab('history')" id="tab-history">Історія</button>
                <button class="tab-btn" onclick="switchTab('profile')" id="tab-profile"><i class="fa-solid fa-user"></i></button>
            </div>
            
            <div class="tab-content active" id="content-orders">
                <div id="ordersList">
                    <div class="empty-state">
                        <i class="fa-solid fa-satellite-dish"></i>
                        <h3>Шукаємо замовлення...</h3>
                        <p>Щойно з'явиться нове замовлення, воно відобразиться тут.</p>
                    </div>
                </div>
            </div>
            
            <div class="tab-content" id="content-active">
                <div id="activeJobContent"></div>
            </div>
            
            <div class="tab-content" id="content-history">
                <h3 style="margin-top:0;">Останні доставки</h3>
                <div id="historyList"></div>
            </div>
            
            <div class="tab-content" id="content-profile">
                <div class="profile-header">
                    <div class="avatar-circle"><i class="fa-solid fa-user-ninja"></i></div>
                    <h2 style="margin:0;">{courier.name}</h2>
                    <p style="color:var(--text-muted); margin:5px 0 0;">{courier.phone}</p>
                    <div style="margin-top:10px; font-weight:bold; color:var(--warning);">
                        <i class="fa-solid fa-star"></i> {getattr(courier, 'avg_rating', 5.0):.1f} ({getattr(courier, 'rating_count', 0)} відгуків)
                    </div>
                </div>
                
                <div class="profile-stat">
                    <div>
                        <div style="color:var(--text-muted); font-size:0.9rem;">Ваш Баланс</div>
                        <div style="font-size:0.8rem; color:#ef4444;">Комісія: {getattr(courier, 'commission_rate', 10.0)}%</div>
                    </div>
                    <div class="stat-val">{getattr(courier, 'balance', 0.0):.2f} ₴</div>
                </div>
                
                <button class="btn outline" style="margin-top:20px; color:var(--danger); border-color:var(--danger);" onclick="window.location.href='/courier/logout'">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> Вийти з акаунту
                </button>
            </div>
        </div>

        <div class="full-modal" id="jobDetailModal">
            <div class="modal-header">
                <button class="modal-back" onclick="closeJobDetail()"><i class="fa-solid fa-arrow-left"></i></button>
                <h3 style="margin:0;">Деталі Замовлення</h3>
            </div>
            <div class="modal-body" id="jobDetailBody"></div>
        </div>

        <div class="full-modal" id="chatModal">
            <div class="modal-header">
                <button class="modal-back" onclick="closeChat()"><i class="fa-solid fa-arrow-left"></i></button>
                <h3 style="margin:0;">Чат із Закладом</h3>
            </div>
            <div class="modal-body" style="display:flex; flex-direction:column; padding:0;">
                <div id="chat-messages" style="flex:1;"></div>
                <div class="chat-input-area">
                    <input type="text" id="chatInput" placeholder="Написати повідомлення...">
                    <button onclick="sendChatMessage()"><i class="fa-solid fa-paper-plane"></i></button>
                </div>
            </div>
        </div>

        <audio id="notifySound" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" preload="auto"></audio>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js"></script>
        <script src="https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js"></script>

        <script>
            // --- FIREBASE PUSH ---
            const firebaseConfig = {{
                apiKey: "{config.get('firebase_api_key', '')}",
                projectId: "{config.get('firebase_project_id', '')}",
                messagingSenderId: "{config.get('firebase_sender_id', '')}",
                appId: "{config.get('firebase_app_id', '')}"
            }};

            if(firebaseConfig.apiKey) {{
                try {{
                    firebase.initializeApp(firebaseConfig);
                    const messaging = firebase.messaging();
                    
                    async function requestPushPermission() {{
                        try {{
                            const currentToken = await messaging.getToken();
                            if (currentToken) {{
                                sendTokenToServer(currentToken);
                            }} else {{
                                console.log('No registration token available.');
                            }}
                        }} catch (err) {{
                            console.log('An error occurred while retrieving token. ', err);
                        }}
                    }}
                    
                    messaging.onMessage((payload) => {{
                        console.log('Message received. ', payload);
                        playNotifySound();
                        if(navigator.vibrate) navigator.vibrate([200, 100, 200]);
                    }});

                    function sendTokenToServer(token) {{
                        const fd = new FormData();
                        fd.append('token', token);
                        fetch('/api/courier/fcm_token', {{ method: 'POST', body: fd }});
                    }}
                    
                    if ('serviceWorker' in navigator) {{
                        navigator.serviceWorker.register('/firebase-messaging-sw.js')
                        .then(function(registration) {{
                            messaging.useServiceWorker(registration);
                            requestPushPermission();
                        }});
                    }}
                }} catch(e) {{ console.error("Firebase init error", e); }}
            }}

            // --- ОСНОВНІ ЗМІННІ ---
            let map, userMarker, ws;
            let currentLat = null, currentLon = null;
            let activeJobId = null;
            let activeJobData = null; // Зберігаємо повні дані про активне замовлення
            let isOnline = {'true' if courier.is_online else 'false'} === 'true';
            
            // Маркери на карті
            let restMarker = null, clientMarker = null, routeLine = null;

            // Іконки
            const courierIcon = L.divIcon({{ html: '<div style="font-size:24px; color:#3b82f6; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));"><i class="fa-solid fa-motorcycle"></i></div>', className: '', iconSize: [24,24], iconAnchor: [12,12] }});
            const restIcon = L.divIcon({{ html: '<div style="font-size:24px; color:#facc15; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));"><i class="fa-solid fa-store"></i></div>', className: '', iconSize: [24,24], iconAnchor: [12,24] }});
            const clientIcon = L.divIcon({{ html: '<div style="font-size:24px; color:#ef4444; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));"><i class="fa-solid fa-location-dot"></i></div>', className: '', iconSize: [24,24], iconAnchor: [12,24] }});

            // --- ІНІЦІАЛІЗАЦІЯ ---
            document.addEventListener('DOMContentLoaded', () => {{
                initMap();
                initBottomSheet();
                initWebSocket();
                startLocationTracking();
                checkActiveJob();
                fetchHistory();
                fetchAnnouncements(); // Виклик системи оголошень
            }});

            function initMap() {{
                map = L.map('map', {{ zoomControl: false }}).setView([48.4647, 35.0461], 13);
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '&copy; OpenStreetMap &copy; CARTO'
                }}).addTo(map);
            }}

            // --- BOTTOM SHEET ЛОГІКА ---
            const sheet = document.getElementById('bottomSheet');
            const handle = document.getElementById('dragHandle');
            const fab = document.getElementById('fabRecenter');
            let startY, startHeight;

            function initBottomSheet() {{
                sheet.style.height = '40vh';
                updateFabPosition('40vh');

                handle.addEventListener('touchstart', (e) => {{
                    startY = e.touches[0].clientY;
                    startHeight = sheet.getBoundingClientRect().height;
                    sheet.style.transition = 'none';
                    fab.style.transition = 'none';
                }});

                handle.addEventListener('touchmove', (e) => {{
                    const deltaY = startY - e.touches[0].clientY;
                    let newHeight = startHeight + deltaY;
                    const vh = window.innerHeight;
                    if(newHeight < vh * 0.15) newHeight = vh * 0.15;
                    if(newHeight > vh * 0.85) newHeight = vh * 0.85;
                    sheet.style.height = newHeight + 'px';
                    updateFabPosition(newHeight + 'px');
                }});

                handle.addEventListener('touchend', () => {{
                    sheet.style.transition = 'height 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)';
                    fab.style.transition = 'bottom 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)';
                    const currentHeight = sheet.getBoundingClientRect().height;
                    const vh = window.innerHeight;
                    
                    let snapHeight = '40vh';
                    if (currentHeight > vh * 0.6) snapHeight = '85vh';
                    else if (currentHeight < vh * 0.25) snapHeight = '15vh';
                    
                    sheet.style.height = snapHeight;
                    updateFabPosition(snapHeight);
                }});
            }}

            function updateFabPosition(sheetHeightStr) {{
                // Якщо sheetHeightStr = '40vh', робимо calc(40vh + 15px)
                fab.style.bottom = `calc(${{sheetHeightStr}} + 15px)`;
            }}

            function switchTab(tabId) {{
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                document.getElementById('tab-' + tabId).classList.add('active');
                document.getElementById('content-' + tabId).classList.add('active');
                
                // Розгортаємо sheet трохи більше при перемиканні
                sheet.style.height = '60vh';
                updateFabPosition('60vh');

                if(tabId === 'orders' && !activeJobId) fetchOpenOrders();
                if(tabId === 'history') fetchHistory();
            }}

            // --- СИСТЕМА ОГОЛОШЕНЬ (ANNOUNCEMENTS) ---
            async function fetchAnnouncements() {{
                try {{
                    const res = await fetch('/api/courier/announcements');
                    if(res.ok) {{
                        const data = await res.json();
                        data.forEach(renderAnnouncement);
                    }}
                }} catch(e) {{ console.error("Announcements fetch error", e); }}
            }}

            function renderAnnouncement(ann) {{
                // Уникаємо дублювання
                if(document.getElementById(`ann-${{ann.id}}`)) return;
                
                const container = document.getElementById('announcements-wrapper');
                const div = document.createElement('div');
                div.id = `ann-${{ann.id}}`;
                div.className = `announcement-bar ann-${{ann.style}}`;
                
                let icon = 'fa-circle-info';
                if(ann.style === 'warning') icon = 'fa-triangle-exclamation';
                if(ann.style === 'danger') icon = 'fa-radiation';
                if(ann.style === 'success') icon = 'fa-check';
                
                div.innerHTML = `
                    <div class="ann-content">
                        <div class="ann-title"><i class="fa-solid ${{icon}}"></i> ${{ann.title}}</div>
                        <div class="ann-text">${{ann.message}}</div>
                    </div>
                    <button class="ann-close" onclick="dismissAnnouncement(${{ann.id}})">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                `;
                container.appendChild(div);
            }}

            async function dismissAnnouncement(id) {{
                const el = document.getElementById(`ann-${{id}}`);
                if(el) {{
                    el.style.opacity = '0';
                    el.style.transform = 'translateY(-20px)';
                    el.style.transition = '0.3s';
                    setTimeout(() => el.remove(), 300);
                }}
                // Відправляємо на сервер
                try {{
                    await fetch(`/api/courier/announcements/${{id}}/dismiss`, {{ method: 'POST' }});
                }} catch(e) {{}}
            }}

            // --- WEBSOCKET ТА ОНОВЛЕННЯ ДАНИХ ---
            let pingInterval;

            function initWebSocket() {{
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/courier`);
                
                ws.onopen = () => {{
                    console.log("WS Connected");
                    if(currentLat && currentLon) sendLocationToWS();
                    
                    // При відновленні з'єднання одразу підтягуємо нові замовлення
                    if(isOnline && !activeJobId) {{
                        fetchOpenOrders();
                    }} else if (activeJobId) {{
                        checkActiveJob();
                    }}
                    
                    if(pingInterval) clearInterval(pingInterval);
                    pingInterval = setInterval(() => {{ if(ws.readyState === WebSocket.OPEN) ws.send("ping"); }}, 30000);
                }};
                
                ws.onmessage = (e) => {{
                    if(e.data === "pong") return;
                    try {{
                        const msg = JSON.parse(e.data);
                        console.log("WS MSG:", msg);
                        
                        if(msg.type === 'new_announcement') {{
                            renderAnnouncement(msg.data);
                            playNotifySound();
                            if(navigator.vibrate) navigator.vibrate([100, 50, 100]);
                        }}
                        else if(msg.type === 'new_order') {{
                            if(!activeJobId) {{
                                fetchOpenOrders();
                                playNotifySound();
                                if(navigator.vibrate) navigator.vibrate([200, 100, 200]);
                            }}
                        }}
                        else if(msg.type === 'order_removed') {{
                            if(!activeJobId) fetchOpenOrders();
                        }}
                        else if(msg.type === 'job_ready') {{
                            playNotifySound();
                            if(navigator.vibrate) navigator.vibrate([300, 100, 300]);
                            checkActiveJob(); 
                        }}
                        else if(msg.type === 'job_update') {{
                            playNotifySound();
                            if(msg.status === 'cancelled' || msg.status === 'delivered') {{
                                alert(msg.message);
                                activeJobId = null;
                                activeJobData = null;
                                clearMap();
                                document.getElementById('tab-active').style.display = 'none';
                                switchTab('orders');
                            }} else {{
                                checkActiveJob();
                            }}
                        }}
                        else if(msg.type === 'chat_message') {{
                            if(document.getElementById('chatModal').classList.contains('active')) {{
                                appendChatMessage(msg.text, msg.role, msg.time);
                            }} else {{
                                playNotifySound();
                                if(navigator.vibrate) navigator.vibrate([100]);
                            }}
                        }}
                        else if(msg.type === 'balance_update') {{
                            // Оновлюємо відображення балансу, якщо треба
                        }}
                    }} catch(err) {{}}
                }};
                
                ws.onclose = () => {{ setTimeout(initWebSocket, 3000); }};
            }}

            // Відстежуємо, коли кур'єр розгортає згорнутий додаток
            document.addEventListener("visibilitychange", () => {{
                if (document.visibilityState === "visible") {{
                    console.log("App became visible, updating data...");
                    if(isOnline && !activeJobId) fetchOpenOrders();
                    if(activeJobId) checkActiveJob();
                }}
            }});

            function playNotifySound() {{
                const audio = document.getElementById('notifySound');
                audio.play().catch(e => console.log("Audio play blocked", e));
            }}

            // --- ГЕОЛОКАЦІЯ ---
            function startLocationTracking() {{
                if ("geolocation" in navigator) {{
                    navigator.geolocation.watchPosition(
                        (position) => {{
                            currentLat = position.coords.latitude;
                            currentLon = position.coords.longitude;
                            
                            if(!userMarker) {{
                                userMarker = L.marker([currentLat, currentLon], {{icon: courierIcon}}).addTo(map);
                                map.setView([currentLat, currentLon], 15);
                            }} else {{
                                userMarker.setLatLng([currentLat, currentLon]);
                            }}
                            
                            sendLocationToWS();
                            updateLocationViaHttp();
                        }},
                        (err) => console.error(err),
                        {{ enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }}
                    );
                }}
            }}

            function recenterMap() {{
                if(currentLat && currentLon) {{
                    map.setView([currentLat, currentLon], 15);
                }}
            }}

            function sendLocationToWS() {{
                if(ws && ws.readyState === WebSocket.OPEN && currentLat && currentLon) {{
                    ws.send(JSON.stringify({{ type: "init_location", lat: currentLat, lon: currentLon }}));
                }}
            }}
            
            let lastHttpUpdate = 0;
            function updateLocationViaHttp() {{
                const now = Date.now();
                if(now - lastHttpUpdate < 30000) return; // Раз на 30 сек
                if(!currentLat || !currentLon) return;
                
                const fd = new FormData();
                fd.append('lat', currentLat);
                fd.append('lon', currentLon);
                fetch('/api/courier/location', {{ method: 'POST', body: fd }});
                lastHttpUpdate = now;
            }}

            async function toggleStatus() {{
                try {{
                    const res = await fetch('/api/courier/toggle_status', {{method: 'POST'}});
                    const data = await res.json();
                    isOnline = data.is_online;
                    
                    const btn = document.getElementById('statusBtn');
                    const txt = document.getElementById('statusText');
                    if(isOnline) {{
                        btn.classList.add('online');
                        txt.innerText = 'На зміні';
                        fetchOpenOrders();
                    }} else {{
                        btn.classList.remove('online');
                        txt.innerText = 'Офлайн';
                        document.getElementById('ordersList').innerHTML = `
                            <div class="empty-state">
                                <i class="fa-solid fa-power-off"></i>
                                <h3>Ви офлайн</h3>
                                <p>Увімкніть статус "На зміні", щоб отримувати замовлення.</p>
                            </div>
                        `;
                    }}
                }} catch(e) {{ alert("Помилка"); }}
            }}

            // --- ЛОГІКА ЗАМОВЛЕНЬ ---
            async function fetchOpenOrders() {{
                if(activeJobId || !isOnline) return;
                try {{
                    const url = currentLat ? `/api/courier/open_orders?lat=${{currentLat}}&lon=${{currentLon}}` : '/api/courier/open_orders?lat=0&lon=0';
                    const res = await fetch(url);
                    const jobs = await res.json();
                    
                    const container = document.getElementById('ordersList');
                    if(jobs.length === 0) {{
                        container.innerHTML = `
                            <div class="empty-state">
                                <i class="fa-solid fa-mug-hot"></i>
                                <h3>Немає вільних замовлень</h3>
                                <p>Випийте кави, ми повідомимо коли щось з'явиться.</p>
                            </div>
                        `;
                        return;
                    }}
                    
                    let html = '';
                    jobs.forEach(j => {{
                        const distStr = j.dist_to_rest !== null && j.dist_to_rest !== "?" ? `${{j.dist_to_rest}} км до закладу` : 'Відстань невідома';
                        html += `
                            <div class="job-card" onclick='openJobDetail(${{JSON.stringify(j)}})'>
                                <div class="job-header">
                                    <div class="job-price">${{j.fee}} ₴</div>
                                    <div class="job-dist"><i class="fa-solid fa-route"></i> ${{distStr}}</div>
                                </div>
                                <div class="job-route">
                                    <div class="route-point point-rest">
                                        <i class="fa-solid fa-store"></i> <b>${{j.restaurant_name}}</b><br>
                                        <small>${{j.restaurant_address}}</small>
                                    </div>
                                    <div class="route-point point-client">
                                        <i class="fa-solid fa-location-dot"></i> <b>${{j.customer_name || 'Клієнт'}}</b><br>
                                        <small>${{j.dropoff_address}}</small>
                                    </div>
                                </div>
                                <div class="job-comment">${{j.comment}}</div>
                                <button class="btn outline" style="padding: 8px;">Деталі</button>
                            </div>
                        `;
                    }});
                    container.innerHTML = html;
                }} catch(e) {{ console.error(e); }}
            }}

            function openJobDetail(job) {{
                const body = document.getElementById('jobDetailBody');
                const distStr = job.dist_to_rest !== null && job.dist_to_rest !== "?" ? `${{job.dist_to_rest}} км` : '?';
                
                body.innerHTML = `
                    <div style="text-align:center; margin-bottom: 20px;">
                        <div style="font-size: 2.5rem; font-weight: 800; color: var(--success);">${{job.fee}} ₴</div>
                        <div style="color: var(--text-muted);">Заробіток за доставку</div>
                    </div>
                    
                    <div class="job-route" style="background: var(--panel); padding: 15px 15px 15px 35px; border-radius: 12px; margin-bottom:20px;">
                        <div class="route-point point-rest">
                            <i class="fa-solid fa-store"></i> 
                            <div style="color:var(--text-muted); font-size:0.8rem;">Забрати (${{distStr}})</div>
                            <b>${{job.restaurant_name}}</b><br>
                            ${{job.restaurant_address}}
                        </div>
                        <div class="route-point point-client">
                            <i class="fa-solid fa-location-dot"></i>
                            <div style="color:var(--text-muted); font-size:0.8rem;">Доставити (${{job.dist_trip}} км)</div>
                            <b>${{job.customer_name || 'Клієнт'}}</b><br>
                            ${{job.dropoff_address}}
                        </div>
                    </div>
                    
                    <div class="job-comment" style="font-size: 1rem; padding: 15px;">
                        <i class="fa-solid fa-circle-info"></i> <b>Коментар:</b><br>
                        ${{job.comment}}
                    </div>
                    
                    <div style="background: var(--panel); padding: 15px; border-radius: 12px; margin-bottom:20px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="color:var(--text-muted);">Тип оплати:</span>
                            <b>${{job.payment_type}}</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="color:var(--text-muted);">Сума чеку:</span>
                            <b>${{job.price}} ₴</b>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Повернення в заклад:</span>
                            <b style="color:${{job.is_return ? 'var(--danger)' : 'var(--success)'}}">${{job.is_return ? 'ТАК' : 'НІ'}}</b>
                        </div>
                    </div>

                    <button class="btn" style="height: 55px; font-size: 1.2rem;" onclick="acceptJob(${{job.id}})" id="acceptBtn">
                        Прийняти замовлення
                    </button>
                `;
                document.getElementById('jobDetailModal').classList.add('active');
            }}

            function closeJobDetail() {{
                document.getElementById('jobDetailModal').classList.remove('active');
            }}

            async function acceptJob(id) {{
                const btn = document.getElementById('acceptBtn');
                btn.innerHTML = '<span class="spinner"></span>';
                btn.disabled = true;
                
                try {{
                    const fd = new FormData();
                    fd.append('job_id', id);
                    const res = await fetch('/api/courier/accept_order', {{method: 'POST', body: fd}});
                    const data = await res.json();
                    
                    if(res.ok) {{
                        closeJobDetail();
                        checkActiveJob();
                    }} else {{
                        alert(data.message || "Помилка");
                        btn.innerHTML = 'Прийняти замовлення';
                        btn.disabled = false;
                        fetchOpenOrders();
                    }}
                }} catch(e) {{
                    alert("Мережева помилка");
                    btn.innerHTML = 'Прийняти замовлення';
                    btn.disabled = false;
                }}
            }}

            // --- АКТИВНЕ ЗАМОВЛЕННЯ ---
            async function checkActiveJob() {{
                try {{
                    const res = await fetch('/api/courier/active_job');
                    const data = await res.json();
                    
                    const tabActive = document.getElementById('tab-active');
                    const tabOrders = document.getElementById('tab-orders');
                    
                    if(data.active) {{
                        activeJobId = data.job.id;
                        activeJobData = data.job; // Зберігаємо повні дані
                        tabActive.style.display = 'block';
                        tabOrders.style.display = 'none';
                        renderActiveJob(data.job);
                        switchTab('active');
                        drawRoute(data.job);
                    }} else {{
                        activeJobId = null;
                        activeJobData = null;
                        tabActive.style.display = 'none';
                        tabOrders.style.display = 'block';
                        clearMap();
                        if(document.getElementById('content-active').classList.contains('active')) {{
                            switchTab('orders');
                        }}
                    }}
                }} catch(e) {{ console.error(e); }}
            }}

            function renderActiveJob(job) {{
                const container = document.getElementById('activeJobContent');
                
                // Визначаємо КРОК
                let stepNum = 1;
                if(job.server_status === 'picked_up') stepNum = 2;
                if(job.server_status === 'returning') stepNum = 3;

                let progressHtml = `
                    <div style="display:flex; justify-content:space-between; margin-bottom:20px; position:relative;">
                        <div style="position:absolute; top:15px; left:10%; right:10%; height:3px; background:#334155; z-index:0;"></div>
                        
                        <div style="z-index:1; text-align:center; width:33%;">
                            <div style="width:32px; height:32px; border-radius:50%; background:${{stepNum >= 1 ? 'var(--primary)' : '#1e293b'}}; color:white; display:flex; justify-content:center; align-items:center; margin:0 auto 5px; font-weight:bold; border:2px solid var(--bg);">1</div>
                            <div style="font-size:0.75rem; color:${{stepNum >= 1 ? 'white' : 'var(--text-muted)'}};">В заклад</div>
                        </div>
                        
                        <div style="z-index:1; text-align:center; width:33%;">
                            <div style="width:32px; height:32px; border-radius:50%; background:${{stepNum >= 2 ? 'var(--primary)' : '#1e293b'}}; color:white; display:flex; justify-content:center; align-items:center; margin:0 auto 5px; font-weight:bold; border:2px solid var(--bg);">2</div>
                            <div style="font-size:0.75rem; color:${{stepNum >= 2 ? 'white' : 'var(--text-muted)'}};">Клієнту</div>
                        </div>
                `;

                if (job.is_return_required) {{
                    progressHtml += `
                        <div style="z-index:1; text-align:center; width:33%;">
                            <div style="width:32px; height:32px; border-radius:50%; background:${{stepNum >= 3 ? 'var(--warning)' : '#1e293b'}}; color:${{stepNum >= 3 ? 'black' : 'white'}}; display:flex; justify-content:center; align-items:center; margin:0 auto 5px; font-weight:bold; border:2px solid var(--bg);">3</div>
                            <div style="font-size:0.75rem; color:${{stepNum >= 3 ? 'var(--warning)' : 'var(--text-muted)'}};">Повернення</div>
                        </div>
                    `;
                }} else {{
                    progressHtml += `
                        <div style="z-index:1; text-align:center; width:33%; opacity:0;"></div>
                    `;
                }}
                progressHtml += `</div>`;

                // КОНТЕНТ ЗАЛЕЖНО ВІД КРОКУ ТА СТАТУСУ
                let actionHtml = '';

                if (stepNum === 1) {{
                    // КРОК 1: Їдемо в заклад
                    actionHtml = `
                        <div style="background:var(--panel); padding:15px; border-radius:12px; margin-bottom:15px;">
                            <h3 style="margin:0 0 10px; color:var(--warning);"><i class="fa-solid fa-store"></i> ${{job.partner_name}}</h3>
                            <p style="margin:0 0 10px;"><i class="fa-solid fa-map-pin"></i> ${{job.partner_address}}</p>
                            <a href="tel:${{job.partner_phone}}" class="btn outline" style="margin-bottom:15px; padding:10px;"><i class="fa-solid fa-phone"></i> Зателефонувати в заклад</a>
                            
                            <div class="job-comment" style="margin-bottom:15px;">${{job.comment}}</div>
                            
                            ${{job.server_status === 'assigned' ? `
                                <button class="btn" onclick="updateStatus('arrived_pickup', this)"><i class="fa-solid fa-location-crosshairs"></i> Я на місці (Заклад)</button>
                            ` : ''}}
                            
                            ${{job.server_status === 'arrived_pickup' ? `
                                <div style="text-align:center; padding:15px; background:rgba(250,204,21,0.1); border-radius:8px; margin-bottom:15px; color:var(--warning);">
                                    ${{job.is_ready ? '<i class="fa-solid fa-check-circle" style="font-size:2rem;margin-bottom:10px;"></i><br><b>Замовлення готове!</b><br>Забирайте пакунок.' : '<i class="fa-solid fa-clock" style="font-size:2rem;margin-bottom:10px;"></i><br><b>Очікуємо приготування...</b><br>Заклад натисне кнопку, коли буде готово.'}}
                                </div>
                                <button class="btn success" onclick="updateStatus('picked_up', this)"><i class="fa-solid fa-box-open"></i> Я забрав замовлення</button>
                            ` : ''}}
                        </div>
                    `;
                }} 
                else if (stepNum === 2) {{
                    // КРОК 2: Їдемо до клієнта
                    actionHtml = `
                        <div style="background:var(--panel); padding:15px; border-radius:12px; margin-bottom:15px; border:1px solid var(--primary);">
                            <h3 style="margin:0 0 10px; color:var(--primary);"><i class="fa-solid fa-user"></i> Клієнт: ${{job.customer_name || 'Не вказано'}}</h3>
                            <p style="margin:0 0 10px; font-size:1.1rem;"><i class="fa-solid fa-map-pin"></i> <b>${{job.customer_address}}</b></p>
                            <a href="tel:${{job.customer_phone}}" class="btn outline" style="margin-bottom:15px; padding:10px; border-color:var(--primary); color:var(--primary);"><i class="fa-solid fa-phone"></i> Зателефонувати клієнту</a>
                            
                            <div style="background:#0f172a; padding:15px; border-radius:8px; margin-bottom:15px; text-align:center;">
                                <div style="color:var(--text-muted); font-size:0.9rem;">До сплати:</div>
                                <div style="font-size:2rem; font-weight:800; color:var(--success); margin:5px 0;">${{job.price}} ₴</div>
                                <div style="font-size:0.9rem;">Спосіб: <b>${{job.payment_type}}</b></div>
                            </div>

                            <button class="btn success" style="height:60px; font-size:1.2rem;" onclick="updateStatus('delivered', this)"><i class="fa-solid fa-check-double"></i> Замовлення доставлено</button>
                        </div>
                    `;
                }}
                else if (stepNum === 3) {{
                    // КРОК 3: Повернення
                    actionHtml = `
                        <div style="background:var(--panel); padding:15px; border-radius:12px; margin-bottom:15px; border:2px solid var(--warning);">
                            <div style="text-align:center; margin-bottom:15px;">
                                <i class="fa-solid fa-sack-dollar" style="font-size:3rem; color:var(--warning); margin-bottom:10px;"></i>
                                <h3 style="margin:0; color:var(--warning);">Поверніть готівку в заклад!</h3>
                            </div>
                            <p style="text-align:center; margin-bottom:20px;">Поверніться в <b>${{job.partner_name}}</b> (${{job.partner_address}}) та віддайте гроші адміністратору.</p>
                            
                            <div style="text-align:center; padding:15px; background:rgba(255,255,255,0.05); border-radius:8px; color:var(--text-muted);">
                                <i class="fa-solid fa-spinner fa-spin" style="font-size:1.5rem; margin-bottom:10px;"></i><br>
                                Очікуємо підтвердження від закладу...<br>
                                Як тільки вони підтвердять отримання грошей, замовлення автоматично закриється.
                            </div>
                        </div>
                    `;
                }}

                // Кнопка Чату (доступна завжди, крім 3 кроку)
                const chatBtn = stepNum < 3 ? `
                    <button class="btn outline" style="margin-bottom:15px;" onclick="openChat()">
                        <i class="fa-solid fa-comments"></i> Чат із закладом
                    </button>
                ` : '';

                container.innerHTML = progressHtml + chatBtn + actionHtml;
            }}

            async function updateStatus(status, btnEl) {{
                if(btnEl) {{
                    btnEl.disabled = true;
                    btnEl.innerHTML = '<span class="spinner"></span>';
                }}
                try {{
                    if(status === 'arrived_pickup') {{
                        const fd = new FormData();
                        fd.append('job_id', activeJobId);
                        await fetch('/api/courier/arrived_pickup', {{method: 'POST', body: fd}});
                    }} else {{
                        const fd = new FormData();
                        fd.append('job_id', activeJobId);
                        fd.append('status', status);
                        await fetch('/api/courier/update_job_status', {{method: 'POST', body: fd}});
                    }}
                    checkActiveJob();
                }} catch(e) {{
                    alert("Помилка оновлення статусу");
                    checkActiveJob(); // Відновлюємо
                }}
            }}

            // --- MAP DRAWING ---
            function drawRoute(job) {{
                clearMap();
                
                // Якщо є координати закладу та клієнта (в ідеалі брати з API, але тут використовуємо те, що є)
                // Оскільки в /active_job ми віддаємо customer_lat/lon, а partner_lat/lon немає напряму, 
                // просто малюємо клієнта, якщо є.
                
                const bounds = [];
                if(currentLat && currentLon) bounds.push([currentLat, currentLon]);

                if(job.customer_lat && job.customer_lon) {{
                    clientMarker = L.marker([job.customer_lat, job.customer_lon], {{icon: clientIcon}}).addTo(map);
                    clientMarker.bindPopup(`<b>Клієнт</b><br>${{job.customer_address}}`);
                    bounds.push([job.customer_lat, job.customer_lon]);
                }}

                if(bounds.length > 0) {{
                    map.fitBounds(bounds, {{padding: [50, 50]}});
                }}
            }}

            function clearMap() {{
                if(restMarker) map.removeLayer(restMarker);
                if(clientMarker) map.removeLayer(clientMarker);
                if(routeLine) map.removeLayer(routeLine);
                restMarker = clientMarker = routeLine = null;
                recenterMap();
            }}

            // --- HISTORY ---
            async function fetchHistory() {{
                try {{
                    const res = await fetch('/api/courier/history');
                    const data = await res.json();
                    
                    const container = document.getElementById('historyList');
                    if(data.length === 0) {{
                        container.innerHTML = '<div class="empty-state"><p>Історія порожня</p></div>';
                        return;
                    }}
                    
                    let html = '';
                    data.forEach(h => {{
                        const color = h.status === 'delivered' ? 'var(--success)' : 'var(--danger)';
                        const icon = h.status === 'delivered' ? 'fa-check' : 'fa-xmark';
                        html += `
                            <div class="history-item">
                                <div>
                                    <b>${{h.date}}</b><br>
                                    <small>${{h.address}}</small>
                                </div>
                                <div style="text-align:right;">
                                    <b style="color:${{color}};">${{h.price}} ₴</b><br>
                                    <small style="color:${{color}}"><i class="fa-solid ${{icon}}"></i> ${{h.status === 'delivered' ? 'Доставлено' : 'Скасовано'}}</small>
                                </div>
                            </div>
                        `;
                    }});
                    container.innerHTML = html;
                }} catch(e) {{}}
            }}

            // --- CHAT LOGIC ---
            async function openChat() {{
                if(!activeJobId) return;
                document.getElementById('chatModal').classList.add('active');
                await loadChatHistory();
            }}

            function closeChat() {{
                document.getElementById('chatModal').classList.remove('active');
            }}

            async function loadChatHistory() {{
                try {{
                    const res = await fetch(`/api/chat/history/${{activeJobId}}`);
                    const msgs = await res.json();
                    const container = document.getElementById('chat-messages');
                    container.innerHTML = '';
                    msgs.forEach(m => appendChatMessage(m.text, m.role, m.time, false));
                    scrollToBottom();
                }} catch(e) {{}}
            }}

            function appendChatMessage(text, role, time, scroll=true) {{
                const container = document.getElementById('chat-messages');
                const div = document.createElement('div');
                div.className = `msg-bubble ${{role === 'courier' ? 'msg-courier' : 'msg-partner'}}`;
                div.innerHTML = `${{text}} <span class="msg-time">${{time}}</span>`;
                container.appendChild(div);
                if(scroll) scrollToBottom();
            }}

            function scrollToBottom() {{
                const c = document.getElementById('chat-messages');
                c.scrollTop = c.scrollHeight;
            }}

            async function sendChatMessage() {{
                const inp = document.getElementById('chatInput');
                const text = inp.value.trim();
                if(!text || !activeJobId) return;
                
                inp.value = '';
                const now = new Date();
                const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
                appendChatMessage(text, 'courier', timeStr);
                
                const fd = new FormData();
                fd.append('job_id', activeJobId);
                fd.append('message', text);
                fd.append('role', 'courier');
                
                try {{ await fetch('/api/chat/send', {{method:'POST', body: fd}}); }} catch(e) {{}}
            }}
        </script>
    </body>
    </html>
    """
    return html