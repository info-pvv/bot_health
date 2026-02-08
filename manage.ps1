# manage.ps1 - Fixed version
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "build", "shell", "migrate", "backup", "clean", "ps")]
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
        Write-Host "✅ Docker is available" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Docker not found!" -ForegroundColor Red
        Write-Host "💡 Install Docker Desktop for Windows first." -ForegroundColor Yellow
        exit 1
    }
}

function Get-Compose-Command {
    # Пробуем разные варианты команд
    $commands = @(
        @("docker", "compose"),    # Docker Compose V2
        "docker-compose"           # Docker Compose V1
    )
    
    foreach ($cmd in $commands) {
        try {
            if ($cmd -is [array]) {
                # Проверяем docker compose
                $test = & $cmd[0] $cmd[1] --version 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✅ Using: $($cmd[0]) $($cmd[1])" -ForegroundColor Green
                    return $cmd
                }
            } else {
                # Проверяем docker-compose
                $test = & $cmd --version 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✅ Using: $cmd" -ForegroundColor Green
                    return @($cmd)
                }
            }
        } catch {
            continue
        }
    }
    
    Write-Host "❌ Docker Compose not found!" -ForegroundColor Red
    Write-Host "💡 Docker Desktop should include Compose." -ForegroundColor Yellow
    exit 1
}

function Run-Compose {
    param([string[]]$Args)
    
    $composeCmd = Get-Compose-Command
    
    # Базовые аргументы
    $allArgs = @()
    
    # Добавляем файл конфигурации, если указан
    if ($ComposeFile -and (Test-Path $ComposeFile)) {
        $allArgs += @("-f", $ComposeFile)
    }
    
    # Добавляем остальные аргументы
    $allArgs += $Args
    
    Write-Host "Running: $($composeCmd -join ' ') $($allArgs -join ' ')" -ForegroundColor Gray
    
    try {
        if ($composeCmd.Count -eq 1) {
            # docker-compose (v1)
            & $composeCmd[0] $allArgs
        } else {
            # docker compose (v2)
            & $composeCmd[0] $composeCmd[1] $allArgs
        }
        
        return $LASTEXITCODE
    } catch {
        Write-Host "❌ Error executing command: $_" -ForegroundColor Red
        return 1
    }
}

# Основная логика
Show-Header
Check-Docker

switch ($Command.ToLower()) {
    "start" {
        Write-Host "🚀 Starting services..." -ForegroundColor Cyan
        $result = Run-Compose @("up", "-d")
        
        if ($result -eq 0) {
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
        } else {
            Write-Host "❌ Failed to start services" -ForegroundColor Red
        }
    }
    
    "stop" {
        Write-Host "🛑 Stopping services..." -ForegroundColor Cyan
        $result = Run-Compose @("down")
        if ($result -eq 0) {
            Write-Host "✅ Services stopped" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to stop services" -ForegroundColor Red
        }
    }
    
    "restart" {
        Write-Host "🔄 Restarting services..." -ForegroundColor Cyan
        if ($Service) {
            $result = Run-Compose @("restart", $Service)
            if ($result -eq 0) {
                Write-Host "✅ Service '$Service' restarted" -ForegroundColor Green
            } else {
                Write-Host "❌ Failed to restart service '$Service'" -ForegroundColor Red
            }
        } else {
            $result = Run-Compose @("restart")
            if ($result -eq 0) {
                Write-Host "✅ All services restarted" -ForegroundColor Green
            } else {
                Write-Host "❌ Failed to restart services" -ForegroundColor Red
            }
        }
    }
    
    "status" {
        Write-Host "📊 Service status:" -ForegroundColor Cyan
        Run-Compose @("ps")
    }
    
    "ps" {
        Write-Host "📊 Container status:" -ForegroundColor Cyan
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
        $result = Run-Compose @("build", "--no-cache")
        if ($result -eq 0) {
            Write-Host "✅ Images built" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to build images" -ForegroundColor Red
        }
    }
    
    "shell" {
        $targetService = if ($Service) { $Service } else { "api-dev" }
        Write-Host "🐚 Opening shell in '$targetService'..." -ForegroundColor Cyan
        Run-Compose @("exec", $targetService, "sh")
    }
    
    "migrate" {
        Write-Host "🗄️ Running migrations..." -ForegroundColor Cyan
        $result = Run-Compose @("exec", "api-dev", "python", "migrations/manage.py", "up")
        if ($result -eq 0) {
            Write-Host "✅ Migrations completed" -ForegroundColor Green
        } else {
            Write-Host "❌ Migrations failed" -ForegroundColor Red
        }
    }
    
    "backup" {
        Write-Host "💾 Creating database backup..." -ForegroundColor Cyan
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "backup_$timestamp.sql"
        
        $result = Run-Compose @("exec", "-T", "postgres-dev", "pg_dump", "-U", "dev_user", "health_tracker_dev")
        
        if ($result -eq 0) {
            Write-Host "✅ Backup completed" -ForegroundColor Green
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
        Write-Host "  ps               - Show container status" -ForegroundColor Gray
        Write-Host "  logs [service]   - View logs (all or specific)" -ForegroundColor Gray
        Write-Host "  build            - Rebuild images" -ForegroundColor Gray
        Write-Host "  shell [service]  - Open shell in container" -ForegroundColor Gray
        Write-Host "  migrate          - Run database migrations" -ForegroundColor Gray
        Write-Host "  backup           - Backup database" -ForegroundColor Gray
        Write-Host "  clean            - Clean up Docker resources" -ForegroundColor Gray
    }
}