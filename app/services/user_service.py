from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User, UserStatus, FIO, Health, Disease
from app.schemas.user import UserCreate, UserUpdate, UserStatusUpdate
from typing import Optional, List  # Добавьте импорты

class UserService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.status))
            .where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate, chat_id: int) -> User:
        # Создаем пользователя
        db_user = User(**user_data.dict())
        db.add(db_user)
        await db.flush()
        
        # Создаем FIO
        db_fio = FIO(
            user_id=user_data.user_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            patronymic_name=user_data.username
        )
        db.add(db_fio)
        
        # Создаем статус
        db_status = UserStatus(
            user_id=user_data.user_id,
            enable_report=True,
            enable_admin=False,
            sector=chat_id
        )
        db.add(db_status)
        
        # Создаем запись здоровья
        db_health = Health(user_id=user_data.user_id, status="")
        db.add(db_health)
        
        # Создаем запись заболевания
        db_disease = Disease(user_id=user_data.user_id, disease="")
        db.add(db_disease)
        
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
        result = await db.execute(
            select(User)
            .where(User.user_id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            for key, value in user_data.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            
            # Обновляем FIO
            await db.execute(
                select(FIO)
                .where(FIO.user_id == user_id)
            )
            db_fio = result.scalar_one_or_none()
            if db_fio:
                if user_data.first_name:
                    db_fio.first_name = user_data.first_name
                if user_data.last_name:
                    db_fio.last_name = user_data.last_name
                if user_data.username:
                    db_fio.patronymic_name = user_data.username
            
            await db.commit()
            await db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    async def update_user_status(db: AsyncSession, user_id: int, status_data: UserStatusUpdate) -> Optional[UserStatus]:
        result = await db.execute(
            select(UserStatus)
            .where(UserStatus.user_id == user_id)
        )
        db_status = result.scalar_one_or_none()
        
        if db_status:
            for key, value in status_data.dict(exclude_unset=True).items():
                setattr(db_status, key, value)
            
            await db.commit()
            await db.refresh(db_status)
        
        return db_status
    
    @staticmethod
    async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.status))
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