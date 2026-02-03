## 3. **backup-database.ps1** - Скрипт для резервного копирования БД

#```powershell
# backup-database.ps1
# Скрипт для резервного копирования базы данных

param(
    [string]$BackupDir = ".\backups",
    [switch]$DockerMode = $false,
    [switch]$AutoClean = $false,
    [int]$KeepDays = 30
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Резервное копирование базы данных" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Создаем директорию для бэкапов
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "Создана директория для бэкапов: $BackupDir" -ForegroundColor Green
}

# Генерируем имя файла бэкапа
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupFile = "$BackupDir\health_tracker_$timestamp.sql"

Write-Host "`nСоздание бэкапа: $backupFile" -ForegroundColor Green

if ($DockerMode) {
    # Резервное копирование из Docker контейнера
    $containerName = "health_tracker_db"
    
    # Проверяем, запущен ли контейнер
    $containerStatus = docker ps -q -f name=$containerName 2>&1
    
    if ($containerStatus) {
        # Создаем бэкап
        docker exec $containerName pg_dump -U admin health_tracker > $backupFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Бэкап успешно создан из Docker контейнера" -ForegroundColor Green
            
            # Сжимаем бэкап
            if (Test-Path $backupFile) {
                $compressedFile = "$backupFile.gz"
                & gzip -c $backupFile > $compressedFile
                Remove-Item $backupFile -Force
                Write-Host "Бэкап сжат: $compressedFile" -ForegroundColor Green
                $backupFile = $compressedFile
            }
        } else {
            Write-Host "Ошибка создания бэкапа из Docker контейнера" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Docker контейнер '$containerName' не найден или не запущен" -ForegroundColor Red
        exit 1
    }
} else {
    # Резервное копирование локальной БД
    # Загружаем настройки из .env
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
    
    $dbUser = if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("POSTGRES_USER", "Process"))) { "admin" } else { [Environment]::GetEnvironmentVariable("POSTGRES_USER", "Process") }
    $dbPassword = if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "Process"))) { "password" } else { [Environment]::GetEnvironmentVariable("POSTGRES_PASSWORD", "Process") }
    $dbHost = if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("POSTGRES_HOST", "Process"))) { "localhost" } else { [Environment]::GetEnvironmentVariable("POSTGRES_HOST", "Process") }
    $dbPort = if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("POSTGRES_PORT", "Process"))) { "5432" } else { [Environment]::GetEnvironmentVariable("POSTGRES_PORT", "Process") }
    $dbName = if ([string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("POSTGRES_DB", "Process"))) { "health_tracker" } else { [Environment]::GetEnvironmentVariable("POSTGRES_DB", "Process") }
    
    # Создаем бэкап с помощью pg_dump
    $env:PGPASSWORD = $dbPassword
    & pg_dump -h $dbHost -p $dbPort -U $dbUser -d $dbName -F c -f $backupFile 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Бэкап успешно создан" -ForegroundColor Green
    } else {
        Write-Host "Ошибка создания бэкапа" -ForegroundColor Red
        exit 1
    }
}

# Очистка старых бэкапов
if ($AutoClean) {
    Write-Host "`nОчистка старых бэкапов..." -ForegroundColor Green
    
    $cutoffDate = (Get-Date).AddDays(-$KeepDays)
    $oldBackups = Get-ChildItem -Path $BackupDir -Filter "*.sql" -File | 
                  Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    $oldBackupsGz = Get-ChildItem -Path $BackupDir -Filter "*.gz" -File | 
                    Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    $allOldBackups = $oldBackups + $oldBackupsGz
    
    if ($allOldBackups.Count -gt 0) {
        $totalSize = ($allOldBackups | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "  Найдено $($allOldBackups.Count) старых бэкапов (общий размер: {0:N2} MB)" -f $totalSize -ForegroundColor Yellow
        
        foreach ($backup in $allOldBackups) {
            Remove-Item -Path $backup.FullName -Force
            Write-Host "  Удален: $($backup.Name)" -ForegroundColor Gray
        }
        
        Write-Host "  Старые бэкапы удалены" -ForegroundColor Green
    } else {
        Write-Host "  Старые бэкапы не найдены" -ForegroundColor Gray
    }
}

# Информация о бэкапе
$backupSize = (Get-Item $backupFile).Length / 1MB
Write-Host "`nИнформация о бэкапе:" -ForegroundColor Yellow
Write-Host "  Файл: $(Split-Path $backupFile -Leaf)" -ForegroundColor White
Write-Host "  Размер: {0:N2} MB" -f $backupSize -ForegroundColor White
Write-Host "  Дата создания: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host "  Путь: $backupFile" -ForegroundColor White

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Резервное копирование завершено!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
```

