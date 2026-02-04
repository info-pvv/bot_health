# app/schemas/user.py - обновленная версия
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserStatusBase(BaseModel):
    enable_report: bool = True
    enable_admin: bool = False
    sector: Optional[int] = None

class HealthBase(BaseModel):
    status: Optional[str] = None

class DiseaseBase(BaseModel):
    disease: Optional[str] = None

class FIOBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic_name: Optional[str] = None

class UserBase(BaseModel):
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class UserStatusUpdate(BaseModel):
    enable_report: Optional[bool] = None
    enable_admin: Optional[bool] = None
    sector: Optional[int] = None

class UserResponse(UserBase):
    id: int
    status_info: Optional[UserStatusBase] = None
    fio_info: Optional[FIOBase] = None
    health_info: Optional[HealthBase] = None
    disease_info: Optional[DiseaseBase] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True