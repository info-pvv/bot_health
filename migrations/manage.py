# migrations/manage.py
import asyncio
import sys
import os
import importlib.util

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

try:
    from app.models.database import engine
    from app.core.config import settings
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("💡 Убедитесь что:")
    print("   1. Вы находитесь в корневой папке проекта")
    print("   2. Структура проекта корректна")
    print("   3. Установлены все зависимости")
    sys.exit(1)

class MigrationManager:
    """Менеджер миграций без Alembic"""
    
    def __init__(self):
        self.migrations_dir = "migrations/versions"
        self.migrations = self._load_migrations()
    
    def _load_migrations(self):
        """Загрузить миграции из файлов"""
        migrations = [
            {
                'id': '001_initial',
                'description': 'Initial database schema',
                'up': [
                    # Таблица users
                    """
                    CREATE TABLE Users (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL UNIQUE,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,
                    
                    # Таблица fio
                    """
                    CREATE TABLE FIO (
                        user_id BIGINT PRIMARY KEY,
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        patronymic_name VARCHAR(255),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,
                    
                    # Таблица health
                    """
                    CREATE TABLE health (
                        user_id BIGINT PRIMARY KEY,
                        status TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,
                    
                    # Таблица disease
                    """
                    CREATE TABLE disease (
                        user_id BIGINT PRIMARY KEY,
                        disease TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """,
                    
                    # Таблица sectors
                    """
                    CREATE TABLE sectors (
                        sector_id BIGINT PRIMARY KEY,
                        name VARCHAR(255)
                    );
                    """,
                    
                    # Таблица id_status
                    """
                    CREATE TABLE id_status (
                        user_id BIGINT PRIMARY KEY,
                        enable_report BOOLEAN DEFAULT FALSE,
                        enable_admin BOOLEAN DEFAULT FALSE,
                        sector_id BIGINT
                    );
                    """
                ],
                'down': [
                    "DROP TABLE IF EXISTS id_status;",
                    "DROP TABLE IF EXISTS sectors;",
                    "DROP TABLE IF EXISTS disease;",
                    "DROP TABLE IF EXISTS health;",
                    "DROP TABLE IF EXISTS fio;",
                    "DROP TABLE IF EXISTS users;"
                ]
            }
        ]
        
        # Загрузка дополнительных миграций из файлов
        if os.path.exists(self.migrations_dir):
            for filename in sorted(os.listdir(self.migrations_dir)):
                if filename.endswith('.py') and filename != '__init__.py':
                    migration_id = filename[:-3]
                    filepath = os.path.join(self.migrations_dir, filename)
                    
                    spec = importlib.util.spec_from_file_location(migration_id, filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'migration'):
                        migrations.append(module.migration)
        
        return sorted(migrations, key=lambda x: x['id'])

    # ... остальные методы без изменений
    
    async def migrate_up(self):
        """Применить все миграции"""
        print("🔼 Применение миграций...")
        print(f"📊 База данных: {settings.POSTGRES_DB}")
        print(f"🔗 Подключение: {settings.POSTGRES_USER}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        
        # Создаем таблицу для отслеживания миграций
        await self._create_migrations_table()
        
        async with engine.begin() as conn:
            # Получаем примененные миграции
            try:
                result = await conn.execute(
                    text("SELECT migration_id FROM applied_migrations")
                )
                applied = {row[0] for row in result.fetchall()}
            except:
                applied = set()
            
            # Применяем новые миграции
            applied_count = 0
            for migration in self.migrations:
                if migration['id'] not in applied:
                    print(f"  📝 Применяем: {migration['id']} - {migration['description']}")
                    
                    for i, sql in enumerate(migration['up'], 1):
                        try:
                            await conn.execute(text(sql))
                        except Exception as e:
                            print(f"    ⚠️ Ошибка в команде {i}: {e}")
                    
                    # Отмечаем как примененную
                    try:
                        await conn.execute(
                            text("INSERT INTO applied_migrations (migration_id) VALUES (:id)"),
                            {"id": migration['id']}
                        )
                        applied_count += 1
                    except Exception as e:
                        print(f"    ⚠️ Ошибка записи статуса: {e}")
            
            if applied_count > 0:
                print(f"✅ Применено миграций: {applied_count}")
            else:
                print("✅ Все миграции уже применены")
    
    async def migrate_down(self, migration_id=None):
        """Откатить миграции"""
        print("🔽 Откат миграций...")
        
        async with engine.begin() as conn:
            if migration_id:
                # Откатить конкретную миграцию
                migration = next((m for m in self.migrations if m['id'] == migration_id), None)
                if migration:
                    print(f"  📝 Откатываем: {migration_id}")
                    for sql in reversed(migration['down']):
                        try:
                            await conn.execute(text(sql))
                        except Exception as e:
                            print(f"    ⚠️ Ошибка: {e}")
                    
                    try:
                        await conn.execute(
                            text("DELETE FROM applied_migrations WHERE migration_id = :id"),
                            {"id": migration_id}
                        )
                    except:
                        pass
            else:
                # Откатить все миграции
                for migration in reversed(self.migrations):
                    print(f"  📝 Откатываем: {migration['id']}")
                    for sql in migration['down']:
                        try:
                            await conn.execute(text(sql))
                        except Exception as e:
                            print(f"    ⚠️ Ошибка: {e}")
                
                try:
                    await conn.execute(text("DROP TABLE IF EXISTS applied_migrations"))
                except:
                    pass
            
            print("✅ Миграции откачены")
    
    async def status(self):
        """Показать статус миграций"""
        print("📊 Статус миграций...")
        
        try:
            async with engine.connect() as conn:
                # Проверяем таблицу миграций
                result = await conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'applied_migrations'
                """))
                
                if result.fetchone():
                    result = await conn.execute(
                        text("SELECT migration_id, applied_at FROM applied_migrations ORDER BY applied_at")
                    )
                    applied = result.fetchall()
                    
                    print(f"✅ Таблица миграций существует")
                    print(f"📋 Примененные миграции ({len(applied)}):")
                    for row in applied:
                        print(f"  • {row[0]} - {row[1]}")
                else:
                    print("❌ Таблица миграций не существует")
                
                # Показываем все таблицы
                result = await conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_name NOT LIKE 'pg_%'
                    ORDER BY table_name
                """))
                
                tables = result.fetchall()
                print(f"\n📊 Таблицы в базе данных ({len(tables)}):")
                for table in tables:
                    print(f"  • {table[0]}")
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    async def _create_migrations_table(self):
        """Создать таблицу для отслеживания миграций"""
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS applied_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_id VARCHAR(50) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

async def main():
    manager = MigrationManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'up':
            await manager.migrate_up()
        elif command == 'down':
            migration_id = sys.argv[2] if len(sys.argv) > 2 else None
            await manager.migrate_down(migration_id)
        elif command == 'status':
            await manager.status()
        elif command == 'create':
            if len(sys.argv) > 2:
                migration_name = sys.argv[2]
                await manager.create_migration(migration_name)
            else:
                print("❌ Укажите имя миграции: python manage.py create <имя>")
        else:
            print(f"❌ Неизвестная команда: {command}")
    else:
        print("📖 Использование:")
        print("  python migrations/manage.py up        - Применить миграции")
        print("  python migrations/manage.py down      - Откатить все миграции")
        print("  python migrations/manage.py down <id> - Откатить конкретную миграцию")
        print("  python migrations/manage.py status    - Показать статус миграций")

if __name__ == "__main__":
    asyncio.run(main())