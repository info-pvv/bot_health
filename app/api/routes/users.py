# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List  # Добавьте импорт
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
    
    return await UserService.create_user(db, user_data, chat_id)

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
    health_update: dict,  # Принимаем словарь напрямую для гибкости
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус здоровья и заболевание пользователя"""
    from app.services.user_service import UserService
    
    # Получаем данные из запроса
    status = health_update.get("status")
    disease = health_update.get("disease")
    
    # Обновляем статус здоровья
    if status:
        await UserService.update_health_status(db, user_id, status)
    
    # Обновляем заболевание
    if disease:
        await UserService.update_disease(db, user_id, disease)
    
    # Возвращаем обновленного пользователя
    updated_user = await UserService.get_user_by_id(db, user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

# Альтернативно можно создать отдельные эндпоинты:
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