# app/api/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.services.admin_service import AdminService
from app.schemas.admin import AdminUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

@router.put("/users/{user_id}/toggle-report")
async def toggle_user_report(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await AdminService.toggle_user_report(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User report status toggled"}

@router.put("/users/{user_id}/toggle-admin")
async def toggle_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    success = await AdminService.toggle_user_admin(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User admin status toggled"}