# bot/handlers/user_selection_handlers.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.api_client import api_client
from bot.utils.formatters import format_user_info
from bot.keyboards.admin import get_user_actions_keyboard, get_user_selection_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)


async def handle_user_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Обработка пагинации пользователей"""
    if callback.data == "current":
        await callback.answer()
        return

    if callback.data.startswith("user_page:"):
        try:
            # Извлекаем номер страницы
            _, page_str = callback.data.split(":")
            new_page = int(page_str)

            # Получаем данные из состояния
            data = await state.get_data()
            users = data.get("users", [])

            if not users:
                await callback.answer("❌ Список пользователей не найден")
                return

            # Обновляем клавиатуру
            keyboard = get_user_selection_keyboard(users, page=new_page)

            total = len(users)
            page_size = 10
            total_pages = (total + page_size - 1) // page_size

            # Обновляем сообщение
            await callback.message.edit_text(
                f"👥 **Выберите пользователя**\n"
                f"📊 Всего: {total}\n"
                f"📄 Страница {new_page + 1}/{total_pages}\n\n"
                f"Нажмите на имя для подробной информации:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

            # Обновляем состояние
            await state.update_data(current_page=new_page)
            await callback.answer(f"📄 Страница {new_page + 1}")

        except Exception as e:
            logger.error(f"Ошибка пагинации: {e}")
            await callback.answer("❌ Ошибка при переключении страницы")


async def handle_user_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора пользователя"""
    if callback.data.startswith("select_user:"):
        try:
            # Извлекаем ID пользователя
            _, user_id_str = callback.data.split(":")
            user_id = int(user_id_str)

            await callback.answer("⏳ Загружаю информацию...")

            # Получаем информацию о пользователе
            user_info = await api_client.get_user(user_id)
            report_data = await api_client.get_report(user_id)

            if "error" in user_info:
                await callback.answer("❌ Пользователь не найден")
                return

            # Форматируем информацию
            formatted_info = format_user_info(user_info, report_data)

            # Обновляем сообщение
            await callback.message.edit_text(formatted_info, parse_mode="Markdown")

            # Добавляем кнопки действий
            keyboard = get_user_actions_keyboard(user_id)

            await callback.message.answer(
                "🛠 **Действия с пользователем:**",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

            # Очищаем состояние (опционально)
            await state.clear()

        except Exception as e:
            logger.error(f"Ошибка выбора пользователя: {e}")
            await callback.answer("❌ Ошибка при загрузке информации")


async def handle_cancel_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка отмены выбора"""
    if callback.data == "cancel_selection":
        try:
            await callback.message.delete()
            await callback.answer("❌ Выбор отменен")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка отмены: {e}")
            await callback.answer("❌ Отменено")
