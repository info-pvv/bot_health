"""
Админские клавиатуры
"""

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_admin_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура админ-панели"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🔍 Найти сотрудника")],
            [types.KeyboardButton(text="👥 Список сотрудников")],
            [types.KeyboardButton(text="📋 Статистика")],
            [types.KeyboardButton(text="⬅️ Главное меню")],
        ],
        resize_keyboard=True,
    )


def get_user_actions_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Inline клавиатура для действий с пользователем"""
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="✅ Вкл/Выкл отчеты", callback_data=f"toggle_report:{user_id}"
        ),
        types.InlineKeyboardButton(
            text="👑 Дать/забрать админа", callback_data=f"toggle_admin:{user_id}"
        ),
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_selection"),
    )

    return builder.as_markup()


def get_user_selection_keyboard(
    users: list, page: int = 0, page_size: int = 10
) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора пользователя из списка"""
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для пользователей на текущей странице
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(users))

    for i in range(start_idx, end_idx):
        user = users[i]
        first_name = user.get("first_name", "")[:15]
        last_name = user.get("last_name", "")[:15]
        user_id = user.get("user_id", user.get("id"))

        text = f"{i+1}. {first_name} {last_name}"[:30]

        builder.row(
            types.InlineKeyboardButton(
                text=text, callback_data=f"select_user:{user_id}"
            )
        )

    # Добавляем кнопки навигации
    nav_buttons = []

    if page > 0:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"user_page:{page-1}"
            )
        )

    if end_idx < len(users):
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="➡️ Вперед", callback_data=f"user_page:{page+1}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка отмены
    builder.row(
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_selection")
    )

    return builder.as_markup()


def get_pagination_keyboard(
    page: int, total_pages: int, prefix: str = "page"
) -> types.InlineKeyboardMarkup:
    """Универсальная клавиатура пагинации"""
    builder = InlineKeyboardBuilder()

    if page > 0:
        builder.add(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"{prefix}:{page-1}"
            )
        )

    builder.add(
        types.InlineKeyboardButton(
            text=f"{page+1}/{total_pages}", callback_data="current"
        )
    )

    if page < total_pages - 1:
        builder.add(
            types.InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"{prefix}:{page+1}"
            )
        )

    return builder.as_markup()
