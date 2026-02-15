# app/services/duty_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from app.models.user import User, FIO, Sector
from app.models.duty import DutyAdminPool, DutySchedule, DutyStatistics
from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime, timedelta
from collections import defaultdict
import random


class DutyService:

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
            "week_dates": week_dates,
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
            return {
                "success": False,
                "message": f"Пользователь с ID {user_id} не найден",
            }

        # Если не force, проверяем, есть ли пользователь в пуле
        if not force:
            pool_result = await db.execute(
                select(DutyAdminPool).where(
                    DutyAdminPool.user_id == user_id,
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
        user_name = await DutyService._get_user_fio(db, user_id)

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
                    "message": f"На некоторые даты уже назначены дежурства. Используйте force=True для перезаписи",
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
                user_id=user_id,
                sector_id=sector_id,
                duty_date=duty_date,
                week_start=week_start,
                created_by=created_by,
            )
            db.add(schedule_entry)

        # Обновляем статистику
        year = week_start.year
        await DutyService._update_statistics(
            db, user_id, sector_id, year, 7, week_dates[-1]
        )

        await db.commit()

        return {
            "success": True,
            "message": f"Дежурство успешно назначено на {user_name}",
            "assigned_user_id": user_id,
            "assigned_user_name": user_name,
            "week_dates": week_dates,
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
                "date": current_date,
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
            "week_start": week_start,
            "week_end": week_end,
            "days": days,
        }
