# app/schemas/health.py
from pydantic import BaseModel
from typing import Optional, Dict, List  # Добавьте все необходимые импорты

class HealthBase(BaseModel):
    user_id: int
    status: str

class HealthCreate(HealthBase):
    pass

class HealthUpdate(BaseModel):
    status: Optional[str] = None

class DiseaseBase(BaseModel):
    user_id: int
    disease: Optional[str] = None

class DiseaseUpdate(BaseModel):
    disease: Optional[str] = None

class HealthResponse(HealthBase):
    id: int
    disease: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReportRequest(BaseModel):
    sector_id: Optional[int] = None

class SectorInfo(BaseModel):
    sector_id: Optional[int] = None
    name: Optional[str] = None
    is_user_sector: Optional[bool] = None
class ReportResponse(BaseModel):
    status_summary: Dict[str, int]
    users: List[dict]
    total: int
    sector_info: Optional[SectorInfo] = None
    
class HealthUpdateRequest(BaseModel):
    status: str
    disease: Optional[str] = None
    reset_disease: bool = False  # Новый флаг
