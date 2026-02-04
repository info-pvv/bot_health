# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.models.database import Base

class User(Base):
    __tablename__ = "users"
    
    # В PostgreSQL лучше использовать BIGINT для больших чисел
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)  # Telegram ID может быть большим
    first_name = Column(String(100))
    last_name = Column(String(100))
    username = Column(String(100))
    
    # Добавляем timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserStatus(Base):
    __tablename__ = "id_status"
    
    #id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, primary_key=True, index=True)
    enable_report = Column(Boolean, default=True)
    enable_admin = Column(Boolean, default=False)
    sector = Column(BigInteger)

class FIO(Base):
    __tablename__ = "fio"
    
    #id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, primary_key=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    patronymic_name = Column(String(100))

class Health(Base):
    __tablename__ = "health"
    
    #id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, primary_key=True, index=True)
    status = Column(String(50))
    
    
class Disease(Base):
    __tablename__ = "disease"
    
    #id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, primary_key=True, index=True)
    disease = Column(String(100))