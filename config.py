# config.py
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Проверяем наличие токена
if not TOKEN:
    print("⚠️  ВНИМАНИЕ: TELEGRAM_TOKEN не найден в .env файле")
    print("💡 Создайте .env файл в корне проекта со следующим содержимым:")
    print("")
    print("TELEGRAM_TOKEN=ваш_токен_бота_здесь")
    print("POSTGRES_USER=postgres")
    print("POSTGRES_PASSWORD=postgres")
    print("POSTGRES_HOST=localhost")
    print("POSTGRES_PORT=5432")
    print("POSTGRES_DB=health_tracker")
    print("")
    print("Или запустите скрипт для создания .env файла:")
    print("python scripts/create-sample-env.py")
    exit(1)

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
    #"sts": -1001567110550,
    #"etivi": -1001727372240,
    "test": -1001764172286
}

# Настройки API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 30

print(f"✅ Конфигурация загружена. Бот: @{(os.getenv('BOT_USERNAME', 'unknown'))}")