# bot/states.py
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

    # Основные состояния
    waiting_for_action = State()  # Ожидание действия в меню дежурств
    waiting_for_sector_selection = State()  # Ожидание выбора сектора
    waiting_for_user_selection = State()  # Ожидание выбора пользователя для добавления
    waiting_for_user_removal = State()  # Ожидание выбора пользователя для удаления

    # Состояния для назначения на период
    waiting_for_week_selection = State()  # Ожидание подтверждения недели (старый метод)
    waiting_for_period_selection = (
        State()
    )  # Ожидание выбора периода (день/неделя/месяц/год)
    waiting_for_period_confirmation = State()  # Ожидание подтверждения периода

    # Состояния для планирования
    waiting_for_plan_year = State()  # Ожидание ввода года
    waiting_for_plan_confirmation = (
        State()
    )  # Ожидание подтверждения планирования на год
    waiting_for_plan_execution = State()  # Выполнение планирования

    # Состояния для проверки доступности
    waiting_for_check_start = State()  # Ожидание начала периода проверки
    waiting_for_check_end = State()  # Ожидание конца периода проверки
    waiting_for_check_results = State()  # Просмотр результатов проверки

    # Состояния для статистики
    waiting_for_stats_sector = State()  # Ожидание выбора сектора для статистики
    waiting_for_stats_year = State()  # Ожидание выбора года для статистики
    waiting_for_stats_view = State()  # Просмотр статистики

    waiting_for_custom_date = State()  # Ожидание ввода произвольной даты
    waiting_for_custom_week = State()  # Ожидание ввода произвольной недели
    waiting_for_date_confirmation = State()

    waiting_for_date_input = State()  # Ожидание ввода даты вручную
