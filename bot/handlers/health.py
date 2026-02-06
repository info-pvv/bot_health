# bot/handlers/health.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext
import logging

# Импорты из центрального файла
from bot.imports import (
    api_client, get_main_keyboard, 
    get_health_keyboard, get_disease_keyboard,
    ActionStates, HealthStates
)

logger = logging.getLogger(__name__)

async def cmd_health(message: types.Message, state: FSMContext):
    """Начать процесс отметки статуса здоровья"""
    keyboard = get_health_keyboard()
    
    await message.answer(
        f"👤 **{message.from_user.first_name}, выберите ваш статус:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(HealthStates.waiting_for_status)

async def process_healthy_status(message: types.Message, state: FSMContext):
    """Обработка здорового статуса"""
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
    
    keyboard = await get_main_keyboard(message.from_user.id)
    
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

async def process_sick_status(message: types.Message, state: FSMContext):
    """Обработка статуса 'болен'"""
    await state.update_data(status="болен")
    
    keyboard = get_disease_keyboard()
    
    await message.answer(
        "🤒 **Укажите заболевание:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(HealthStates.waiting_for_disease)

async def process_disease(message: types.Message, state: FSMContext):
    """Обработка заболевания"""
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
    
    keyboard = await get_main_keyboard(message.from_user.id)
    
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