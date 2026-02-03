
## 2. **setup-environment.ps1** - Скрипт для настройки окружения

#```powershell
# setup-environment.ps1
# Скрипт для настройки окружения разработки

param(
    [string]$PythonVersion = "3.11",
    [switch]$InstallPostgreSQL = $false,
    [switch]$InstallDocker = $false,
    [switch]$InstallVSCode = $false,
    [switch]$Force = $false
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Настройка окружения разработки" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "Запустите скрипт от имени администратора для установки ПО" -ForegroundColor Yellow
}

# 1. Проверка и установка Python
Write-Host "`n1. Проверка Python..." -ForegroundColor Green

$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
}

if ($pythonPath) {
    $pythonVersion = & python --version 2>&1
    Write-Host "  Python найден: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  Python не найден" -ForegroundColor Red
    
    if ($Force -or (Read-Host "Установить Python $PythonVersion? (y/n)") -eq 'y') {
        Write-Host "  Установка Python $PythonVersion..." -ForegroundColor Yellow
        
        # Скачиваем Python установщик
        $pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
        $installerPath = "$env:TEMP\python-$PythonVersion-installer.exe"
        
        try {
            Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
            Write-Host "  Запуск установщика..." -ForegroundColor Yellow
            Start-Process -FilePath $installerPath -Args "/quiet InstallAllUsers=1 PrependPath=1" -Wait
            Write-Host "  Python установлен успешно" -ForegroundColor Green
        } catch {
            Write-Host "  Ошибка установки Python: $_" -ForegroundColor Red
        }
    }
}

# 2. Проверка и установка Git
Write-Host "`n2. Проверка Git..." -ForegroundColor Green

$gitPath = Get-Command git -ErrorAction SilentlyContinue
if ($gitPath) {
    $gitVersion = & git --version 2>&1
    Write-Host "  Git найден: $gitVersion" -ForegroundColor Green
} else {
    Write-Host "  Git не найден" -ForegroundColor Red
    
    if ($Force -or (Read-Host "Установить Git? (y/n)") -eq 'y') {
        Write-Host "  Установка Git..." -ForegroundColor Yellow
        
        try {
            # Используем winget для установки Git
            winget install --id Git.Git -e --source winget
            Write-Host "  Git установлен успешно" -ForegroundColor Green
        } catch {
            Write-Host "  Попытка установки через chocolatey..." -ForegroundColor Yellow
            try {
                choco install git -y
                Write-Host "  Git установлен успешно" -ForegroundColor Green
            } catch {
                Write-Host "  Скачивание установщика Git..." -ForegroundColor Yellow
                $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
                $installerPath = "$env:TEMP\git-installer.exe"
                
                Invoke-WebRequest -Uri $gitUrl -OutFile $installerPath
                Start-Process -FilePath $installerPath -Args "/VERYSILENT /NORESTART" -Wait
                Write-Host "  Git установлен успешно" -ForegroundColor Green
            }
        }
    }
}

# 3. Проверка и установка PostgreSQL
if ($InstallPostgreSQL) {
    Write-Host "`n3. Проверка PostgreSQL..." -ForegroundColor Green
    
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    if ($psqlPath) {
        $psqlVersion = & psql --version 2>&1
        Write-Host "  PostgreSQL найден: $psqlVersion" -ForegroundColor Green
    } else {
        Write-Host "  PostgreSQL не найден" -ForegroundColor Red
        
        if ($Force -or (Read-Host "Установить PostgreSQL 15? (y/n)") -eq 'y') {
            Write-Host "  Установка PostgreSQL 15..." -ForegroundColor Yellow
            
            $postgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-15.5-1-windows-x64.exe"
            $installerPath = "$env:TEMP\postgresql-installer.exe"
            
            try {
                Invoke-WebRequest -Uri $postgresUrl -OutFile $installerPath
                Write-Host "  Запуск установщика..." -ForegroundColor Yellow
                Write-Host "  Пожалуйста, завершите установку в графическом интерфейсе" -ForegroundColor Yellow
                Write-Host "  Не забудьте запомнить пароль для пользователя postgres!" -ForegroundColor Yellow
                Start-Process -FilePath $installerPath -Wait
                Write-Host "  PostgreSQL установлен" -ForegroundColor Green
            } catch {
                Write-Host "  Ошибка установки PostgreSQL: $_" -ForegroundColor Red
            }
        }
    }
}

# 4. Проверка и установка Docker
if ($InstallDocker) {
    Write-Host "`n4. Проверка Docker..." -ForegroundColor Green
    
    $dockerPath = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerPath) {
        $dockerVersion = & docker --version 2>&1
        Write-Host "  Docker найден: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "  Docker не найден" -ForegroundColor Red
        
        if ($Force -or (Read-Host "Установить Docker Desktop? (y/n)") -eq 'y') {
            Write-Host "  Установка Docker Desktop..." -ForegroundColor Yellow
            
            $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
            $installerPath = "$env:TEMP\docker-desktop-installer.exe"
            
            try {
                Invoke-WebRequest -Uri $dockerUrl -OutFile $installerPath
                Write-Host "  Запуск установщика..." -ForegroundColor Yellow
                Start-Process -FilePath $installerPath -Args "install --quiet" -Wait
                Write-Host "  Docker Desktop установлен. Перезагрузите компьютер для завершения установки." -ForegroundColor Green
            } catch {
                Write-Host "  Ошибка установки Docker: $_" -ForegroundColor Red
            }
        }
    }
}

# 5. Проверка и установка VSCode
if ($InstallVSCode) {
    Write-Host "`n5. Проверка VSCode..." -ForegroundColor Green
    
    $codePath = Get-Command code -ErrorAction SilentlyContinue
    if ($codePath) {
        $codeVersion = & code --version 2>&1 | Select-Object -First 1
        Write-Host "  VSCode найден: версия $codeVersion" -ForegroundColor Green
    } else {
        Write-Host "  VSCode не найден" -ForegroundColor Red
        
        if ($Force -or (Read-Host "Установить VSCode? (y/n)") -eq 'y') {
            Write-Host "  Установка VSCode..." -ForegroundColor Yellow
            
            try {
                winget install Microsoft.VisualStudioCode
                Write-Host "  VSCode установлен успешно" -ForegroundColor Green
            } catch {
                Write-Host "  Скачивание установщика VSCode..." -ForegroundColor Yellow
                $vscodeUrl = "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64"
                $installerPath = "$env:TEMP\vscode-installer.exe"
                
                Invoke-WebRequest -Uri $vscodeUrl -OutFile $installerPath
                Start-Process -FilePath $installerPath -Args "/VERYSILENT /MERGETASKS=!runcode" -Wait
                Write-Host "  VSCode установлен успешно" -ForegroundColor Green
            }
        }
    }
}

# 6. Установка расширений VSCode
if ($InstallVSCode -and $codePath) {
    Write-Host "`n6. Установка расширений VSCode для Python разработки..." -ForegroundColor Green
    
    $extensions = @(
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "ms-python.isort",
        "ms-azuretools.vscode-docker",
        "mtxr.sqltools",
        "mtxr.sqltools-driver-pg",
        "ms-vscode.powershell"
    )
    
    foreach ($extension in $extensions) {
        Write-Host "  Установка расширения: $extension" -ForegroundColor Gray
        & code --install-extension $extension --force 2>&1 | Out-Null
    }
    Write-Host "  Расширения VSCode установлены" -ForegroundColor Green
}

# 7. Настройка виртуального окружения
Write-Host "`n7. Настройка виртуального окружения..." -ForegroundColor Green

if (Test-Path "venv") {
    Write-Host "  Виртуальное окружение уже существует" -ForegroundColor Yellow
    
    if ($Force -or (Read-Host "Пересоздать виртуальное окружение? (y/n)") -eq 'y') {
        Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
        & python -m venv venv
        Write-Host "  Виртуальное окружение пересоздано" -ForegroundColor Green
    }
} else {
    & python -m venv venv
    Write-Host "  Виртуальное окружение создано" -ForegroundColor Green
}

# 8. Активация виртуального окружения и установка зависимостей
Write-Host "`n8. Установка зависимостей Python..." -ForegroundColor Green

if (Test-Path "requirements.txt") {
    # Активируем виртуальное окружение
    $activateScript = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        
        # Обновляем pip
        & python -m pip install --upgrade pip
        Write-Host "  pip обновлен" -ForegroundColor Gray
        
        # Устанавливаем зависимости
        & pip install -r requirements.txt
        Write-Host "  Зависимости установлены" -ForegroundColor Green
        
        # Устанавливаем дополнительные утилиты для разработки
        & pip install ipython pre-commit
        Write-Host "  Утилиты для разработки установлены" -ForegroundColor Green
        
        # Настройка pre-commit
        if (Test-Path ".pre-commit-config.yaml") {
            & pre-commit install
            Write-Host "  pre-commit настроен" -ForegroundColor Green
        }
    } else {
        Write-Host "  Файл активации не найден" -ForegroundColor Red
    }
} else {
    Write-Host "  Файл requirements.txt не найден" -ForegroundColor Yellow
}

# 9. Настройка .env файла
Write-Host "`n9. Настройка файла окружения..." -ForegroundColor Green

if (Test-Path ".env.example" -and -not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Создан файл .env на основе .env.example" -ForegroundColor Green
    Write-Host "  Отредактируйте .env файл, указав свои настройки" -ForegroundColor Yellow
} elseif (Test-Path ".env") {
    Write-Host "  Файл .env уже существует" -ForegroundColor Yellow
} else {
    Write-Host "  Создайте файл .env с необходимыми переменными" -ForegroundColor Yellow
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Настройка окружения завершена!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`nКраткая справка:" -ForegroundColor Yellow
Write-Host "Активация виртуального окружения:" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate" -ForegroundColor Gray

Write-Host "`nЗапуск инициализации проекта:" -ForegroundColor White
Write-Host "  .\init-project.ps1" -ForegroundColor Gray

Write-Host "`nИнициализация базы данных:" -ForegroundColor White
Write-Host "  .\init-database.ps1" -ForegroundColor Gray

Write-Host "`nЗапуск API:" -ForegroundColor White
Write-Host "  uvicorn main:app --reload" -ForegroundColor Gray

Write-Host "`nЗапуск бота:" -ForegroundColor White
Write-Host "  python bot.py" -ForegroundColor Gray
```

