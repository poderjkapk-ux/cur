from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import auth
from models import get_db, Courier, DeliveryPartner

router = APIRouter()

# Красивый HTML-шаблон страницы удаления
DELETION_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Видалення акаунту - Restify</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-xl shadow-lg w-full max-w-md border border-gray-200">
        <div class="text-center mb-6">
            <h2 class="text-2xl font-extrabold text-gray-800">Видалення акаунту</h2>
            <p class="text-gray-500 mt-2 text-sm">
                Щоб назавжди видалити свій акаунт та всі пов'язані з ним дані, будь ласка, авторизуйтесь.
            </p>
        </div>
        
        <form id="deleteForm" class="space-y-5">
            <div>
                <label class="block text-gray-700 text-sm font-bold mb-2">Хто ви?</label>
                <select id="acc_type" name="acc_type" class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-gray-50" onchange="toggleLoginType()">
                    <option value="courier">Кур'єр (по номеру телефону)</option>
                    <option value="partner">Заклад/Партнер (по Email)</option>
                </select>
            </div>
            
            <div>
                <label id="loginLabel" class="block text-gray-700 text-sm font-bold mb-2">Номер телефону</label>
                <input type="text" id="login" name="login" required class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-gray-50" placeholder="380...">
            </div>
            
            <div>
                <label class="block text-gray-700 text-sm font-bold mb-2">Пароль</label>
                <input type="password" id="password" name="password" required class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-gray-50" placeholder="Введіть ваш пароль">
            </div>
            
            <button type="submit" class="w-full bg-red-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-red-700 transition duration-300 shadow-md">
                Назавжди видалити акаунт
            </button>
            
            <div id="message" class="mt-4 text-center text-sm font-bold hidden p-3 rounded-lg"></div>
        </form>
    </div>

    <script>
        function toggleLoginType() {
            const type = document.getElementById('acc_type').value;
            const label = document.getElementById('loginLabel');
            const input = document.getElementById('login');
            if (type === 'courier') {
                label.innerText = 'Номер телефону';
                input.placeholder = '380...';
            } else {
                label.innerText = 'Email';
                input.placeholder = 'email@example.com';
            }
        }
        
        document.getElementById('deleteForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const msgDiv = document.getElementById('message');
            
            msgDiv.classList.remove('hidden', 'bg-green-100', 'text-green-700', 'bg-red-100', 'text-red-700');
            msgDiv.classList.add('bg-gray-100', 'text-gray-700');
            msgDiv.innerText = 'Перевірка даних...';
            
            if(!confirm('Ви впевнені? Цю дію НЕМОЖЛИВО скасувати. Всі ваші дані будуть стерті.')) {
                msgDiv.classList.add('hidden');
                return;
            }

            try {
                const response = await fetch('/api/account/delete', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                msgDiv.classList.remove('bg-gray-100', 'text-gray-700');
                if (response.ok) {
                    msgDiv.classList.add('bg-green-100', 'text-green-700');
                    msgDiv.innerText = 'Ваш акаунт та дані успішно видалено.';
                    e.target.reset();
                } else {
                    msgDiv.classList.add('bg-red-100', 'text-red-700');
                    msgDiv.innerText = result.detail || 'Помилка видалення.';
                }
            } catch (error) {
                msgDiv.classList.add('bg-red-100', 'text-red-700');
                msgDiv.innerText = 'Помилка з\'єднання із сервером.';
            }
        });
    </script>
</body>
</html>
"""

@router.get("/account-deletion", response_class=HTMLResponse)
async def account_deletion_page():
    """Віддає сторінку видалення акаунту для Google Play"""
    return HTMLResponse(content=DELETION_HTML)

@router.post("/api/account/delete")
async def api_delete_account(
    acc_type: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Обробляє запит на видалення, перевіряючи пароль"""
    if acc_type == "courier":
        # Очищаємо телефон від плюсів та пробілів (як у вашому API)
        clean_phone = login.replace('+', '').strip()
        
        # Використовуємо вашу існуючу функцію авторизації для перевірки пароля
        courier = await auth.authenticate_courier(db, clean_phone, password)
        if not courier:
            return JSONResponse(status_code=400, content={"detail": "Невірний номер телефону або пароль"})
        
        # Якщо пароль вірний - видаляємо кур'єра
        await db.delete(courier)
        await db.commit()
        return JSONResponse({"status": "ok", "message": "Акаунт кур'єра видалено"})
        
    elif acc_type == "partner":
        # Логіка для партнерів/закладів
        result = await db.execute(select(DeliveryPartner).where(DeliveryPartner.email == login.strip()))
        partner = result.scalar_one_or_none()
        
        if not partner or not auth.verify_password(password, partner.hashed_password):
            return JSONResponse(status_code=400, content={"detail": "Невірний email або пароль"})
        
        # Якщо пароль вірний - видаляємо партнера
        await db.delete(partner)
        await db.commit()
        return JSONResponse({"status": "ok", "message": "Акаунт закладу видалено"})
        
    return JSONResponse(status_code=400, content={"detail": "Невідомий тип акаунту"})