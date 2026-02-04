# bot_v3.py - для aiogram 3.x
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
    

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message,state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Отметить статус здоровья")],
            [types.KeyboardButton(text="Получить отчет")],
            [types.KeyboardButton(text="Отменить текущее действие")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👋 Привет! Я бот для отслеживания здоровья сотрудников.\n\n",
        reply_markup=keyboard
    )
    await state.set_state(ActionStates.waiting_for_action)


# Команда /health
@dp.message(ActionStates.waiting_for_action, F.text == "Отметить статус здоровья")
async def cmd_health(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="здоров")],
            [types.KeyboardButton(text="болен")],
            [types.KeyboardButton(text="отпуск")],
            [types.KeyboardButton(text="удаленка")],
            [types.KeyboardButton(text="отгул")],
            [types.KeyboardButton(text="учеба")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👤 {message.from_user.first_name}, выберите ваш статус:",
        reply_markup=keyboard
    )
    await state.set_state(HealthStates.waiting_for_status)

# Обработка статуса
@dp.message(HealthStates.waiting_for_status, F.text.in_(["здоров", "отпуск", "удаленка", "отгул", "учеба"]))
async def process_healthy_status(message: types.Message, state: FSMContext):
    status = message.text
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    await message.answer(
        f"✅ {username}, ваш статус: {status}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()
    
    logger.info(f"User {message.from_user.id} set status: {status}")

# Обработка "болен"
@dp.message(HealthStates.waiting_for_status, F.text == "болен")
async def process_sick_status(message: types.Message, state: FSMContext):
    await state.update_data(status="болен")
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="орви")],
            [types.KeyboardButton(text="ковид")],
            [types.KeyboardButton(text="давление")],
            [types.KeyboardButton(text="понос")],
            [types.KeyboardButton(text="прочее")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("🤒 Укажите заболевание:", reply_markup=keyboard)
    await state.set_state(HealthStates.waiting_for_disease)

# Обработка заболевания
@dp.message(HealthStates.waiting_for_disease, F.text.in_(["орви", "ковид", "давление", "понос", "прочее"]))
async def process_disease(message: types.Message, state: FSMContext):
    disease = message.text
    data = await state.get_data()
    status = data.get("status", "болен")
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    await message.answer(
        f"🤒 {username}, статус: {status}, заболевание: {disease}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()
    
    logger.info(f"User {message.from_user.id} has disease: {disease}")

# Команда /report
@dp.message(ActionStates.waiting_for_action, F.text == "Получить отчет")
#@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    await message.answer(
        "📊 Отчет по сотрудникам:\n"
        "Здоровых: 10\n"
        "Больных: 2\n"
        "В отпуске: 3\n"
        "Всего: 15",
        reply_markup=types.ReplyKeyboardRemove()
    )
async def report_health(dp:Dispatcher):
    id_sectors=get_id_sectors()
    for tuple in id_sectors:
        get_list_all=get_list_chat_id(tuple[0])
        string_status = ''
        string_to_send = ''
        hop_count = 0
        ill_healt = 0
        st_healt={}
        for str_to_append in get_list_all:
            for string_to_append in str_to_append:
                string_to_send += str(string_to_append)+' '
            string_to_send += '\n'
            ill_healt=st_healt.setdefault(str_to_append[2],0)+1
            st_healt[str_to_append[2]]=ill_healt
        for key in st_healt.keys():
            hop_count+=st_healt[key]
            string_status+=f'{key} - {st_healt[key]}\n'
        string_status+=f'Всего: {hop_count}\n'    
        print(tuple[0])
        print(string_status)
        print(string_to_send)
        await dp.bot.send_message(tuple[0],text=string_status)
        await dp.bot.send_message(tuple[0],text=string_to_send)

# Команда /cancel
@dp.message(ActionStates.waiting_for_action, F.text == "Отменить текущее действие")
#@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Действие отменено",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Главная функция
async def main():
    print("🤖 Запуск Telegram бота...")
    bot_info = await bot.get_me()
    print(f"👤 Бот: @{bot_info.username}")
    print("🔄 Для остановки нажмите Ctrl+C")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())