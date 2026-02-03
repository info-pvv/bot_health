from pydantic import BaseModel
from typing import Optional

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

class ReportResponse(BaseModel):
    status_summary: dict
    users: list
    total: int