Инструкция по запуску "Сайта-витрины" (Lander) - ВЕРСИЯ 2 (SaaS Control Plane)Этот проект (main.py) — это сердце вашего SaaS. Он принимает регистрации, управляет клиентами в своей базе данных (main_saas_db) и автоматически создает новые CRM-сайты для ваших клиентов.Он ДОЛЖЕН быть запущен как Docker-контейнер, чтобы иметь доступ к Docker и сети saas_network.Шаг 1: Сборка Docker-образа "Сайта-витрины"Убедитесь, что вы находитесь в папке C:\SaaS_Lander (где лежат main.py, provision.py, models.py, auth.py и Dockerfile).Выполните команду сборки в PowerShell:docker build -t lander-app .
Шаг 2: Запуск контейнера "Сайта-витрины"Это самый важный шаг. Мы запускаем этот контейнер и подключаем его к Traefik (чтобы он был доступен по вашему главному домену https://restify.site), к Docker (чтобы он мог запускать другие контейнеры) и к PostgreSQL (чтобы он хранил список клиентов).ВНИМАНИЕ: Замените ВСЕ 7 плейсхолдеров [...] на ваши реальные значения.docker run -d --name saas_lander_app \
  --restart always \
  --network saas_network \
  \
  # --- 1. Переменные окружения для этого сайта (Lander) ---
  # Пароль для входа на [https://restify.site/admin](https://restify.site/admin)
  -e ADMIN_USER="[ВАШ_ЛОГИН_ДЛЯ_ВИТРИНЫ]" \
  -e ADMIN_PASS="[ВАШ_ПАРОЛЬ_ДЛЯ_ВИТРИНЫ]" \
  # Секретный ключ для шифрования токенов (придумайте)
  -e JWT_SECRET_KEY="[ВАШ_СЕКРЕТНЫЙ_КЛЮЧ_JWT]" \
  \
  # --- 2. Переменные для автоматизации (Provisioning) ---
  # Пароль от postgres_db (из C:\saas_infra\docker-compose.yml)
  -e SAAS_ADMIN_PASSWORD="[PgS3rv!_2025_#saa]" \
  # Ваш корневой домен
  -e ROOT_DOMAIN="restify.site" \
  \
  # --- 3. Подключение к ГЛАВНОЙ Базе Данных (для хранения списка клиентов) ---
  -e DATABASE_URL="postgresql+asyncpg://saas_admin:[PgS3rv!_2025_#saa]@postgres_db:5432/main_saas_db" \
  \
  # --- 4. Переменные для Telegram-уведомлений (О НОВЫХ КЛИЕНТАХ) ---
  -e TG_BOT_TOKEN="[8529997696:AAE3ae_ml24qEElHt-qo0TF80yqPGem9eh0]" \
  -e TG_CHAT_ID="[-5064990818]" \
  -e BOT_USERNAME="Landerrestify_bot" \
  \
  # --- 5. Подключение к Docker (ОБЯЗАТЕЛЬНО!) ---
  # Позволяет этому контейнеру выполнять команды 'docker exec' и 'docker run'
  -v "\\.\pipe\docker_engine:\\.\pipe\docker_engine" \
  \
  # --- 6. Метки Traefik (для вашего главного домена) ---
  -l "traefik.enable=true" \
  -l "traefik.http.routers.lander.rule=Host(\`"restify.site\`")" \
  -l "traefik.http.routers.lander.entrypoints=websecure" \
  -l "traefik.http.routers.lander.tls.certresolver=le" \
  -l "traefik.http.services.lander.loadbalancer.server.port=8001" \
  \
  # Имя образа, который мы собрали на Шаге 1
  lander-app
Шаг 3: Настройка "Планировщика Заданий" Windows (Контроль оплаты)Этот шаг критически важен для автоматического отключения клиентов за неуплату.Откройте "Планировщик заданий" (Task Scheduler) на вашем Windows Server.Создайте "Простую задачу".Триггер: "Ежедневно" (Daily), время 01:00:00.Действие: "Запуск программы".Программа/сценарий: dockerДобавить аргументы (обязательно):exec saas_lander_app python payment_checker.py
(Эта команда говорит Docker: "Найди контейнер saas_lander_app и выполни внутри него скрипт payment_checker.py")Сохраните задачу.Шаг 4: Финальная проверкаПроверьте DNS: Убедитесь, что на nic.ua у вас есть A-запись для корневого домена (@), указывающая на IP вашего сервера.Проверьте Docker: Выполните docker ps. Теперь у вас должно быть 4 контейнера: traefik, postgres_db, client10_app (ваш тестовый клиент) и saas_lander_app (ваша витрина).Подождите 1-2 минуты (пока Traefik получит SSL-сертификат для restify.site).Откройте https://restify.site.Заполните форму на сайте и нажмите "Оплатить".Следите за логами: docker logs -f saas_lander_app. Вы увидите, как он создает нового клиента.Проверьте docker ps — там появится пятый контейнер (например, romashka_f4c_app).