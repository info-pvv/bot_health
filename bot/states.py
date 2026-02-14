"""
Состояния FSM для бота
"""

from aiogram.fsm.state import State, StatesGroup


class HealthStates(StatesGroup):
    waiting_for_status = State()
    waiting_for_disease = State()


class ActionStates(StatesGroup):
    waiting_for_action = State()


class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()


class AdminStates(StatesGroup):
    waiting_admin_command = State()
    waiting_user_id = State()
    waiting_sector_id = State()
    waiting_user_query = State()
    waiting_user_selection = State()
    waiting_sector_selection = State()


class ScheduleStates(StatesGroup):
    waiting_schedule_time = State()
    waiting_schedule_days = State()


class DutyStates(StatesGroup):
    """Состояния для управления дежурствами"""

    waiting_for_action = State()  # Ожидание действия в меню дежурств
    waiting_for_sector_selection = State()  # Ожидание выбора сектора
    waiting_for_user_selection = State()  # Ожидание выбора пользователя для добавления
    waiting_for_user_removal = State()  # Ожидание выбора пользователя для удаления
    waiting_for_week_selection = State()  # Ожидание подтверждения недели для назначения
