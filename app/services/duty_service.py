# app/services/duty_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from app.models.user import User, FIO, Sector
from app.models.duty import DutyAdminPool, DutySchedule, DutyStatistics
from app.schemas.duty import DutyAdminPoolCreate, DutyScheduleCreate
from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime, timedelta
from collections import defaultdict
import random


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

        # Добавляем имена пользователей и названия секторов
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

    # ========== ОСНОВНЫЕ МЕТОДЫ ДЛЯ НАЗНАЧЕНИЯ ==========

    @staticmethod
    async def assign_weekly_duty_auto(
        db: AsyncSession,
        sector_id: int,
        week_start: date,
        created_by: Optional[int] = None,
        allow_same_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Автоматически назначить дежурного на неделю с циклическим распределением

        Args:
            db: Сессия БД
            sector_id: ID сектора
            week_start: Начало недели (понедельник)
            created_by: ID создателя (админа)
            allow_same_admin: Разрешить ли назначать того же админа, что и на прошлой неделе

        Returns:
            Dict с результатом назначения
        """
        # Проверяем существование сектора
        sector = await db.get(Sector, sector_id)
        if not sector:
            return {
                "success": False,
                "message": f"Сектор с ID {sector_id} не найден",
                "assigned_user_id": None,
            }

        # Получаем всех активных дежурных в пуле
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

        # Получаем ID дежурных в пуле
        pool_user_ids = [p.user_id for p in active_pool]

        # Определяем предыдущую неделю
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = prev_week_start + timedelta(days=6)

        # Получаем дежурного на предыдущей неделе
        prev_week_result = await db.execute(
            select(DutySchedule)
            .where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date >= prev_week_start,
                DutySchedule.duty_date <= prev_week_end,
            )
            .limit(1)
        )
        prev_week_duty = prev_week_result.scalar_one_or_none()
        prev_admin_id = prev_week_duty.user_id if prev_week_duty else None

        # Получаем статистику за год
        year = week_start.year
        stats_result = await db.execute(
            select(DutyStatistics).where(
                DutyStatistics.sector_id == sector_id,
                DutyStatistics.year == year,
                DutyStatistics.user_id.in_(pool_user_ids),
            )
        )
        stats = stats_result.scalars().all()
        stats_dict = {s.user_id: s.total_duties for s in stats}

        # Получаем всех дежурных с их количеством дежурств
        candidates = []
        for user_id in pool_user_ids:
            # Получаем ФИО
            fio = await DutyService._get_user_fio(db, user_id)

            # Проверяем, был ли этот админ на прошлой неделе
            was_last_week = prev_admin_id == user_id

            # Если запрещено назначать того же и он был на прошлой неделе - пропускаем
            if not allow_same_admin and was_last_week:
                continue

            candidates.append(
                {
                    "user_id": user_id,
                    "user_name": fio,
                    "total_duties": stats_dict.get(user_id, 0),
                    "was_last_week": was_last_week,
                }
            )

        # Если после фильтрации не осталось кандидатов, снимаем фильтр
        if not candidates and not allow_same_admin:
            # Добавляем всех, включая того, кто был на прошлой неделе
            for user_id in pool_user_ids:
                fio = await DutyService._get_user_fio(db, user_id)
                candidates.append(
                    {
                        "user_id": user_id,
                        "user_name": fio,
                        "total_duties": stats_dict.get(user_id, 0),
                        "was_last_week": (prev_admin_id == user_id),
                    }
                )

        # Сортируем по количеству дежурств (меньше -> лучше)
        candidates.sort(key=lambda x: x["total_duties"])

        # Выбираем кандидата с наименьшим количеством дежурств
        # Если есть несколько с одинаковым минимальным, выбираем случайного
        min_duties = candidates[0]["total_duties"] if candidates else 0
        best_candidates = [c for c in candidates if c["total_duties"] == min_duties]
        selected = random.choice(best_candidates)

        # Создаем записи в расписании
        week_dates = [week_start + timedelta(days=i) for i in range(7)]

        # Удаляем существующие записи на эту неделю (если есть)
        await db.execute(
            select(DutySchedule).where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.week_start == week_start,
            )
        )
        await db.execute(
            DutySchedule.__table__.delete().where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.week_start == week_start,
            )
        )

        # Создаем новые записи
        for duty_date in week_dates:
            schedule_entry = DutySchedule(
                user_id=selected["user_id"],
                sector_id=sector_id,
                duty_date=duty_date,
                week_start=week_start,
                created_by=created_by,
            )
            db.add(schedule_entry)

        # Обновляем статистику
        await DutyService._update_statistics(
            db, selected["user_id"], sector_id, year, 7, week_dates[-1]
        )

        await db.commit()

        return {
            "success": True,
            "message": f"Дежурство успешно назначено на {selected['user_name']}",
            "assigned_user_id": selected["user_id"],
            "assigned_user_name": selected["user_name"],
            "week_dates": [d.isoformat() for d in week_dates],
            "total_duties": selected["total_duties"] + 7,
        }

    @staticmethod
    async def assign_weekly_duty_manual(
        db: AsyncSession,
        sector_id: int,
        week_start: date,
        user_id: int,
        created_by: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Ручное назначение конкретного дежурного на неделю

        Args:
            db: Сессия БД
            sector_id: ID сектора
            week_start: Начало недели (понедельник)
            user_id: ID назначаемого дежурного
            created_by: ID создателя (админа)
            force: Принудительное назначение (даже если не в пуле или уже есть назначения)

        Returns:
            Dict с результатом назначения
        """
        # Проверяем существование сектора
        sector = await db.get(Sector, sector_id)
        if not sector:
            return {
                "success": False,
                "message": f"Сектор с ID {sector_id} не найден",
            }

        # Проверяем существование пользователя
        user = await db.get(User, user_id)
        if not user:
            # Пробуем найти по user_id если не нашли по id
            user_result = await db.execute(select(User).where(User.user_id == user_id))
            user = user_result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "message": f"Пользователь с ID {user_id} не найден",
            }

        # Если не force, проверяем, есть ли пользователь в пуле
        if not force:
            pool_result = await db.execute(
                select(DutyAdminPool).where(
                    DutyAdminPool.user_id == user.user_id,
                    DutyAdminPool.sector_id == sector_id,
                    DutyAdminPool.is_active == True,
                )
            )
            if not pool_result.scalar_one_or_none():
                return {
                    "success": False,
                    "message": f"Пользователь не находится в активном пуле дежурных для этого сектора",
                }

        # Получаем ФИО пользователя
        user_name = await DutyService._get_user_fio(db, user.user_id)

        # Создаем записи в расписании
        week_dates = [week_start + timedelta(days=i) for i in range(7)]

        # Если не force, проверяем существующие записи
        if not force:
            existing = await db.execute(
                select(DutySchedule).where(
                    DutySchedule.sector_id == sector_id,
                    DutySchedule.duty_date.in_(week_dates),
                )
            )
            if existing.first():
                return {
                    "success": False,
                    "message": f"На некоторые даты уже назначены дежурства. Используйте force=true для перезаписи",
                }

        # Удаляем существующие записи на эту неделю (если есть)
        await db.execute(
            DutySchedule.__table__.delete().where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date.in_(week_dates),
            )
        )

        # Создаем новые записи
        for duty_date in week_dates:
            schedule_entry = DutySchedule(
                user_id=user.user_id,
                sector_id=sector_id,
                duty_date=duty_date,
                week_start=week_start,
                created_by=created_by,
            )
            db.add(schedule_entry)

        # Обновляем статистику
        year = week_start.year
        await DutyService._update_statistics(
            db, user.user_id, sector_id, year, 7, week_dates[-1]
        )

        await db.commit()

        return {
            "success": True,
            "message": f"Дежурство успешно назначено на {user_name}",
            "assigned_user_id": user.user_id,
            "assigned_user_name": user_name,
            "week_dates": [d.isoformat() for d in week_dates],
        }

    @staticmethod
    async def assign_yearly_schedule(
        db: AsyncSession,
        sector_id: int,
        year: int,
        working_days_only: bool = True,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Автоматически распределить дежурства на весь год с циклическим распределением

        Args:
            db: Сессия БД
            sector_id: ID сектора
            year: Год
            working_days_only: Только рабочие дни
            created_by: ID создателя

        Returns:
            Dict с результатами распределения
        """
        # Получаем всех активных дежурных
        pool_result = await db.execute(
            select(DutyAdminPool)
            .where(
                DutyAdminPool.sector_id == sector_id, DutyAdminPool.is_active == True
            )
            .options(selectinload(DutyAdminPool.user))
        )
        active_pool = pool_result.scalars().all()

        if not active_pool:
            return {
                "success": False,
                "message": "В пуле нет активных дежурных",
                "assignments": [],
            }

        pool_user_ids = [p.user_id for p in active_pool]

        # Получаем ФИО для всех
        user_names = {}
        for user_id in pool_user_ids:
            user_names[user_id] = await DutyService._get_user_fio(db, user_id)

        # Определяем все даты в году
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            if working_days_only:
                # Пропускаем выходные
                if current_date.weekday() < 5:  # 0-4 = пн-пт
                    all_dates.append(current_date)
            else:
                all_dates.append(current_date)
            current_date += timedelta(days=1)

        # Группируем по неделям
        weeks = {}
        for d in all_dates:
            week_num = d.isocalendar()[1]
            week_key = f"{year}-W{week_num}"
            if week_key not in weeks:
                weeks[week_key] = {
                    "start": d - timedelta(days=d.weekday()),
                    "dates": [],
                }
            weeks[week_key]["dates"].append(d)

        # Удаляем существующие расписания на этот год
        await db.execute(
            DutySchedule.__table__.delete().where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date >= start_date,
                DutySchedule.duty_date <= end_date,
            )
        )

        # Распределяем дежурства по неделям
        assignments = []
        user_index = 0
        num_users = len(pool_user_ids)

        # Получаем текущую статистику
        stats = {}
        for user_id in pool_user_ids:
            stats[user_id] = 0

        # Сортируем недели
        sorted_weeks = sorted(weeks.keys())

        for week_key in sorted_weeks:
            week_data = weeks[week_key]
            week_start = week_data["start"]

            # Выбираем следующего пользователя по кругу
            current_user_id = pool_user_ids[user_index % num_users]
            user_index += 1

            # Создаем записи для всех дней недели
            for duty_date in week_data["dates"]:
                schedule_entry = DutySchedule(
                    user_id=current_user_id,
                    sector_id=sector_id,
                    duty_date=duty_date,
                    week_start=week_start,
                    created_by=created_by,
                )
                db.add(schedule_entry)
                stats[current_user_id] += 1

            assignments.append(
                {
                    "week_start": week_start.isoformat(),
                    "user_id": current_user_id,
                    "user_name": user_names[current_user_id],
                    "days": len(week_data["dates"]),
                }
            )

        # Обновляем статистику
        for user_id, total in stats.items():
            await DutyService._update_statistics(
                db, user_id, sector_id, year, total, end_date if total > 0 else None
            )

        await db.commit()

        return {
            "success": True,
            "message": f"Годовое расписание создано: {len(assignments)} недель",
            "assignments": assignments,
            "stats": stats,
        }

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    @staticmethod
    async def _get_user_fio(db: AsyncSession, user_id: int) -> str:
        """Получить ФИО пользователя"""
        fio_result = await db.execute(select(FIO).where(FIO.user_id == user_id))
        fio = fio_result.scalar_one_or_none()

        if fio and fio.last_name and fio.first_name:
            return f"{fio.last_name} {fio.first_name}".strip()

        user_result = await db.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.last_name and user.first_name:
            return f"{user.last_name} {user.first_name}".strip()

        return f"Пользователь {user_id}"

    @staticmethod
    async def _update_statistics(
        db: AsyncSession,
        user_id: int,
        sector_id: int,
        year: int,
        days_added: int,
        last_date: Optional[date],
    ):
        """Обновить статистику пользователя"""
        stats_result = await db.execute(
            select(DutyStatistics).where(
                DutyStatistics.user_id == user_id,
                DutyStatistics.sector_id == sector_id,
                DutyStatistics.year == year,
            )
        )
        stats = stats_result.scalar_one_or_none()

        if stats:
            stats.total_duties += days_added
            if last_date:
                stats.last_duty_date = last_date
            stats.updated_at = datetime.utcnow()
        else:
            stats = DutyStatistics(
                user_id=user_id,
                sector_id=sector_id,
                year=year,
                total_duties=days_added,
                last_duty_date=last_date,
            )
            db.add(stats)

    # ========== МЕТОДЫ ДЛЯ ПРОВЕРКИ И ПОЛУЧЕНИЯ ДАННЫХ ==========

    @staticmethod
    async def get_available_admins_for_week(
        db: AsyncSession,
        sector_id: int,
        week_start: date,
        exclude_last_week: bool = True,
    ) -> List[Dict]:
        """
        Получить список доступных администраторов для назначения на неделю

        Args:
            db: Сессия БД
            sector_id: ID сектора
            week_start: Начало недели
            exclude_last_week: Исключить админа с прошлой недели

        Returns:
            Список доступных админов
        """
        # Получаем всех активных дежурных
        pool_result = await db.execute(
            select(DutyAdminPool).where(
                DutyAdminPool.sector_id == sector_id, DutyAdminPool.is_active == True
            )
        )
        active_pool = pool_result.scalars().all()
        pool_user_ids = [p.user_id for p in active_pool]

        if exclude_last_week:
            # Получаем админа с прошлой недели
            prev_week = week_start - timedelta(days=7)
            prev_result = await db.execute(
                select(DutySchedule)
                .where(
                    DutySchedule.sector_id == sector_id,
                    DutySchedule.week_start == prev_week,
                )
                .limit(1)
            )
            prev_duty = prev_result.scalar_one_or_none()
            if prev_duty:
                # Исключаем его из списка
                pool_user_ids = [
                    uid for uid in pool_user_ids if uid != prev_duty.user_id
                ]

        # Получаем статистику за год
        year = week_start.year
        stats_result = await db.execute(
            select(DutyStatistics).where(
                DutyStatistics.sector_id == sector_id,
                DutyStatistics.year == year,
                DutyStatistics.user_id.in_(pool_user_ids),
            )
        )
        stats = stats_result.scalars().all()
        stats_dict = {s.user_id: s.total_duties for s in stats}

        # Формируем список
        result = []
        for user_id in pool_user_ids:
            result.append(
                {
                    "user_id": user_id,
                    "user_name": await DutyService._get_user_fio(db, user_id),
                    "total_duties": stats_dict.get(user_id, 0),
                }
            )

        # Сортируем по количеству дежурств
        result.sort(key=lambda x: x["total_duties"])

        return result

    @staticmethod
    async def get_week_schedule(
        db: AsyncSession,
        sector_id: int,
        week_start: Optional[date] = None,
    ) -> Dict:
        """
        Получить расписание на неделю

        Args:
            db: Сессия БД
            sector_id: ID сектора
            week_start: Начало недели (если не указано - текущая)

        Returns:
            Расписание на неделю
        """
        if not week_start:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        result = await db.execute(
            select(DutySchedule)
            .where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date >= week_start,
                DutySchedule.duty_date <= week_end,
            )
            .order_by(DutySchedule.duty_date)
            .options(selectinload(DutySchedule.user))
        )
        duties = result.scalars().all()

        # Группируем по дням
        days = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_duties = [d for d in duties if d.duty_date == current_date]

            day_info = {
                "date": current_date.isoformat(),
                "day_name": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][i],
                "is_weekend": i >= 5,
                "is_today": current_date == date.today(),
                "duties": [],
            }

            for duty in day_duties:
                day_info["duties"].append(
                    {
                        "duty_id": duty.duty_id,
                        "user_id": duty.user_id,
                        "user_name": await DutyService._get_user_fio(db, duty.user_id),
                    }
                )

            days.append(day_info)

        return {
            "sector_id": sector_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "days": days,
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

    @staticmethod
    async def assign_duty_for_period(
        db: AsyncSession,
        sector_id: int,
        start_date: date,
        end_date: date,
        days_count: int,
        created_by: Optional[int] = None,
    ) -> Dict:
        """Назначить дежурного на указанный период"""
        # Проверяем существование сектора
        sector = await db.get(Sector, sector_id)
        if not sector:
            return {
                "success": False,
                "message": f"Сектор с ID {sector_id} не найден",
                "assigned_user_id": None,
            }

        # Проверяем, есть ли активные дежурные в пуле для этого сектора
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

        # Проверяем, не назначено ли уже на какие-то даты в этом периоде
        existing = await db.execute(
            select(DutySchedule).where(
                DutySchedule.sector_id == sector_id,
                DutySchedule.duty_date.between(start_date, end_date),
            )
        )
        existing_duties = existing.scalars().all()

        if existing_duties:
            existing_dates = [d.duty_date for d in existing_duties]
            return {
                "success": False,
                "message": f"На некоторые даты уже назначены дежурства: {existing_dates}",
                "assigned_user_id": None,
            }

        year = start_date.year

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

            # Получаем предыдущие дежурства в этом году для более точного распределения
            prev_duties_result = await db.execute(
                select(DutySchedule).where(
                    DutySchedule.user_id == user_id,
                    DutySchedule.sector_id == sector_id,
                    DutySchedule.duty_date >= date(year, 1, 1),
                    DutySchedule.duty_date <= date(year, 12, 31),
                )
            )
            prev_duties = prev_duties_result.scalars().all()
            prev_days_count = len(prev_duties)

            user_stats.append(
                {
                    "user_id": user_id,
                    "fio": fio,
                    "total_duties": stats.total_duties if stats else 0,
                    "prev_days_count": prev_days_count,
                    "last_duty_date": stats.last_duty_date if stats else None,
                }
            )

        # Сортируем по количеству дежурств (меньше -> лучше)
        user_stats.sort(
            key=lambda x: (
                x["total_duties"],
                x["prev_days_count"],
                x["last_duty_date"] or date.min,
            )
        )

        # Выбираем первого (с наименьшим количеством)
        selected = user_stats[0]
        selected_user_id = selected["user_id"]

        # Создаем массив дат на период
        period_dates = []
        current_date = start_date
        while current_date <= end_date:
            period_dates.append(current_date)
            current_date += timedelta(days=1)

        # Создаем записи в расписании
        for duty_date in period_dates:
            schedule_entry = DutySchedule(
                user_id=selected_user_id,
                sector_id=sector_id,
                duty_date=duty_date,
                week_start=start_date,  # Для недели это начало недели, для других периодов - начало периода
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
            stats.total_duties += days_count
            stats.last_duty_date = period_dates[-1]
            stats.updated_at = datetime.utcnow()
        else:
            stats = DutyStatistics(
                user_id=selected_user_id,
                sector_id=sector_id,
                year=year,
                total_duties=days_count,
                last_duty_date=period_dates[-1],
            )
            db.add(stats)

        await db.commit()

        # Формируем имя пользователя
        user_name = "Неизвестно"
        if selected["fio"]:
            user_name = (
                f"{selected['fio'].last_name} {selected['fio'].first_name}".strip()
            )
        else:
            user_result = await db.execute(
                select(User).where(User.user_id == selected_user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.last_name and user.first_name:
                user_name = f"{user.last_name} {user.first_name}".strip()

        return {
            "success": True,
            "message": f"Дежурство успешно назначено на {days_count} дней",
            "assigned_user_id": selected_user_id,
            "assigned_user_name": user_name,
            "dates": [d.isoformat() for d in period_dates],
        }
