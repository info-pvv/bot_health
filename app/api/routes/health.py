# app/api/routes/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional  # Добавьте импорт
from app.models.database import get_db
from app.services.health_service import HealthService
from app.services.user_service import UserService
from app.schemas.health import ReportResponse, ReportRequest

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/report", response_model=ReportResponse)
async def get_health_report(
    user_id: Optional[int] = None,
    sector_id: Optional[int] = None,
    include_sector_name: bool = False,  # Новый параметр
    db: AsyncSession = Depends(get_db)
):
    # Определяем sector_id
    final_sector_id = sector_id
    sector_name = None
    
    if user_id is not None:
        user_sector = await UserService.get_user_sector_id(db, user_id)
        if user_sector:
            final_sector_id = user_sector
    
    # Получаем отчет
    status_stats, users_data = await HealthService.get_report(db, final_sector_id)
    
    # Получаем название сектора если нужно
    if include_sector_name and final_sector_id:
        sector_name = await HealthService.get_sector_name(db, final_sector_id)
    
    users_list = []
    for user in users_data:
        users_list.append({
            "first_name": user[0],
            "last_name": user[1],
            "status": user[2],
            "disease": user[3] if user[3] else ""
        })
    
    # Создаем ответ
    response = ReportResponse(
        status_summary=status_stats,
        users=users_list,
        total=len(users_list)
    )
    
    # Добавляем информацию о секторе в ответ
    if include_sector_name:
        response_dict = response.dict()
        response_dict["sector_info"] = {
            "sector_id": final_sector_id,
            "name": sector_name or f"Сектор {final_sector_id}",
            "is_user_sector": user_id is not None and final_sector_id == user_sector
        }
        return response_dict
    
    return response


@router.get("/sectors")
async def get_sectors(db: AsyncSession = Depends(get_db)):
    # Используем метод, который получает данные из таблицы sectors
    sectors = await HealthService.get_all_sectors_with_names(db)
    return {"sectors": sectors}