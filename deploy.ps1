do# deploy.ps1 - Updated for Docker Compose v2
param(
    [string]$Environment = "dev",
    [switch]$Build,
    [switch]$NoCache
)

Write-Host "🚀 Health Tracker Deployment Script for Windows" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Проверка наличия Docker
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found! Please install Docker Desktop for Windows." -ForegroundColor Red
    Write-Host "📥 Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# Функция для получения правильной команды compose
function Get-Compose-Command {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        Write-Host "✅ Using docker-compose (v1)" -ForegroundColor Green
        return @("docker-compose")
    } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "✅ Using docker compose (v2)" -ForegroundColor Green
        return @("docker", "compose")
    } else {
        Write-Host "❌ Docker Compose not found!" -ForegroundColor Red
        exit 1
    }
}

# Выбор окружения
$composeFile = "docker-compose.dev.yml"
$envFile = ".env.windows"

if ($Environment -eq "prod") {
    Write-Host "⚠️  Production deployment should be done on Linux server!" -ForegroundColor Yellow
    Write-Host "💡 Use deploy-linux.ps1 for remote deployment" -ForegroundColor Yellow
    exit 1
}

Write-Host "📁 Environment: $Environment" -ForegroundColor Cyan
Write-Host "📄 Compose file: $composeFile" -ForegroundColor Cyan
Write-Host "📄 Env file: $envFile" -ForegroundColor Cyan

# Проверка наличия .env файла
if (-not (Test-Path $envFile)) {
    Write-Host "❌ $envFile not found!" -ForegroundColor Red
    Write-Host "💡 Copy .env.example to $envFile and fill in the values" -ForegroundColor Yellow
    
    # Создание файла из примера
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" $envFile
        Write-Host "✅ Created $envFile from .env.example" -ForegroundColor Green
        Write-Host "📝 Please edit $envFile and add your Telegram token" -ForegroundColor Yellow
    }
    exit 1
}

# Проверка TELEGRAM_TOKEN
$envContent = Get-Content $envFile -Raw
if (-not ($envContent -match "TELEGRAM_TOKEN=")) {
    Write-Host "❌ TELEGRAM_TOKEN not found in $envFile" -ForegroundColor Red
    Write-Host "💡 Add your Telegram bot token to $envFile" -ForegroundColor Yellow
    exit 1
}

# Получаем команду compose
$composeCmd = Get-Compose-Command

# Функция для запуска compose команд
function Run-Compose {
    param([string[]]$Args)
    
    $allArgs = @("-f", $composeFile) + $Args
    
    if ($composeCmd.Count -eq 1) {
        # docker-compose (v1)
        & $composeCmd[0] $allArgs
    } else {
        # docker compose (v2)
        & $composeCmd[0] $composeCmd[1] $allArgs
    }
}

if ($Build) {
    Write-Host "🔨 Building images..." -ForegroundColor Cyan
    $buildArgs = @("build")
    if ($NoCache) {
        $buildArgs += "--no-cache"
    }
    Run-Compose $buildArgs
}

Write-Host "🚀 Starting services..." -ForegroundColor Cyan
Run-Compose @("up", "-d")

Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Проверка сервисов
Write-Host "🔍 Checking service status..." -ForegroundColor Cyan

# Проверка PostgreSQL
try {
    $pgCheck = Run-Compose @("exec", "-T", "postgres-dev", "pg_isready", "-U", "dev_user", "-d", "health_tracker_dev")
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL is ready" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL is not ready" -ForegroundColor Red
        Run-Compose @("logs", "postgres-dev")
        exit 1
    }
} catch {
    Write-Host "⚠️  Could not check PostgreSQL" -ForegroundColor Yellow
}

# Проверка API
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 10 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ API is running" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ API is not responding" -ForegroundColor Red
    Run-Compose @("logs", "api-dev")
    exit 1
}

Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Services:" -ForegroundColor Cyan
Run-Compose @("ps")
Write-Host ""
Write-Host "🔗 API URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🛠️  PgAdmin: http://localhost:5050 (login: dev@example.com / dev_password)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "  View logs: .\manage.ps1 logs" -ForegroundColor Gray
Write-Host "  Stop services: .\manage.ps1 stop" -ForegroundColor Gray
Write-Host "  Restart bot: .\manage.ps1 restart bot-dev" -ForegroundColor Gray
Write-Host "  View bot logs: .\manage.ps1 logs bot-dev" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Health Tracker is now running in development mode!" -ForegroundColor Green