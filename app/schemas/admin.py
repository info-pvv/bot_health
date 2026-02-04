# app/schemas/admin.py
from pydantic import BaseModel
from typing import Optional

class AdminUpdate(BaseModel):
    enable_report: Optional[bool] = None
    enable_admin: Optional[bool] = None