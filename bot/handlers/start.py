# bot/handlers/start.py
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

# Импорты из центрального файла
from bot.imports import (
    is_user_admin,
    get_main_keyboard,
    api_client,
    ActionStates,
    RegistrationStates,
)

logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    # Проверяем доступность API
    api_available = await api_client.check_health()

    if not api_available:
        await message.answer(
            "⚠️ **Внимание!**\n"
            "API сервер недоступен. Некоторые функции могут не работать.\n"
            "Пожалуйста, сообщите об этом администратору."
        )

    # Проверяем, есть ли пользователь в системе
    user_info = await api_client.get_user(message.from_user.id)

    if "error" in user_info and "not found" in user_info["error"].lower():
        # Пользователя нет в системе, предлагаем регистрацию
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📝 Зарегистрироваться")],
                [types.KeyboardButton(text="ℹ️ Помощь")],
            ],
            resize_keyboard=True,
        )

        await message.answer(
            "👋 **Добро пожаловать!**\n\n"
            "Я бот для отслеживания здоровья сотрудников.\n"
            "Похоже, вы еще не зарегистрированы в системе.\n\n"
            "Для регистрации нажмите '📝 Зарегистрироваться'.\n"
            "После регистрации вы сможете отмечать свой статус здоровья.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        await state.set_state(ActionStates.waiting_for_action)
    else:
        # Пользователь уже в системе
        keyboard = await get_main_keyboard(message.from_user.id)

        first_name = user_info.get("first_name", "Сотрудник")
        await message.answer(
            f"👋 **С возвращением, {first_name}!**\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        await state.set_state(ActionStates.waiting_for_action)


async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "🤖 **ПОМОЩЬ ПО ИСПОЛЬЗОВАНИЮ БОТА**\n\n"
        "**Основные команды:**\n"
        "• /start - Начать работу с ботом\n"
        "• /help - Показать эту справку\n\n"
        "**Основные функции:**\n"
        "• 📊 Отчет по сектору - Просмотр отчета по вашему сектору\n"
        "• 📈 Отчет по всем - Общий отчет по всем секторам\n"
        "• 💊 Отметить статус - Указать свой текущий статус\n"
        "• 👤 Моя информация - Просмотр вашей информации\n"
        "• 🏢 Список секторов - Просмотр всех секторов\n\n"
        "**Административные функции:**\n"
        "• 👑 Админ панель - Панель управления системой (только для админов)\n"
        "• ✅ Вкл/выкл отчеты - Управление отчетами пользователей\n"
        "• 👑 Дать/забрать админа - Управление правами администратора\n"
        "• 📋 Статистика - Общая статистика системы\n\n"
        "**Проблемы?**\n"
        "Если бот не работает, проверьте:\n"
        "1. Интернет-соединение\n"
        "2. Доступность API сервера\n"
        "3. Сообщите администратору об ошибке"
    )

    await message.answer(help_text, parse_mode="Markdown")


async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработчик отмены действия"""
    current_state = await state.get_state()
    user_id = message.from_user.id

    # Если мы уже в главном меню (ожидаем действия)
    if current_state == ActionStates.waiting_for_action.state:
        # Просто скрываем клавиатуру
        await message.answer(
            "👋 **До свидания!**\n\n" "Чтобы начать заново, нажмите /start",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await state.clear()  # Полностью завершаем диалог
    else:
        # Если мы в каком-то другом состоянии - возвращаем в главное меню
        keyboard = await get_main_keyboard(user_id)
        await state.set_state(ActionStates.waiting_for_action)
        await message.answer(
            "❌ **Действие отменено**\n\n" "Вы вернулись в главное меню.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


async def back_to_main_menu(message: types.Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    keyboard = await get_main_keyboard(message.from_user.id)

    await message.answer(
        "🏠 **Главное меню**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(ActionStates.waiting_for_action)


async def start_registration(message: types.Message, state: FSMContext):
    """Начать процесс регистрации"""
    await message.answer(
        "📝 **Регистрация нового пользователя**\n\n"
        "Пожалуйста, введите ваше **имя**:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(RegistrationStates.waiting_for_first_name)


async def process_first_name(message: types.Message, state: FSMContext):
    """Обработка введенного имени"""
    first_name = message.text.strip()
    if len(first_name) < 2:
        await message.answer(
            "❌ Имя слишком короткое. Пожалуйста, введите корректное имя:"
        )
        return

    await state.update_data(first_name=first_name)
    await message.answer(
        f"✅ Имя сохранено: {first_name}\n\n" "Теперь введите вашу **фамилию**:",
        parse_mode="Markdown",
    )
    await state.set_state(RegistrationStates.waiting_for_last_name)


async def process_last_name(message: types.Message, state: FSMContext):
    """Обработка введенной фамилии и завершение регистрации"""
    last_name = message.text.strip()
    if len(last_name) < 2:
        await message.answer(
            "❌ Фамилия слишком короткая. Пожалуйста, введите корректную фамилию:"
        )
        return

    user_data = await state.get_data()
    first_name = user_data.get("first_name", "")

    # Подготавливаем данные для регистрации
    registration_data = {
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "first_name": first_name,
        "last_name": last_name,
        "username": message.from_user.username or "",
    }

    await message.answer("⏳ Регистрирую в системе...")

    # Используем упрощенный метод регистрации
    result = await api_client.register_user(registration_data)

    if "error" in result:
        await message.answer(
            f"❌ Ошибка регистрации:\n{result['error']}\n\n"
            "Пожалуйста, обратитесь к администратору.",
            parse_mode="Markdown",
        )
    else:
        # Регистрация успешна
        keyboard = await get_main_keyboard(message.from_user.id)

        await message.answer(
            f"✅ **Регистрация завершена!**\n\n"
            f"Добро пожаловать в систему, {first_name} {last_name}!\n"
            "Теперь вы можете использовать все функции бота.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    await state.clear()
    await state.set_state(ActionStates.waiting_for_action)
