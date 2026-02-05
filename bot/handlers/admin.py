from aiogram import types, F
from aiogram.fsm.context import FSMContext
import aiohttp

from app.api_client import api_client
from bot.states import AdminStates, ActionStates
from bot.keyboards.admin import get_admin_keyboard, get_user_actions_keyboard
from bot.utils.decorators import admin_only
from bot.utils.formatters import format_report, format_user_info

# Админ панель
@admin_only
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    """Открыть админ панель"""
    keyboard = get_admin_keyboard()
    
    await message.answer(
        "👑 **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_admin_command)

# Отчет по конкретному сектору
async def admin_report_by_sector(message: types.Message, state: FSMContext):
    """Запросить ID сектора для отчета"""
    await message.answer(
        "Введите **ID сектора** для отчета:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AdminStates.waiting_sector_id)

async def process_admin_sector_id(message: types.Message, state: FSMContext):
    """Обработка ID сектора для отчета"""
    try:
        sector_id = int(message.text.strip())
        await message.answer(f"⏳ Загружаю отчет для сектора {sector_id}...")
        
        report_data = await api_client.get_report(sector_id=sector_id)
        formatted_report = format_report(report_data)
        
        # Улучшаем заголовок
        if "ОТЧЕТ: Сектор" in formatted_report:
            formatted_report = formatted_report.replace(
                "ОТЧЕТ: Сектор", 
                f"ОТЧЕТ ПО СЕКТОРУ {sector_id}"
            )
        
        if len(formatted_report) > 4000:
            parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(formatted_report, parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")
        return
    
    # Возвращаем в админ панель
    await cmd_admin_panel(message, state)

# Информация о пользователе
async def admin_user_info(message: types.Message, state: FSMContext):
    """Запросить ID пользователя для просмотра информации"""
    await message.answer(
        "Введите **ID пользователя** для просмотра информации:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AdminStates.waiting_user_id)

async def process_admin_user_id(message: types.Message, state: FSMContext):
    """Обработка ID пользователя"""
    try:
        user_id = int(message.text.strip())
        await message.answer(f"⏳ Ищу пользователя с ID {user_id}...")
        
        user_info = await api_client.get_user(user_id)
        
        if "error" in user_info:
            await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
        else:
            formatted_info = format_user_info(user_info)
            await message.answer(formatted_info, parse_mode="Markdown")
            
            # Создаем inline клавиатуру для быстрых действий
            keyboard = get_user_actions_keyboard(user_id)
            
            await message.answer(
                "**Быстрые действия:**",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")
    
    # Возвращаем в админ панель
    await cmd_admin_panel(message, state)

# Callback обработчики для inline кнопок
async def process_toggle_action(callback: types.CallbackQuery):
    """Обработка действий с пользователем через inline кнопки"""
    action, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)
    
    # Получаем текущую информацию о пользователе
    user_info = await api_client.get_user(user_id)
    
    if "error" in user_info:
        await callback.answer("❌ Пользователь не найден")
        return
    
    status_info = user_info.get("status_info", {})
    current_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
    
    if action == "toggle_report":
        await toggle_user_report(callback, user_id, current_name, status_info)
    elif action == "toggle_admin":
        await toggle_user_admin(callback, user_id, current_name, status_info)

async def toggle_user_report(callback: types.CallbackQuery, user_id: int, name: str, status_info: dict):
    """Переключить статус отчетов пользователя"""
    current_status = status_info.get("enable_report", False)
    new_status = not current_status
    status_text = "включены" if new_status else "выключены"
    
    # Используем API для изменения статуса
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{api_client.base_url}/admin/users/{user_id}/toggle-report"
            ) as response:
                if response.status == 200:
                    await callback.answer(
                        f"✅ Отчеты для {name} {status_text}"
                    )
                    
                    # Обновляем сообщение
                    await update_user_info_message(callback, user_id)
                else:
                    await callback.answer("❌ Ошибка при изменении настроек")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")

async def toggle_user_admin(callback: types.CallbackQuery, user_id: int, name: str, status_info: dict):
    """Переключить админ права пользователя"""
    current_status = status_info.get("enable_admin", False)
    new_status = not current_status
    status_text = "даны" if new_status else "забраны"
    
    # Используем API для изменения статуса
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{api_client.base_url}/admin/users/{user_id}/toggle-admin"
            ) as response:
                if response.status == 200:
                    await callback.answer(
                        f"✅ Админ права для {name} {status_text}"
                    )
                    
                    # Обновляем сообщение
                    await update_user_info_message(callback, user_id)
                else:
                    await callback.answer("❌ Ошибка при изменении прав")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")

async def update_user_info_message(callback: types.CallbackQuery, user_id: int):
    """Обновить сообщение с информацией о пользователе"""
    updated_info = await api_client.get_user(user_id)
    formatted_info = format_user_info(updated_info)
    
    keyboard = get_user_actions_keyboard(user_id)
    
    await callback.message.edit_text(
        formatted_info,
        parse_mode="Markdown"
    )
    await callback.message.edit_reply_markup(
        reply_markup=keyboard
    )

# Статистика
async def admin_statistics(message: types.Message):
    """Показать статистику системы"""
    # Получаем общий отчет
    report_data = await api_client.get_report()
    
    if "error" in report_data:
        await message.answer(f"❌ Ошибка при получении статистики: {report_data['error']}")
        return
    
    summary = report_data.get("status_summary", {})
    total = report_data.get("total", 0)
    
    # Получаем список секторов
    sectors_data = await api_client.get_sectors()
    sectors_count = len(sectors_data.get("sectors", [])) if not "error" in sectors_data else 0
    
    message_text = "📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"
    message_text += f"**Общая информация:**\n"
    message_text += f"👥 Всего сотрудников: {total}\n"
    message_text += f"🏢 Количество секторов: {sectors_count}\n\n"
    
    message_text += "**Распределение по статусам:**\n"
    status_emojis = {
        "здоров": "✅",
        "болен": "🤒", 
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚",
        "не указан": "❓"
    }
    
    for status, count in summary.items():
        if status:  # Пропускаем пустые статусы
            emoji = status_emojis.get(status, "📝")
            percentage = (count / total * 100) if total > 0 else 0
            message_text += f"{emoji} {status.capitalize()}: {count} ({percentage:.1f}%)\n"
    
    await message.answer(message_text, parse_mode="Markdown")

# Возврат в админ панель
async def back_to_admin_panel(message: types.Message, state: FSMContext):
    """Вернуться в админ панель"""
    await cmd_admin_panel(message, state)