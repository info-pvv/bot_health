# manage.ps1 - PowerShell management script
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "build", "shell", "migrate", "backup", "clean")]
    [string]$Command,
    
    [string]$Service = "",
    [string]$ComposeFile = "docker-compose.dev.yml"
)

$ErrorActionPreference = "Stop"

function Show-Header {
    Write-Host "🤖 Health Tracker Management for Windows" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
}

function Check-Docker {
    try {
        $null = docker --version
        $null = docker-compose --version
    } catch {
        Write-Host "❌ Docker or Docker Compose not found!" -ForegroundColor Red
        Write-Host "💡 Install Docker Desktop for Windows first." -ForegroundColor Yellow
        exit 1
    }
}

function Run-Compose {
    param([string[]]$Args)
    
    $composeArgs = @("-f", $ComposeFile) + $Args
    Write-Host "Running: docker-compose $composeArgs" -ForegroundColor Gray
    docker-compose $composeArgs
}

Show-Header
Check-Docker

switch ($Command) {
    "start" {
        Write-Host "🚀 Starting services..." -ForegroundColor Cyan
        Run-Compose @("up", "-d")
        
        Write-Host "⏳ Waiting for services..." -ForegroundColor Cyan
        Start-Sleep -Seconds 5
        
        # Проверка API
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 10 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Services started successfully" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️  Services started but API check failed" -ForegroundColor Yellow
        }
    }
    
    "stop" {
        Write-Host "🛑 Stopping services..." -ForegroundColor Cyan
        Run-Compose @("down")
        Write-Host "✅ Services stopped" -ForegroundColor Green
    }
    
    "restart" {
        Write-Host "🔄 Restarting services..." -ForegroundColor Cyan
        if ($Service) {
            Run-Compose @("restart", $Service)
            Write-Host "✅ Service '$Service' restarted" -ForegroundColor Green
        } else {
            Run-Compose @("restart")
            Write-Host "✅ All services restarted" -ForegroundColor Green
        }
    }
    
    "status" {
        Write-Host "📊 Service status:" -ForegroundColor Cyan
        Run-Compose @("ps")
    }
    
    "logs" {
        if ($Service) {
            Write-Host "📋 Logs for '$Service':" -ForegroundColor Cyan
            Run-Compose @("logs", "-f", $Service)
        } else {
            Write-Host "📋 All logs:" -ForegroundColor Cyan
            Run-Compose @("logs", "-f")
        }
    }
    
    "build" {
        Write-Host "🔨 Building images..." -ForegroundColor Cyan
        Run-Compose @("build", "--no-cache")
        Write-Host "✅ Images built" -ForegroundColor Green
    }
    
    "shell" {
        $targetService = if ($Service) { $Service } else { "api-dev" }
        Write-Host "🐚 Opening shell in '$targetService'..." -ForegroundColor Cyan
        Run-Compose @("exec", $targetService, "sh")
    }
    
    "migrate" {
        Write-Host "🗄️ Running migrations..." -ForegroundColor Cyan
        Run-Compose @("exec", "api-dev", "python", "migrations/manage.py", "up")
        Write-Host "✅ Migrations completed" -ForegroundColor Green
    }
    
    "backup" {
        Write-Host "💾 Creating database backup..." -ForegroundColor Cyan
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "backup_$timestamp.sql"
        
        Run-Compose @("exec", "-T", "postgres-dev", "pg_dump", "-U", "dev_user", "health_tracker_dev") | Out-File $backupFile -Encoding UTF8
        
        if (Test-Path $backupFile -and (Get-Item $backupFile).Length -gt 0) {
            Write-Host "✅ Backup saved to $backupFile" -ForegroundColor Green
        } else {
            Write-Host "❌ Backup failed!" -ForegroundColor Red
        }
    }
    
    "clean" {
        Write-Host "🧹 Cleaning up Docker resources..." -ForegroundColor Cyan
        
        # Остановка контейнеров
        Write-Host "Stopping containers..." -ForegroundColor Gray
        Run-Compose @("down") | Out-Null
        
        # Удаление ненужных образов
        Write-Host "Removing dangling images..." -ForegroundColor Gray
        docker image prune -f | Out-Null
        
        # Удаление ненужных volumes
        Write-Host "Removing unused volumes..." -ForegroundColor Gray
        docker volume prune -f | Out-Null
        
        Write-Host "✅ Cleanup completed" -ForegroundColor Green
    }
    
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Write-Host "📋 Available commands:" -ForegroundColor Cyan
        Write-Host "  start            - Start all services" -ForegroundColor Gray
        Write-Host "  stop             - Stop all services" -ForegroundColor Gray
        Write-Host "  restart [service]- Restart all or specific service" -ForegroundColor Gray
        Write-Host "  status           - Show service status" -ForegroundColor Gray
        Write-Host "  logs [service]   - View logs (all or specific)" -ForegroundColor Gray
        Write-Host "  build            - Rebuild images" -ForegroundColor Gray
        Write-Host "  shell [service]  - Open shell in container" -ForegroundColor Gray
        Write-Host "  migrate          - Run database migrations" -ForegroundColor Gray
        Write-Host "  backup           - Backup database" -ForegroundColor Gray
        Write-Host "  clean            - Clean up Docker resources" -ForegroundColor Gray
    }
}