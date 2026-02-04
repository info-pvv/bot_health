# bot_v3.py - обновленная версия для работы с вашим API
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.api_client import api_client
from config import TOKEN

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

# Функция для форматирования отчета
def format_report(report_data: dict) -> str:
    """Форматировать данные отчета в читаемый вид"""
    if "error" in report_data:
        return f"❌ Ошибка при получении отчета:\n{report_data['error']}"
    
    summary = report_data.get("status_summary", {})
    users = report_data.get("users", [])
    total = report_data.get("total", 0)
    
    # Формируем сообщение
    message = "📊 **ОТЧЕТ ПО СОТРУДНИКАМ**\n\n"
    
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
    
    message += f"\n**Всего сотрудников в отчете:** {total}\n"
    
    # Список сотрудников (первые 20 чтобы не перегружать)
    if users:
        message += "\n**Сотрудники:**\n"
        for i, user in enumerate(users[:20], 1):
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
        
        if len(users) > 20:
            message += f"\n... и еще {len(users) - 20} сотрудников"
    
    return message

# Функция для форматирования информации о пользователе
def format_user_info(user_data: dict) -> str:
    """Форматировать информацию о пользователе"""
    if "error" in user_data:
        return f"❌ Ошибка: {user_data['error']}"
    
    message = "👤 **ВАША ИНФОРМАЦИЯ**\n\n"
    
    # Основная информация
    first_name = user_data.get("first_name", "Не указано")
    last_name = user_data.get("last_name", "Не указано")
    username = user_data.get("username", "Не указано")
    
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
        
        message += f"\n**Права:**\n"
        message += f"📊 Отчеты: {'✅ Включены' if enable_report else '❌ Выключены'}\n"
        message += f"👑 Админ: {'✅ Да' if enable_admin else '❌ Нет'}\n"
    
    # Даты
    created_at = user_data.get("created_at", "")
    updated_at = user_data.get("updated_at", "")
    
    if created_at:
        message += f"\n📅 Зарегистрирован: {created_at[:10]}"
    
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
        # Пользователь уже в системе
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📊 Получить отчет")],
                [types.KeyboardButton(text="💊 Отметить статус здоровья")],
                [types.KeyboardButton(text="👤 Моя информация")],
                [types.KeyboardButton(text="❌ Отменить действие")]
            ],
            resize_keyboard=True
        )
        
        first_name = user_info.get("first_name", "Сотрудник")
        await message.answer(
            f"👋 **С возвращением, {first_name}!**\n\n"
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
    
    # Создаем пользователя через API
    user_info = {
        "user_id": message.from_user.id,
        "first_name": first_name,
        "last_name": last_name,
        "username": message.from_user.username or ""
    }
    
    await message.answer("⏳ Регистрирую в системе...")
    
    result = await api_client.create_user(user_info, chat_id=message.chat.id)
    
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
                [types.KeyboardButton(text="📊 Получить отчет")],
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
@dp.message(ActionStates.waiting_for_action, F.text == "📊 Получить отчет")
async def cmd_report_api(message: types.Message):
    await message.answer("⏳ Загружаю отчет...")
    
    # Получаем отчет через API
    report_data = await api_client.get_report()
    
    # Форматируем и отправляем отчет
    formatted_report = format_report(report_data)
    
    # Разбиваем длинные сообщения (Telegram имеет лимит 4096 символов)
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
        status=status
    )
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Получить отчет")],
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
            [types.KeyboardButton(text="📊 Получить отчет")],
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

# Команда отмены
@dp.message(F.text == "❌ Отменить действие")
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Получить отчет")],
            [types.KeyboardButton(text="💊 Отметить статус здоровья")],
            [types.KeyboardButton(text="👤 Моя информация")],
            [types.KeyboardButton(text="❌ Отменить действие")]
        ],
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
        "🤖 **Помощь по использованию бота**\n\n"
        "**Основные команды:**\n"
        "• /start - Начать работу с ботом\n"
        "• /help - Показать эту справку\n\n"
        "**Основные функции:**\n"
        "• 📊 Получить отчет - Просмотр отчета по сотрудникам\n"
        "• 💊 Отметить статус здоровья - Указать свой текущий статус\n"
        "• 👤 Моя информация - Просмотр вашей информации\n"
        "• ❌ Отменить действие - Отменить текущую операцию\n\n"
        "**Статусы здоровья:**\n"
        "• ✅ здоров - Вы здоровы и на работе\n"
        "• 🤒 болен - Вы заболели (требуется указать заболевание)\n"
        "• 🏖 отпуск - Вы в отпуске\n"
        "• 🏠 удаленка - Работаете удаленно\n"
        "• 📋 отгул - Взяли отгул\n"
        "• 📚 учеба - На учебе\n\n"
        "**Проблемы?**\n"
        "Если бот не работает, проверьте:\n"
        "1. Интернет-соединение\n"
        "2. Доступность API сервера\n"
        "3. Сообщите администратору об ошибке"
    )
    
    await message.answer(help_text, parse_mode="Markdown")

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