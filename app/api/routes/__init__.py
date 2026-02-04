# app/api/routes/__init__.py
# Этот файл должен экспортировать router из каждого модуля

# Импортируем router из каждого файла
from .health import router as health_router
from .users import router as users_router
from .admin import router as admin_router

# Экспортируем их
__all__ = ["health_router", "users_router", "admin_router"]