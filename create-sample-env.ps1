
## 5. **create-sample-env.ps1** - Скрипт для создания настроенного .env файла

#```powershell
# create-sample-env.ps1
# Скрипт для создания предварительно настроенного .env файла

param(
    [string]$TelegramToken = "",
    [string]$DbPassword = "",
    [switch]$GeneratePasswords = $false,
    [switch]$Interactive = $false
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Создание файла конфигурации .env" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Функция для генерации случайных паролей
function Generate-RandomPassword {
    param([int]$Length = 16)
    
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $random = New-Object System.Random
    $password = ""
    
    1..$Length | ForEach-Object {
        $password += $chars[$random.Next(0, $chars.Length)]
    }
    
    return $password
}

# Функция для безопасного ввода
function Read-SecureInput {
    param([string]$Prompt)
    
    Write-Host $Prompt -ForegroundColor Yellow -NoNewline
    $secure = Read-Host -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    
    return $plain
}

# Определяем значения
$envVars = @{}

if ($Interactive) {
    Write-Host "`nИнтерактивная настройка .env файла" -ForegroundColor Green
    Write-Host "Нажмите Enter для использования значений по умолчанию`n" -ForegroundColor Gray
    
    $envVars["POSTGRES_USER"] = Read-Host "Имя пользователя PostgreSQL [admin]"
    if ([string]::IsNullOrWhiteSpace($envVars["POSTGRES_USER"])) { $envVars["POSTGRES_USER"] = "admin" }
    
    if ([string]::IsNullOrWhiteSpace($DbPassword)) {
        $envVars["POSTGRES_PASSWORD"] = Read-SecureInput "Пароль PostgreSQL (скрытый ввод) [password] "
        if ([string]::IsNullOrWhiteSpace($envVars["POSTGRES_PASSWORD"])) { $envVars["POSTGRES_PASSWORD"] = "password" }
    } else {
        $envVars["POSTGRES_PASSWORD"] = $DbPassword
    }
    
    $envVars["POSTGRES_HOST"] = Read-Host "Хост PostgreSQL [localhost]"
    if ([string]::IsNullOrWhiteSpace($envVars["POSTGRES_HOST"])) { $envVars["POSTGRES_HOST"] = "localhost" }
    
    $envVars["POSTGRES_PORT"] = Read-Host "Порт PostgreSQL [5432]"
    if ([string]::IsNullOrWhiteSpace($envVars["POSTGRES_PORT"])) { $envVars["POSTGRES_PORT"] = "5432" }
    
    $envVars["POSTGRES_DB"] = Read-Host "Имя базы данных [health_tracker]"
    if ([string]::IsNullOrWhiteSpace($envVars["POSTGRES_DB"])) { $envVars["POSTGRES_DB"] = "health_tracker" }
    
    if ([string]::IsNullOrWhiteSpace($TelegramToken)) {
        $envVars["TELEGRAM_TOKEN"] = Read-Host "Токен Telegram бота (можно указать позже)"
    } else {
        $envVars["TELEGRAM_TOKEN"] = $TelegramToken
    }
    
    $envVars["SECRET_KEY"] = Read-Host "Секретный ключ для JWT (можно сгенерировать)"
    if ([string]::IsNullOrWhiteSpace($envVars["SECRET_KEY"])) { 
        $envVars["SECRET_KEY"] = Generate-RandomPassword 32
        Write-Host "Сгенерирован ключ: $($envVars['SECRET_KEY'])" -ForegroundColor Green
    }
    
    $envVars["API_BASE_URL"] = Read-Host "Базовый URL API [http://localhost:8000]"
    if ([string]::IsNullOrWhiteSpace($envVars["API_BASE_URL"])) { $envVars["API_BASE_URL"] = "http://localhost:8000" }
    
} else {
    # Используем переданные значения или значения по умолчанию
    $envVars = @{
        POSTGRES_USER = "admin"
        POSTGRES_PASSWORD = if ($GeneratePasswords) { Generate-RandomPassword 16 } else { if ([string]::IsNullOrWhiteSpace($DbPassword)) { "your_strong_password" } else { $DbPassword } }
        POSTGRES_HOST = "localhost"
        POSTGRES_PORT = "5432"
        POSTGRES_DB = "health_tracker"
        TELEGRAM_TOKEN = if ([string]::IsNullOrWhiteSpace($TelegramToken)) { "your_telegram_bot_token_here" } else { $TelegramToken }
        SECRET_KEY = if ($GeneratePasswords) { Generate-RandomPassword 32 } else { "your_secret_key_for_jwt_tokens" }
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = "30"
        API_BASE_URL = "http://localhost:8000"
        LOG_LEVEL = "INFO"
        REPORT_TIME = "07:30"
        REPORT_TIMEZONE = "Europe/Moscow"
    }
}

# Создаем содержимое .env файла
$envContent = @"
# ==========================================
# Конфигурация Employee Health Tracker
# Сгенерировано: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# ==========================================

# База данных PostgreSQL
POSTGRES_USER=$($envVars["POSTGRES_USER"])
POSTGRES_PASSWORD=$($envVars["POSTGRES_PASSWORD"])
POSTGRES_HOST=$($envVars["POSTGRES_HOST"])
POSTGRES_PORT=$($envVars["POSTGRES_PORT"])
POSTGRES_DB=$($envVars["POSTGRES_DB"])

# Telegram Bot
TELEGRAM_TOKEN=$($envVars["TELEGRAM_TOKEN"])

# Безопасность API
SECRET_KEY=$($envVars["SECRET_KEY"])
ALGORITHM=$($envVars["ALGORITHM"])
ACCESS_TOKEN_EXPIRE_MINUTES=$($envVars["ACCESS_TOKEN_EXPIRE_MINUTES"])

# Настройки API
API_BASE_URL=$($envVars["API_BASE_URL"])

# Логирование
LOG_LEVEL=$($envVars["LOG_LEVEL"])

# Настройки отчетов
REPORT_TIME=$($envVars["REPORT_TIME"])
REPORT_TIMEZONE=$($envVars["REPORT_TIMEZONE"])

# Дополнительные настройки (раскомментируйте при необходимости)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=

# SMTP для уведомлений (раскомментируйте при необходимости)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your_email@gmail.com
# SMTP_PASSWORD=your_email_password
# SMTP_FROM=noreply@healthtracker.com
"@

# Записываем в файл
$envFile = ".env"
Set-Content -Path $envFile -Value $envContent -Encoding UTF8

Write-Host "`nФайл .env создан успешно!" -ForegroundColor Green
Write-Host "Путь: $(Resolve-Path $envFile)" -ForegroundColor White

# Показываем важную информацию
Write-Host "`nВажная информация:" -ForegroundColor Yellow

if ($envVars["TELEGRAM_TOKEN"] -eq "your_telegram_bot_token_here") {
    Write-Host "⚠️  Не забудьте указать реальный TELEGRAM_TOKEN" -ForegroundColor Red
}

if ($envVars["POSTGRES_PASSWORD"] -eq "your_strong_password" -or 
    $envVars["POSTGRES_PASSWORD"] -eq "password") {
    Write-Host "⚠️  Рекомендуется изменить POSTGRES_PASSWORD на более сложный" -ForegroundColor Red
}

if ($envVars["SECRET_KEY"] -eq "your_secret_key_for_jwt_tokens") {
    Write-Host "⚠️  Рекомендуется изменить SECRET_KEY на более сложный" -ForegroundColor Red
}

Write-Host "`nСледующие шаги:" -ForegroundColor White
Write-Host "1. Проверьте и при необходимости отредактируйте файл .env" -ForegroundColor Gray
Write-Host "2. Инициализируйте базу данных:" -ForegroundColor Gray
Write-Host "   .\init-database.ps1" -ForegroundColor Gray
Write-Host "3. Запустите проект:" -ForegroundColor Gray
Write-Host "   .\run-all.ps1" -ForegroundColor Gray

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Конфигурация завершена!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

