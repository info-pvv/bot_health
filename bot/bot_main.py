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
from aiogram.fsm.context import FSMContext

from bot.config import TOKEN

# Импорт обработчиков
from bot.handlers.start import (
    cmd_start,
    cmd_help,
    cmd_cancel,
    back_to_main_menu,
    start_registration,
    process_first_name,
    process_last_name,
)

from bot.handlers.health import (
    cmd_health,
    process_healthy_status,
    process_sick_status,
    process_disease,
)

from bot.handlers.report import (
    cmd_report_api,
    cmd_report_all_sectors,
    cmd_list_sectors,
    cmd_my_info,
)

from bot.handlers.admin import (
    cmd_admin_panel,
    admin_general_report,
    admin_statistics,
    process_toggle_action,
    cmd_user_info,
    show_all_users,
    admin_back_to_main_menu,
    get_pagination_keyboard,
)

from bot.handlers.user_selection_handlers import (
    handle_user_pagination,
    handle_user_selection,
    handle_cancel_selection,
)

# Импорт обработчиков дежурств
from bot.handlers.duty import (
    cmd_duty_management,
    duty_view_pool_start,
    duty_view_pool_by_sector,
    duty_add_to_pool_start,
    duty_add_select_sector,
    duty_add_confirm,
    duty_remove_from_pool_start,
    duty_remove_select_sector,
    duty_remove_confirm,
    duty_assign_week_start,
    duty_assign_week_auto_sector,
    duty_auto_confirm,
    duty_assign_week_manual_start,
    duty_manual_sector_selected,
    duty_manual_select,
    duty_manual_force,
    duty_manual_force_confirm,
    duty_today,
    duty_stats_start,
    duty_stats_sector,
    duty_menu,
    duty_cancel,
    duty_back_to_admin,
    duty_assign_period_start,
    duty_period_sector_selected,
    duty_period_selected,
    duty_auto_plan_start,
    duty_plan_year_sector,
    duty_plan_execute,
    duty_view_schedules_start,
    schedule_view_sector_selected,
    schedule_view_week,
    schedule_view_month,
    schedule_view_year,
    schedule_view_stats,
    schedule_month_navigate,
    schedule_year_navigate,
    schedule_view_menu,
    duty_manual_select_start,
    duty_select_custom_day,
    duty_select_custom_week,
    duty_week_month_navigate,
    duty_ask_custom_date,
    process_custom_date,
    duty_manual_select_day,
    duty_confirm_week,
    duty_manual_select_week,
    duty_back_to_date_menu,
)

# Импорт состояний из центрального файла
from bot.imports import (
    ActionStates,
    HealthStates,
    AdminStates,
    RegistrationStates,
    ScheduleStates,
    DutyStates,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    dp.message.register(
        start_registration,
        ActionStates.waiting_for_action,
        F.text == "📝 Зарегистрироваться",
    )
    dp.message.register(process_first_name, RegistrationStates.waiting_for_first_name)
    dp.message.register(process_last_name, RegistrationStates.waiting_for_last_name)

    # Здоровье
    dp.message.register(
        cmd_health,
        ActionStates.waiting_for_action,
        F.text == "💊 Отметить статус здоровья",
    )
    dp.message.register(
        process_healthy_status,
        HealthStates.waiting_for_status,
        F.text.in_(["✅ здоров", "🏖 отпуск", "🏠 удаленка", "📋 отгул", "📚 учеба"]),
    )
    dp.message.register(
        process_sick_status, HealthStates.waiting_for_status, F.text == "🤒 болен"
    )
    dp.message.register(
        process_disease,
        HealthStates.waiting_for_disease,
        F.text.in_(["🤧 орви", "🦠 ковид", "💊 давление", "🤢 понос", "📝 прочее"]),
    )

    # Отчеты и информация
    dp.message.register(
        cmd_report_api,
        ActionStates.waiting_for_action,
        F.text == "📊 Отчет по моему сектору",
    )
    dp.message.register(
        cmd_report_all_sectors,
        ActionStates.waiting_for_action,
        F.text == "📈 Отчет по всем секторам",
    )
    dp.message.register(
        cmd_list_sectors,
        ActionStates.waiting_for_action,
        F.text == "🏢 Список секторов",
    )
    dp.message.register(
        cmd_my_info, ActionStates.waiting_for_action, F.text == "👤 Моя информация"
    )

    # Админ панель
    dp.message.register(
        cmd_admin_panel, ActionStates.waiting_for_action, F.text == "👑 Админ панель"
    )

    # Админ команды
    dp.message.register(
        show_all_users,
        AdminStates.waiting_admin_command,
        F.text == "🔍 Найти сотрудника",
    )
    dp.message.register(
        admin_general_report,
        AdminStates.waiting_admin_command,
        F.text == "👥 Список сотрудников",
    )
    dp.message.register(
        admin_statistics, AdminStates.waiting_admin_command, F.text == "📋 Статистика"
    )
    dp.message.register(
        admin_back_to_main_menu,
        AdminStates.waiting_admin_command,
        F.text == "⬅️ Главное меню",
    )

    # Вход в меню дежурств
    dp.message.register(
        cmd_duty_management,
        AdminStates.waiting_admin_command,
        F.text == "👨‍✈️ Управление дежурствами",
    )

    # ========== ОСНОВНЫЕ CALLBACK-ОБРАБОТЧИКИ ДЕЖУРСТВ ==========

    # Просмотр пула
    dp.callback_query.register(
        duty_view_pool_start, F.data == "duty_view_pool", DutyStates.waiting_for_action
    )
    dp.callback_query.register(
        duty_view_pool_by_sector,
        F.data.startswith("duty_view_pool:"),
        DutyStates.waiting_for_sector_selection,
    )

    # Добавление в пул
    dp.callback_query.register(
        duty_add_to_pool_start,
        F.data == "duty_add_to_pool",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        duty_add_select_sector,
        F.data.startswith("duty_add_select_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_add_confirm,
        F.data.startswith("duty_add_confirm:"),
        DutyStates.waiting_for_user_selection,
    )

    # Удаление из пула
    dp.callback_query.register(
        duty_remove_from_pool_start,
        F.data == "duty_remove_from_pool",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        duty_remove_select_sector,
        F.data.startswith("duty_remove_select_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_remove_confirm,
        F.data.startswith("duty_remove_confirm:"),
        DutyStates.waiting_for_user_removal,
    )

    # Автоматическое назначение
    dp.callback_query.register(
        duty_assign_week_start,
        F.data == "duty_assign_week",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        duty_assign_week_auto_sector,
        F.data.startswith("duty_assign_week_auto_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_auto_confirm,
        F.data.startswith("duty_auto_confirm:"),
        DutyStates.waiting_for_week_selection,
    )

    # Ручное назначение
    dp.callback_query.register(
        duty_assign_week_manual_start,
        F.data == "duty_assign_week_manual",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        duty_manual_sector_selected,
        F.data.startswith("duty_manual_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_manual_select,
        F.data.startswith("duty_manual_select:"),
        DutyStates.waiting_for_user_selection,
    )
    dp.callback_query.register(
        duty_manual_force,
        F.data.startswith("duty_manual_force:"),
        DutyStates.waiting_for_user_selection,
    )
    dp.callback_query.register(
        duty_manual_force_confirm,
        F.data.startswith("duty_manual_force_confirm:"),
        DutyStates.waiting_for_user_selection,
    )

    # Дежурный сегодня
    dp.callback_query.register(
        duty_today, F.data == "duty_today", DutyStates.waiting_for_action
    )

    # Статистика
    dp.callback_query.register(
        duty_stats_start, F.data == "duty_stats", DutyStates.waiting_for_action
    )
    dp.callback_query.register(
        duty_stats_sector,
        F.data.startswith("duty_stats_sector:"),
        DutyStates.waiting_for_sector_selection,
    )

    # Назначение на период
    dp.callback_query.register(
        duty_assign_period_start,
        F.data == "duty_assign_period",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        duty_period_sector_selected,
        F.data.startswith("duty_period_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_period_selected,
        F.data.startswith("duty_period:"),
        DutyStates.waiting_for_period_selection,
    )

    # Авто-планирование на год
    dp.callback_query.register(
        duty_auto_plan_start, F.data == "duty_auto_plan", DutyStates.waiting_for_action
    )
    dp.callback_query.register(
        duty_plan_year_sector,
        F.data.startswith("duty_plan_year_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        duty_plan_execute,
        F.data.startswith("duty_plan_execute:"),
        DutyStates.waiting_for_plan_confirmation,
    )

    # Просмотр графиков
    dp.callback_query.register(
        duty_view_schedules_start,
        F.data == "duty_view_schedules",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_view_sector_selected,
        F.data.startswith("schedule_view_sector:"),
        DutyStates.waiting_for_sector_selection,
    )
    dp.callback_query.register(
        schedule_view_week,
        F.data.startswith("schedule_view:week:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_view_month,
        F.data.startswith("schedule_view:month:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_view_year,
        F.data.startswith("schedule_view:year:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_view_stats,
        F.data.startswith("schedule_view:stats:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_month_navigate,
        F.data.startswith("schedule_month:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_year_navigate,
        F.data.startswith("schedule_year:"),
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(
        schedule_view_menu,
        F.data.startswith("schedule_view_menu:"),
        DutyStates.waiting_for_action,
    )

    # Админские callback'и
    dp.callback_query.register(process_toggle_action, F.data.startswith("toggle_"))
    dp.callback_query.register(handle_user_pagination, F.data.startswith("user_page:"))
    dp.callback_query.register(handle_user_selection, F.data.startswith("select_user:"))
    dp.callback_query.register(handle_cancel_selection, F.data == "cancel_selection")

    # Вспомогательные
    dp.callback_query.register(
        duty_menu,
        F.data == "duty_menu",
        DutyStates.waiting_for_action,
    )
    dp.callback_query.register(duty_cancel, F.data == "duty_cancel")
    dp.callback_query.register(
        duty_back_to_admin,
        F.data == "duty_back_to_admin",
        DutyStates.waiting_for_action,
    )

    dp.callback_query.register(
        duty_manual_select_start,
        F.data.startswith("duty_manual_select_start:"),
        DutyStates.waiting_for_week_selection,
    )

    # Выбор типа назначения (день/неделя)
    dp.callback_query.register(
        duty_select_custom_day,
        F.data.startswith("duty_select_custom_day:"),
        # DutyStates.waiting_for_custom_date,
    )

    # Выбор произвольной недели
    dp.callback_query.register(
        duty_select_custom_week,
        F.data.startswith("duty_select_custom_week:"),
        # DutyStates.waiting_for_custom_week,
    )

    # Навигация по месяцам для выбора недели
    dp.callback_query.register(
        duty_week_month_navigate,
        F.data.startswith("duty_week_month:"),
        DutyStates.waiting_for_custom_week,
    )

    # Запрос ввода произвольной даты
    dp.callback_query.register(
        duty_ask_custom_date,
        F.data.startswith("duty_ask_custom_date:"),
        # DutyStates.waiting_for_custom_date,
    )

    dp.callback_query.register(
        duty_back_to_date_menu,
        F.data.startswith("duty_back_to_date_menu:"),
        # DutyStates.waiting_for_date_input,
    )

    # Обработка введенной даты (сообщение)
    dp.message.register(
        process_custom_date,
        DutyStates.waiting_for_date_input,
    )

    # Назначение на конкретный день
    dp.callback_query.register(
        duty_manual_select_day,
        F.data.startswith("duty_manual_select_day:"),
        DutyStates.waiting_for_user_selection,
    )

    # Подтверждение выбранной недели
    dp.callback_query.register(
        duty_confirm_week,
        F.data.startswith("duty_confirm_week:"),
        DutyStates.waiting_for_custom_week,
    )

    # Назначение на выбранную неделю
    dp.callback_query.register(
        duty_manual_select_week,
        F.data.startswith("duty_manual_select_week:"),
        DutyStates.waiting_for_user_selection,
    )

    @dp.callback_query()
    async def debug_all_callbacks(callback: types.CallbackQuery, state: FSMContext):
        """Отладочный обработчик - показывает все callback данные и состояние"""
        current_state = await state.get_state()
        logger.info(f"🔍 DEBUG: Получен callback: '{callback.data}'")
        logger.info(f"🔍 DEBUG: Текущее состояние: {current_state}")
        logger.info(f"🔍 DEBUG: Тип callback: {type(callback.data)}")

        # Показываем все зарегистрированные обработчики для этого префикса
        if callback.data.startswith("duty_select_custom_day:"):
            logger.info(f"🔍 DEBUG: Найден обработчик для duty_select_custom_day")

        await callback.answer(f"Обработка: {callback.data[:50]}")

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
