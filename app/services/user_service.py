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
    async def create_user(db: AsyncSession, user_data: UserCreate, chat_id: int) -> Optional[User]:
        """Создать пользователя или вернуть существующего"""
        # Проверяем, существует ли уже пользователь
        existing_user = await UserService.get_user_by_id(db, user_data.user_id)
        if existing_user:
            return existing_user
        
        try:
            # Простая попытка создать пользователя
            db_user = User(
                user_id=user_data.user_id,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                username=user_data.username
            )
            
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
                sector_id=chat_id
            )
            db.add(db_status)
            
            db_health = Health(user_id=user_data.user_id, status="")
            db.add(db_health)
            
            db_disease = Disease(user_id=user_data.user_id, disease="")
            db.add(db_disease)
            
            await db.commit()
            await db.refresh(db_user)
            return db_user
            
        except Exception as e:
            await db.rollback()
            print(f"Ошибка при создании пользователя: {e}")
            
            # Если ошибка связана с уникальностью ID, попробуем альтернативный подход
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                # Пробуем создать пользователя без указания ID (полагаясь на DEFAULT)
                try:
                    # Используем raw SQL чтобы обойти проблему с последовательностью
                    from sqlalchemy import text
                    
                    # Сначала создаем связанные записи
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
                        sector_id=chat_id
                    )
                    db.add(db_status)
                    
                    db_health = Health(user_id=user_data.user_id, status="")
                    db.add(db_health)
                    
                    db_disease = Disease(user_id=user_data.user_id, disease="")
                    db.add(db_disease)
                    
                    # Используем SQL для вставки пользователя
                    await db.execute(
                        text("""
                            INSERT INTO users (user_id, first_name, last_name, username) 
                            VALUES (:user_id, :first_name, :last_name, :username)
                            ON CONFLICT (user_id) DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            username = EXCLUDED.username
                            RETURNING *
                        """),
                        {
                            "user_id": user_data.user_id,
                            "first_name": user_data.first_name,
                            "last_name": user_data.last_name,
                            "username": user_data.username
                        }
                    )
                    
                    await db.commit()
                    
                    # Получаем созданного/обновленного пользователя
                    result = await db.execute(
                        select(User).where(User.user_id == user_data.user_id)
                    )
                    db_user = result.scalar_one_or_none()
                    
                    return db_user
                    
                except Exception as e2:
                    await db.rollback()
                    print(f"Альтернативный метод тоже не сработал: {e2}")
                    # Возвращаем None - это вызовет ошибку валидации
            
            # Если мы здесь, значит все попытки не удались
            return None
    
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
    async def update_health_status(db: AsyncSession, user_id: int, status: str, reset_disease: bool = False) -> tuple[Optional[Health], Optional[Disease]]:
        """Обновить статус здоровья и при необходимости сбросить заболевание"""
        # Обновляем статус здоровья
        health_result = await db.execute(
            select(Health).where(Health.user_id == user_id)
        )
        db_health = health_result.scalar_one_or_none()
        
        if db_health:
            db_health.status = status
        else:
            db_health = Health(user_id=user_id, status=status)
            db.add(db_health)
        
        # Сбрасываем заболевание если статус не "болен" или явно указано reset_disease
        db_disease = None
        if status != "болен" or reset_disease:
            disease_result = await db.execute(
                select(Disease).where(Disease.user_id == user_id)
            )
            db_disease = disease_result.scalar_one_or_none()
            
            if db_disease:
                db_disease.disease = ""  # Сбрасываем заболевание
                await db.commit()
            else:
                # Создаем пустую запись если её нет
                db_disease = Disease(user_id=user_id, disease="")
                db.add(db_disease)
        
        await db.commit()
        await db.refresh(db_health)
        if db_disease:
            await db.refresh(db_disease)
        
        return db_health, db_disease
    
    @staticmethod
    async def update_disease(db: AsyncSession, user_id: int, disease: str) -> Optional[Disease]:
        """Обновить заболевание (только для статуса "болен")"""
        # Сначала проверяем статус пользователя
        health_result = await db.execute(
            select(Health).where(Health.user_id == user_id)
        )
        db_health = health_result.scalar_one_or_none()
        
        # Если статус не "болен", не обновляем заболевание
        if db_health and db_health.status != "болен":
            return None
        
        # Обновляем заболевание
        disease_result = await db.execute(
            select(Disease).where(Disease.user_id == user_id)
        )
        db_disease = disease_result.scalar_one_or_none()
        
        if db_disease:
            db_disease.disease = disease
        else:
            db_disease = Disease(user_id=user_id, disease=disease)
            db.add(db_disease)
        
        await db.commit()
        await db.refresh(db_disease)
        return db_disease
    
    @staticmethod
    async def get_user_with_details(db: AsyncSession, user_id: int) -> dict:
        """Получить пользователя с расширенной информацией"""
        # Получаем пользователя
        user_result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Получаем статус
        status_result = await db.execute(
            select(UserStatus).where(UserStatus.user_id == user_id)
        )
        status = status_result.scalar_one_or_none()
        
        # Получаем ФИО
        fio_result = await db.execute(
            select(FIO).where(FIO.user_id == user_id)
        )
        fio = fio_result.scalar_one_or_none()
        
        # Получаем здоровье
        health_result = await db.execute(
            select(Health).where(Health.user_id == user_id)
        )
        health = health_result.scalar_one_or_none()
        
        # Получаем заболевание
        disease_result = await db.execute(
            select(Disease).where(Disease.user_id == user_id)
        )
        disease = disease_result.scalar_one_or_none()
        
        return {
            "user": user,
            "status": status,
            "fio": fio,
            "health": health,
            "disease": disease
        }
    
    @staticmethod
    async def get_user_sector_id(db: AsyncSession, user_id: int) -> Optional[int]:
        """Получить sector_id пользователя"""
        result = await db.execute(
            select(UserStatus.sector_id).where(UserStatus.user_id == user_id)
        )
        sector = result.scalar_one_or_none()
        return sector