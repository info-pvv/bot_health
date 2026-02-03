from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.database import get_db
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserStatusUpdate

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