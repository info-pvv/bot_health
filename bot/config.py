"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройки Telegram бота
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен в переменных окружения")

# Настройки API
API_BASE_URL = os.getenv("API_BASE_URL", "http://api-prod:8000")

# Дополнительные настройки
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ADMIN_USER_IDS = list(map(int, os.getenv("ADMIN_USER_IDS", "").split(","))) if os.getenv("ADMIN_USER_IDS") else []

REPORT_TIME = os.getenv("REPORT_TIME", "07:30")
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Europe/Moscow")
REPORT_DAYS = list(map(int, os.getenv("REPORT_DAYS", "0,1,2,3,4").split(",")))
REPORT_ENABLED = os.getenv("REPORT_ENABLED", "true").lower() == "true"