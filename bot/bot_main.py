# bot/bot_main.py
#!/usr/bin/env python3
"""
Главный файл для запуска Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import types
from bot.scheduler import ReportScheduler


from bot.config import TOKEN

# Импорт обработчиков
from bot.handlers.start import (
    cmd_start, cmd_help,  cmd_cancel, back_to_main_menu,
    start_registration, process_first_name, process_last_name
)

from bot.handlers.health import (
    cmd_health, process_healthy_status, 
    process_sick_status, process_disease
)

from bot.handlers.report import (
    cmd_report_api, cmd_report_all_sectors,
    cmd_list_sectors, cmd_my_info
)

from bot.handlers.admin import (
    cmd_admin_panel, 
    admin_general_report, admin_statistics,
    process_toggle_action, cmd_user_info,
    show_all_users, admin_back_to_main_menu,
    get_pagination_keyboard
)

from bot.handlers.user_selection_handlers import (
    handle_user_pagination,
    handle_user_selection,
    handle_cancel_selection
)

# Импорт состояний из центрального файла
from bot.imports import ActionStates, HealthStates, AdminStates, RegistrationStates, ScheduleStates

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Настройка и конфигурация бота"""
    bot = Bot(token=TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    
     # Создаем планировщик
    scheduler = ReportScheduler(bot)
    
    # Планируем задачи
    scheduler.schedule_daily_report("07:30")  # Ежедневно в 7:30
    # scheduler.schedule_test_report(60)  # Тест каждые 60 секунд
    
    # Запускаем планировщик
    scheduler.start()
    
    # Регистрация обработчиков
    
    # Команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
        
    # Основные действия
    dp.message.register(cmd_cancel, F.text == "❌ Отменить действие")
    dp.message.register(back_to_main_menu, F.text == "⬅️ Назад в меню")
    
    # Регистрация
    dp.message.register(start_registration, ActionStates.waiting_for_action, F.text == "📝 Зарегистрироваться")
    dp.message.register(process_first_name, RegistrationStates.waiting_for_first_name)
    dp.message.register(process_last_name, RegistrationStates.waiting_for_last_name)
    
    # Здоровье
    dp.message.register(cmd_health, ActionStates.waiting_for_action, F.text == "💊 Отметить статус здоровья")
    dp.message.register(
        process_healthy_status, 
        HealthStates.waiting_for_status, 
        F.text.in_(["✅ здоров", "🏖 отпуск", "🏠 удаленка", "📋 отгул", "📚 учеба"])
    )
    dp.message.register(process_sick_status, HealthStates.waiting_for_status, F.text == "🤒 болен")
    dp.message.register(
        process_disease, 
        HealthStates.waiting_for_disease, 
        F.text.in_(["🤧 орви", "🦠 ковид", "💊 давление", "🤢 понос", "📝 прочее"])
    )
    
    # Отчеты и информация
    dp.message.register(cmd_report_api, ActionStates.waiting_for_action, F.text == "📊 Отчет по моему сектору")
    dp.message.register(cmd_report_all_sectors, ActionStates.waiting_for_action, F.text == "📈 Отчет по всем секторам")
    dp.message.register(cmd_list_sectors, ActionStates.waiting_for_action, F.text == "🏢 Список секторов")
    dp.message.register(cmd_my_info, ActionStates.waiting_for_action, F.text == "👤 Моя информация")
    
    # Админ панель
    dp.message.register(cmd_admin_panel, ActionStates.waiting_for_action, F.text == "👑 Админ панель")
    
    # Админ команды
    dp.message.register(show_all_users, AdminStates.waiting_admin_command, F.text == "🔍 Найти сотрудника")
    dp.message.register(admin_general_report, AdminStates.waiting_admin_command, F.text == "👥 Список сотрудников")
    dp.message.register(admin_statistics, AdminStates.waiting_admin_command, F.text == "📋 Статистика")
    dp.message.register(admin_back_to_main_menu, AdminStates.waiting_admin_command, F.text == "⬅️ Главное меню")
    
    
    
    # Callback обработчики
    dp.callback_query.register(process_toggle_action, F.data.startswith("toggle_"))
    
    
    dp.callback_query.register(handle_user_pagination, F.data.startswith("user_page:"))
    dp.callback_query.register(handle_user_selection, F.data.startswith("select_user:"))
    dp.callback_query.register(handle_cancel_selection, F.data == "cancel_selection")

    #@dp.callback_query()
    #async def temp_handler(callback: types.CallbackQuery):
    #    print(f"🔍 DEBUG: callback.data = '{callback.data}'")
    #    print(f"🔍 DEBUG: type = {type(callback.data)}")
#
    #    # Ответьте что угодно, чтобы пользователь видел реакцию
    #    await callback.answer(f"📨: {callback.data}")
    
    return bot, dp

async def main():
    """Основная функция запуска бота"""
    print("🤖 Запуск Telegram бота с модульной структурой...")
    
    from app.api_client import api_client
    print(f"🌐 API сервер: {api_client.base_url}")
    
    # Проверяем доступность API
    if await api_client.check_health():
        print("✅ API сервер доступен")
    else:
        print("⚠️  API сервер недоступен. Проверьте запущен ли FastAPI сервер.")
    
    # Настраиваем бота
    bot, dp = await setup_bot()
    
    bot_info = await bot.get_me()
    print(f"👤 Бот: @{bot_info.username}")
    print("🔄 Для остановки нажмите Ctrl+C\n")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Остановка бота...")
    finally:
        # Закрываем сессию API клиента
        await api_client.close()
        print("✅ Сессия API закрыта")

if __name__ == "__main__":
    asyncio.run(main())