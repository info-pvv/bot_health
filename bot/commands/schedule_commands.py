# bot/commands/schedule_commands.py
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.imports import is_user_admin, api_client,ScheduleStates



async def cmd_schedule_report(message: types.Message, state: FSMContext):
    """Настроить расписание отчетов"""
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ Только для администраторов")
        return
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⏰ Установить время",
                    callback_data="schedule_set_time"
                ),
                types.InlineKeyboardButton(
                    text="📅 Выбрать дни",
                    callback_data="schedule_set_days"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="✅ Включить рассылку",
                    callback_data="schedule_enable"
                ),
                types.InlineKeyboardButton(
                    text="❌ Выключить рассылку",
                    callback_data="schedule_disable"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔍 Показать расписание",
                    callback_data="schedule_show"
                ),
                types.InlineKeyboardButton(
                    text="🚀 Тестовая отправка",
                    callback_data="schedule_test"
                )
            ]
        ]
    )
    
    await message.answer(
        "📅 **Управление расписанием отчетов**\n\n"
        "Настройте автоматическую рассылку отчетов:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def cmd_schedule_now(message: types.Message):
    """Отправить отчет прямо сейчас"""
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ Только для администраторов")
        return
    
    await message.answer("⏳ Отправляю отчеты...")
    
    # Вызываем рассылку
    from bot.scheduler import ReportScheduler
    scheduler = ReportScheduler(message.bot)
    await scheduler.send_all_sectors_reports()
    
    await message.answer("✅ Отчеты отправлены")

async def handle_schedule_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка callback от кнопок расписания"""
    if callback.data == "schedule_set_time":
        await callback.message.answer(
            "⏰ **Установите время рассылки**\n\n"
            "Введите время в формате ЧЧ:ММ\n"
            "Например: 07:30 или 18:00",
            parse_mode="Markdown"
        )
        await state.set_state(ScheduleStates.waiting_schedule_time)
        await callback.answer()
    
    elif callback.data == "schedule_test":
        # Тестовая отправка
        from bot.scheduler import ReportScheduler
        scheduler = ReportScheduler(callback.message.bot)
        await scheduler.send_test_report()
        await callback.answer("🧪 Тестовая рассылка отправлена")
    
    # ... другие обработчики