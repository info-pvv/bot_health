# app/services/user_service.py - упрощенная версия
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserStatus, FIO, Health, Disease
from app.schemas.user import UserCreate, UserUpdate, UserStatusUpdate
from typing import Optional, List

class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        # Упрощенный запрос без сложных join
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate, chat_id: int) -> User:
        # Создаем пользователя
        db_user = User(**user_data.dict())
        db.add(db_user)
        await db.flush()  # Получаем ID
        
        # Создаем связанные записи
        db_fio = FIO(
            user_id=user_data.user_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            patronymic_name=user_data.username or ""
        )
        db.add(db_fio)
        
        db_status = UserStatus(
            user_id=user_data.user_id,
            enable_report=True,
            enable_admin=False,
            sector=chat_id
        )
        db.add(db_status)
        
        db_health = Health(user_id=user_data.user_id, status="")
        db.add(db_health)
        
        db_disease = Disease(user_id=user_data.user_id, disease="")
        db.add(db_disease)
        
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            # Обновляем основную информацию
            for key, value in user_data.dict(exclude_unset=True).items():
                if value is not None:
                    setattr(db_user, key, value)
            
            await db.commit()
            await db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    async def update_user_status(db: AsyncSession, user_id: int, status_data: UserStatusUpdate) -> Optional[UserStatus]:
        result = await db.execute(
            select(UserStatus).where(UserStatus.user_id == user_id)
        )
        db_status = result.scalar_one_or_none()
        
        if db_status:
            for key, value in status_data.dict(exclude_unset=True).items():
                if value is not None:
                    setattr(db_status, key, value)
            await db.commit()
        
        return db_status
    
    @staticmethod
    async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        result = await db.execute(
            select(User)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def is_user_admin(db: AsyncSession, user_id: int) -> bool:
        result = await db.execute(
            select(UserStatus)
            .where(UserStatus.user_id == user_id)
            .where(UserStatus.enable_admin == True)
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def update_health_status(db: AsyncSession, user_id: int, status: str) -> Optional[Health]:
        result = await db.execute(
            select(Health).where(Health.user_id == user_id)
        )
        db_health = result.scalar_one_or_none()
        
        if db_health:
            db_health.status = status
        else:
            db_health = Health(user_id=user_id, status=status)
            db.add(db_health)
        
        await db.commit()
        return db_health
    
    @staticmethod
    async def update_disease(db: AsyncSession, user_id: int, disease: str) -> Optional[Disease]:
        result = await db.execute(
            select(Disease).where(Disease.user_id == user_id)
        )
        db_disease = result.scalar_one_or_none()
        
        if db_disease:
            db_disease.disease = disease
        else:
            db_disease = Disease(user_id=user_id, disease=disease)
            db.add(db_disease)
        
        await db.commit()
        return db_disease