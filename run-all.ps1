## 4. **run-all.ps1** - Скрипт для запуска всего проекта

#```powershell
# run-all.ps1
# Скрипт для запуска всех компонентов проекта

param(
    [switch]$DockerMode = $false,
    [switch]$ApiOnly = $false,
    [switch]$BotOnly = $false,
    [switch]$DevMode = $false,
    [int]$ApiPort = 8000,
    [string]$LogDir = ".\logs"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Запуск Employee Health Tracker" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Создаем директорию для логов
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "Создана директория для логов: $LogDir" -ForegroundColor Green
}

if ($DockerMode) {
    Write-Host "`nЗапуск через Docker Compose..." -ForegroundColor Green
    
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Host "Файл docker-compose.yml не найден" -ForegroundColor Red
        exit 1
    }
    
    # Проверяем, запущен ли Docker
    $dockerRunning = docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker не запущен. Запустите Docker Desktop." -ForegroundColor Red
        exit 1
    }
    
    # Определяем, какие сервисы запускать
    $services = @()
    if (-not $BotOnly) { $services += "api" }
    if (-not $ApiOnly) { $services += "bot" }
    $services += "postgres", "pgadmin"
    
    $servicesString = $services -join " "
    
    Write-Host "Запуск сервисов: $servicesString" -ForegroundColor Yellow
    
    # Запускаем сервисы
    if ($DevMode) {
        docker-compose up $servicesString
    } else {
        docker-compose up -d $servicesString
        
        Write-Host "`nСервисы запущены в фоновом режиме" -ForegroundColor Green
        Write-Host "`nПросмотр логов:" -ForegroundColor White
        Write-Host "  docker-compose logs -f api" -ForegroundColor Gray
        Write-Host "  docker-compose logs -f bot" -ForegroundColor Gray
        
        Write-Host "`nОстановка сервисов:" -ForegroundColor White
        Write-Host "  docker-compose down" -ForegroundColor Gray
    }
    
} else {
    Write-Host "`nЗапуск в локальном режиме..." -ForegroundColor Green
    
    # Проверяем виртуальное окружение
    if (-not (Test-Path "venv")) {
        Write-Host "Виртуальное окружение не найдено. Создайте его:" -ForegroundColor Red
        Write-Host "  python -m venv venv" -ForegroundColor Gray
        Write-Host "  .\venv\Scripts\Activate" -ForegroundColor Gray
        Write-Host "  pip install -r requirements.txt" -ForegroundColor Gray
        exit 1
    }
    
    # Активируем виртуальное окружение
    $activateScript = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Host "Виртуальное окружение активировано" -ForegroundColor Green
    } else {
        Write-Host "Не удалось активировать виртуальное окружение" -ForegroundColor Red
        exit 1
    }
    
    # Проверяем, запущена ли база данных
    Write-Host "`nПроверка подключения к базе данных..." -ForegroundColor Green
    
    try {
        # Проверяем с помощью скрипта
        $dbCheckScript = @"
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import engine
from sqlalchemy import text

async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(check_db())
"@
        
        $tempFile = "$env:TEMP\db_check.py"
        Set-Content -Path $tempFile -Value $dbCheckScript -Encoding UTF8
        
        $result = & python $tempFile 2>&1
        Remove-Item -Path $tempFile -Force
        
        if ($result -match "SUCCESS") {
            Write-Host "  Подключение к базе данных успешно" -ForegroundColor Green
        } else {
            Write-Host "  Ошибка подключения к базе данных: $result" -ForegroundColor Red
            
            if ((Read-Host "Запустить init-database.ps1? (y/n)") -eq 'y') {
                .\init-database.ps1
            } else {
                exit 1
            }
        }
        
    } catch {
        Write-Host "  Ошибка проверки базы данных: $_" -ForegroundColor Red
    }
    
    # Запуск API
    if (-not $BotOnly) {
        Write-Host "`nЗапуск REST API..." -ForegroundColor Green
        
        $apiLogFile = "$LogDir\api_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').log"
        $apiCommand = "uvicorn main:app --host 0.0.0.0 --port $ApiPort"
        
        if ($DevMode) {
            $apiCommand += " --reload"
        }
        
        Write-Host "  Команда: $apiCommand" -ForegroundColor Gray
        Write-Host "  Логи: $apiLogFile" -ForegroundColor Gray
        Write-Host "  Документация: http://localhost:$ApiPort/docs" -ForegroundColor Cyan
        
        if ($DevMode) {
            # Запускаем в текущем окне
            Invoke-Expression $apiCommand
        } else {
            # Запускаем в отдельном процессе
            Start-Process powershell -ArgumentList "-NoExit -Command `"$apiCommand 2>&1 | Tee-Object -FilePath '$apiLogFile'`""
            Write-Host "  API запущен в фоновом режиме" -ForegroundColor Green
        }
    }
    
    # Запуск бота
    if (-not $ApiOnly) {
        Write-Host "`nЗапуск Telegram бота..." -ForegroundColor Green
        
        $botLogFile = "$LogDir\bot_$(Get-Date -Format 'yyyy-MM-dd_HH-mm').log"
        
        Write-Host "  Команда: python bot.py" -ForegroundColor Gray
        Write-Host "  Логи: $botLogFile" -ForegroundColor Gray
        
        if ($DevMode) {
            # Запускаем в текущем окне (только если API не запущен здесь же)
            if ($BotOnly) {
                & python bot.py
            } else {
                # Для API+Bot в dev mode запускаем бота в отдельном окне
                Start-Process powershell -ArgumentList "-NoExit -Command `"python bot.py 2>&1 | Tee-Object -FilePath '$botLogFile'`""
                Write-Host "  Бот запущен в отдельном окне" -ForegroundColor Green
            }
        } else {
            # Запускаем в отдельном процессе
            Start-Process powershell -ArgumentList "-NoExit -Command `"python bot.py 2>&1 | Tee-Object -FilePath '$botLogFile'`""
            Write-Host "  Бот запущен в фоновом режиме" -ForegroundColor Green
        }
    }
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Проект запущен!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not $DockerMode -and -not $DevMode) {
    Write-Host "`nПроцессы запущены в фоне." -ForegroundColor Yellow
    Write-Host "Для остановки закройте окна PowerShell или выполните:" -ForegroundColor White
    Write-Host "  taskkill /F /IM python.exe" -ForegroundColor Gray
}

if ($DockerMode) {
    Write-Host "`nДоступные сервисы:" -ForegroundColor Yellow
    Write-Host "  API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  Документация API: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "  pgAdmin: http://localhost:5050" -ForegroundColor Cyan
    Write-Host "    Логин: admin@healthtracker.com" -ForegroundColor Gray
    Write-Host "    Пароль: admin" -ForegroundColor Gray
} elseif (-not $BotOnly) {
    Write-Host "`nAPI доступен по адресу: http://localhost:$ApiPort" -ForegroundColor Cyan
    Write-Host "Документация: http://localhost:$ApiPort/docs" -ForegroundColor Cyan
}
```
