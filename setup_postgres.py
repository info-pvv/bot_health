# setup_postgres.py
import asyncio
import asyncpg
from app.core.config import settings

async def setup_postgres():
    """Настройка PostgreSQL: создание БД, пользователей, привилегий"""
    print("🛠️ Настройка PostgreSQL...")
    
    try:
        # Подключаемся к системной БД
        conn = await asyncpg.connect(
            user='postgres',
            password='postgres',  # или ваш пароль
            host='localhost',
            port=5432,
            database='postgres'
        )
        
        # 1. Создаем базу данных если не существует
        print("📦 Проверяем базу данных...")
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            settings.POSTGRES_DB
        )
        
        if not db_exists:
            print(f"Создаем базу данных: {settings.POSTGRES_DB}")
            await conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            print("✅ База данных создана")
        
        # 2. Создаем пользователя если нужно
        print("👤 Проверяем пользователя...")
        user_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1",
            settings.POSTGRES_USER
        )
        
        if not user_exists and settings.POSTGRES_USER != 'postgres':
            print(f"Создаем пользователя: {settings.POSTGRES_USER}")
            await conn.execute(
                f"CREATE USER {settings.POSTGRES_USER} WITH PASSWORD '{settings.POSTGRES_PASSWORD}'"
            )
            print("✅ Пользователь создан")
        
        # 3. Даем привилегии
        if settings.POSTGRES_USER != 'postgres':
            print("🔑 Назначаем привилегии...")
            await conn.execute(
                f'GRANT ALL PRIVILEGES ON DATABASE "{settings.POSTGRES_DB}" TO {settings.POSTGRES_USER}'
            )
            print("✅ Привилегии назначены")
        
        await conn.close()
        
        # 4. Подключаемся к нашей БД и создаем расширения
        print("🔌 Подключаемся к созданной БД...")
        db_conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
        
        # Создаем полезные расширения
        await db_conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        await db_conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
        
        print("✅ Расширения созданы")
        await db_conn.close()
        
        print("\n🎉 Настройка PostgreSQL завершена успешно!")
        print(f"База данных: {settings.POSTGRES_DB}")
        print(f"Пользователь: {settings.POSTGRES_USER}")
        print(f"Хост: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(setup_postgres())