# Dockerfile для Сайта-Витрины (Lander)

# Используем тот же базовый образ, что и CRM
FROM python:3.11-slim
# --- НОВОЕ: Устанавливаем Docker CLI ---
# Обновляем apt и устанавливаем зависимости, необходимые для добавления репозитория Docker
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавляем GPG ключ Docker
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Настраиваем репозиторий Docker
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker CLI (только клиент!)
RUN apt-get update && apt-get install -y docker-ce-cli
# --- КОНЕЦ НОВОГО БЛОКА ---
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код (включая app.py, models.py, static/ и т.д.)
COPY . .

# Этот сервер будет работать на порту 8001
ENV PORT 8001
EXPOSE 8001

# ОБНОВЛЕНО: Запускаем uvicorn с app:app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]