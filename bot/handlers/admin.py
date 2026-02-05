"""
Упрощенная версия админ-обработчиков
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.api_client import api_client
from bot.states import AdminStates, ActionStates
from bot.keyboards.admin import get_admin_keyboard, get_user_actions_keyboard
from bot.utils.decorators import admin_only
from bot.utils.formatters import format_report, format_user_info
from bot.keyboards.main import get_main_keyboard

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def show_user_info_simple(message: types.Message, user: dict):
    """Показать информацию о пользователе (упрощенно)"""
    first_name = user.get("first_name", "Не указано")
    last_name = user.get("last_name", "Не указано")
    username = user.get("username", "Не указано")
    user_id = user.get("user_id", user.get("id", "Не указано"))
    
    # Статус здоровья
    health_info = user.get("health_info", {})
    status = health_info.get("status", "не указан")
    
    # Права
    status_info = user.get("status_info", {})
    enable_report = status_info.get("enable_report", False)
    enable_admin = status_info.get("enable_admin", False)
    
    message_text = f"👤 **Информация о сотруднике**\n\n"
    message_text += f"**Имя:** {first_name} {last_name}\n"
    if username and username != "Не указано":
        message_text += f"**Username:** @{username}\n"
    message_text += f"**ID:** {user_id}\n\n"
    
    message_text += f"**Статус здоровья:** {status}\n"
    message_text += f"**Отчеты:** {'✅ Включены' if enable_report else '❌ Выключены'}\n"
    message_text += f"**Админ:** {'✅ Да' if enable_admin else '❌ Нет'}\n"
    
    await message.answer(message_text, parse_mode="Markdown")
    
    # Кнопки действий
    if user_id and user_id != "Не указано" and str(user_id).isdigit():
        keyboard = get_user_actions_keyboard(int(user_id))
        await message.answer("**Действия:**", reply_markup=keyboard, parse_mode="Markdown")

async def show_user_list_simple(message: types.Message, users: list, query: str = ""):
    """Показать список пользователей (упрощенно)"""
    message_text = f"🔍 **Найдено сотрудников: {len(users)}**"
    if query:
        message_text += f" по запросу: '{query}'"
    message_text += "\n\n"
    
    for i, user in enumerate(users[:10], 1):  # Ограничиваем 10 результатами
        first_name = user.get("first_name", "Не указано")
        last_name = user.get("last_name", "Не указано")
        user_id = user.get("user_id", user.get("id", "Не указано"))
        
        # Получаем статус здоровья, если есть
        health_info = user.get("health_info", {})
        status = health_info.get("status", "")
        status_emoji = {
            "здоров": "✅", "болен": "🤒", "отпуск": "🏖",
            "удаленка": "🏠", "отгул": "📋", "учеба": "📚"
        }.get(status, "❓")
        
        # Админский статус
        status_info = user.get("status_info", {})
        admin_emoji = " 👑" if status_info.get("enable_admin", False) else ""
        
        message_text += f"{i}. {status_emoji} **{first_name} {last_name}**{admin_emoji}\n"
        message_text += f"   ID: {user_id}\n\n"
    
    if len(users) > 10:
        message_text += f"*... и еще {len(users) - 10} сотрудников*\n\n"
    
    message_text += "ℹ️ Для подробной информации используйте команду:\n"
    if users and users[0].get('user_id'):
        message_text += f"`/user_info {users[0].get('user_id')}`"
    else:
        message_text += "`/user_info ID`"
    
    await message.answer(message_text, parse_mode="Markdown")

# ========== ОСНОВНЫЕ ФУНКЦИИ АДМИН-ПАНЕЛИ ==========

@admin_only
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    """Открыть админ панель"""
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
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_admin_command)

# ========== ПОИСК СОТРУДНИКА ==========

@admin_only
async def admin_search_user(message: types.Message, state: FSMContext):
    """Начать поиск сотрудника"""
    await message.answer(
        "🔍 **Поиск сотрудника**\n\n"
        "ℹ️ *Поиск временно недоступен*\n\n"
        "Для информации о сотруднике используйте команду:\n"
        "`/user_info ID`\n\n"
        "Пример: `/user_info 123456789`",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await cmd_admin_panel(message, state)

async def process_user_search(message: types.Message, state: FSMContext):
    """Заглушка для обработки поискового запроса"""
    await message.answer("ℹ️ Поиск временно недоступен")
    await cmd_admin_panel(message, state)

# ========== ОТЧЕТ ПО СЕКТОРУ ==========

@admin_only 
async def admin_select_sector(message: types.Message, state: FSMContext):
    """Выбор сектора для отчета"""
    await message.answer(
        "🏢 **Для отчета по сектору:**\n\n"
        "Используйте команду:\n"
        "`/sector_report ID`\n\n"
        "Пример: `/sector_report 100`\n\n"
        "Чтобы узнать ID секторов, используйте:\n"
        "команду '🏢 Список секторов' из главного меню",
        parse_mode="Markdown"
    )

# ========== ОБЩИЙ ОТЧЕТ ==========

@admin_only
async def admin_general_report(message: types.Message, state: FSMContext):
    """Показать общий отчет"""
    await message.answer("⏳ Загружаю общий отчет по всем секторам...")
    
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

# ========== СТАТИСТИКА ==========

@admin_only
async def admin_statistics(message: types.Message, state: FSMContext):
    """Показать статистику системы"""
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

# ========== КОМАНДЫ ДЛЯ АДМИНОВ ==========

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

# ========== CALLBACK ОБРАБОТЧИКИ ==========

async def process_toggle_action(callback: types.CallbackQuery):
    """Обработка переключения настроек пользователя"""
    import aiohttp
    action, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)
    
    # Получаем информацию о пользователе
    user_info = await api_client.get_user(user_id)
    
    if "error" in user_info:
        await callback.answer("❌ Пользователь не найден")
        return
    
    status_info = user_info.get("status_info", {})
    current_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
    
    if action == "toggle_report":
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
                        await callback.answer(f"✅ Отчеты для {current_name} {status_text}")
                    else:
                        await callback.answer("❌ Ошибка при изменении настроек")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}")
    
    elif action == "toggle_admin":
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
                        await callback.answer(f"✅ Админ права для {current_name} {status_text}")
                    else:
                        await callback.answer("❌ Ошибка при изменении прав")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}")

# ========== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ==========

async def admin_back_to_main_menu(message: types.Message, state: FSMContext):
    """Вернуться в главное меню из админ-панели"""
    await state.clear()
    
    keyboard = await get_main_keyboard(message.from_user.id)
    
    await message.answer(
        "🏠 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ActionStates.waiting_for_action)