import asyncio
from sqlalchemy import text
from models import engine

async def fix_db():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE couriers ADD COLUMN document_photo VARCHAR(255);"))
            print("✅ Колонку document_photo успішно додано!")
        except Exception as e:
            print(f"Помилка (можливо колонка вже існує): {e}")

if __name__ == "__main__":
    asyncio.run(fix_db())