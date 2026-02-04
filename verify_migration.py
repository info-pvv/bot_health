# verify_migration.py
import os
import sqlite3
import asyncio
import asyncpg


async def verify_migration():
    """Проверка корректности миграции"""
    print("🔍 Проверка миграции данных...")
    
    # Подключаемся к SQLite
    sqlite_conn = sqlite3.connect('health.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Подключаемся к PostgreSQL
    pg_conn = await asyncpg.connect(
        user='postgres',
        password='b4H78Q9z)',
        host='localhost',
        port=5432,
        database='health_tracker'
    )
    
    tables = ['users', 'fio', 'health', 'disease', 'id_status']
    
    print("📊 Сравнение количества записей:")
    print("-" * 50)
    print(f"{'Таблица':<15} {'SQLite':<10} {'PostgreSQL':<10} {'Статус':<10}")
    print("-" * 50)
    
    all_ok = True
    
    for table in tables:
        # Количество в SQLite
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = sqlite_cursor.fetchone()[0]
        
        # Количество в PostgreSQL
        pg_count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        
        status = "✅ OK" if sqlite_count == pg_count else f"❌ Разница: {abs(sqlite_count - pg_count)}"
        if sqlite_count != pg_count:
            all_ok = False
        
        print(f"{table:<15} {sqlite_count:<10} {pg_count:<10} {status:<10}")
    
    print("-" * 50)
    
    # Закрываем соединения
    sqlite_conn.close()
    await pg_conn.close()
    
    if all_ok:
        print("\n🎉 Все данные успешно мигрированы!")
    else:
        print("\n⚠️  Обнаружены расхождения в количестве записей")
    
    return all_ok

if __name__ == "__main__":
    asyncio.run(verify_migration())