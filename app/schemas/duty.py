# app/schemas/duty.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


class DutyAdminPoolBase(BaseModel):
    user_id: int
    sector_id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class DutyAdminPoolCreate(BaseModel):
    user_id: int
    sector_id: int
    added_by: Optional[int] = None


class DutyAdminPoolUpdate(BaseModel):
    is_active: Optional[bool] = None


class DutyAdminPoolResponse(DutyAdminPoolBase):
    pool_id: int
    added_at: datetime
    added_by: Optional[int] = None
    user_name: Optional[str] = None  # Добавляем поле для имени
    sector_name: Optional[str] = None  # Добавляем поле для названия сектора

    model_config = ConfigDict(from_attributes=True)


class DutyScheduleBase(BaseModel):
    user_id: int
    sector_id: int
    duty_date: date
    week_start: date

    model_config = ConfigDict(from_attributes=True)


class DutyScheduleCreate(BaseModel):
    user_id: int
    sector_id: int
    duty_date: date
    week_start: date
    created_by: Optional[int] = None


class DutyScheduleResponse(DutyScheduleBase):
    duty_id: int
    created_at: datetime
    created_by: Optional[int] = None
    user_name: Optional[str] = None
    sector_name: Optional[str] = None
    day_of_week: Optional[str] = None


class DutyStatisticsBase(BaseModel):
    user_id: int
    sector_id: int
    year: int
    total_duties: int = 0
    last_duty_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class DutyStatisticsResponse(DutyStatisticsBase):
    stat_id: int
    updated_at: datetime
    user_name: Optional[str] = None
    sector_name: Optional[str] = None


class DutyStatisticsSummary(BaseModel):
    user_id: int
    user_name: str
    total_duties: int
    last_duty_date: Optional[date] = None
    in_pool: bool


class WeeklyDutyAssignment(BaseModel):
    sector_id: int
    week_start: date
    assigned_user_id: Optional[int] = None
    assigned_user_name: Optional[str] = None
    week_dates: List[date]
    message: str


class DutyScheduleMonthRequest(BaseModel):
    sector_id: int
    year: int
    month: int


class DutyAdminPoolListResponse(BaseModel):
    items: List[DutyAdminPoolResponse]
    total: int
    skip: int
    limit: int


class DutyScheduleListResponse(BaseModel):
    items: List[DutyScheduleResponse]
    total: int
    skip: int
    limit: int


class DutyStatisticsListResponse(BaseModel):
    items: List[DutyStatisticsResponse]
    total: int
    skip: int
    limit: int
