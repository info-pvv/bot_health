# migrate_data_compatible.py
import os
import sqlite3
import asyncio
import asyncpg
from datetime import datetime
from app.core.config import settings

async def migrate_data_compatible():
    """Миграция данных совместимая с вашими миграциями"""
    print("🔄 Миграция данных (совместимая версия)...")
    
    # Проверяем существование файла SQLite
    if not os.path.exists('health.db'):
        print("❌ Файл health.db не найден")
        return False
    
    print(f"📊 База данных: {settings.POSTGRES_DB}")
    print(f"🔗 Подключение: {settings.POSTGRES_USER}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    pg_config = {
        'user': settings.POSTGRES_USER,
        'password': settings.POSTGRES_PASSWORD,
        'host': settings.POSTGRES_HOST,
        'port': settings.POSTGRES_PORT,
        'database': settings.POSTGRES_DB
    }
    
    try:
        # Подключаемся к SQLite
        print("🔗 Подключение к SQLite...")
        sqlite_conn = sqlite3.connect('health.db')
        sqlite_conn.row_factory = sqlite3.Row
        
        # Подключаемся к PostgreSQL
        print("🔗 Подключение к PostgreSQL...")
        pg_conn = await asyncpg.connect(**pg_config)
        
        print("\n📊 Проверяем структуру таблиц в PostgreSQL...")
        
        # Проверяем, какие таблицы существуют в PostgreSQL
        existing_tables = await pg_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_table_names = {row['table_name'].lower() for row in existing_tables}
        print(f"Найдено таблиц в PostgreSQL: {len(existing_table_names)}")
        
        # Определяем соответствие между SQLite и PostgreSQL
        table_mapping = {
            'users': {
                'sqlite_name': 'Users',
                'pg_name': 'users',
                'columns_map': {
                    'id': 'id',
                    'user_id': 'user_id', 
                    'username': 'username',
                    'first_name': 'first_name',
                    'last_name': 'last_name'
                },
                'additional_columns': {
                    'created_at': datetime.now()
                }
            },
            'fio': {
                'sqlite_name': 'FIO',
                'pg_name': 'fio',
                'columns_map': {
                    'user_id': 'user_id',
                    'first_name': 'first_name',
                    'last_name': 'last_name',
                    'patronymic_name': 'patronymic_name'
                },
                'additional_columns': {
                    'updated_at': datetime.now()
                }
            },
            'health': {
                'sqlite_name': 'health',
                'pg_name': 'health',
                'columns_map': {
                    'id': 'user_id',  # В SQLite id = user_id
                    'status': 'status'
                },
                'additional_columns': {
                    'recorded_at': datetime.now()
                }
            },
            'disease': {
                'sqlite_name': 'disease',
                'pg_name': 'disease',
                'columns_map': {
                    'id': 'user_id',  # В SQLite id = user_id
                    'disease': 'disease'
                },
                'additional_columns': {
                    'recorded_at': datetime.now()
                }
            },
            'id_status': {
                'sqlite_name': 'id_status',
                'pg_name': 'id_status',
                'columns_map': {
                    'user_id': 'user_id',
                    'enable_report': 'enable_report',
                    'enable_admin': 'enable_admin',
                    'sector': 'sector_id'  # sector -> sector_id
                },
                'additional_columns': {}
            },
            'sectors': {
                'sqlite_name': 'sectors',
                'pg_name': 'sectors',
                'columns_map': {
                    'sector': 'sector_id',  # sector -> sector_id
                    'name': 'name'
                },
                'additional_columns': {}
            }
        }
        
        total_migrated = 0
        
        # Мигрируем в правильном порядке (сначала sectors, потом остальные)
        migration_order = ['sectors', 'users', 'fio', 'health', 'disease', 'id_status']
        
        for table_key in migration_order:
            config = table_mapping[table_key]
            sqlite_table = config['sqlite_name']
            pg_table = config['pg_name']
            
            print(f"\n{'='*50}")
            print(f"📋 Таблица: {sqlite_table} -> {pg_table}")
            
            # Проверяем существование таблицы в SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (sqlite_table,))
            if not sqlite_cursor.fetchone():
                print(f"  ⚠️  Таблица {sqlite_table} не найдена в SQLite")
                continue
            
            # Проверяем существование таблицы в PostgreSQL
            if pg_table.lower() not in existing_table_names:
                print(f"  ⚠️  Таблица {pg_table} не найдена в PostgreSQL")
                continue
            
            # Получаем данные из SQLite
            sqlite_columns = list(config['columns_map'].keys())
            sql_select = f"SELECT {', '.join(sqlite_columns)} FROM {sqlite_table}"
            
            try:
                sqlite_cursor.execute(sql_select)
                rows = sqlite_cursor.fetchall()
            except Exception as e:
                print(f"  ❌ Ошибка чтения из SQLite: {e}")
                continue
            
            if not rows:
                print(f"  ℹ️  Таблица {sqlite_table} пустая")
                continue
            
            print(f"  📊 Найдено записей: {len(rows)}")
            
            # Подготавливаем колонки для PostgreSQL
            pg_columns = list(config['columns_map'].values()) + list(config['additional_columns'].keys())
            
            # Мигрируем данные
            migrated_count = 0
            error_count = 0
            
            for row in rows:
                try:
                    # Подготавливаем значения
                    values = []
                    
                    # Значения из SQLite
                    for i, sqlite_col in enumerate(sqlite_columns):
                        value = row[i]
                        
                        # Преобразование типов
                        if value is not None:
                            # Boolean преобразование
                            if sqlite_col in ['enable_report', 'enable_admin']:
                                value = bool(value)
                            # Очистка строк
                            elif isinstance(value, str):
                                value = value.strip()
                                if len(value) > 255:
                                    value = value[:255]
                            # Для sector -> sector_id преобразование не нужно, оставляем как есть
                        
                        values.append(value)
                    
                    # Добавляем дополнительные значения
                    for additional_value in config['additional_columns'].values():
                        values.append(additional_value)
                    
                    # Создаем SQL запрос
                    placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
                    columns_str = ', '.join(pg_columns)
                    
                    # Определяем primary key для ON CONFLICT
                    if table_key == 'users':
                        conflict_column = 'id'
                    elif table_key in ['fio', 'health', 'disease', 'id_status']:
                        conflict_column = 'user_id'
                    elif table_key == 'sectors':
                        conflict_column = 'sector_id'
                    else:
                        conflict_column = None
                    
                    # Создаем запрос
                    if conflict_column:
                        query = f"""
                            INSERT INTO {pg_table} ({columns_str}) 
                            VALUES ({placeholders}) 
                            ON CONFLICT ({conflict_column}) DO NOTHING
                        """
                    else:
                        query = f"INSERT INTO {pg_table} ({columns_str}) VALUES ({placeholders})"
                    
                    await pg_conn.execute(query, *values)
                    migrated_count += 1
                    
                except asyncpg.UniqueViolationError:
                    # Игнорируем дубликаты
                    pass
                except asyncpg.ForeignKeyViolationError as e:
                    print(f"    ⚠️  Ошибка внешнего ключа: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"    ⚠️  Ошибка: {e}")
                    error_count += 1
            
            # Выводим результат
            if error_count == 0:
                print(f"  ✅ Успешно мигрировано: {migrated_count}/{len(rows)}")
            else:
                print(f"  ⚠️  Мигрировано: {migrated_count}/{len(rows)} (ошибок: {error_count})")
            
            total_migrated += migrated_count
        
        # Закрываем соединения
        sqlite_conn.close()
        await pg_conn.close()
        
        print(f"\n{'='*50}")
        print("🎉 МИГРАЦИЯ ЗАВЕРШЕНА!")
        print(f"📊 Всего мигрировано записей: {total_migrated}")
        
        # Показываем итоговую статистику
        await show_final_stats(pg_config)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def show_final_stats(pg_config):
    """Показать итоговую статистику"""
    print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    print("-" * 40)
    
    try:
        pg_conn = await asyncpg.connect(**pg_config)
        
        tables = ['users', 'fio', 'health', 'disease', 'id_status', 'sectors']
        
        for table in tables:
            try:
                count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table:<15}: {count:>4} записей")
            except:
                print(f"  {table:<15}: таблица не найдена")
        
        await pg_conn.close()
        
    except Exception as e:
        print(f"  ❌ Ошибка получения статистики: {e}")
    
    print("-" * 40)

async def check_tables_before_migration():
    """Проверить таблицы перед миграцией"""
    print("🔍 Проверка перед миграцией...")
    
    pg_config = {
        'user': settings.POSTGRES_USER,
        'password': settings.POSTGRES_PASSWORD,
        'host': settings.POSTGRES_HOST,
        'port': settings.POSTGRES_PORT,
        'database': settings.POSTGRES_DB
    }
    
    try:
        pg_conn = await asyncpg.connect(**pg_config)
        
        # Проверяем существование таблиц
        required_tables = ['users', 'fio', 'health', 'disease', 'id_status', 'sectors']
        
        print("📋 Требуемые таблицы:")
        for table in required_tables:
            exists = await pg_conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                table
            )
            status = "✅ найдена" if exists else "❌ отсутствует"
            print(f"  {table}: {status}")
        
        # Проверяем структуру таблиц
        print(f"\n📊 Структура таблиц:")
        for table in required_tables:
            try:
                columns = await pg_conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1 ORDER BY ordinal_position",
                    table
                )
                print(f"\n{table}:")
                for col in columns:
                    print(f"  • {col['column_name']} ({col['data_type']})")
            except:
                print(f"\n{table}: не доступна")
        
        await pg_conn.close()
        
        print(f"\n{'='*50}")
        print("💡 Если таблицы отсутствуют, выполните:")
        print("python migrations/manage.py down")
        print("python migrations/manage.py up")
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")

async def main():
    """Основная функция"""
    print("🚀 МИГРАЦИЯ ДАННЫХ ИЗ SQLite В PostgreSQL")
    print("=" * 50)
    
    # Проверяем наличие SQLite файла
    if not os.path.exists('health.db'):
        print("❌ Файл health.db не найден!")
        print("💡 Поместите файл health.db в текущую директорию")
        return
    
    # Проверяем таблицы в PostgreSQL
    await check_tables_before_migration()
    
    confirm = input(f"\n{'='*50}\nПродолжить миграцию данных? (yes/no): ")
    
    if confirm.lower() == 'yes':
        print(f"\n{'='*50}")
        success = await migrate_data_compatible()
        
        if success:
            print(f"\n{'='*50}")
            print("✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        else:
            print(f"\n{'='*50}")
            print("❌ МИГРАЦИЯ ЗАВЕРШИЛАСЬ С ОШИБКАМИ")
    else:
        print("❌ Миграция отменена")

if __name__ == "__main__":
    asyncio.run(main())