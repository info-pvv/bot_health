# app/models/user.py - обновленная версия
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    username = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_duty_eligible = Column(Boolean, default=False)  # НОВОЕ ПОЛЕ

    # Relationships
    status_info = relationship(
        "UserStatus", back_populates="user", uselist=False, lazy="selectin"
    )
    fio_info = relationship(
        "FIO", back_populates="user", uselist=False, lazy="selectin"
    )
    health_info = relationship(
        "Health", back_populates="user", uselist=False, lazy="selectin"
    )
    disease_info = relationship(
        "Disease", back_populates="user", uselist=False, lazy="selectin"
    )


class UserStatus(Base):
    __tablename__ = "id_status"

    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True, index=True
    )
    enable_report = Column(Boolean, default=True)
    enable_admin = Column(Boolean, default=False)
    sector_id = Column(BigInteger)

    # Relationship
    user = relationship("User", back_populates="status_info", lazy="selectin")


class FIO(Base):
    __tablename__ = "fio"

    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True, index=True
    )
    first_name = Column(String(100))
    last_name = Column(String(100))
    patronymic_name = Column(String(100))

    # Relationship
    user = relationship("User", back_populates="fio_info", lazy="selectin")


class Health(Base):
    __tablename__ = "health"

    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True, index=True
    )
    status = Column(String(50))

    # Relationship
    user = relationship("User", back_populates="health_info", lazy="selectin")


class Disease(Base):
    __tablename__ = "disease"

    user_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True, index=True
    )
    disease = Column(String(100))

    # Relationship
    user = relationship("User", back_populates="disease_info", lazy="selectin")


class Sector(Base):
    __tablename__ = "sectors"

    sector_id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255))
