# bot/handlers/admin.py
"""
Улучшенные админ-функции с единым стилем импортов
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove

# Импорты из центрального файла
from bot.imports import (
    admin_only,
    is_user_admin,
    api_client,
    format_report,
    format_user_info,
    get_main_keyboard,
    get_admin_keyboard,
    get_user_selection_keyboard,
    get_pagination_keyboard,
    AdminStates,
    ActionStates,
)

# ========== ОСНОВНЫЕ ФУНКЦИИ АДМИН-ПАНЕЛИ ==========


@admin_only
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    """Открыть админ панель"""
    keyboard = get_admin_keyboard()

    await message.answer(
        "👑 **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(AdminStates.waiting_admin_command)


@admin_only
async def show_all_users(message: types.Message, state: FSMContext):
    """Показать всех пользователей"""
    await message.answer("⏳ Загружаю список пользователей...")

    result = await api_client.get_admin_users_list(limit=100)

    if "error" in result:
        await message.answer(f"❌ Ошибка: {result['error']}")
        return

    users = result.get("users", [])

    if not users:
        await message.answer("📭 Пользователи не найдены")
        return

    keyboard = get_user_selection_keyboard(users, page=0)

    await message.answer("🔽", reply_markup=ReplyKeyboardRemove())
    # await message.answer("‎", reply_markup=ReplyKeyboardRemove())

    await message.answer(
        f"📋 **Список пользователей**\n"
        f"👥 Всего: {len(users)}\n\n"
        f"Выберите пользователя:",
        reply_markup=keyboard,
        parse_mode="Markdown",
        # reply_markup_remove=True,
        # reply_markup=ReplyKeyboardRemove(),  # 🆕 Скрываем основную клавиатуру
    )

    await state.update_data(users=users, current_page=0)
    await state.set_state(AdminStates.waiting_user_selection)


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
        parts = [
            formatted_report[i : i + 4000]
            for i in range(0, len(formatted_report), 4000)
        ]
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
        "учеба": "📚",
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
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Использование:** `/user_info ID`\n\n"
            "Пример: `/user_info 123456789`",
            parse_mode="Markdown",
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
    if not await is_user_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Использование:** `/sector_report ID`\n\n"
            "Пример: `/sector_report 100`",
            parse_mode="Markdown",
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
            parts = [
                formatted_report[i : i + 4000]
                for i in range(0, len(formatted_report), 4000)
            ]
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
    current_name = (
        f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
    )

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
                        await callback.answer(
                            f"✅ Отчеты для {current_name} {status_text}"
                        )
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
                        await callback.answer(
                            f"✅ Админ права для {current_name} {status_text}"
                        )
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
        "🏠 **Главное меню**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(ActionStates.waiting_for_action)
