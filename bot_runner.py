#!/usr/bin/env python3
"""
Отдельный скрипт для запуска Telegram бота
"""
import asyncio
import sys
import os

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def run_bot():
    """Запустить бота"""
    from bot.bot_main import main
    await main()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")