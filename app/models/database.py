# app/models/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import asyncpg

# Используем PostgreSQL
DATABASE_URL = settings.DATABASE_URL

# Создаем асинхронный движок для PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True  # Проверка соединения перед использованием
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """Зависимость для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """Инициализация базы данных (создание если не существует)"""
    try:
        # Подключаемся к системной БД для создания нашей БД
        sys_conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database='postgres'
        )
        
        # Проверяем существование нашей БД
        db_exists = await sys_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            settings.POSTGRES_DB
        )
        
        if not db_exists:
            print(f"📦 Создаем базу данных: {settings.POSTGRES_DB}")
            await sys_conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
            print(f"✅ База данных создана")
        
        await sys_conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False