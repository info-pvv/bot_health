from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models.database import get_db
from app.services.health_service import HealthService
from app.schemas.health import ReportResponse, ReportRequest

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/report", response_model=ReportResponse)
async def get_health_report(
    sector_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    status_stats, users_data = await HealthService.get_report(db, sector_id)
    
    users_list = []
    for user in users_data:
        users_list.append({
            "first_name": user[0],
            "last_name": user[1],
            "status": user[2],
            "disease": user[3] if user[3] else ""
        })
    
    return ReportResponse(
        status_summary=status_stats,
        users=users_list,
        total=len(users_list)
    )

@router.get("/sectors")
async def get_sectors(db: AsyncSession = Depends(get_db)):
    sectors = await HealthService.get_all_sectors(db)
    return {"sectors": sectors}