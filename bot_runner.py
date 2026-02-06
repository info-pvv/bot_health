#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
"""
import asyncio
import sys
import os
from bot.scheduler import ReportScheduler
import signal
from bot.bot_main import main

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_bot():
    """Запустить бота"""
    #from bot.bot_main import main
    await main()
    
async def shutdown(scheduler, loop):
    """Корректное завершение"""
    print("\n🛑 Завершение работы...")
    
    if scheduler:
        scheduler.stop()
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def run_with_scheduler():
    """Запуск с планировщиком"""
    from aiogram import Bot
    from bot.config import TOKEN
    
    bot = Bot(token=TOKEN)
    scheduler = ReportScheduler(bot)
    
    # Настройка расписания
    #scheduler.schedule_daily_report("21:02")
    #scheduler.start()
    
    # Запуск бота
    try:
        await main()
    finally:
        scheduler.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_with_scheduler())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        print("\n💡 Проверьте:")
        print("1. Наличие файла .env с TELEGRAM_TOKEN")
        print("2. Запущен ли FastAPI сервер (python main.py)")
        print("3. Установлены ли зависимости: pip install aiogram aiohttp python-dotenv")