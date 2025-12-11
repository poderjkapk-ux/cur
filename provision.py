import os
import secrets
import logging
import subprocess # Используем subprocess вместо os.system для лучшего контроля

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# --- Загружаем критические переменные окружения ---
SAAS_ADMIN_PASSWORD = os.environ.get("SAAS_ADMIN_PASSWORD")
if not SAAS_ADMIN_PASSWORD:
    logging.warning("SAAS_ADMIN_PASSWORD не установлен! Развертывание невозможно.")


def generate_safe_password(length=16):
    """Генерирует безопасный алфавитно-цифровой пароль."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(chars) for i in range(length))

def run_system_command(command_args, is_sql=False, check_stdout=False):
    """
    Выполняет системную команду (например, ['docker', 'exec', ...])
    и возвращает True в случае успеха.
    """
    logging.info(f"Выполнение: {' '.join(command_args)}")
    try:
        env = os.environ.copy()
        if is_sql:
             # Это особый случай для psql, передаем пароль через окружение
             env["PGPASSWORD"] = SAAS_ADMIN_PASSWORD

        # =================================================================
        # ИСПРАВЛЕНИЕ: Убрано shell=True. Теперь Popen
        # корректно обработает список command_args в Linux.
        # =================================================================
        process = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, env=env)
        stdout, stderr = process.communicate(timeout=60) # 60 секунд на команду
        
        stdout_str = stdout.decode('utf-8', 'ignore').strip()
        stderr_str = stderr.decode('utf-8', 'ignore').strip()

        if process.returncode != 0:
            logging.error(f"Команда не удалась (код {process.returncode}): {' '.join(command_args)}")
            logging.error(f"Stderr: {stderr_str}")
            return False
        
        if check_stdout and not stdout_str:
            logging.error(f"Команда удалась, но STDOUT пустой, что считается ошибкой: {' '.join(command_args)}")
            logging.error(f"Stderr (если есть): {stderr_str}")
            return False

        logging.info(f"Stdout: {stdout_str}")
        return True

    except Exception as e:
        logging.error(f"Исключение при выполнении команды: {e}")
        return False

# --- Функция создания (без изменений, кроме тех, что в run_system_command) ---
def create_new_client_instance(client_name_base, root_domain, client_bot_token, admin_bot_token, admin_chat_id):
    """
    Полный цикл развертывания нового клиента.
    Генерирует имена, создает БД, запускает контейнер.
    """
    if not SAAS_ADMIN_PASSWORD:
        raise Exception("Отсутствует SAAS_ADMIN_PASSWORD. Невозможно создать клиента.")

    client_id = client_name_base 
    db_name = f"{client_id}_db"
    db_user = f"{client_id}_user"
    subdomain = f"{client_id}.{root_domain}"
    
    db_pass = generate_safe_password(16)
    admin_pass = generate_safe_password(10) # Пароль для админки CRM

    # 2. Очистка (на всякий случай)
    run_system_command(["docker", "stop", f"{client_id}_app"])
    run_system_command(["docker", "rm", f"{client_id}_app"])
    run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {db_name}"], is_sql=True)
    run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", f"DROP USER IF EXISTS {db_user}"], is_sql=True)

    # 3. Создание БД и Пользователя
    sql_create_db = f"CREATE DATABASE {db_name}"
    sql_create_user = f"CREATE USER {db_user} WITH PASSWORD '{db_pass}'"
    sql_grant_db = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}"
    sql_grant_schema = f"GRANT ALL PRIVILEGES ON SCHEMA public TO {db_user}"

    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", sql_create_db], is_sql=True):
        raise Exception("Не удалось создать базу данных.")
    
    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", sql_create_user], is_sql=True):
        raise Exception("Не удалось создать пользователя БД.")
        
    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", db_name, "-c", sql_grant_db], is_sql=True):
        raise Exception("Не удалось выдать права на БД.")
        
    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", db_name, "-c", sql_grant_schema], is_sql=True):
        raise Exception("Не удалось выдать права на схему public.")

    # 4. Запуск Docker-контейнера
    database_url = f"postgresql+asyncpg://{db_user}:{db_pass}@postgres_db:5432/{db_name}"
    
    docker_run_command = [
        "docker", "run", "-d", "--name", f"{client_id}_app",
        "-e", f"DATABASE_URL={database_url}",
        "-e", f"CLIENT_BOT_TOKEN={client_bot_token}",
        "-e", f"ADMIN_BOT_TOKEN={admin_bot_token}",
        "-e", f"ADMIN_CHAT_ID={admin_chat_id}",
        "-e", "ADMIN_USER=admin",
        "-e", f"ADMIN_PASS={admin_pass}",
        "--network", "saas_network",
        "-l", "traefik.enable=true",
        "-l", f"traefik.http.routers.{client_id}.rule=Host(\"{subdomain}\")",
        "-l", f"traefik.http.routers.{client_id}.entrypoints=websecure",
        "-l", f"traefik.http.routers.{client_id}.tls.certresolver=le",
        "-l", f"traefik.http.services.{client_id}.loadbalancer.server.port=8000",
        "crm-template"
    ]
    
    if not run_system_command(docker_run_command, check_stdout=True):
        raise Exception("Не удалось запустить Docker-контейнер клиента. Docker не вернул ID.")

    # 5. Возвращаем данные
    return {
        "url": f"https://{subdomain}",
        "login": "admin",
        "password": admin_pass,
        "subdomain": subdomain,
        "container_name": f"{client_id}_app"
    }

def stop_instance(container_name):
    """Останавливает контейнер клиента."""
    return run_system_command(["docker", "stop", container_name], check_stdout=True)

def start_instance(container_name):
    """Запускает остановленный контейнер клиента."""
    return run_system_command(["docker", "start", container_name], check_stdout=True)

def delete_client_instance(container_name):
    """
    Полностью удаляет экземпляр клиента:
    1. Останавливает контейнер
    2. Удаляет контейнер
    3. Удаляет базу данных
    4. Удаляет пользователя базы данных
    """
    if not container_name or not container_name.endswith("_app"):
        logging.error(f"Неверное имя контейнера для удаления: {container_name}")
        return False
        
    client_id = container_name.replace("_app", "")
    db_name = f"{client_id}_db"
    db_user = f"{client_id}_user"
    
    logging.warning(f"Начало полного удаления для клиента: {client_id}")

    # 1. Остановка и удаление контейнера
    if not run_system_command(["docker", "stop", container_name]):
        logging.warning(f"Не удалось остановить контейнер {container_name} (возможно, уже остановлен).")
    
    if not run_system_command(["docker", "rm", container_name], check_stdout=True):
        logging.error(f"Критическая ошибка: Не удалось удалить контейнер {container_name}.")
        return False # Не продолжаем, если не смогли удалить контейнер

    # 2. Удаление Базы Данных
    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {db_name}"], is_sql=True):
        logging.error(f"Не удалось удалить базу данных {db_name}.")
        return False

    # 3. Удаление Пользователя БД
    if not run_system_command(["docker", "exec", "postgres_db", "psql", "-U", "saas_admin", "-d", "postgres", "-c", f"DROP USER IF EXISTS {db_user}"], is_sql=True):
        logging.error(f"Не удалось удалить пользователя {db_user}.")
        return False

    logging.info(f"Клиент {client_id} успешно и полностью удален.")
    return True