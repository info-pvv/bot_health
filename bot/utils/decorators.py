"""
Декораторы для бота
"""
from functools import wraps
from typing import Callable
from aiogram import types
from aiogram.fsm.context import FSMContext

from bot.services.admin_check import is_user_admin

def admin_only(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(message: types.Message, state: FSMContext, *args, **kwargs):
        if not await is_user_admin(message.from_user.id):
            await message.answer(
                "⛔ **Доступ запрещен!**\n\n"
                "У вас нет прав администратора.\n"
                "Для получения доступа обратитесь к администратору системы.",
                parse_mode="Markdown"
            )
            return
        return await func(message, state, *args, **kwargs)
    return wrapper