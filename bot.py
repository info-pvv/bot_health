#!venv/bin/python
import logging
import asyncio
import aiohttp
from typing import Optional

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import BotCommand, Message
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BotBlocked
import aiogram.utils.markdown as fmt

from config import TOKEN
from app.handlers.health import register_handlers_health
from app.handlers.health import OrderHealth
from app.handlers.common import register_handlers_common
from app.handlers.admin import register_handlers_admin

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tzlocal import get_localzone

logger = logging.getLogger(__name__)

# Конфигурация API
API_BASE_URL = "http://localhost:8000"

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f"{self.base_url}{endpoint}", **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    response.raise_for_status()
    
    async def get_user(self, user_id: int):
        return await self._make_request("GET", f"/users/{user_id}")
    
    async def create_user(self, user_data: dict, chat_id: int):
        return await self._make_request("POST", f"/users/?chat_id={chat_id}", json=user_data)
    
    async def update_user(self, user_id: int, user_data: dict):
        return await self._make_request("PUT", f"/users/{user_id}", json=user_data)
    
    async def update_health_status(self, user_id: int, status: str):
        return await self._make_request("POST", f"/health/{user_id}/status", json={"status": status})
    
    async def update_disease(self, user_id: int, disease: str):
        return await self._make_request("POST", f"/health/{user_id}/disease", json={"disease": disease})
    
    async def get_report(self, sector_id: Optional[int] = None):
        endpoint = "/health/report"
        if sector_id:
            endpoint += f"?sector_id={sector_id}"
        return await self._make_request("GET", endpoint)
    
    async def is_user_admin(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return user.get("status", {}).get("enable_admin", False) if user else False

api_client = APIClient(API_BASE_URL)

# Регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/cancel", description="Отменить текущее действие"),
        BotCommand(command="/report", description="Получить отчет")
    ]
    await bot.set_my_commands(commands)

async def report_health(dp: Dispatcher):
    try:
        # Получаем список секторов через API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health/sectors") as response:
                if response.status == 200:
                    data = await response.json()
                    sectors = data.get("sectors", [])
                else:
                    logger.error(f"Failed to get sectors: {response.status}")
                    return
    except Exception as e:
        logger.error(f"Error getting sectors: {e}")
        return
    
    for sector_id in sectors:
        try:
            report_data = await api_client.get_report(sector_id)
            if not report_data:
                continue
                
            string_status = ''
            string_to_send = ''
            hop_count = 0
            
            for status, count in report_data.get("status_summary", {}).items():
                hop_count += count
                string_status += f'{status} - {count}\n'
            
            string_status += f'Всего: {hop_count}\n'
            
            for user in report_data.get("users", []):
                string_to_send += f"{user.get('first_name', '')} {user.get('last_name', '')} "
                string_to_send += f"{user.get('status', '')} {user.get('disease', '')}\n"
            
            await dp.bot.send_message(sector_id, text=string_status)
            if string_to_send.strip():
                await dp.bot.send_message(sector_id, text=string_to_send)
                
        except Exception as e:
            logger.error(f"Error sending report for sector {sector_id}: {e}")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.error("Starting bot")
    
    bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot, storage=MemoryStorage())
    scheduler = AsyncIOScheduler(timezone=str(get_localzone()))
    
    # Регистрация хэндлеров (нужно будет обновить их для работы с API)
    register_handlers_common(dp, api_client)
    register_handlers_health(dp, api_client)
    register_handlers_admin(dp, api_client)
    
    # Установка команд бота
    await set_commands(bot)
    scheduler.add_job(report_health, 'cron', day_of_week='mon-sun', hour=7, minute=30, args=(dp,))
    
    # Обработчики для тестирования
    @dp.message_handler(lambda message: message.text == "ид")
    async def with_puree1(message: types.Message):
        print(message.chat.id)
        await message.reply(message.chat.id)
    
    @dp.message_handler(lambda message: message.text == "pr")
    async def with_puree2(message: types.Message):
        await report_health(dp)
    
    @dp.errors_handler(exception=BotBlocked)
    async def error_bot_blocked(update: types.Update, exception: BotBlocked):
        print(f"Меня заблокировал пользователь!\nСообщение: {update}\nОшибка: {exception}")
        return True
    
    scheduler.start()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())