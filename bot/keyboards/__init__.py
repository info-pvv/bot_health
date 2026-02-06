"""
Клавиатуры для бота
"""
from .main import get_main_keyboard, get_health_keyboard, get_disease_keyboard
from .admin import get_admin_keyboard, get_user_actions_keyboard

__all__ = [
    'get_main_keyboard', 'get_health_keyboard', 'get_disease_keyboard',
    'get_admin_keyboard', 'get_user_actions_keyboard'
]