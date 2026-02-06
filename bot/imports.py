# bot/imports.py
"""
Централизованные импорты для бота
"""

# Services
from bot.services.admin_check import is_user_admin

# Utils
from bot.utils.formatters import format_report, format_user_info
from bot.utils.decorators import admin_only

# Keyboards
from bot.keyboards.main import get_main_keyboard, get_health_keyboard, get_disease_keyboard
from bot.keyboards.admin import get_admin_keyboard, get_user_actions_keyboard,get_user_selection_keyboard,get_pagination_keyboard

# States
from bot.states import ActionStates, HealthStates, AdminStates, RegistrationStates, ScheduleStates

# API
from app.api_client import api_client

__all__ = [
    'is_user_admin',
    'format_report', 'format_user_info', 'admin_only',
    'get_main_keyboard', 'get_health_keyboard', 'get_disease_keyboard',
    'get_admin_keyboard', 'get_user_actions_keyboard','get_user_selection_keyboard',
    'ActionStates', 'HealthStates', 'AdminStates', 'RegistrationStates','ScheduleStates',
    'api_client','get_pagination_keyboard'
]