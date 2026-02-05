#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
"""
import asyncio
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_bot():
    """Запустить бота"""
    from bot.bot_main import main
    await main()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        print("\n💡 Проверьте:")
        print("1. Наличие файла .env с TELEGRAM_TOKEN")
        print("2. Запущен ли FastAPI сервер (python main.py)")
        print("3. Установлены ли зависимости: pip install aiogram aiohttp python-dotenv")