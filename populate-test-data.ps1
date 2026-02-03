# populate-test-data.ps1
# Скрипт для наполнения базы данных тестовыми данными

param(
    [int]$UserCount = 50,
    [switch]$ClearExisting = $false,
    [switch]$DockerMode = $false
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Наполнение базы данных тестовыми данными" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Проверяем Python
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonPath) {
    Write-Host "Python не найден" -ForegroundColor Red
    exit 1
}

# Создаем скрипт для генерации тестовых данных
$testDataScript = @"
import asyncio
import sys
import os
import random
from faker import Faker
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import AsyncSessionLocal
from app.models.user import User, UserStatus, FIO, Health, Disease
from sqlalchemy import select, delete

fake = Faker('ru_RU')

# Секторы/чаты
SECTORS = [
    -1001567110550,  # стс
    -1001727372240,  # ЭТиВИ
    -1001764172286,  # тест
    -1001234567890,  # дополнительный 1
    -1000987654321   # дополнительный 2
]

# Статусы здоровья
HEALTH_STATUSES = [
    ("здоров", 0.6),      # 60% здоровы
    ("болен", 0.15),      # 15% больны
    ("отпуск", 0.1),      # 10% в отпуске
    ("удаленка", 0.08),   # 8% на удаленке
    ("отгул", 0.05),      # 5% в отгуле
    ("учеба", 0.02)       # 2% на учебе
]

# Заболевания (только для статуса "болен")
DISEASES = [
    ("орви", 0.4),
    ("ковид", 0.3),
    ("давление", 0.15),
    ("понос", 0.1),
    ("прочее", 0.05)
]

def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    return choices[-1][0]

async def generate_test_data(user_count=50, clear_existing=False):
    async with AsyncSessionLocal() as session:
        
        if clear_existing:
            Write-Host "Очистка существующих данных..." -ForegroundColor Yellow
            await session.execute(delete(Disease))
            await session.execute(delete(Health))
            await session.execute(delete(FIO))
            await session.execute(delete(UserStatus))
            await session.execute(delete(User))
            await session.commit()
        
        print(f"Генерация {user_count} тестовых пользователей...")
        
        generated_users = []
        
        for i in range(1, user_count + 1):
            user_id = 1000000 + i  # Уникальный ID
            
            # Генерация данных пользователя
            first_name = fake.first_name_male() if random.choice([True, False]) else fake.first_name_female()
            last_name = fake.last_name_male() if random.choice([True, False]) else fake.last_name_female()
            
            # Создаем username на основе имени и фамилии
            username = f"{last_name.lower()}_{first_name[0].lower()}"
            
            # Выбираем сектор
            sector = random.choice(SECTORS)
            
            # Админские права (10% пользователей - админы)
            is_admin = random.random() < 0.1
            
            # Статус отчета (90% в отчете)
            in_report = random.random() < 0.9
            
            # Создаем пользователя
            user = User(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username
            )
            session.add(user)
            
            # FIO
            fio = FIO(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                patronymic_name=fake.middle_name() if random.choice([True, False]) else ""
            )
            session.add(fio)
            
            # Статус
            user_status = UserStatus(
                user_id=user_id,
                enable_report=in_report,
                enable_admin=is_admin,
                sector=sector
            )
            session.add(user_status)
            
            # Статус здоровья
            health_status = weighted_choice(HEALTH_STATUSES)
            health = Health(
                user_id=user_id,
                status=health_status
            )
            session.add(health)
            
            # Заболевание (только если статус "болен")
            disease = ""
            if health_status == "болен":
                disease = weighted_choice(DISEASES)
            
            disease_record = Disease(
                user_id=user_id,
                disease=disease
            )
            session.add(disease_record)
            
            generated_users.append({
                "id": user_id,
                "name": f"{last_name} {first_name}",
                "sector": sector,
                "status": health_status,
                "disease": disease,
                "admin": is_admin,
                "in_report": in_report
            })
            
            # Коммитим каждые 10 пользователей
            if i % 10 == 0:
                await session.commit()
                print(f"Добавлено {i} пользователей...")
        
        # Финальный коммит
        await session.commit()
        
        # Выводим статистику
        print(f"\nГенерация завершена! Добавлено {len(generated_users)} пользователей.")
        print("\nСтатистика:")
        
        # По секторам
        sectors_stats = {}
        for user in generated_users:
            sector = user["sector"]
            sectors_stats[sector] = sectors_stats.get(sector, 0) + 1
        
        print("\nПо секторам:")
        for sector, count in sectors_stats.items():
            print(f"  Сектор {sector}: {count} пользователей")
        
        # По статусам здоровья
        health_stats = {}
        for user in generated_users:
            status = user["status"]
            health_stats[status] = health_stats.get(status, 0) + 1
        
        print("\nПо статусам здоровья:")
        for status, count in health_stats.items():
            percentage = (count / len(generated_users)) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        # Администраторы
        admins = [u for u in generated_users if u["admin"]]
        print(f"\nАдминистраторов: {len(admins)}")
        
        # В отчете
        in_report = [u for u in generated_users if u["in_report"]]
        print(f"В отчете: {len(in_report)} из {len(generated_users)}")
        
        # Примеры сгенерированных пользователей
        print(f"\nПримеры сгенерированных пользователей:")
        for i in range(min(5, len(generated_users))):
            user = generated_users[i]
            print(f"  {user['name']}: {user['status']}" + (f" ({user['disease']})" if user['disease'] else ""))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Генерация тестовых данных')
    parser.add_argument('--count', type=int, default=50, help='Количество пользователей')
    parser.add_argument('--clear', action='store_true', help='Очистить существующие данные')
    
    args = parser.parse_args()
    
    asyncio.run(generate_test_data(args.count, args.clear))
"@

# Проверяем, установлен ли Faker
Write-Host "`nПроверка зависимостей..." -ForegroundColor Green
$fakerInstalled = & $pythonPath -c "import faker" 2>&1

if ($fakerInstalled -match "ModuleNotFoundError") {
    Write-Host "  Установка Faker для генерации тестовых данных..." -ForegroundColor Yellow
    & $pythonPath -m pip install faker 2>&1 | Out-Null
    Write-Host "  Faker установлен" -ForegroundColor Green
}

# Сохраняем скрипт во временный файл
$tempFile = "generate_test_data_temp.py"
Set-Content -Path $tempFile -Value $testDataScript -Encoding UTF8

# Запускаем генерацию
Write-Host "`nЗапуск генерации тестовых данных..." -ForegroundColor Green

$clearFlag = if ($ClearExisting) { "--clear" } else { "" }
& $pythonPath $tempFile --count $UserCount $clearFlag

# Удаляем временный файл
Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Генерация тестовых данных завершена!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
