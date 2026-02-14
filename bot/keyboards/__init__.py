# bot/keyboards/__init__.py
"""
Клавиатуры для бота
"""
from .main import get_main_keyboard, get_health_keyboard, get_disease_keyboard
from .admin import get_admin_keyboard, get_user_actions_keyboard

# +++ ИМПОРТ НОВЫХ КЛАВИАТУР +++
from .duty import (
    get_duty_main_keyboard,
    get_sector_selection_keyboard,
    get_user_selection_keyboard_duty,
    get_week_confirmation_keyboard,
    get_duty_pool_actions_keyboard,
    get_duty_back_keyboard,
)

__all__ = [
    "get_main_keyboard",
    "get_health_keyboard",
    "get_disease_keyboard",
    "get_admin_keyboard",
    "get_user_actions_keyboard",
    # +++ НОВЫЕ КЛАВИАТУРЫ +++
    "get_duty_main_keyboard",
    "get_sector_selection_keyboard",
    "get_user_selection_keyboard_duty",
    "get_week_confirmation_keyboard",
    "get_duty_pool_actions_keyboard",
    "get_duty_back_keyboard",
]
