# bot/keyboards/duty.py
"""
Клавиатуры для системы дежурств
"""
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder  # ← ВАЖНО: правильный импорт
from typing import List, Dict, Optional


def get_duty_main_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню управления дежурствами"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Пул дежурных", callback_data="duty_view_pool"
        ),
        types.InlineKeyboardButton(
            text="➕ Добавить в пул", callback_data="duty_add_to_pool"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="➖ Удалить из пула", callback_data="duty_remove_from_pool"
        ),
        types.InlineKeyboardButton(
            text="📅 Назначить на неделю", callback_data="duty_assign_week"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="👤 Дежурный сегодня", callback_data="duty_today"
        ),
        types.InlineKeyboardButton(
            text="📊 Статистика сектора", callback_data="duty_stats"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад в админку", callback_data="duty_back_to_admin"
        )
    )
    return builder.as_markup()


def get_sector_selection_keyboard(
    sectors: List[Dict], action_prefix: str = "duty_select_sector"
) -> types.InlineKeyboardMarkup:
    """
    Клавиатура для выбора сектора.

    Args:
        sectors: Список секторов [{'sector_id': 1, 'name': 'Название'}, ...]
        action_prefix: Префикс для callback_data (например, "duty_select_sector_add")
    """
    builder = InlineKeyboardBuilder()
    for sector in sectors:
        sector_id = sector.get("sector_id")
        name = sector.get("name", f"Сектор {sector_id}")
        builder.row(
            types.InlineKeyboardButton(
                text=f"{sector_id}. {name}",
                callback_data=f"{action_prefix}:{sector_id}",
            )
        )
    builder.row(
        types.InlineKeyboardButton(text="🔙 Отмена", callback_data="duty_cancel")
    )
    return builder.as_markup()


def get_user_selection_keyboard_duty(
    users: List[Dict], sector_id: int, action_prefix: str = "duty_select_user"
) -> types.InlineKeyboardMarkup:
    """
    Клавиатура для выбора пользователя из списка (для дежурств).

    Args:
        users: Список пользователей с полями user_id, first_name, last_name
        sector_id: ID сектора, для которого выбирается пользователь
        action_prefix: Префикс для callback_data
    """
    builder = InlineKeyboardBuilder()
    for user in users:
        user_id = user.get("user_id")
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        name = f"{first_name} {last_name}".strip()
        if not name:
            name = f"ID {user_id}"

        builder.row(
            types.InlineKeyboardButton(
                text=f"{name[:30]}",
                callback_data=f"{action_prefix}:{sector_id}:{user_id}",
            )
        )
    builder.row(
        types.InlineKeyboardButton(text="🔙 Отмена", callback_data="duty_cancel")
    )
    return builder.as_markup()


def get_week_confirmation_keyboard(
    sector_id: int, week_start: str
) -> types.InlineKeyboardMarkup:
    """Клавиатура для подтверждения назначения на неделю"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"duty_confirm_week:{sector_id}:{week_start}",
        ),
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="duty_cancel"),
    )
    return builder.as_markup()


def get_duty_pool_actions_keyboard(
    sector_id: int, user_id: int
) -> types.InlineKeyboardMarkup:
    """Кнопки действий для конкретной записи в пуле"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Удалить из пула",
            callback_data=f"duty_remove_confirm:{sector_id}:{user_id}",
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад к пулу", callback_data=f"duty_view_pool:{sector_id}"
        )
    )
    return builder.as_markup()


def get_duty_back_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопка возврата в меню дежурств"""
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="duty_menu"))
    return builder.as_markup()
