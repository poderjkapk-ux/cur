import json
from typing import Any, Dict, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем модель SystemSetting из вашего файла models.py
from models import SystemSetting

async def get_setting(session: AsyncSession, key: str, default: Any = None) -> Any:
    """
    Получает настройку из БД по ключу.
    Автоматически пытается десериализовать JSON (словари, списки, булевые значения).
    
    :param session: Асинхронная сессия SQLAlchemy
    :param key: Ключ настройки (например, 'firebase_config')
    :param default: Значение по умолчанию, если ключ не найден
    """
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting and setting.value is not None:
        try:
            # Пытаемся распарсить JSON (для словарей, списков, чисел, bool)
            return json.loads(setting.value)
        except (json.JSONDecodeError, TypeError):
            # Если не получилось (это обычная строка), возвращаем как есть
            return setting.value
    return default


async def set_setting(session: AsyncSession, key: str, value: Any) -> None:
    """
    Создает новую или обновляет существующую настройку в БД (Upsert).
    Автоматически сериализует словари, списки, числа и булевы значения в JSON.
    
    :param session: Асинхронная сессия SQLAlchemy
    :param key: Ключ настройки
    :param value: Значение настройки (строка, словарь, список, число, bool)
    """
    # Если передано что-то, что нужно сериализовать (dict, list, bool, int, float)
    if isinstance(value, (dict, list, bool, int, float)):
        # ensure_ascii=False сохранит кириллицу в читабельном виде, а не в \uXXXX
        str_value = json.dumps(value, ensure_ascii=False)
    else:
        # Для обычных строк сохраняем как есть
        str_value = str(value) if value is not None else None

    # Инициализируем объект модели
    setting = SystemSetting(key=key, value=str_value)
    
    # session.merge() работает как Upsert: 
    # обновит запись, если первичный ключ (key) уже существует, 
    # или создаст новую, если её нет.
    await session.merge(setting)
    await session.commit()


async def get_all_settings(session: AsyncSession) -> Dict[str, Any]:
    """
    Получает все настройки из базы данных и возвращает их в виде словаря.
    Удобно для загрузки всех конфигураций при старте сервера или для админки.
    """
    result = await session.execute(select(SystemSetting))
    settings = result.scalars().all()
    
    settings_dict = {}
    for s in settings:
        if s.value is not None:
            try:
                settings_dict[s.key] = json.loads(s.value)
            except (json.JSONDecodeError, TypeError):
                settings_dict[s.key] = s.value
        else:
            settings_dict[s.key] = None
            
    return settings_dict


async def delete_setting(session: AsyncSession, key: str) -> bool:
    """
    Удаляет настройку по ключу из базы данных.
    
    :return: True, если настройка была найдена и удалена, иначе False.
    """
    result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        await session.delete(setting)
        await session.commit()
        return True
    return False