# bot_v3.py - исправленная версия с правильными сигнатурами обработчиков
import asyncio
import logging
from typing import Optional 
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.api_client import api_client
from config import TOKEN
import aiohttp

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
class HealthStates(StatesGroup):
    waiting_for_status = State()
    waiting_for_disease = State()
    
class ActionStates(StatesGroup):
    waiting_for_action = State()

class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()

class AdminStates(StatesGroup):
    waiting_admin_command = State()
    waiting_user_id = State()
    waiting_sector_id = State()
    waiting_search_query = State()
    waiting_new_sector_name = State()
    waiting_edit_sector = State()

# Функция для проверки прав администратора
async def check_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    user_info = await api_client.get_user(user_id)
    
    if "error" in user_info:
        return False
    
    # Проверяем поле enable_admin в status_info
    status_info = user_info.get("status_info", {})
    is_admin = status_info.get("enable_admin", False)
    
    return is_admin

# Исправленный декоратор для защиты админских команд
def admin_only(handler):
    async def wrapper(message: types.Message, state: FSMContext):
        if not await check_admin(message.from_user.id):
            await message.answer(
                "⛔ **Доступ запрещен!**\n\n"
                "У вас нет прав администратора.\n"
                "Для получения доступа обратитесь к администратору системы.",
                parse_mode="Markdown"
            )
            return
        return await handler(message, state)
    return wrapper

# Функция для форматирования отчета
def format_report(report_data: dict) -> str:
    """Форматировать данные отчета в читаемый вид"""
    if "error" in report_data:
        return f"❌ Ошибка при получении отчета:\n{report_data['error']}"
    
    summary = report_data.get("status_summary", {})
    users = report_data.get("users", [])
    total = report_data.get("total", 0)
    sector_info = report_data.get("sector_info", {})
    
    # Определяем заголовок
    sector_name = sector_info.get("name") if sector_info else None
    sector_id = sector_info.get("sector_id") if sector_info else None
    
    if sector_name:
        header = f"📊 **ОТЧЕТ: {sector_name}**\n\n"
    elif sector_id:
        header = f"📊 **ОТЧЕТ: Сектор {sector_id}**\n\n"
    else:
        header = "📊 **ОТЧЕТ ПО ВСЕМ СЕКТОРАМ**\n\n"
    
    message = header
    
    # Сводка по статусам
    message += "**Статистика:**\n"
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
            message += f"{emoji} {status.capitalize()}: {count}\n"
    
    message += f"\n**Всего сотрудников:** {total}\n"
    
    # Список сотрудников
    if users:
        message += "\n**Сотрудники:**\n"
        for i, user in enumerate(users[:15], 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Без имени"
            status = user.get('status', 'не указан')
            disease = user.get('disease', '')
            
            emoji = status_emojis.get(status, "❓")
            
            message += f"{i}. {emoji} {name}"
            if status and status != "не указан":
                message += f" - {status}"
            if disease:
                message += f" ({disease})"
            message += "\n"
        
        if len(users) > 15:
            message += f"\n... и еще {len(users) - 15} сотрудников"
    
    return message

def format_user_info(user_data: dict) -> str:
    """Форматировать информацию о пользователе"""
    if "error" in user_data:
        return f"❌ Ошибка: {user_data['error']}"
    
    message = "👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n\n"
    
    # Основная информация
    first_name = user_data.get("first_name", "Не указано")
    last_name = user_data.get("last_name", "Не указано")
    username = user_data.get("username", "Не указано")
    user_id = user_data.get("user_id", "Не указано")
    
    message += f"**ID:** {user_id}\n"
    message += f"**Имя:** {first_name}\n"
    message += f"**Фамилия:** {last_name}\n"
    message += f"**Username:** {username}\n"
    
    # Информация о здоровье
    health_info = user_data.get("health_info", {})
    disease_info = user_data.get("disease_info", {})
    
    status = health_info.get("status") if health_info else "не указан"
    disease = disease_info.get("disease") if disease_info else "не указано"
    
    status_emojis = {
        "здоров": "✅",
        "болен": "🤒",
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚"
    }
    
    emoji = status_emojis.get(status, "❓")
    message += f"\n**Статус здоровья:** {emoji} {status if status else 'не указан'}\n"
    
    if disease and disease != "не указано":
        message += f"**Заболевание:** {disease}\n"
    
    # Информация о правах
    status_info = user_data.get("status_info", {})
    if status_info:
        enable_report = status_info.get("enable_report", False)
        enable_admin = status_info.get("enable_admin", False)
        sector_id = status_info.get("sector_id", "Не указан")
        
        message += f"\n**Настройки доступа:**\n"
        message += f"📊 Отчеты: {'✅ Включены' if enable_report else '❌ Выключены'}\n"
        message += f"👑 Админ: {'✅ Да' if enable_admin else '❌ Нет'}\n"
        message += f"🏢 Сектор: {sector_id}\n"
    
    # Даты
    created_at = user_data.get("created_at", "")
    updated_at = user_data.get("updated_at", "")
    
    if created_at:
        created_str = str(created_at)
        if '.' in created_str:
            created_str = created_str.split('.')[0]
        message += f"\n📅 Зарегистрирован: {created_str}"
    
    return message

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
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
                [types.KeyboardButton(text="ℹ️ Помощь")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            "👋 **Добро пожаловать!**\n\n"
            "Я бот для отслеживания здоровья сотрудников.\n"
            "Похоже, вы еще не зарегистрированы в системе.\n\n"
            "Для регистрации нажмите '📝 Зарегистрироваться'.\n"
            "После регистрации вы сможете отмечать свой статус здоровья.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(ActionStates.waiting_for_action)
    else:
        # Проверяем права администратора
        is_admin = await check_admin(message.from_user.id)
        
        # Основная клавиатура
        keyboard_buttons = [
            [types.KeyboardButton(text="📊 Отчет по моему сектору")],
            [types.KeyboardButton(text="📈 Отчет по всем секторам")],
            [types.KeyboardButton(text="🏢 Список секторов")],
            [types.KeyboardButton(text="💊 Отметить статус здоровья")],
            [types.KeyboardButton(text="👤 Моя информация")]
        ]
        
        # Добавляем админ-панель если пользователь админ
        if is_admin:
            keyboard_buttons.append([types.KeyboardButton(text="👑 Админ панель")])
        
        keyboard_buttons.append([types.KeyboardButton(text="❌ Отменить действие")])
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True
        )
        
        first_name = user_info.get("first_name", "Сотрудник")
        admin_text = "\n👑 Вы являетесь администратором системы." if is_admin else ""
        
        await message.answer(
            f"👋 **С возвращением, {first_name}!**{admin_text}\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await state.set_state(ActionStates.waiting_for_action)

# Команда регистрации
@dp.message(ActionStates.waiting_for_action, F.text == "📝 Зарегистрироваться")
async def start_registration(message: types.Message, state: FSMContext):
    await message.answer(
        "📝 **Регистрация нового пользователя**\n\n"
        "Пожалуйста, введите ваше **имя**:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_for_first_name)

# Обработка имени
@dp.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    first_name = message.text.strip()
    if len(first_name) < 2:
        await message.answer("❌ Имя слишком короткое. Пожалуйста, введите корректное имя:")
        return
    
    await state.update_data(first_name=first_name)
    await message.answer(
        f"✅ Имя сохранено: {first_name}\n\n"
        "Теперь введите вашу **фамилию**:",
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_last_name)

# Обработка фамилии и завершение регистрации
@dp.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    last_name = message.text.strip()
    if len(last_name) < 2:
        await message.answer("❌ Фамилия слишком короткая. Пожалуйста, введите корректную фамилию:")
        return
    
    user_data = await state.get_data()
    first_name = user_data.get("first_name", "")
    
    # Подготавливаем данные для регистрации
    registration_data = {
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "first_name": first_name,
        "last_name": last_name,
        "username": message.from_user.username or ""
    }
    
    await message.answer("⏳ Регистрирую в системе...")
    
    # Используем упрощенный метод регистрации
    result = await api_client.register_user(registration_data)
    
    if "error" in result:
        await message.answer(
            f"❌ Ошибка регистрации:\n{result['error']}\n\n"
            "Пожалуйста, обратитесь к администратору.",
            parse_mode="Markdown"
        )
    else:
        # Регистрация успешна
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📊 Отчет по моему сектору")],
                [types.KeyboardButton(text="📈 Отчет по всем секторам")],
                [types.KeyboardButton(text="🏢 Список секторов")],
                [types.KeyboardButton(text="💊 Отметить статус здоровья")],
                [types.KeyboardButton(text="👤 Моя информация")],
                [types.KeyboardButton(text="❌ Отменить действие")]
            ],
            resize_keyboard=True
        )
        
        await message.answer(
            f"✅ **Регистрация завершена!**\n\n"
            f"Добро пожаловать в систему, {first_name} {last_name}!\n"
            "Теперь вы можете использовать все функции бота.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await state.clear()
    await state.set_state(ActionStates.waiting_for_action)

# Получение отчета через API
@dp.message(ActionStates.waiting_for_action, F.text == "📊 Отчет по моему сектору")
async def cmd_report_api(message: types.Message):
    await message.answer("⏳ Загружаю отчет для вашего сектора...")
    
    # Получаем отчет через API с названием сектора
    report_data = await api_client.get_report(user_id=message.from_user.id)
    
    # Форматируем отчет
    formatted_report = format_report(report_data)
    
    # Разбиваем длинные сообщения
    if len(formatted_report) > 4000:
        parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(formatted_report, parse_mode="Markdown")

@dp.message(ActionStates.waiting_for_action, F.text == "📈 Отчет по всем секторам")
async def cmd_report_all_sectors(message: types.Message):
    await message.answer("⏳ Загружаю отчет по всем секторам...")
    
    # Получаем отчет без фильтрации по сектору
    report_data = await api_client.get_report()
    
    # Форматируем отчет
    formatted_report = format_report(report_data)
    
    if len(formatted_report) > 4000:
        parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(formatted_report, parse_mode="Markdown")

# Отметка статуса здоровья
@dp.message(ActionStates.waiting_for_action, F.text == "💊 Отметить статус здоровья")
async def cmd_health(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="✅ здоров"), types.KeyboardButton(text="🤒 болен")],
            [types.KeyboardButton(text="🏖 отпуск"), types.KeyboardButton(text="🏠 удаленка")],
            [types.KeyboardButton(text="📋 отгул"), types.KeyboardButton(text="📚 учеба")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👤 **{message.from_user.first_name}, выберите ваш статус:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(HealthStates.waiting_for_status)

# Обработка здорового статуса
@dp.message(HealthStates.waiting_for_status, F.text.in_(["✅ здоров", "🏖 отпуск", "🏠 удаленка", "📋 отгул", "📚 учеба"]))
async def process_healthy_status_api(message: types.Message, state: FSMContext):
    # Извлекаем чистый статус (без эмодзи)
    status_text = message.text
    status_map = {
        "✅ здоров": "здоров",
        "🏖 отпуск": "отпуск", 
        "🏠 удаленка": "удаленка",
        "📋 отгул": "отгул",
        "📚 учеба": "учеба"
    }
    status = status_map.get(status_text, status_text.split(" ", 1)[-1])
    
    # Отправляем статус в API
    result = await api_client.update_health_status(
        user_id=message.from_user.id,
        status=status,
        disease=""
    )
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Отчет по моему сектору")],
            [types.KeyboardButton(text="📈 Отчет по всем секторам")],
            [types.KeyboardButton(text="🏢 Список секторов")],
            [types.KeyboardButton(text="💊 Отметить статус здоровья")],
            [types.KeyboardButton(text="👤 Моя информация")],
            [types.KeyboardButton(text="❌ Отменить действие")]
        ],
        resize_keyboard=True
    )
    
    if "error" in result:
        await message.answer(
            f"❌ Ошибка при сохранении статуса:\n{result['error']}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        await message.answer(
            f"✅ **{username}, ваш статус сохранен:** {status}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.info(f"User {message.from_user.id} set status via API: {status}")
    
    await state.clear()
    await state.set_state(ActionStates.waiting_for_action)

# Обработка статуса "болен"
@dp.message(HealthStates.waiting_for_status, F.text == "🤒 болен")
async def process_sick_status_api(message: types.Message, state: FSMContext):
    await state.update_data(status="болен")
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🤧 орви"), types.KeyboardButton(text="🦠 ковид")],
            [types.KeyboardButton(text="💊 давление"), types.KeyboardButton(text="🤢 понос")],
            [types.KeyboardButton(text="📝 прочее"), types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "🤒 **Укажите заболевание:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(HealthStates.waiting_for_disease)

# Обработка заболевания
@dp.message(HealthStates.waiting_for_disease, F.text.in_(["🤧 орви", "🦠 ковид", "💊 давление", "🤢 понос", "📝 прочее"]))
async def process_disease_api(message: types.Message, state: FSMContext):
    # Извлекаем чистое заболевание
    disease_text = message.text
    disease_map = {
        "🤧 орви": "орви",
        "🦠 ковид": "ковид",
        "💊 давление": "давление",
        "🤢 понос": "понос",
        "📝 прочее": "прочее"
    }
    disease = disease_map.get(disease_text, disease_text.split(" ", 1)[-1])
    
    data = await state.get_data()
    status = data.get("status", "болен")
    
    # Отправляем статус и заболевание в API
    result = await api_client.update_health_status(
        user_id=message.from_user.id,
        status=status,
        disease=disease
    )
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Отчет по моему сектору")],
            [types.KeyboardButton(text="📈 Отчет по всем секторам")],
            [types.KeyboardButton(text="🏢 Список секторов")],
            [types.KeyboardButton(text="💊 Отметить статус здоровья")],
            [types.KeyboardButton(text="👤 Моя информация")],
            [types.KeyboardButton(text="❌ Отменить действие")]
        ],
        resize_keyboard=True
    )
    
    if "error" in result:
        await message.answer(
            f"❌ Ошибка при сохранении:\n{result['error']}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        await message.answer(
            f"🤒 **{username}, статус сохранен:**\n"
            f"• Статус: {status}\n"
            f"• Заболевание: {disease}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.info(f"User {message.from_user.id} set status via API: {status}, disease: {disease}")
    
    await state.clear()
    await state.set_state(ActionStates.waiting_for_action)

# Просмотр своей информации
@dp.message(ActionStates.waiting_for_action, F.text == "👤 Моя информация")
async def cmd_my_info(message: types.Message):
    # Получаем информацию о пользователе через API
    user_info = await api_client.get_user(message.from_user.id)
    
    if "error" in user_info:
        await message.answer(
            "❌ **Не удалось получить информацию**\n\n"
            "Возможные причины:\n"
            "1. Вы не зарегистрированы в системе\n"
            "2. Проблемы с подключением к серверу\n\n"
            "Попробуйте зарегистрироваться или обратитесь к администратору.",
            parse_mode="Markdown"
        )
    else:
        formatted_info = format_user_info(user_info)
        await message.answer(formatted_info, parse_mode="Markdown")

# АДМИН ПАНЕЛЬ
@dp.message(ActionStates.waiting_for_action, F.text == "👑 Админ панель")
@admin_only
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Отчет по сектору"), types.KeyboardButton(text="📈 Отчет по всем")],
            [types.KeyboardButton(text="👤 Инфо о пользователе")],
            [types.KeyboardButton(text="✅ Вкл/выкл отчеты"), types.KeyboardButton(text="👑 Дать/забрать админа")],
            [types.KeyboardButton(text="📋 Статистика")],
            [types.KeyboardButton(text="⬅️ Назад в меню")]
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

# Отчет по конкретному сектору
@dp.message(AdminStates.waiting_admin_command, F.text == "📊 Отчет по сектору")
async def admin_report_by_sector(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите **ID сектора** для отчета:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AdminStates.waiting_sector_id)

@dp.message(AdminStates.waiting_sector_id)
async def process_admin_sector_id(message: types.Message, state: FSMContext):
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

# Поиск пользователя по ID
@dp.message(AdminStates.waiting_admin_command, F.text == "👤 Инфо о пользователе")
async def admin_user_info(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите **ID пользователя** для просмотра информации:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AdminStates.waiting_user_id)

@dp.message(AdminStates.waiting_user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
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
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Вкл/Выкл отчеты", 
                            callback_data=f"toggle_report:{user_id}"
                        ),
                        InlineKeyboardButton(
                            text="👑 Дать/забрать админа", 
                            callback_data=f"toggle_admin:{user_id}"
                        )
                    ]
                ]
            )
            
            await message.answer(
                "**Быстрые действия:**",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")
    
    # Возвращаем в админ панель
    await cmd_admin_panel(message, state)

# Включить/выключить отчеты для пользователя
@dp.message(AdminStates.waiting_admin_command, F.text == "✅ Вкл/выкл отчеты")
async def admin_toggle_reports(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите **ID пользователя** для изменения настроек отчетов:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(action="toggle_report")
    await state.set_state(AdminStates.waiting_user_id)

# Дать/забрать админ права
@dp.message(AdminStates.waiting_admin_command, F.text == "👑 Дать/забрать админа")
async def admin_toggle_admin(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите **ID пользователя** для изменения админ прав:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(action="toggle_admin")
    await state.set_state(AdminStates.waiting_user_id)

# Обработка действий с пользователем (callback)
@dp.callback_query(F.data.startswith("toggle_"))
async def process_toggle_action(callback: types.CallbackQuery):
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
                        
                        # Обновляем сообщение
                        updated_info = await api_client.get_user(user_id)
                        formatted_info = format_user_info(updated_info)
                        
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="✅ Вкл/Выкл отчеты", 
                                        callback_data=f"toggle_report:{user_id}"
                                    ),
                                    InlineKeyboardButton(
                                        text="👑 Дать/забрать админа", 
                                        callback_data=f"toggle_admin:{user_id}"
                                    )
                                ]
                            ]
                        )
                        
                        await callback.message.edit_text(
                            formatted_info,
                            parse_mode="Markdown"
                        )
                        await callback.message.edit_reply_markup(
                            reply_markup=keyboard
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
                        
                        # Обновляем сообщение
                        updated_info = await api_client.get_user(user_id)
                        formatted_info = format_user_info(updated_info)
                        
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="✅ Вкл/Выкл отчеты", 
                                        callback_data=f"toggle_report:{user_id}"
                                    ),
                                    InlineKeyboardButton(
                                        text="👑 Дать/забрать админа", 
                                        callback_data=f"toggle_admin:{user_id}"
                                    )
                                ]
                            ]
                        )
                        
                        await callback.message.edit_text(
                            formatted_info,
                            parse_mode="Markdown"
                        )
                        await callback.message.edit_reply_markup(
                            reply_markup=keyboard
                        )
                    else:
                        await callback.answer("❌ Ошибка при изменении прав")
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}")

# Статистика
@dp.message(AdminStates.waiting_admin_command, F.text == "📋 Статистика")
async def admin_statistics(message: types.Message):
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

# Возврат в главное меню
@dp.message(F.text == "⬅️ Назад в меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Проверяем права пользователя
    is_admin = await check_admin(message.from_user.id)
    
    # Основная клавиатура
    keyboard_buttons = [
        [types.KeyboardButton(text="📊 Отчет по моему сектору")],
        [types.KeyboardButton(text="📈 Отчет по всем секторам")],
        [types.KeyboardButton(text="🏢 Список секторов")],
        [types.KeyboardButton(text="💊 Отметить статус здоровья")],
        [types.KeyboardButton(text="👤 Моя информация")]
    ]
    
    # Добавляем админ-панель если пользователь админ
    if is_admin:
        keyboard_buttons.append([types.KeyboardButton(text="👑 Админ панель")])
    
    keyboard_buttons.append([types.KeyboardButton(text="❌ Отменить действие")])
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )
    
    await message.answer(
        "🏠 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ActionStates.waiting_for_action)

# Возврат в админ панель (для обработки при возврате из подсостояний)
@dp.message(AdminStates.waiting_admin_command, F.text == "⬅️ Назад в меню")
async def back_to_admin_menu(message: types.Message, state: FSMContext):
    await cmd_admin_panel(message, state)

# Команда отмены
@dp.message(F.text == "❌ Отменить действие")
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Проверяем права пользователя
    is_admin = await check_admin(message.from_user.id)
    
    # Основная клавиатура
    keyboard_buttons = [
        [types.KeyboardButton(text="📊 Отчет по моему сектору")],
        [types.KeyboardButton(text="📈 Отчет по всем секторам")],
        [types.KeyboardButton(text="🏢 Список секторов")],
        [types.KeyboardButton(text="💊 Отметить статус здоровья")],
        [types.KeyboardButton(text="👤 Моя информация")]
    ]
    
    # Добавляем админ-панель если пользователь админ
    if is_admin:
        keyboard_buttons.append([types.KeyboardButton(text="👑 Админ панель")])
    
    keyboard_buttons.append([types.KeyboardButton(text="❌ Отменить действие")])
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )
    
    await message.answer(
        "❌ **Действие отменено**\n\n"
        "Вы вернулись в главное меню.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(ActionStates.waiting_for_action)

# Обработка команды /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
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

@dp.message(ActionStates.waiting_for_action, F.text == "🏢 Список секторов")
async def cmd_list_sectors(message: types.Message):
    await message.answer("⏳ Загружаю список секторов...")
    
    sectors_data = await api_client.get_sectors()
    
    if "error" in sectors_data:
        await message.answer(f"❌ Ошибка: {sectors_data['error']}")
        return
    
    sectors = sectors_data.get("sectors", [])
    
    if not sectors:
        await message.answer("📭 Секторы не найдены")
        return
    
    message_text = "🏢 **СПИСОК СЕКТОРОВ**\n\n"
    
    for sector in sectors:
        sector_id = sector.get("sector_id")
        name = sector.get("name", f"Сектор {sector_id}")
        
        message_text += f"**{sector_id}. {name}**\n\n"
    
    await message.answer(message_text, parse_mode="Markdown")

# Главная функция
async def main():
    print("🤖 Запуск Telegram бота с API...")
    print(f"🌐 API сервер: {api_client.base_url}")
    
    # Проверяем доступность API
    if await api_client.check_health():
        print("✅ API сервер доступен")
    else:
        print("⚠️  API сервер недоступен. Проверьте запущен ли FastAPI сервер.")
    
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