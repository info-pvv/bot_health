# init-database.ps1
# Скрипт для инициализации базы данных

param(
    [string]$EnvFile = ".env",
    [switch]$Reset = $false,
    [switch]$TestData = $false,
    [switch]$DockerMode = $false
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Инициализация базы данных" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Загрузка переменных окружения
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "Файл $EnvFile не найден. Используются переменные окружения системы." -ForegroundColor Yellow
}

# Получение параметров подключения к БД
$dbUser = [Environment]::GetEnvironmentVariable("POSTGRES_USER", "Process")
$dbPassword = [Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "Process")
$dbHost = [Environment]::GetEnvironmentVariable("POSTGRES_HOST", "Process")
$dbPort = [Environment]::GetEnvironmentVariable("POSTGRES_PORT", "Process")
$dbName = [Environment]::GetEnvironmentVariable("POSTGRES_DB", "Process")

if (-not $dbUser -or -not $dbPassword -or -not $dbHost) {
    Write-Host "Ошибка: Не указаны параметры подключения к БД" -ForegroundColor Red
    exit 1
}

Write-Host "`nПараметры подключения:" -ForegroundColor Yellow
Write-Host "  Хост: $dbHost" -ForegroundColor Gray
Write-Host "  Порт: $dbPort" -ForegroundColor Gray
Write-Host "  БД: $dbName" -ForegroundColor Gray
Write-Host "  Пользователь: $dbUser" -ForegroundColor Gray

# Проверка доступности PostgreSQL
Write-Host "`nПроверка доступности PostgreSQL..." -ForegroundColor Green

try {
    # Проверяем, установлен ли psql
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $psqlPath) {
        Write-Host "psql не найден. Установите PostgreSQL или добавьте в PATH." -ForegroundColor Red
        exit 1
    }
    
    # Проверяем подключение
    $env:PGPASSWORD = $dbPassword
    $connectionTest = & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "SELECT 1;" -t 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Подключение к PostgreSQL успешно" -ForegroundColor Green
    } else {
        Write-Host "  Ошибка подключения к PostgreSQL: $connectionTest" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "  Ошибка: $_" -ForegroundColor Red
    exit 1
}

# Создание базы данных (если не существует)
Write-Host "`nСоздание базы данных..." -ForegroundColor Green

$dbExists = & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$dbName';" -t 2>&1

if ($dbExists -match "1") {
    Write-Host "  База данных '$dbName' уже существует" -ForegroundColor Yellow
    
    if ($Reset) {
        Write-Host "  Удаление существующей базы данных..." -ForegroundColor Yellow
        & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "DROP DATABASE IF EXISTS $dbName WITH (FORCE);" 2>&1 | Out-Null
        
        Write-Host "  Создание новой базы данных..." -ForegroundColor Green
        & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "CREATE DATABASE $dbName;" 2>&1 | Out-Null
        Write-Host "  База данных создана успешно" -ForegroundColor Green
    }
} else {
    Write-Host "  Создание базы данных '$dbName'..." -ForegroundColor Green
    & psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "CREATE DATABASE $dbName;" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  База данных создана успешно" -ForegroundColor Green
    } else {
        Write-Host "  Ошибка создания базы данных" -ForegroundColor Red
        exit 1
    }
}

# Инициализация Alembic и создание таблиц
Write-Host "`nИнициализация Alembic..." -ForegroundColor Green

try {
    # Проверяем, установлен ли Python и зависимости
    $pythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonPath) {
        $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if (-not $pythonPath) {
        Write-Host "Python не найден" -ForegroundColor Red
        exit 1
    }
    
    # Инициализируем Alembic (если еще не инициализирован)
    if (-not (Test-Path "alembic.ini")) {
        Write-Host "  Инициализация Alembic..." -ForegroundColor Green
        & $pythonPath -m alembic init alembic 2>&1 | Out-Null
    }
    
    # Обновляем alembic.ini с правильными параметрами подключения
    $alembicIni = Get-Content -Path "alembic.ini" -Raw
    $alembicIni = $alembicIni -replace "sqlalchemy.url = .*", "sqlalchemy.url = postgresql+asyncpg://$dbUser`:$dbPassword@$dbHost`:$dbPort/$dbName"
    Set-Content -Path "alembic.ini" -Value $alembicIni -Encoding UTF8
    
    # Создаем миграции
    Write-Host "  Создание миграций..." -ForegroundColor Green
    & $pythonPath -m alembic revision --autogenerate -m "Initial migration" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Предупреждение: Не удалось создать миграции" -ForegroundColor Yellow
    }
    
    # Применяем миграции
    Write-Host "  Применение миграций..." -ForegroundColor Green
    & $pythonPath -m alembic upgrade head 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Миграции успешно применены" -ForegroundColor Green
    } else {
        Write-Host "  Ошибка применения миграций" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "  Ошибка: $_" -ForegroundColor Red
    exit 1
}

# Наполнение тестовыми данными (если нужно)
if ($TestData) {
    Write-Host "`nНаполнение тестовыми данными..." -ForegroundColor Green
    
    # Создаем Python скрипт для наполнения данными
    $populateScript = @"
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import AsyncSessionLocal, engine
from app.models.user import User, UserStatus, FIO, Health, Disease
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random

async def populate_test_data():
    async with AsyncSessionLocal() as session:
        # Тестовые пользователи
        test_users = [
            {
                "user_id": 1001,
                "first_name": "Иван",
                "last_name": "Иванов",
                "username": "ivanov_i",
                "sector": -1001567110550,
                "admin": True
            },
            {
                "user_id": 1002,
                "first_name": "Петр",
                "last_name": "Петров",
                "username": "petrov_p",
                "sector": -1001567110550,
                "admin": False
            },
            {
                "user_id": 1003,
                "first_name": "Мария",
                "last_name": "Сидорова",
                "username": "sidorova_m",
                "sector": -1001727372240,
                "admin": False
            },
            {
                "user_id": 1004,
                "first_name": "Алексей",
                "last_name": "Кузнецов",
                "username": "kuznetsov_a",
                "sector": -1001727372240,
                "admin": False
            },
            {
                "user_id": 1005,
                "first_name": "Елена",
                "last_name": "Смирнова",
                "username": "smirnova_e",
                "sector": -1001764172286,
                "admin": True
            }
        ]
        
        statuses = ["здоров", "болен", "отпуск", "удаленка", "отгул"]
        diseases = ["орви", "ковид", "давление", "понос", "прочее", ""]
        
        for user_data in test_users:
            # Проверяем, существует ли пользователь
            result = await session.execute(
                select(User).where(User.user_id == user_data["user_id"])
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                # Создаем пользователя
                user = User(
                    user_id=user_data["user_id"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    username=user_data["username"]
                )
                session.add(user)
                await session.flush()
                
                # FIO
                fio = FIO(
                    user_id=user_data["user_id"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    patronymic_name=""
                )
                session.add(fio)
                
                # Статус
                status = UserStatus(
                    user_id=user_data["user_id"],
                    enable_report=True,
                    enable_admin=user_data["admin"],
                    sector=user_data["sector"]
                )
                session.add(status)
                
                # Здоровье
                health_status = random.choice(statuses)
                health = Health(
                    user_id=user_data["user_id"],
                    status=health_status
                )
                session.add(health)
                
                # Заболевание
                disease = Disease(
                    user_id=user_data["user_id"],
                    disease=random.choice(diseases) if health_status == "болен" else ""
                )
                session.add(disease)
        
        await session.commit()
        print("Тестовые данные успешно добавлены!")

if __name__ == "__main__":
    asyncio.run(populate_test_data())
"@

    Set-Content -Path "populate_test_data.py" -Value $populateScript -Encoding UTF8
    
    Write-Host "  Запуск скрипта наполнения..." -ForegroundColor Green
    & $pythonPath populate_test_data.py 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Тестовые данные успешно добавлены" -ForegroundColor Green
    } else {
        Write-Host "  Ошибка добавления тестовых данных" -ForegroundColor Yellow
    }
    
    # Удаляем временный файл
    Remove-Item -Path "populate_test_data.py" -Force -ErrorAction SilentlyContinue
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Инициализация базы данных завершена!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "`nДля запуска API выполните:" -ForegroundColor Yellow
Write-Host "  uvicorn main:app --reload" -ForegroundColor White
Write-Host "`nДля запуска бота выполните:" -ForegroundColor Yellow
Write-Host "  python bot.py" -ForegroundColor White

if ($DockerMode) {
    Write-Host "`nДля запуска через Docker выполните:" -ForegroundColor Yellow
    Write-Host "  docker-compose up -d" -ForegroundColor White
}
