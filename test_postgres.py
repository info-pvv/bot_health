# test_postgres.py
import asyncio
import asyncpg
from app.core.config import settings

async def test_postgres():
    print("🧪 Тестирование подключения к PostgreSQL...")
    print(f"Хост: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"Пользователь: {settings.POSTGRES_USER}")
    print(f"База данных: {settings.POSTGRES_DB}")
    
    try:
        # Пробуем разные варианты подключения
        test_cases = [
            {
                "user": settings.POSTGRES_USER,
                "password": settings.POSTGRES_PASSWORD,
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
                "database": "postgres"  # Пробуем подключиться к системной БД
            },
            {
                "user": "postgres",  # Стандартный пользователь
                "password": settings.POSTGRES_PASSWORD,
                "host": "localhost",
                "port": "5432",
                "database": "postgres"
            },
            {
                "user": "postgres",
                "password": "",  # Пустой пароль
                "host": "localhost",
                "port": "5432",
                "database": "postgres"
            }
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n🔍 Попытка #{i}: {params['user']}@{params['host']}:{params['port']}")
            try:
                conn = await asyncpg.connect(**params)
                print(f"✅ Успешное подключение!")
                
                # Проверяем версию
                version = await conn.fetchval('SELECT version()')
                print(f"📋 Версия PostgreSQL: {version.split(',')[0]}")
                
                # Проверяем существование нашей БД
                db_exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1", 
                    settings.POSTGRES_DB
                )
                
                if db_exists:
                    print(f"✅ База данных '{settings.POSTGRES_DB}' существует")
                else:
                    print(f"❌ База данных '{settings.POSTGRES_DB}' не существует")
                
                await conn.close()
                return True
                
            except Exception as e:
                print(f"❌ Ошибка: {str(e)[:100]}...")
                continue
                
        print("\n❌ Все попытки подключения неудачны")
        print("\n💡 Рекомендации:")
        print("1. Убедитесь что PostgreSQL запущен")
        print("2. Проверьте пароль (часто 'postgres' или пустой)")
        print("3. Проверьте порт (обычно 5432)")
        print("4. Проверьте .env файл")
        return False
        
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_postgres())