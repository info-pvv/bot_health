# app/services/health_service.py - обновленная версия
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.user import User, UserStatus, FIO, Health, Disease, Sector
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

class HealthService:
    @staticmethod
    async def update_health_status(db: AsyncSession, user_id: int, status: str) -> Health:
        result = await db.execute(
            select(Health)
            .where(Health.user_id == user_id)
        )
        db_health = result.scalar_one_or_none()
        
        if db_health:
            db_health.status = status
        else:
            db_health = Health(user_id=user_id, status=status)
            db.add(db_health)
        
        await db.commit()
        await db.refresh(db_health)
        return db_health
    
    @staticmethod
    async def update_disease(db: AsyncSession, user_id: int, disease: str) -> Disease:
        result = await db.execute(
            select(Disease)
            .where(Disease.user_id == user_id)
        )
        db_disease = result.scalar_one_or_none()
        
        if db_disease:
            db_disease.disease = disease
        else:
            db_disease = Disease(user_id=user_id, disease=disease)
            db.add(db_disease)
        
        await db.commit()
        await db.refresh(db_disease)
        return db_disease
    
    @staticmethod
    async def get_report(db: AsyncSession, sector_id: Optional[int] = None) -> Tuple[Dict, List]:
        # Базовый запрос с JOIN
        query = (
            select(
                FIO.first_name,
                FIO.last_name,
                Health.status,
                Disease.disease
            )
            .select_from(User)
            .join(FIO, FIO.user_id == User.user_id)
            .join(Health, Health.user_id == User.user_id)
            .join(Disease, Disease.user_id == User.user_id)
            .join(UserStatus, UserStatus.user_id == User.user_id)
            .where(UserStatus.enable_report == True)
        )
        
        if sector_id:
            query = query.where(UserStatus.sector_id == sector_id)
        
        result = await db.execute(query)
        users_data = result.all()
        
        # Статистика по статусам
        status_stats = defaultdict(int)
        
        for user in users_data:
            status = user[2] or "не указан"
            status_stats[status] += 1
        
        return dict(status_stats), users_data
    
    @staticmethod
    async def get_all_sectors(db: AsyncSession) -> List[int]:
        result = await db.execute(
            select(UserStatus.sector_id)
            .distinct()
            .where(UserStatus.enable_report == True)
            .where(UserStatus.sector_id.isnot(None))
        )
        return [row[0] for row in result.all()]
    
    @staticmethod
    async def get_sector_name(db: AsyncSession, sector_id: int) -> Optional[str]:
        """Получить название сектора по ID из таблицы sectors"""
        if not sector_id:
            return None
        
        try:
            result = await db.execute(
                select(Sector.name).where(Sector.sector_id == sector_id)
            )
            name = result.scalar_one_or_none()
            return name or f"Сектор {sector_id}"
        except Exception as e:
            print(f"Ошибка при получении названия сектора {sector_id}: {e}")
            return f"Сектор {sector_id}"
    
    @staticmethod
    async def get_all_sectors_with_names(db: AsyncSession) -> List[dict]:
        """Получить все сектора с названиями из таблицы sectors"""
        try:
            result = await db.execute(
                select(Sector.sector_id, Sector.name)
                .order_by(Sector.sector_id)
            )
            
            sectors = []
            for row in result.all():
                sectors.append({
                    "sector_id": row[0],
                    "name": row[1] or f"Сектор {row[0]}"
                })
            
            return sectors
        except Exception as e:
            print(f"Ошибка при получении секторов из БД: {e}")
            # Fallback на случай ошибки
            return []