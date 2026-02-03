
## 1. **init-project.ps1** - Основной скрипт инициализации проекта

#```powershell
# init-project.ps1
# Скрипт для инициализации проекта Employee Health Tracker

param(
    [string]$ProjectName = "employee-health-tracker",
    [switch]$UseDocker = $false,
    [switch]$InitDB = $false,
    [switch]$SkipTelegram = $false
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Инициализация проекта Employee Health Tracker" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Создание структуры проекта
Write-Host "`n1. Создание структуры проекта..." -ForegroundColor Green

$projectStructure = @"
$ProjectName/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── admin.py
│   │   │   └── users.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── user.py
│   │   └── health.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── health.py
│   └── services/
│       ├── __init__.py
│       ├── user_service.py
│       ├── health_service.py
│       └── admin_service.py
├── alembic/
│   ├── __init__.py
│   ├── versions/
│   ├── env.py
│   ├── script.py.mako
│   └── README
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── main.py
├── bot.py
├── config.py
├── init-database.ps1
├── populate-test-data.ps1
└── README.md
"@

Write-Host "Структура проекта:" -ForegroundColor Yellow
Write-Host $projectStructure

# Создание директорий
$directories = @(
    "app",
    "app/api",
    "app/api/routes",
    "app/core",
    "app/models",
    "app/schemas",
    "app/services",
    "alembic",
    "alembic/versions"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Создана директория: $dir" -ForegroundColor Gray
    }
}

# 2. Создание файлов конфигурации
Write-Host "`n2. Создание файлов конфигурации..." -ForegroundColor Green

# .env.example
$envExample = @"
# Database Configuration
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_strong_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=health_tracker

# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_bot_token_here

# API Configuration
SECRET_KEY=your_secret_key_for_jwt_tokens
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: Redis for caching (if needed)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=

# Logging
LOG_LEVEL=INFO
"@

Set-Content -Path ".env.example" -Value $envExample
Write-Host "  Создан: .env.example" -ForegroundColor Gray

# .gitignore
$gitignore = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite3

# Environment variables
.env
.env.local

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore
*.dockerfile
"@

Set-Content -Path ".gitignore" -Value $gitignore
Write-Host "  Создан: .gitignore" -ForegroundColor Gray

# requirements.txt
$requirements = @"
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.13.0
psycopg2-binary==2.9.9

# Telegram Bot
aiogram==2.25.1
apscheduler==3.10.4

# Environment & Configuration
python-dotenv==1.0.0
pydantic-settings==2.1.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HTTP Client
aiohttp==3.9.1
httpx==0.25.1

# Utilities
pytz==2023.3.post1
tzlocal==5.2

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Development
black==23.11.0
flake8==6.1.0
pre-commit==3.5.0
"@

Set-Content -Path "requirements.txt" -Value $requirements
Write-Host "  Создан: requirements.txt" -ForegroundColor Gray

# 3. Создание Docker файлов
if ($UseDocker) {
    Write-Host "`n3. Настройка Docker..." -ForegroundColor Green
    
    # Dockerfile
    $dockerfile = @"
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание не-root пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"@

    Set-Content -Path "Dockerfile" -Value $dockerfile
    Write-Host "  Создан: Dockerfile" -ForegroundColor Gray
    
    # docker-compose.yml
    $dockerCompose = @"
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: health_tracker_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_DB: ${POSTGRES_DB:-health_tracker}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-admin}"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  api:
    build: .
    container_name: health_tracker_api
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-health_tracker}
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN}
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
  
  bot:
    build: .
    container_name: health_tracker_bot
    command: python bot.py
    volumes:
      - .:/app
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-health_tracker}
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN}
    depends_on:
      - api
    restart: unless-stopped
  
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: health_tracker_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@healthtracker.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
"@

    Set-Content -Path "docker-compose.yml" -Value $dockerCompose
    Write-Host "  Создан: docker-compose.yml" -ForegroundColor Gray
    
    # init.sql для инициализации БД
    $initSql = @"
-- Инициализация базы данных для Employee Health Tracker
-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Комментарии к таблицам
COMMENT ON DATABASE health_tracker IS 'База данных для отслеживания состояния здоровья сотрудников';

-- Создание таблиц уже будет выполнено через Alembic
-- Этот файл можно использовать для начального наполнения тестовыми данными

-- Тестовые данные для администраторов (при необходимости)
-- INSERT INTO users (user_id, first_name, last_name, username) VALUES 
-- (123456789, 'Admin', 'User', 'admin_user');
-- 
-- INSERT INTO id_status (user_id, enable_report, enable_admin, sector) VALUES 
-- (123456789, true, true, -1000000000000);
"@

    Set-Content -Path "init.sql" -Value $initSql
    Write-Host "  Создан: init.sql" -ForegroundColor Gray
}

# 4. Создание основных Python файлов
Write-Host "`n4. Создание Python файлов..." -ForegroundColor Green

# config.py (для совместимости с текущим ботом)
$configPy = @"
# config.py
# Конфигурационный файл для Telegram бота (для обратной совместимости)

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Настройки отчета
REPORT_TIME = "07:30"  # Время отправки отчета
REPORT_TIMEZONE = "Europe/Moscow"  # Часовой пояс

# Список статусов здоровья
HEALTH_STATUSES = [
    "здоров",
    "болен",
    "отпуск",
    "учеба",
    "удаленка",
    "отгул"
]

# Список заболеваний
DISEASES = [
    "орви",
    "ковид",
    "давление",
    "понос",
    "прочее"
]

# Секторы/чаты для отчетов
SECTORS = {
    "sts": -1001567110550,
    "etivi": -1001727372240,
    "test": -1001764172286
}

# Настройки API
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
API_TIMEOUT = 30
"@

Set-Content -Path "config.py" -Value $configPy
Write-Host "  Создан: config.py" -ForegroundColor Gray

# 5. Создание вспомогательных скриптов
Write-Host "`n5. Создание вспомогательных скриптов..." -ForegroundColor Green

# Скрипт для инициализации базы данных
$initDbScript = @'
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
'@

Set-Content -Path "init-database.ps1" -Value $initDbScript
Write-Host "  Создан: init-database.ps1" -ForegroundColor Gray

# Скрипт для наполнения тестовыми данными
$populateTestDataScript = @'
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
'@

Set-Content -Path "populate-test-data.ps1" -Value $populateTestDataScript
Write-Host "  Создан: populate-test-data.ps1" -ForegroundColor Gray

# 6. Создание README.md
Write-Host "`n6. Создание документации..." -ForegroundColor Green

$readme = @"
# Employee Health Tracker

Система для отслеживания статусов здоровья сотрудников через Telegram бот и REST API.

## 🚀 Быстрый старт

### 1. Настройка окружения

```powershell
# Клонируйте проект (если нужно)
# git clone <repository-url>
# cd employee-health-tracker

# Инициализируйте проект
.\init-project.ps1

# Скопируйте файл окружения и настройте его
Copy-Item .env.example .env
# Отредактируйте .env файл, указав свои настройки
```

### 2. Настройка базы данных

#### Вариант A: С использованием Docker (рекомендуется)

```powershell
# Запустите базу данных и вспомогательные сервисы
docker-compose up -d postgres pgadmin

# Инициализируйте базу данных
.\init-database.ps1 -DockerMode
```

#### Вариант B: Без Docker

1. Установите PostgreSQL 15+
2. Создайте базу данных
3. Настройте параметры подключения в `.env`
4. Выполните:
```powershell
.\init-database.ps1
```

### 3. Установка зависимостей

```powershell
# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте виртуальное окружение
# Для Windows:
.\venv\Scripts\activate
# Для Linux/Mac:
# source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 4. Запуск приложений

#### Запуск REST API:
```powershell
uvicorn main:app --reload
```
API будет доступно по адресу: http://localhost:8000
Документация: http://localhost:8000/docs

#### Запуск Telegram бота:
```powershell
python bot.py
```

#### Запуск всего через Docker:
```powershell
docker-compose up -d
```

## 📁 Структура проекта

```
employee-health-tracker/
├── app/                    # Основное приложение
│   ├── api/               # REST API endpoints
│   ├── core/              # Конфигурация и утилиты
│   ├── models/            # SQLAlchemy модели
│   ├── schemas/           # Pydantic схемы
│   └── services/          # Бизнес-логика
├── alembic/               # Миграции базы данных
├── scripts/               # Вспомогательные скрипты
└── tests/                 # Тесты
```

## 🔧 Вспомогательные скрипты

### Инициализация базы данных
```powershell
.\init-database.ps1 [-Reset] [-TestData] [-DockerMode]
```

Параметры:
- `-Reset`: Удалить и пересоздать базу данных
- `-TestData`: Добавить тестовые данные
- `-DockerMode`: Использовать Docker-контейнеры

### Генерация тестовых данных
```powershell
.\populate-test-data.ps1 [-UserCount 100] [-ClearExisting]
```

### Полная инициализация проекта
```powershell
.\init-project.ps1 [-UseDocker] [-InitDB]
```

## 📊 API Endpoints

### Пользователи
- `GET /users/` - Список пользователей
- `GET /users/{user_id}` - Информация о пользователе
- `POST /users/` - Создание пользователя
- `PUT /users/{user_id}` - Обновление пользователя

### Статусы здоровья
- `GET /health/report` - Отчет по статусам
- `GET /health/sectors` - Список секторов

### Администрирование
- `PUT /users/{user_id}/status` - Обновление статуса пользователя

## 🤖 Telegram Bot

### Команды бота
- `/start` - Запустить бота
- `/cancel` - Отменить текущее действие
- `/report` - Получить отчет

### Основные функции
1. Отметка статуса здоровья
2. Отчеты по сотрудникам
3. Администрирование пользователей
4. Автоматические ежедневные отчеты

## 🐳 Docker

### Сервисы
- **postgres**: База данных PostgreSQL
- **api**: REST API приложение
- **bot**: Telegram бот
- **pgadmin**: Веб-интерфейс для управления БД

### Команды
```powershell
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f api
docker-compose logs -f bot

# Пересборка образов
docker-compose build --no-cache
```

## 🔒 Безопасность

1. Все пароли и токены хранятся в `.env` файле
2. Файл `.env` добавлен в `.gitignore`
3. Используется JWT для аутентификации API
4. Telegram бот использует токен из окружения

## 🧪 Тестирование

```powershell
# Запуск тестов
pytest tests/

# Запуск тестов с покрытием
pytest tests/ --cov=app --cov-report=html
```

## 📈 Мониторинг

### Health Check
- API: http://localhost:8000/health
- База данных: Проверяется через healthcheck в docker-compose

### Логирование
- Логи хранятся в стандартном выводе
- Уровень логирования настраивается через `LOG_LEVEL`

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Добавьте тесты
4. Отправьте Pull Request

## 📄 Лицензия

MIT
"@

Set-Content -Path "README.md" -Value $readme -Encoding UTF8
Write-Host "  Создан: README.md" -ForegroundColor Gray

# 7. Создание файлов Python с основным кодом
Write-Host "`n7. Создание основных файлов Python..." -ForegroundColor Green

# Создаем пустые __init__.py файлы
$initFiles = @(
    "app/__init__.py",
    "app/api/__init__.py",
    "app/api/routes/__init__.py",
    "app/core/__init__.py",
    "app/models/__init__.py",
    "app/schemas/__init__.py",
    "app/services/__init__.py",
    "alembic/__init__.py"
)

foreach ($file in $initFiles) {
    if (-not (Test-Path $file)) {
        Set-Content -Path $file -Value ""
        Write-Host "  Создан: $file" -ForegroundColor Gray
    }
}

# Краткое сообщение о завершении
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Инициализация проекта завершена!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`nСледующие шаги:" -ForegroundColor Yellow
Write-Host "1. Настройте файл .env:" -ForegroundColor White
Write-Host "   Copy-Item .env.example .env" -ForegroundColor Gray
Write-Host "   # Отредактируйте .env, указав свои настройки" -ForegroundColor Gray

Write-Host "`n2. Инициализируйте базу данных:" -ForegroundColor White
Write-Host "   .\init-database.ps1" -ForegroundColor Gray

if ($UseDocker) {
    Write-Host "`n3. Запустите через Docker:" -ForegroundColor White
    Write-Host "   docker-compose up -d" -ForegroundColor Gray
} else {
    Write-Host "`n3. Установите зависимости:" -ForegroundColor White
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "`n4. Запустите приложения:" -ForegroundColor White
    Write-Host "   # В одном терминале:" -ForegroundColor Gray
    Write-Host "   uvicorn main:app --reload" -ForegroundColor Gray
    Write-Host "   # В другом терминале:" -ForegroundColor Gray
    Write-Host "   python bot.py" -ForegroundColor Gray
}

Write-Host "`n5. Добавьте тестовые данные (опционально):" -ForegroundColor White
Write-Host "   .\populate-test-data.ps1" -ForegroundColor Gray

Write-Host "`nДокументация API будет доступна по адресу:" -ForegroundColor White
Write-Host "   http://localhost:8000/docs" -ForegroundColor Cyan

Write-Host "`nУдачи в разработке! 🚀" -ForegroundColor Green
