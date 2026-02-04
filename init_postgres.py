# init_postgres.py
import asyncio
from app.models.database import engine, Base
from sqlalchemy import text

async def init_postgres():
    """Инициализация PostgreSQL без Alembic"""
    print("🚀 Инициализация PostgreSQL...")
    
    try:
        # Создаем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Таблицы созданы")
        
        # Проверяем
        async with engine.connect() as conn:
            # Проверяем версию PostgreSQL
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"📋 PostgreSQL: {version.split(',')[0]}")
            
            # Проверяем таблицы
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            print(f"📊 Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"  • {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(init_postgres())