"""
Простая версия админ-функций
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.api_client import api_client
from bot.states import AdminStates, ActionStates
from bot.utils.decorators import admin_only
from bot.utils.formatters import format_report, format_user_info
from bot.keyboards.main import get_main_keyboard

@admin_only
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    """Простая админ-панель"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Отчет по сектору")],
            [types.KeyboardButton(text="📈 Общий отчет")],
            [types.KeyboardButton(text="📋 Статистика")],
            [types.KeyboardButton(text="⬅️ Главное меню")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👑 **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n"
        "ℹ️ *Поиск сотрудников временно недоступен*\n"
        "Для информации о сотруднике используйте команду:\n"
        "`/user_info ID`\n\n"
        "Для отчета по сектору:\n"
        "`/sector_report ID`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_admin_command)

@admin_only 
async def admin_select_sector(message: types.Message, state: FSMContext):
    """Простой выбор сектора"""
    await message.answer(
        "🏢 **Для отчета по сектору:**\n\n"
        "Используйте команду:\n"
        "`/sector_report ID`\n\n"
        "Пример: `/sector_report 100`\n\n"
        "Чтобы узнать ID секторов, используйте:\n"
        "`/sectors`",
        parse_mode="Markdown"
    )

@admin_only
async def admin_general_report(message: types.Message):
    """Общий отчет"""
    await message.answer("⏳ Загружаю общий отчет...")
    
    report_data = await api_client.get_report()
    
    if "error" in report_data:
        await message.answer(f"❌ Ошибка: {report_data['error']}")
        return
    
    formatted_report = format_report(report_data)
    
    if len(formatted_report) > 4000:
        parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(formatted_report, parse_mode="Markdown")

@admin_only
async def admin_statistics(message: types.Message):
    """Статистика"""
    await message.answer("⏳ Загружаю статистику...")
    
    report_data = await api_client.get_report()
    
    if "error" in report_data:
        await message.answer(f"❌ Ошибка: {report_data['error']}")
        return
    
    summary = report_data.get("status_summary", {})
    total = report_data.get("total", 0)
    
    message_text = "📊 **Статистика системы**\n\n"
    message_text += f"**Всего сотрудников:** {total}\n\n"
    message_text += "**Распределение по статусам:**\n"
    
    status_emojis = {
        "здоров": "✅",
        "болен": "🤒", 
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚"
    }
    
    for status, count in summary.items():
        if status:
            emoji = status_emojis.get(status, "📝")
            percentage = (count / total * 100) if total > 0 else 0
            message_text += f"{emoji} {status}: {count} ({percentage:.1f}%)\n"
    
    await message.answer(message_text, parse_mode="Markdown")

async def cmd_user_info(message: types.Message):
    """Команда для получения информации о пользователе"""
    # Проверка админских прав
    from bot.services.admin_check import is_user_admin
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ **Использование:** `/user_info ID`\n\n"
            "Пример: `/user_info 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        user_id = int(args[1])
        await message.answer(f"⏳ Загружаю информацию о пользователе ID: {user_id}...")
        
        user_info = await api_client.get_user(user_id)
        
        if "error" in user_info:
            await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
            return
        
        formatted_info = format_user_info(user_info)
        await message.answer(formatted_info, parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")

async def cmd_sector_report(message: types.Message):
    """Команда для отчета по сектору"""
    # Проверка админских прав
    from bot.services.admin_check import is_user_admin
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    args = message.text.split()
    
    if len(args) < 2:
        await message.answer(
            "❌ **Использование:** `/sector_report ID`\n\n"
            "Пример: `/sector_report 100`",
            parse_mode="Markdown"
        )
        return
    
    try:
        sector_id = int(args[1])
        await message.answer(f"⏳ Загружаю отчет для сектора ID: {sector_id}...")
        
        report_data = await api_client.get_report(sector_id=sector_id)
        
        if "error" in report_data:
            await message.answer(f"❌ Ошибка: {report_data['error']}")
            return
        
        formatted_report = format_report(report_data)
        
        if len(formatted_report) > 4000:
            parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(formatted_report, parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")