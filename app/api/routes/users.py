# app/api/routes/users.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.database import get_db
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserStatusUpdate
from app.schemas.health import HealthUpdate, DiseaseUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    users = await UserService.get_all_users(db, skip, limit)
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    chat_id: int,
    db: AsyncSession = Depends(get_db)
):
    existing_user = await UserService.get_user_by_id(db, user_data.user_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user = await UserService.create_user(db, user_data, chat_id)
    
    if not user:
        raise HTTPException(
            status_code=500, 
            detail="Failed to create user due to database sequence issue. Please contact administrator."
        )
    
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    user = await UserService.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await UserService.update_user_status(db, user_id, status_data)
    return await UserService.get_user_by_id(db, user_id)

@router.put("/{user_id}/health")
async def update_user_health(
    user_id: int,
    health_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус здоровья пользователя"""
    from app.services.user_service import UserService
    
    status = health_data.get("status")
    disease = health_data.get("disease")
    
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    # Обновляем статус здоровья
    health, updated_disease = await UserService.update_health_status(
        db, user_id, status, reset_disease=(status != "болен")
    )
    
    # Если статус "болен" и указано заболевание - обновляем
    if status == "болен" and disease:
        await UserService.update_disease(db, user_id, disease)
    
    # Возвращаем обновленного пользователя с деталями
    user_details = await UserService.get_user_with_details(db, user_id)
    if not user_details or not user_details.get("user"):
        raise HTTPException(status_code=404, detail="User not found")
    
    # Формируем ответ
    response = {
        "id": user_details["user"].id,
        "user_id": user_details["user"].user_id,
        "first_name": user_details["user"].first_name,
        "last_name": user_details["user"].last_name,
        "username": user_details["user"].username,
        "created_at": user_details["user"].created_at,
        "updated_at": user_details["user"].updated_at,
        "health_info": {
            "status": health.status if health else None
        },
        "disease_info": {
            "disease": user_details["disease"].disease if user_details.get("disease") else ""
        }
    }
    
    return response

@router.put("/{user_id}/health/status")
async def update_health_status_only(
    user_id: int,
    health_data: HealthUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить только статус здоровья"""
    from app.services.user_service import UserService
    
    if health_data.status:
        await UserService.update_health_status(db, user_id, health_data.status)
    
    updated_user = await UserService.get_user_by_id(db, user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

@router.put("/{user_id}/health/disease")
async def update_disease_only(
    user_id: int,
    disease_data: DiseaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить только заболевание"""
    from app.services.user_service import UserService
    
    if disease_data.disease:
        await UserService.update_disease(db, user_id, disease_data.disease)
    
    updated_user = await UserService.get_user_by_id(db, user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

@router.post("/register")
async def register_user(
    user_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Упрощенный эндпоинт для регистрации пользователя"""
    try:
        user_id = user_data.get("user_id")
        chat_id = user_data.get("chat_id")
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        username = user_data.get("username", "")
        
        if not all([user_id, chat_id, first_name, last_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Проверяем существование пользователя
        existing_user = await UserService.get_user_by_id(db, user_id)
        if existing_user:
            return {
                "status": "success", 
                "message": "User already exists",
                "user": existing_user
            }
        
        # Создаем пользователя через UserService
        user = await UserService.create_user(db, UserCreate(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username
        ), chat_id)
        
        if user:
            return {
                "status": "success",
                "message": "User created successfully",
                "user": user
            }
        else:
            # Если не удалось создать через ORM, используем raw SQL
            from sqlalchemy import text
            
            try:
                # Создаем связанные записи
                from app.models.user import FIO, UserStatus, Health, Disease, User
                
                db_fio = FIO(
                    user_id=user_id,
                    first_name=first_name,
                    last_name=last_name,
                    patronymic_name=username or ""
                )
                db.add(db_fio)
                
                db_status = UserStatus(
                    user_id=user_id,
                    enable_report=True,
                    enable_admin=False,
                    sector_id=chat_id
                )
                db.add(db_status)
                
                db_health = Health(user_id=user_id, status="")
                db.add(db_health)
                
                db_disease = Disease(user_id=user_id, disease="")
                db.add(db_disease)
                
                # Используем SQL для обхода проблемы с последовательностью
                await db.execute(
                    text("""
                        INSERT INTO users (user_id, first_name, last_name, username) 
                        VALUES (:user_id, :first_name, :last_name, :username)
                        ON CONFLICT (user_id) DO NOTHING
                    """),
                    {
                        "user_id": user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "username": username
                    }
                )
                
                await db.commit()
                
                # Получаем пользователя
                from sqlalchemy import select
                result = await db.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                return {
                    "status": "success",
                    "message": "User created via alternative method",
                    "user": user
                }
                
            except Exception as e:
                await db.rollback()
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

# ДОБАВЛЕННЫЙ ЭНДПОИНТ ДЛЯ ПОИСКА
@router.get("/search/")
async def search_users(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Поиск пользователей по имени, фамилии или username"""
    from sqlalchemy import or_, select
    from app.models.user import User, FIO
    
    # Создаем запрос с JOIN
    query = (
        select(User)
        .join(FIO, FIO.user_id == User.user_id)
        .where(
            or_(
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
                User.username.ilike(f"%{q}%"),
                FIO.first_name.ilike(f"%{q}%"),
                FIO.last_name.ilike(f"%{q}%")
            )
        )
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Форматируем ответ
    users_list = []
    for user in users:
        users_list.append({
            "id": user.id,
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        })
    
    return {"users": users_list, "total": len(users_list), "query": q}


@router.get("/admin/list")
async def get_users_for_admin(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить список пользователей для админ-панели с расширенной информацией"""
    from sqlalchemy import select
    from app.models.user import User, UserStatus, FIO, Health, Disease
    
    # Запрос с JOIN всех связанных таблиц
    query = (
        select(
            User.user_id,
            User.first_name,
            User.last_name,
            User.username,
            User.created_at,
            UserStatus.enable_report,
            UserStatus.enable_admin,
            UserStatus.sector_id,
            Health.status,
            Disease.disease
        )
        .select_from(User)
        .outerjoin(UserStatus, User.user_id == UserStatus.user_id)
        .outerjoin(FIO, User.user_id == FIO.user_id)
        .outerjoin(Health, User.user_id == Health.user_id)
        .outerjoin(Disease, User.user_id == Disease.user_id)
        .order_by(User.user_id)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    users_list = []
    for row in rows:
        users_list.append({
            "user_id": row[0],
            "first_name": row[1] or "Не указано",
            "last_name": row[2] or "Не указано",
            "username": row[3] or "Не указано",
            "created_at": row[4],
            "enable_report": row[5] if row[5] is not None else False,
            "enable_admin": row[6] if row[6] is not None else False,
            "sector_id": row[7],
            "status": row[8] or "не указан",
            "disease": row[9] or ""
        })
    
    return {
        "users": users_list,
        "total": len(users_list),
        "skip": skip,
        "limit": limit
    }