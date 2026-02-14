# app/api/routes/__init__.py
from .health import router as health_router
from .users import router as users_router
from .admin import router as admin_router
from .duty import router as duty_router  # НОВЫЙ ИМПОРТ

__all__ = ["health_router", "users_router", "admin_router", "duty_router"]
