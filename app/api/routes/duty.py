# app/api/routes/duty.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func  # ← ВАЖНО: добавляем все необходимые импорты
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date, datetime

from app.models.database import get_db
from app.models.user import User, FIO  # Добавляем все нужные модели
from app.models.duty import DutyAdminPool, DutySchedule, DutyStatistics
from app.services.duty_service import DutyService
from app.services.user_service import UserService
from app.services.health_service import HealthService
from app.schemas.duty import (
    DutyAdminPoolCreate,
    DutyAdminPoolResponse,
    DutyAdminPoolUpdate,
    DutyScheduleCreate,
    DutyScheduleResponse,
    DutyStatisticsResponse,
    DutyStatisticsSummary,
    WeeklyDutyAssignment,
    DutyScheduleMonthRequest,
    DutyAdminPoolListResponse,
    DutyScheduleListResponse,
    DutyStatisticsListResponse,
)

router = APIRouter(prefix="/duty", tags=["duty"])

# ========== УПРАВЛЕНИЕ ПУЛОМ ДЕЖУРНЫХ ==========


@router.post("/pool", response_model=DutyAdminPoolResponse)
async def add_to_duty_pool(
    pool_data: DutyAdminPoolCreate, db: AsyncSession = Depends(get_db)
):
    """Добавить пользователя в пул дежурных администраторов"""
    # Проверяем существование пользователя
    user = await UserService.get_user_by_id(db, pool_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем, может ли пользователь быть дежурным
    if not user.is_duty_eligible:
        # Автоматически отмечаем как дежурного
        user.is_duty_eligible = True
        await db.commit()

    result = await DutyService.add_to_pool(db, pool_data)

    # Загружаем дополнительные данные для ответа
    from sqlalchemy.orm import selectinload

    refreshed = await db.execute(
        select(DutyAdminPool)
        .where(DutyAdminPool.pool_id == result.pool_id)
        .options(
            selectinload(DutyAdminPool.user),
            selectinload(DutyAdminPool.sector),
            selectinload(DutyAdminPool.added_by_user),
        )
    )
    result = refreshed.scalar_one()

    return result


@router.delete("/pool/{user_id}/{sector_id}")
async def remove_from_duty_pool(
    user_id: int, sector_id: int, db: AsyncSession = Depends(get_db)
):
    """Удалить пользователя из пула дежурных (деактивировать)"""
    success = await DutyService.remove_from_pool(db, user_id, sector_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found in pool")
    return {"message": "User removed from duty pool"}


@router.get("/pool/sector/{sector_id}", response_model=DutyAdminPoolListResponse)
async def get_sector_pool(
    sector_id: int,
    active_only: bool = Query(True, description="Только активные"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Получить пул дежурных для сектора"""
    items, total = await DutyService.get_pool_by_sector(
        db, sector_id, active_only, skip, limit
    )

    # Добавляем имена пользователей и названия секторов
    for item in items:
        # Имя пользователя
        if item.user:
            # Пробуем получить из FIO
            fio_result = await db.execute(
                select(FIO).where(FIO.user_id == item.user_id)
            )
            fio = fio_result.scalar_one_or_none()
            if fio:
                item.user_name = f"{fio.last_name} {fio.first_name}".strip()
            elif item.user.last_name and item.user.first_name:
                item.user_name = f"{item.user.last_name} {item.user.first_name}".strip()
            else:
                item.user_name = f"Пользователь {item.user_id}"

        # Название сектора
        if item.sector:
            item.sector_name = item.sector.name or f"Сектор {item.sector_id}"
        else:
            # Если сектор не загружен, получаем отдельно
            sector_result = await db.execute(
                select(Sector).where(Sector.sector_id == item.sector_id)
            )
            sector = sector_result.scalar_one_or_none()
            item.sector_name = sector.name if sector else f"Сектор {item.sector_id}"

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/pool/user/{user_id}", response_model=List[DutyAdminPoolResponse])
async def get_user_pool_entries(user_id: int, db: AsyncSession = Depends(get_db)):
    """Получить все записи пользователя в пулах"""
    items = await DutyService.get_user_pool_entries(db, user_id)
    return items


# ========== УПРАВЛЕНИЕ РАСПИСАНИЕМ ==========


@router.post("/assign-weekly", response_model=WeeklyDutyAssignment)
async def assign_weekly_duty(
    sector_id: int,
    week_start: date,
    created_by: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Автоматически назначить дежурного на неделю"""
    # Проверяем существование сектора
    sector_name = await HealthService.get_sector_name(db, sector_id)
    if not sector_name:
        raise HTTPException(status_code=404, detail="Sector not found")

    result = await DutyService.assign_weekly_duty(db, sector_id, week_start, created_by)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "sector_id": sector_id,
        "week_start": week_start,
        "assigned_user_id": result["assigned_user_id"],
        "assigned_user_name": result["assigned_user_name"],
        "week_dates": result["week_dates"],
        "message": result["message"],
    }


@router.get("/schedule", response_model=DutyScheduleListResponse)
async def get_duty_schedule(
    sector_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Получить расписание дежурств с фильтрацией"""
    items, total = await DutyService.get_schedule(
        db, sector_id, user_id, start_date, end_date, skip, limit
    )

    # Добавляем день недели для каждого элемента
    for item in items:
        item.day_of_week = item.duty_date.strftime("%A")

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/schedule/monthly", response_model=List[DutyScheduleResponse])
async def get_monthly_schedule(
    sector_id: int, year: int, month: int, db: AsyncSession = Depends(get_db)
):
    """Получить расписание на месяц"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    items = await DutyService.get_monthly_schedule(db, sector_id, year, month)

    # Добавляем день недели
    for item in items:
        item.day_of_week = item.duty_date.strftime("%A")

    return items


@router.get("/schedule/today")
async def get_today_duty(
    sector_id: Optional[int] = None, db: AsyncSession = Depends(get_db)
):
    """Кто дежурит сегодня"""
    today = date.today()

    query = select(DutySchedule).where(DutySchedule.duty_date == today)
    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)

    query = query.options(
        selectinload(DutySchedule.user), selectinload(DutySchedule.sector)
    )

    result = await db.execute(query)
    duties = result.scalars().all()

    if not duties:
        return {"message": "Сегодня нет назначенных дежурных", "duties": []}

    response = []
    for duty in duties:
        # Получаем ФИО пользователя
        user_name = "Неизвестно"
        if duty.user:
            fio_result = await db.execute(
                select(FIO).where(FIO.user_id == duty.user_id)
            )
            fio = fio_result.scalar_one_or_none()
            if fio:
                user_name = f"{fio.last_name} {fio.first_name}".strip()
            elif duty.user.last_name and duty.user.first_name:
                user_name = f"{duty.user.last_name} {duty.user.first_name}".strip()
            else:
                user_name = f"Пользователь {duty.user_id}"

        # Получаем название сектора
        sector_name = f"Сектор {duty.sector_id}"
        if duty.sector and duty.sector.name:
            sector_name = duty.sector.name

        response.append(
            {
                "duty_id": duty.duty_id,
                "user_id": duty.user_id,
                "user_name": user_name,
                "sector_id": duty.sector_id,
                "sector_name": sector_name,
                "duty_date": duty.duty_date,
            }
        )

    return {"duties": response}


# ========== СТАТИСТИКА ==========


@router.get("/statistics", response_model=DutyStatisticsListResponse)
async def get_duty_statistics(
    sector_id: Optional[int] = None,
    user_id: Optional[int] = None,
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Получить статистику дежурств"""
    items, total = await DutyService.get_statistics(
        db, sector_id, user_id, year, skip, limit
    )

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get(
    "/statistics/sector/{sector_id}/summary", response_model=List[DutyStatisticsSummary]
)
async def get_sector_statistics_summary(
    sector_id: int, year: Optional[int] = None, db: AsyncSession = Depends(get_db)
):
    """Получить сводку статистики по сектору"""
    summary = await DutyService.get_sector_statistics_summary(db, sector_id, year)

    # Добавляем имена пользователей
    for item in summary:
        # Получаем ФИО из таблицы fio
        fio_result = await db.execute(select(FIO).where(FIO.user_id == item["user_id"]))
        fio = fio_result.scalar_one_or_none()

        if fio:
            item["user_name"] = f"{fio.last_name} {fio.first_name}".strip()
        else:
            # Если нет в fio, пробуем получить из users
            user_result = await db.execute(
                select(User).where(User.user_id == item["user_id"])
            )
            user = user_result.scalar_one_or_none()
            if user and user.last_name and user.first_name:
                item["user_name"] = f"{user.last_name} {user.first_name}".strip()
            else:
                item["user_name"] = f"Пользователь {item['user_id']}"

    return summary


# ========== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ==========


@router.get("/eligible-users")
async def get_eligible_users(
    sector_id: Optional[int] = None, db: AsyncSession = Depends(get_db)
):
    """Получить список пользователей, которые могут быть дежурными"""
    from sqlalchemy import select
    from app.models.user import User, FIO

    query = select(User).where(User.is_duty_eligible == True)
    result = await db.execute(query)
    users = result.scalars().all()

    response = []
    for user in users:
        # Проверяем, в пуле ли пользователь для данного сектора
        in_pool = False
        if sector_id:
            pool_result = await db.execute(
                select(DutyAdminPool).where(
                    DutyAdminPool.user_id == user.user_id,
                    DutyAdminPool.sector_id == sector_id,
                    DutyAdminPool.is_active == True,
                )
            )
            in_pool = pool_result.first() is not None

        # Получаем ФИО из таблицы fio
        fio_result = await db.execute(select(FIO).where(FIO.user_id == user.user_id))
        fio = fio_result.scalar_one_or_none()

        # Формируем имя
        if fio and fio.last_name and fio.first_name:
            user_name = f"{fio.last_name} {fio.first_name}".strip()
        elif user.last_name and user.first_name:
            user_name = f"{user.last_name} {user.first_name}".strip()
        elif user.username:
            user_name = f"@{user.username}"
        else:
            user_name = f"Пользователь {user.user_id}"

        response.append(
            {
                "user_id": user.user_id,
                "user_name": user_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "in_pool": in_pool,
            }
        )

    return response


@router.post("/eligible-users/{user_id}/toggle")
async def toggle_user_eligible(
    user_id: int,
    eligible: bool = Query(..., description="true/false"),
    db: AsyncSession = Depends(get_db),
):
    """Включить/выключить возможность быть дежурным для пользователя"""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_duty_eligible = eligible
    await db.commit()

    status = "включена" if eligible else "отключена"
    return {"message": f"Возможность быть дежурным {status} для пользователя {user_id}"}
