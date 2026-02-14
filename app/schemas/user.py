# app/schemas/user.py - полная обновленная версия
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserStatusBase(BaseModel):
    enable_report: bool = True
    enable_admin: bool = False
    sector_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class HealthBase(BaseModel):
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DiseaseBase(BaseModel):
    disease: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FIOBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_duty_eligible: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class UserStatusUpdate(BaseModel):
    enable_report: Optional[bool] = None
    enable_admin: Optional[bool] = None
    sector_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_duty_eligible: bool = False

    # Опциональные связанные данные (комментируем если вызывают ошибки)
    status_info: Optional[UserStatusBase] = None
    fio_info: Optional[FIOBase] = None
    health_info: Optional[HealthBase] = None
    disease_info: Optional[DiseaseBase] = None

    model_config = ConfigDict(from_attributes=True)
