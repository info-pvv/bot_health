# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database Configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str
    
    # Telegram Bot Configuration
    TELEGRAM_TOKEN: str
    
    # API Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Optional API settings
    API_BASE_URL: Optional[str] = "http://localhost:8000"
    LOG_LEVEL: Optional[str] = "INFO"
    REPORT_TIME: Optional[str] = "07:30"
    REPORT_TIMEZONE: Optional[str] = "Europe/Moscow"
    
    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """URL для синхронных операций (Alembic)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        # Разрешаем дополнительные поля в .env файле
        extra = "allow"

settings = Settings()