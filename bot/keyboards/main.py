"""
Основные клавиатуры
"""

from aiogram import types
from bot.services.admin_check import is_user_admin


async def get_main_keyboard(user_id: int = None) -> types.ReplyKeyboardMarkup:
    """Получить основную клавиатуру с проверкой прав админа"""
    keyboard_buttons = [
        [types.KeyboardButton(text="💊 Отметить статус здоровья")],
        [types.KeyboardButton(text="👤 Моя информация")],
    ]

    # Добавляем админ-панель если пользователь админ
    if user_id and await is_user_admin(user_id):
        keyboard_buttons.append([types.KeyboardButton(text="👑 Админ панель")])
        keyboard_buttons.append(
            [types.KeyboardButton(text="📊 Отчет по моему сектору")]
        )
        keyboard_buttons.append(
            [types.KeyboardButton(text="📈 Отчет по всем секторам")]
        )
        keyboard_buttons.append([types.KeyboardButton(text="🏢 Список секторов")])

    keyboard_buttons.append([types.KeyboardButton(text="❌ Отменить действие")])

    return types.ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)


def get_health_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для выбора статуса здоровья"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="✅ здоров"),
                types.KeyboardButton(text="🤒 болен"),
            ],
            [
                types.KeyboardButton(text="🏖 отпуск"),
                types.KeyboardButton(text="🏠 удаленка"),
            ],
            [
                types.KeyboardButton(text="📋 отгул"),
                types.KeyboardButton(text="📚 учеба"),
            ],
            [types.KeyboardButton(text="⬅️ Назад в меню")],
        ],
        resize_keyboard=True,
    )


def get_disease_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для выбора заболевания"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="🤧 орви"),
                types.KeyboardButton(text="🦠 ковид"),
            ],
            [
                types.KeyboardButton(text="💊 давление"),
                types.KeyboardButton(text="🤢 понос"),
            ],
            [
                types.KeyboardButton(text="📝 прочее"),
                types.KeyboardButton(text="⬅️ Назад в меню"),
            ],
        ],
        resize_keyboard=True,
    )
