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
