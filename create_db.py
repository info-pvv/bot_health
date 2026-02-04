# create_db.py
import asyncio
import asyncpg
from app.core.config import settings

async def create_database():
    """Создание базы данных если не существует"""
    print("🗃️ Создание базы данных PostgreSQL...")
    
    try:
        # Подключаемся к системной БД
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database='postgres'
        )
        
        # Проверяем существование
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            settings.POSTGRES_DB
        )
        
        if not db_exists:
            print(f"📦 Создаем базу данных: {settings.POSTGRES_DB}")
            await conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            print(f"✅ База данных '{settings.POSTGRES_DB}' создана")
            
            # Подключаемся к новой БД и создаем схему
            await conn.close()
            conn = await asyncpg.connect(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB
            )
            
            # Создаем расширения
            await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            print("✅ Расширения созданы")
            
            await conn.close()
            return True
        else:
            print(f"✅ База данных '{settings.POSTGRES_DB}' уже существует")
            await conn.close()
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n💡 Возможные решения:")
        print("1. Проверьте что PostgreSQL запущен")
        print(f"2. Проверьте пароль для пользователя '{settings.POSTGRES_USER}'")
        print("3. Попробуйте создать БД вручную:")
        print(f'   psql -U postgres -c "CREATE DATABASE {settings.POSTGRES_DB};"')
        return False

if __name__ == "__main__":
    success = asyncio.run(create_database())
    if success:
        print("\n✅ База данных готова. Запускайте main.py")
    else:
        print("\n❌ Не удалось создать базу данных")