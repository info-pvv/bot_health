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