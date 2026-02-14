# app/services/duty_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from app.models.user import User, FIO, Sector
from app.models.duty import DutyAdminPool, DutySchedule, DutyStatistics
from app.schemas.duty import DutyAdminPoolCreate, DutyScheduleCreate
from typing import List, Optional, Tuple, Dict
from datetime import date, datetime, timedelta
from collections import defaultdict


class DutyService:

    # ========== УПРАВЛЕНИЕ ПУЛОМ ДЕЖУРНЫХ ==========

    @staticmethod
    async def add_to_pool(
        db: AsyncSession, pool_data: DutyAdminPoolCreate
    ) -> Optional[DutyAdminPool]:
        """Добавить пользователя в пул дежурных"""
        # Проверяем, есть ли уже в пуле
        existing = await db.execute(
            select(DutyAdminPool).where(
                DutyAdminPool.user_id == pool_data.user_id,
                DutyAdminPool.sector_id == pool_data.sector_id,
            )
        )
        existing_pool = existing.scalar_one_or_none()

        if existing_pool:
            # Если есть, активируем
            existing_pool.is_active = True
            existing_pool.added_by = pool_data.added_by
            existing_pool.added_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing_pool)
            return existing_pool

        # Создаем новую запись
        db_pool = DutyAdminPool(**pool_data.model_dump())
        db.add(db_pool)
        await db.commit()
        await db.refresh(db_pool)
        return db_pool

    @staticmethod
    async def remove_from_pool(db: AsyncSession, user_id: int, sector_id: int) -> bool:
        """Деактивировать пользователя в пуле (мягкое удаление)"""
        result = await db.execute(
            select(DutyAdminPool).where(
                DutyAdminPool.user_id == user_id,
                DutyAdminPool.sector_id == sector_id,
                DutyAdminPool.is_active == True,
            )
        )
        db_pool = result.scalar_one_or_none()

        if db_pool:
            db_pool.is_active = False
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_pool_by_sector(
        db: AsyncSession,
        sector_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[DutyAdminPool], int]:
        """Получить пул дежурных для сектора"""
        query = select(DutyAdminPool).where(DutyAdminPool.sector_id == sector_id)

        if active_only:
            query = query.where(DutyAdminPool.is_active == True)

        # Получаем общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # Получаем данные с пагинацией
        query = query.order_by(DutyAdminPool.added_at.desc())
        query = query.offset(skip).limit(limit)

        # Загружаем связанные данные
        query = query.options(
            selectinload(DutyAdminPool.user),
            selectinload(DutyAdminPool.sector),
            selectinload(DutyAdminPool.added_by_user),
        )

        result = await db.execute(query)
        items = result.scalars().all()

        # Добавляем имена и названия
        for item in items:
            # Имя пользователя
            if item.user:
                # Пробуем получить из FIO
                fio_result = await db.execute(
                    select(FIO).where(FIO.user_id == item.user_id)
                )
                fio = fio_result.scalar_one_or_none()
                if fio and fio.last_name and fio.first_name:
                    item.user_name = f"{fio.last_name} {fio.first_name}".strip()
                elif item.user.last_name and item.user.first_name:
                    item.user_name = (
                        f"{item.user.last_name} {item.user.first_name}".strip()
                    )
                else:
                    item.user_name = f"Пользователь {item.user_id}"

            # Название сектора
            if item.sector and item.sector.name:
                item.sector_name = item.sector.name
            else:
                item.sector_name = f"Сектор {item.sector_id}"

        return items, total

    @staticmethod
    async def get_user_pool_entries(
        db: AsyncSession, user_id: int
    ) -> List[DutyAdminPool]:
        """Получить все записи пользователя в пулах"""
        result = await db.execute(
            select(DutyAdminPool)
            .where(DutyAdminPool.user_id == user_id)
            .options(
                selectinload(DutyAdminPool.sector),
                selectinload(DutyAdminPool.added_by_user),
            )
        )
        return result.scalars().all()

    # ========== УПРАВЛЕНИЕ РАСПИСАНИЕМ ==========

    @staticmethod
    async def assign_weekly_duty(
        db: AsyncSession,
        sector_id: int,
        week_start: date,
        created_by: Optional[int] = None,
    ) -> Dict:
        """Автоматически назначить дежурного на неделю"""
        # Проверяем, есть ли активные дежурные в пуле
        pool_result = await db.execute(
            select(DutyAdminPool).where(
                DutyAdminPool.sector_id == sector_id, DutyAdminPool.is_active == True
            )
        )
        active_pool = pool_result.scalars().all()

        if not active_pool:
            return {
                "success": False,
                "message": "В пуле нет активных дежурных для этого сектора",
                "assigned_user_id": None,
            }

        # Проверяем, не назначено ли уже на эту неделю
        existing = await db.execute(
            select(DutySchedule).where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.week_start == week_start,
            )
        )
        if existing.first():
            return {
                "success": False,
                "message": "Дежурство на эту неделю уже назначено",
                "assigned_user_id": None,
            }

        year = week_start.year

        # Получаем статистику для всех в пуле
        user_stats = []
        for pool_entry in active_pool:
            user_id = pool_entry.user_id

            # Статистика за год
            stats_result = await db.execute(
                select(DutyStatistics).where(
                    DutyStatistics.user_id == user_id,
                    DutyStatistics.sector_id == sector_id,
                    DutyStatistics.year == year,
                )
            )
            stats = stats_result.scalar_one_or_none()

            # Получаем ФИО
            fio_result = await db.execute(select(FIO).where(FIO.user_id == user_id))
            fio = fio_result.scalar_one_or_none()

            user_stats.append(
                {
                    "user_id": user_id,
                    "fio": fio,
                    "total_duties": stats.total_duties if stats else 0,
                    "last_duty_date": stats.last_duty_date if stats else None,
                }
            )

        # Сортируем по количеству дежурств (меньше -> лучше)
        user_stats.sort(
            key=lambda x: (x["total_duties"], x["last_duty_date"] or date.min)
        )

        # Выбираем первого (с наименьшим количеством)
        selected = user_stats[0]
        selected_user_id = selected["user_id"]

        # Создаем массив дат на неделю
        week_dates = [week_start + timedelta(days=i) for i in range(7)]

        # Создаем записи в расписании
        for duty_date in week_dates:
            schedule_entry = DutySchedule(
                user_id=selected_user_id,
                sector_id=sector_id,
                duty_date=duty_date,
                week_start=week_start,
                created_by=created_by,
            )
            db.add(schedule_entry)

        # Обновляем статистику
        stats_result = await db.execute(
            select(DutyStatistics).where(
                DutyStatistics.user_id == selected_user_id,
                DutyStatistics.sector_id == sector_id,
                DutyStatistics.year == year,
            )
        )
        stats = stats_result.scalar_one_or_none()

        if stats:
            stats.total_duties += 7
            stats.last_duty_date = week_dates[-1]
            stats.updated_at = datetime.utcnow()
        else:
            stats = DutyStatistics(
                user_id=selected_user_id,
                sector_id=sector_id,
                year=year,
                total_duties=7,
                last_duty_date=week_dates[-1],
            )
            db.add(stats)

        await db.commit()

        # Формируем имя пользователя
        user_name = "Неизвестно"
        if selected["fio"]:
            user_name = (
                f"{selected['fio'].last_name} {selected['fio'].first_name}".strip()
            )

        return {
            "success": True,
            "message": "Дежурство успешно назначено",
            "assigned_user_id": selected_user_id,
            "assigned_user_name": user_name,
            "week_dates": week_dates,
        }

    @staticmethod
    async def get_schedule(
        db: AsyncSession,
        sector_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[DutySchedule], int]:
        """Получить расписание с фильтрацией"""
        query = select(DutySchedule)

        if sector_id:
            query = query.where(DutySchedule.sector_id == sector_id)
        if user_id:
            query = query.where(DutySchedule.user_id == user_id)
        if start_date:
            query = query.where(DutySchedule.duty_date >= start_date)
        if end_date:
            query = query.where(DutySchedule.duty_date <= end_date)

        # Общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # Загружаем с пагинацией
        query = query.order_by(DutySchedule.duty_date.desc())
        query = query.offset(skip).limit(limit)
        query = query.options(
            selectinload(DutySchedule.user),
            selectinload(DutySchedule.sector),
            selectinload(DutySchedule.created_by_user),
        )

        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    @staticmethod
    async def get_monthly_schedule(
        db: AsyncSession, sector_id: int, year: int, month: int
    ) -> List[DutySchedule]:
        """Получить расписание на месяц"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        result = await db.execute(
            select(DutySchedule)
            .where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date >= start_date,
                DutySchedule.duty_date <= end_date,
            )
            .order_by(DutySchedule.duty_date)
            .options(selectinload(DutySchedule.user), selectinload(DutySchedule.sector))
        )
        return result.scalars().all()

    # ========== СТАТИСТИКА ==========

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        sector_id: Optional[int] = None,
        user_id: Optional[int] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[DutyStatistics], int]:
        """Получить статистику дежурств"""
        query = select(DutyStatistics)

        if sector_id:
            query = query.where(DutyStatistics.sector_id == sector_id)
        if user_id:
            query = query.where(DutyStatistics.user_id == user_id)
        if year:
            query = query.where(DutyStatistics.year == year)

        # Общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        # Загружаем с пагинацией
        query = query.order_by(
            DutyStatistics.year.desc(), DutyStatistics.total_duties.desc()
        )
        query = query.offset(skip).limit(limit)
        query = query.options(
            selectinload(DutyStatistics.user), selectinload(DutyStatistics.sector)
        )

        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    @staticmethod
    async def get_sector_statistics_summary(
        db: AsyncSession, sector_id: int, year: Optional[int] = None
    ) -> List[Dict]:
        """Получить сводку по сектору"""
        if not year:
            year = date.today().year

        # Получаем всех пользователей, которые могут быть дежурными
        users_result = await db.execute(
            select(User).where(User.is_duty_eligible == True)
        )
        users = users_result.scalars().all()

        result = []
        for user in users:
            # Проверяем, в пуле ли пользователь
            pool_result = await db.execute(
                select(DutyAdminPool).where(
                    DutyAdminPool.user_id == user.user_id,
                    DutyAdminPool.sector_id == sector_id,
                    DutyAdminPool.is_active == True,
                )
            )
            in_pool = pool_result.first() is not None

            # Получаем статистику
            stats_result = await db.execute(
                select(DutyStatistics).where(
                    DutyStatistics.user_id == user.user_id,
                    DutyStatistics.sector_id == sector_id,
                    DutyStatistics.year == year,
                )
            )
            stats = stats_result.scalar_one_or_none()

            # Получаем ФИО
            fio_result = await db.execute(
                select(FIO).where(FIO.user_id == user.user_id)
            )
            fio = fio_result.scalar_one_or_none()

            user_name = "Неизвестно"
            if fio:
                user_name = f"{fio.last_name} {fio.first_name}".strip()
            elif user.last_name and user.first_name:
                user_name = f"{user.last_name} {user.first_name}".strip()

            result.append(
                {
                    "user_id": user.user_id,
                    "user_name": user_name,
                    "total_duties": stats.total_duties if stats else 0,
                    "last_duty_date": stats.last_duty_date if stats else None,
                    "in_pool": in_pool,
                }
            )

        # Сортируем: сначала в пуле, потом по количеству дежурств
        result.sort(key=lambda x: (not x["in_pool"], -x["total_duties"]))

        return result
