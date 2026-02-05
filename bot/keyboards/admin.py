"""
Админские клавиатуры
"""
from aiogram import types

def get_admin_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура админ-панели"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📊 Отчет по сектору"), types.KeyboardButton(text="📈 Отчет по всем")],
            [types.KeyboardButton(text="👤 Инфо о пользователе")],
            [types.KeyboardButton(text="✅ Вкл/выкл отчеты"), types.KeyboardButton(text="👑 Дать/забрать админа")],
            [types.KeyboardButton(text="📋 Статистика")],
            [types.KeyboardButton(text="⬅️ Назад в меню")]
        ],
        resize_keyboard=True
    )

def get_user_actions_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Inline клавиатура для быстрых действий с пользователем"""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Вкл/Выкл отчеты", 
                    callback_data=f"toggle_report:{user_id}"
                ),
                types.InlineKeyboardButton(
                    text="👑 Дать/забрать админа", 
                    callback_data=f"toggle_admin:{user_id}"
                )
            ]
        ]
    )