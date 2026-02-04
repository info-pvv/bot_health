# app/services/db.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.user import User, UserStatus, FIO, Health, Disease
from typing import List, Optional, Tuple
import asyncpg
from app.core.config import settings

class DatabaseService:
    
    @staticmethod
    async def get_users(db: AsyncSession) -> List[User]:
        """Получить всех пользователей"""
        result = await db.execute(select(User))
        return result.scalars().all()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: dict) -> User:
        """Создать пользователя"""
        user = User(**user_data)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def execute_raw_sql(query: str, params: dict = None):
        """Выполнить raw SQL запрос (для сложных операций)"""
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
        
        try:
            if params:
                result = await conn.fetch(query, *params.values())
            else:
                result = await conn.fetch(query)
            return result
        finally:
            await conn.close()
    
    @staticmethod
    async def get_health_report(db: AsyncSession, sector_id: Optional[int] = None) -> Tuple[dict, list]:
        """Получить отчет по здоровью с использованием JOIN для PostgreSQL"""
        query = """
        SELECT 
            f.first_name,
            f.last_name,
            h.status,
            COALESCE(d.disease, '') as disease
        FROM users u
        LEFT JOIN fio f ON f.user_id = u.user_id
        LEFT JOIN health h ON h.user_id = u.user_id
        LEFT JOIN disease d ON d.user_id = u.user_id
        LEFT JOIN id_status s ON s.user_id = u.user_id
        WHERE s.enable_report = true
        """
        
        params = {}
        if sector_id:
            query += " AND s.sector = :sector_id"
            params['sector_id'] = sector_id
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        # Статистика
        status_stats = {}
        for row in rows:
            status = row[2]
            status_stats[status] = status_stats.get(status, 0) + 1
        
        return status_stats, rows