# app/services/admin_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserStatus

class AdminService:
    @staticmethod
    async def toggle_user_report(db: AsyncSession, user_id: int) -> bool:
        result = await db.execute(
            select(UserStatus)
            .where(UserStatus.user_id == user_id)
        )
        user_status = result.scalar_one_or_none()
        
        if user_status:
            user_status.enable_report = not user_status.enable_report
            await db.commit()
            return True
        return False
    
    @staticmethod
    async def toggle_user_admin(db: AsyncSession, user_id: int) -> bool:
        result = await db.execute(
            select(UserStatus)
            .where(UserStatus.user_id == user_id)
        )
        user_status = result.scalar_one_or_none()
        
        if user_status:
            user_status.enable_admin = not user_status.enable_admin
            await db.commit()
            return True
        return False