"""
Проверка прав администратора
"""
from app.api_client import api_client

async def is_user_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    user_info = await api_client.get_user(user_id)
    
    if "error" in user_info:
        return False
    
    # Проверяем поле enable_admin в status_info
    status_info = user_info.get("status_info", {})
    is_admin = status_info.get("enable_admin", False)
    
    return is_admin