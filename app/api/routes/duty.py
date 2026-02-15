# app/api/routes/duty.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from enum import Enum
from collections import defaultdict
import calendar

from app.models.database import get_db
from app.models.user import User, FIO, Sector
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


class DutyPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


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


@router.get("/schedule/month")
async def get_month_schedule(
    sector_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить график дежурств на месяц в формате календаря
    """
    # Определяем год и месяц
    if not year or not month:
        today = date.today()
        year = year or today.year
        month = month or today.month

    # Валидация месяца
    if month < 1 or month > 12:
        return {"error": f"Некорректный месяц: {month}. Допустимые значения: 1-12"}

    # Получаем первый и последний день месяца
    try:
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
    except ValueError as e:
        return {"error": f"Некорректная дата: {e}"}

    # Получаем все дежурства за месяц
    query = select(DutySchedule).where(
        DutySchedule.duty_date.between(first_day, last_day)
    )

    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)

    query = query.options(
        selectinload(DutySchedule.user), selectinload(DutySchedule.sector)
    ).order_by(DutySchedule.duty_date)

    result = await db.execute(query)
    duties = result.scalars().all()

    # Группируем по датам
    duties_by_date = {}
    for duty in duties:
        date_str = duty.duty_date.isoformat()
        if date_str not in duties_by_date:
            duties_by_date[date_str] = []

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

        sector_name = duty.sector.name if duty.sector else f"Сектор {duty.sector_id}"

        duties_by_date[date_str].append(
            {
                "duty_id": duty.duty_id,
                "user_id": duty.user_id,
                "user_name": user_name,
                "sector_name": sector_name,
            }
        )

    # Создаем календарную сетку
    cal = calendar.monthcalendar(year, month)
    calendar_data = []

    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": None, "date": None, "duties": []})
            else:
                current_date = date(year, month, day)
                date_str = current_date.isoformat()
                week_data.append(
                    {
                        "day": day,
                        "date": date_str,
                        "is_today": current_date == date.today(),
                        "is_weekend": current_date.weekday() >= 5,
                        "duties": duties_by_date.get(date_str, []),
                    }
                )
        calendar_data.append(week_data)

    return {
        "period": "month",
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "first_day": first_day.isoformat(),
        "last_day": last_day.isoformat(),
        "calendar": calendar_data,
    }


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


# ========== ГРАФИКИ ДЕЖУРСТВ ==========


@router.get("/schedule/week")
async def get_week_schedule(
    sector_id: Optional[int] = None,
    week_start: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить график дежурств на неделю в формате для визуализации
    """
    # Определяем даты недели
    if week_start:
        try:
            start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Некорректный формат даты. Используйте ГГГГ-ММ-ДД"}
    else:
        # Текущая неделя (понедельник)
        today = date.today()
        start_date = today - timedelta(days=today.weekday())

    end_date = start_date + timedelta(days=6)

    # Получаем все дежурства за неделю
    query = select(DutySchedule).where(
        DutySchedule.duty_date.between(start_date, end_date)
    )

    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)

    query = query.options(
        selectinload(DutySchedule.user), selectinload(DutySchedule.sector)
    ).order_by(DutySchedule.duty_date)

    result = await db.execute(query)
    duties = result.scalars().all()

    # Группируем по датам
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    schedule_by_day = {i: [] for i in range(7)}

    for duty in duties:
        day_index = duty.duty_date.weekday()  # 0 = понедельник
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

        schedule_by_day[day_index].append(
            {
                "duty_id": duty.duty_id,
                "user_id": duty.user_id,
                "user_name": user_name,
                "sector_id": duty.sector_id,
                "sector_name": (
                    duty.sector.name if duty.sector else f"Сектор {duty.sector_id}"
                ),
                "date": duty.duty_date.isoformat(),
            }
        )

    # Формируем ответ для графика
    chart_data = []
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        chart_data.append(
            {
                "day": i,
                "day_name": days_of_week[i],
                "date": current_date.isoformat(),
                "is_today": current_date == date.today(),
                "is_weekend": i >= 5,  # Сб и Вс
                "duties": schedule_by_day[i],
            }
        )

    return {
        "period": "week",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": chart_data,
    }


@router.get("/schedule/month")
async def get_month_schedule(
    sector_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить график дежурств на месяц в формате календаря
    """
    # Определяем год и месяц
    if not year or not month:
        today = date.today()
        year = year or today.year
        month = month or today.month

    # Получаем первый и последний день месяца
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Получаем все дежурства за месяц
    query = select(DutySchedule).where(
        DutySchedule.duty_date.between(first_day, last_day)
    )

    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)

    query = query.options(
        selectinload(DutySchedule.user), selectinload(DutySchedule.sector)
    ).order_by(DutySchedule.duty_date)

    result = await db.execute(query)
    duties = result.scalars().all()

    # Группируем по датам
    duties_by_date = {}
    for duty in duties:
        date_str = duty.duty_date.isoformat()
        if date_str not in duties_by_date:
            duties_by_date[date_str] = []

        user_name = "Неизвестно"
        if duty.user:
            fio_result = await db.execute(
                select(FIO).where(FIO.user_id == duty.user_id)
            )
            fio = fio_result.scalar_one_or_none()
            if fio:
                user_name = f"{fio.last_name} {fio.first_name}".strip()

        duties_by_date[date_str].append(
            {
                "duty_id": duty.duty_id,
                "user_id": duty.user_id,
                "user_name": user_name,
                "sector_name": (
                    duty.sector.name if duty.sector else f"Сектор {duty.sector_id}"
                ),
            }
        )

    # Создаем календарную сетку
    cal = calendar.monthcalendar(year, month)
    calendar_data = []

    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": None, "date": None, "duties": []})
            else:
                current_date = date(year, month, day)
                date_str = current_date.isoformat()
                week_data.append(
                    {
                        "day": day,
                        "date": date_str,
                        "is_today": current_date == date.today(),
                        "is_weekend": current_date.weekday() >= 5,
                        "duties": duties_by_date.get(date_str, []),
                    }
                )
        calendar_data.append(week_data)

    return {
        "period": "month",
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "first_day": first_day.isoformat(),
        "last_day": last_day.isoformat(),
        "calendar": calendar_data,
    }


@router.get("/schedule/year")
async def get_year_schedule(
    sector_id: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить годовую статистику дежурств в формате для графика
    """
    if not year:
        year = date.today().year

    # Получаем статистику за год по месяцам
    query = select(DutySchedule).where(
        func.extract("year", DutySchedule.duty_date) == year
    )

    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)

    query = query.options(selectinload(DutySchedule.user))

    result = await db.execute(query)
    duties = result.scalars().all()

    # Группируем по месяцам
    monthly_stats = defaultdict(
        lambda: {
            "total_duties": 0,  # ← ИСПРАВЛЕНО: используем total_duties вместо total
            "users": defaultdict(int),
        }
    )

    user_names = {}

    for duty in duties:
        month = duty.duty_date.month
        monthly_stats[month]["total_duties"] += 1  # ← ИСПРАВЛЕНО

        # Получаем имя пользователя
        user_id = duty.user_id
        if user_id not in user_names:
            if duty.user:
                fio_result = await db.execute(select(FIO).where(FIO.user_id == user_id))
                fio = fio_result.scalar_one_or_none()
                if fio:
                    user_names[user_id] = f"{fio.last_name} {fio.first_name}".strip()
                elif duty.user.last_name and duty.user.first_name:
                    user_names[user_id] = (
                        f"{duty.user.last_name} {duty.user.first_name}".strip()
                    )
                else:
                    user_names[user_id] = f"ID {user_id}"

        monthly_stats[month]["users"][user_id] += 1

    # Формируем данные для графика
    months = []
    for month in range(1, 13):
        month_data = monthly_stats[month]

        # Топ-3 дежурных в этом месяце
        top_users = sorted(
            month_data["users"].items(), key=lambda x: x[1], reverse=True
        )[:3]

        months.append(
            {
                "month": month,
                "month_name": calendar.month_name[month],
                "total_duties": month_data["total_duties"],  # ← ИСПРАВЛЕНО
                "top_users": [
                    {
                        "user_id": user_id,
                        "user_name": user_names.get(user_id, f"ID {user_id}"),
                        "count": count,
                    }
                    for user_id, count in top_users
                ],
            }
        )

    # Общая статистика за год
    total_duties = sum(m["total_duties"] for m in months)  # ← ИСПРАВЛЕНО

    # Статистика по пользователям за год
    user_yearly_stats = defaultdict(int)
    for duty in duties:
        user_yearly_stats[duty.user_id] += 1

    top_users_yearly = sorted(
        user_yearly_stats.items(), key=lambda x: x[1], reverse=True
    )[:5]

    return {
        "period": "year",
        "year": year,
        "total_duties": total_duties,
        "average_per_month": total_duties / 12 if total_duties > 0 else 0,
        "months": months,
        "top_users": [
            {
                "user_id": user_id,
                "user_name": user_names.get(user_id, f"ID {user_id}"),
                "count": count,
            }
            for user_id, count in top_users_yearly
        ],
    }


@router.get("/statistics/chart")
async def get_duty_statistics_chart(
    sector_id: Optional[int] = None,
    user_id: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить данные для построения графиков статистики
    """
    if not year:
        year = date.today().year

    # Базовый запрос
    query = select(DutySchedule).where(
        func.extract("year", DutySchedule.duty_date) == year
    )

    if sector_id:
        query = query.where(DutySchedule.sector_id == sector_id)
    if user_id:
        query = query.where(DutySchedule.user_id == user_id)

    result = await db.execute(query)
    duties = result.scalars().all()

    # Данные для графика по месяцам
    monthly_data = [0] * 12
    for duty in duties:
        monthly_data[duty.duty_date.month - 1] += 1

    # Данные для графика по дням недели
    weekday_data = [0] * 7
    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for duty in duties:
        weekday_data[duty.duty_date.weekday()] += 1

    return {
        "year": year,
        "monthly": {
            "labels": [calendar.month_name[i] for i in range(1, 13)],
            "data": monthly_data,
        },
        "weekly": {"labels": weekday_names, "data": weekday_data},
        "total": len(duties),
    }


@router.get("/sector-info/{sector_id}")
async def get_sector_info(sector_id: int, db: AsyncSession = Depends(get_db)):
    """Получить информацию о секторе по ID"""
    from app.models.user import Sector

    sector = await db.get(Sector, sector_id)
    if not sector:
        # Пробуем найти по user_id в id_status
        from app.models.user import UserStatus

        result = await db.execute(
            select(UserStatus).where(UserStatus.sector_id == sector_id).limit(1)
        )
        status = result.scalar_one_or_none()
        if status:
            return {
                "sector_id": sector_id,
                "name": f"Сектор {sector_id} (по данным пользователей)",
                "exists_in_sectors": False,
            }
        return {
            "sector_id": sector_id,
            "name": f"Сектор {sector_id}",
            "exists_in_sectors": False,
        }

    return {
        "sector_id": sector.sector_id,
        "name": sector.name,
        "exists_in_sectors": True,
    }


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


@router.post("/assign")
async def assign_duty(
    sector_id: int,
    period: DutyPeriod,
    start_date: date,
    created_by: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Назначить дежурного на указанный период"""

    # Рассчитываем количество дней в зависимости от периода
    if period == DutyPeriod.DAY:
        days_count = 1
        end_date = start_date
        period_name = "день"
    elif period == DutyPeriod.WEEK:
        days_count = 7
        end_date = start_date + timedelta(days=6)
        period_name = "неделю"
    elif period == DutyPeriod.MONTH:
        # Определяем количество дней в месяце
        if start_date.month == 12:
            next_month = date(start_date.year + 1, 1, 1)
        else:
            next_month = date(start_date.year, start_date.month + 1, 1)
        end_date = next_month - timedelta(days=1)
        days_count = (end_date - start_date).days + 1
        period_name = "месяц"
    elif period == DutyPeriod.YEAR:
        end_date = date(start_date.year, 12, 31)
        days_count = (end_date - start_date).days + 1
        period_name = "год"
    else:
        raise HTTPException(status_code=400, detail="Invalid period")

    # Проверяем существование сектора
    sector_name = await HealthService.get_sector_name(db, sector_id)
    if not sector_name:
        raise HTTPException(status_code=404, detail="Sector not found")

    # Вызываем сервис для назначения
    result = await DutyService.assign_duty_for_period(
        db, sector_id, start_date, end_date, days_count, created_by
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        "sector_id": sector_id,
        "sector_name": sector_name,
        "period": period,
        "period_name": period_name,
        "start_date": start_date,
        "end_date": end_date,
        "days_count": days_count,
        "assigned_user_id": result["assigned_user_id"],
        "assigned_user_name": result["assigned_user_name"],
        "dates": result["dates"],
        "message": result["message"],
    }


# Оставляем старый метод для обратной совместимости
@router.post("/assign-weekly", response_model=WeeklyDutyAssignment)
async def assign_weekly_duty(
    sector_id: int,
    week_start: date,
    created_by: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Автоматически назначить дежурного на неделю (устаревший метод)"""
    return await assign_duty(
        sector_id=sector_id,
        period=DutyPeriod.WEEK,
        start_date=week_start,
        created_by=created_by,
        db=db,
    )


@router.post("/plan-year")
async def plan_yearly_duty_schedule(
    sector_id: int,
    year: int,
    working_days_only: bool = Query(True, description="Только рабочие дни"),
    db: AsyncSession = Depends(get_db),
):
    """Автоматически спланировать дежурства на весь год"""

    # Вызываем SQL функцию
    from sqlalchemy import text

    result = await db.execute(
        text(
            "SELECT * FROM assign_yearly_duty_schedule(:sector_id, :year, :working_days_only)"
        ),
        {"sector_id": sector_id, "year": year, "working_days_only": working_days_only},
    )

    assignments = result.fetchall()

    return {
        "sector_id": sector_id,
        "year": year,
        "working_days_only": working_days_only,
        "total_assignments": len(assignments),
        "assignments": [
            {"month": a[0], "week": a[1], "user_id": a[2], "user_name": a[3]}
            for a in assignments
        ],
    }


@router.get("/availability/{sector_id}")
async def check_duty_availability(
    sector_id: int,
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    """Проверить доступность дежурных на период"""

    # Получаем всех активных дежурных
    pool_result = await db.execute(
        select(DutyAdminPool)
        .where(DutyAdminPool.sector_id == sector_id, DutyAdminPool.is_active == True)
        .options(selectinload(DutyAdminPool.user))
    )
    active_pool = pool_result.scalars().all()

    # Получаем уже назначенные дежурства на этот период
    schedule_result = await db.execute(
        select(DutySchedule)
        .where(
            DutySchedule.sector_id == sector_id,
            DutySchedule.duty_date.between(start_date, end_date),
        )
        .options(selectinload(DutySchedule.user))
    )
    existing = schedule_result.scalars().all()

    # Группируем по пользователям
    from collections import defaultdict

    user_duties = defaultdict(list)
    for duty in existing:
        user_duties[duty.user_id].append(duty.duty_date)

    # Формируем ответ
    availability = []
    for pool_entry in active_pool:
        user = pool_entry.user
        user_name = "Неизвестно"
        if user:
            fio_result = await db.execute(
                select(FIO).where(FIO.user_id == user.user_id)
            )
            fio = fio_result.scalar_one_or_none()
            if fio:
                user_name = f"{fio.last_name} {fio.first_name}".strip()

        duties_count = len(user_duties.get(pool_entry.user_id, []))

        availability.append(
            {
                "user_id": pool_entry.user_id,
                "user_name": user_name,
                "assigned_dates": [
                    d.isoformat() for d in user_duties.get(pool_entry.user_id, [])
                ],
                "assigned_count": duties_count,
                "available": duties_count == 0,  # Простая проверка
            }
        )

    return {
        "sector_id": sector_id,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": (end_date - start_date).days + 1,
        },
        "availability": availability,
    }
