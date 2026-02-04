# app/services/health_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.user import User, UserStatus, FIO, Health, Disease
from app.schemas.health import HealthUpdate, DiseaseUpdate
from typing import List, Tuple, Dict, Optional  # Добавьте Optional здесь
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
        # Базовый запрос
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
            query = query.where(UserStatus.sector == sector_id)
        
        result = await db.execute(query)
        users_data = result.all()
        
        # Статистика по статусам
        status_stats = defaultdict(int)
        total = 0
        
        for user in users_data:
            status_stats[user[2]] += 1
            total += 1
        
        return dict(status_stats), users_data
    
    @staticmethod
    async def get_all_sectors(db: AsyncSession) -> List[int]:
        result = await db.execute(
            select(UserStatus.sector)
            .distinct()
            .where(UserStatus.enable_report == True)
        )
        return [row[0] for row in result.all() if row[0]]