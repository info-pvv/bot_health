# init-windows.ps1 - Updated
Write-Host "🔧 Health Tracker Windows Development Setup" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Проверка Docker Desktop
Write-Host "🔍 Checking Docker Desktop..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Host "✅ $dockerVersion" -ForegroundColor Green
    
    # Проверяем версию Compose
    Write-Host "🔍 Checking Docker Compose..." -ForegroundColor Cyan
    try {
        $composeVersion = docker compose version
        Write-Host "✅ Docker Compose v2 available" -ForegroundColor Green
    } catch {
        try {
            $composeVersion = docker-compose --version
            Write-Host "✅ Docker Compose v1 available" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  Docker Compose not found" -ForegroundColor Yellow
            Write-Host "💡 Docker Desktop should include Compose by default" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "❌ Docker Desktop not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "📥 Please install Docker Desktop for Windows:" -ForegroundColor Yellow
    Write-Host "   1. Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Gray
    Write-Host "   2. Install with WSL 2 backend" -ForegroundColor Gray
    Write-Host "   3. Start Docker Desktop" -ForegroundColor Gray
    exit 1
}

# Проверка WSL
Write-Host "🔍 Checking WSL..." -ForegroundColor Cyan
try {
    $wslVersion = wsl --list --verbose
    Write-Host "✅ WSL is available" -ForegroundColor Green
} catch {
    Write-Host "⚠️  WSL not found or not enabled" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Enabling WSL:" -ForegroundColor Gray
    Write-Host "   1. Open PowerShell as Administrator" -ForegroundColor Gray
    Write-Host "   2. Run: wsl --install" -ForegroundColor Gray
    Write-Host "   3. Restart computer" -ForegroundColor Gray
}

# Создание файлов окружения
Write-Host "📄 Creating environment files..." -ForegroundColor Cyan

if (-not (Test-Path ".env.windows")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env.windows"
        Write-Host "✅ Created .env.windows from .env.example" -ForegroundColor Green
        Write-Host "📝 Please edit .env.windows and add your Telegram token" -ForegroundColor Yellow
    } else {
        # Создаем минимальный .env.windows
        @"
# Telegram Bot Token from @BotFather
TELEGRAM_TOKEN=your_bot_token_here

# Database settings for development
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_DB=health_tracker_dev

# API settings
SECRET_KEY=dev_secret_key_change_this
API_BASE_URL=http://localhost:8000
LOG_LEVEL=DEBUG
REPORT_ENABLED=false
"@ | Out-File ".env.windows" -Encoding UTF8
        Write-Host "✅ Created .env.windows with default values" -ForegroundColor Green
    }
}

if (-not (Test-Path ".env.production")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env.production"
        Write-Host "✅ Created .env.production from .env.example" -ForegroundColor Green
        Write-Host "📝 Please edit .env.production for production deployment" -ForegroundColor Yellow
    }
}

# Создание необходимых директорий
Write-Host "📁 Creating directories..." -ForegroundColor Cyan
$directories = @(
    "docker/logs/api",
    "docker/logs/bot", 
    "backups",
    "scripts"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# Создание файла docker-compose.dev.yml если его нет
if (-not (Test-Path "docker-compose.dev.yml")) {
    Write-Host "📄 Creating docker-compose.dev.yml..." -ForegroundColor Cyan
    @"
# docker-compose.dev.yml - Windows Development
version: '3.8'

services:
  postgres-dev:
    image: postgres:15-alpine
    container_name: health_tracker_postgres_dev
    restart: unless-stopped
    environment:
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: health_tracker_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_user -d health_tracker_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  api-dev:
    build: .
    container_name: health_tracker_api_dev
    restart: unless-stopped
    command: >
      sh -c "python migrations/manage.py up &&
             uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    depends_on:
      postgres-dev:
        condition: service_healthy
    environment:
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
      POSTGRES_HOST: postgres-dev
      POSTGRES_PORT: 5432
      POSTGRES_DB: health_tracker_dev
      SECRET_KEY: dev_secret_key_change_this
      API_BASE_URL: http://localhost:8000
      LOG_LEVEL: DEBUG
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN:-dummy_token}
    ports:
      - "8000:8000"
    volumes:
      - .:/app

  bot-dev:
    build: .
    container_name: health_tracker_bot_dev
    restart: unless-stopped
    command: python bot_runner.py
    depends_on:
      api-dev:
        condition: service_started
    environment:
      TELEGRAM_TOKEN: ${TELEGRAM_TOKEN:-dummy_token}
      API_BASE_URL: http://api-dev:8000
      LOG_LEVEL: DEBUG
      REPORT_TIME: "09:00"
      REPORT_ENABLED: "false"
    volumes:
      - .:/app

volumes:
  postgres_data_dev:
"@ | Out-File "docker-compose.dev.yml" -Encoding UTF8
    Write-Host "✅ Created docker-compose.dev.yml" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 Setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Edit .env.windows and add your Telegram token" -ForegroundColor Gray
Write-Host "   2. Run: .\deploy.ps1 -Build" -ForegroundColor Gray
Write-Host "   3. Check services: .\manage.ps1 status" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 For production deployment:" -ForegroundColor Cyan
Write-Host "   1. Set up Linux server (VPS)" -ForegroundColor Gray
Write-Host "   2. Edit .env.production with production values" -ForegroundColor Gray
Write-Host "   3. Run: .\deploy-linux.ps1 -Server your-server.com -Setup" -ForegroundColor Gray