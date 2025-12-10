import asyncio
import logging
import os
import subprocess
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# --- 1. Настройка ---
DATABASE_URL = os.environ.get("DATABASE_URL")
SAAS_ADMIN_PASSWORD = os.environ.get("SAAS_ADMIN_PASSWORD") # Нужен для docker exec

if not DATABASE_URL or not SAAS_ADMIN_PASSWORD:
    print("Ошибка: DATABASE_URL или SAAS_ADMIN_PASSWORD не установлены.")
    exit(1)

# Импортируем модели
try:
    import sys
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    from models import Instance
except ImportError:
    print("Ошибка: Не удалось импортировать 'models.Instance'. Убедитесь, что models.py в той же папке.")
    exit(1)
    
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def run_docker_command(command_args):
    """Выполняет команду docker (stop/start)"""
    logging.info(f"Выполнение: {' '.join(command_args)}")
    try:
        # =================================================================
        # ИСПРАВЛЕНИЕ: Убрано shell=True.
        # =================================================================
        process = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        stdout, stderr = process.communicate(timeout=60) # 60 секунд на команду
        
        stdout_str = stdout.decode('utf-8', 'ignore').strip()
        stderr_str = stderr.decode('utf-8', 'ignore').strip()

        if process.returncode != 0:
            logging.error(f"Ошибка выполнения: {stderr_str}")
            return False
            
        # Также проверяем stdout здесь, чтобы убедиться, что stop/start вернули ID
        if not stdout_str:
            logging.error(f"Команда docker удалась, но STDOUT пустой: {' '.join(command_args)}")
            return False
            
        return True
    except Exception as e:
        logging.error(f"Исключение при выполнении docker: {e}")
        return False

async def check_subscriptions():
    """
    Главная функция: находит просроченные подписки и отключает контейнеры.
    """
    logging.info("--- Запуск проверки подписок ---")
    
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        try:
            # 1. Найти все АКТИВНЫЕ экземпляры, у которых дата оплаты прошла
            now = datetime.utcnow()
            query = select(Instance).where(
                Instance.status == "active",
                Instance.next_payment_due < now
            )
            result = await session.execute(query)
            overdue_instances = result.scalars().all()

            if not overdue_instances:
                logging.info("Просроченных подписок не найдено.")
                return

            logging.warning(f"Найдено {len(overdue_instances)} просроченных подписок.")

            for instance in overdue_instances:
                logging.warning(f"Отключение клиента: {instance.subdomain} (Контейнер: {instance.container_name})")
                
                # 2. Выполнить docker stop
                if run_docker_command(["docker", "stop", instance.container_name]):
                    # 3. Обновить статус в БД
                    instance.status = "suspended"
                    session.add(instance)
                    logging.info(f"Контейнер {instance.container_name} успешно остановлен.")
                else:
                    logging.error(f"Не удалось остановить контейнер {instance.container_name}!")

            await session.commit()
            
        except Exception as e:
            logging.critical(f"Критическая ошибка при проверке подписок: {e}")
            await session.rollback()
        finally:
            await engine.dispose()
            
    logging.info("--- Проверка подписок завершена ---")

if __name__ == "__main__":
    # Убедимся, что PYTHONPATH включает текущую директорию
    sys.path.append(os.getcwd())
    try:
        from models import Instance
    except ImportError:
        print("Повторная попытка импорта 'models' не удалась.")
        exit(1)
        
    asyncio.run(check_subscriptions())