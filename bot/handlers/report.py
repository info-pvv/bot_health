# bot/handlers/report.py
from aiogram import types, F
from aiogram.fsm.context import FSMContext

# Импорты из центрального файла
from bot.imports import (
    api_client, format_report, format_user_info,
    ActionStates
)

async def cmd_report_api(message: types.Message):
    """Получить отчет по своему сектору"""
    await message.answer("⏳ Загружаю отчет для вашего сектора...")
    
    # Получаем отчет через API с названием сектора
    report_data = await api_client.get_report(user_id=message.from_user.id)
    formatted_report = format_report(report_data)
    
    # Разбиваем длинные сообщения
    if len(formatted_report) > 4000:
        parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(formatted_report, parse_mode="Markdown")

async def cmd_report_all_sectors(message: types.Message):
    """Получить отчет по всем секторам"""
    await message.answer("⏳ Загружаю отчет по всем секторам...")
    
    # Получаем отчет без фильтрации по сектору
    report_data = await api_client.get_report()
    formatted_report = format_report(report_data)
    
    if len(formatted_report) > 4000:
        parts = [formatted_report[i:i+4000] for i in range(0, len(formatted_report), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(formatted_report, parse_mode="Markdown")

async def cmd_list_sectors(message: types.Message):
    """Показать список секторов"""
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

async def cmd_my_info(message: types.Message):
    """Показать информацию о себе"""
    # Получаем информацию о пользователе через API
    user_info = await api_client.get_user(message.from_user.id)
    report_data = await api_client.get_report(user_id=message.from_user.id)
    
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
        formatted_info = format_user_info(user_info, report_data)
        await message.answer(formatted_info, parse_mode="Markdown")