# app/models/duty.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
from sqlalchemy.ext.hybrid import hybrid_property


class DutyAdminPool(Base):
    __tablename__ = "duty_admin_pool"

    pool_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    sector_id = Column(BigInteger, ForeignKey("sectors.sector_id"), nullable=False)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(BigInteger, ForeignKey("users.user_id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    sector = relationship("Sector", foreign_keys=[sector_id], lazy="selectin")
    added_by_user = relationship("User", foreign_keys=[added_by], lazy="selectin")

    @hybrid_property
    def user_name(self):
        """Получить имя пользователя"""
        if not self.user:
            return f"Пользователь {self.user_id}"

        # Здесь мы не можем сделать запрос к FIO, поэтому это поле будет заполняться в сервисе
        return getattr(self, "_user_name", f"Пользователь {self.user_id}")

    @user_name.setter
    def user_name(self, value):
        self._user_name = value

    @hybrid_property
    def sector_name(self):
        """Получить название сектора"""
        if self.sector and self.sector.name:
            return self.sector.name
        return getattr(self, "_sector_name", f"Сектор {self.sector_id}")

    @sector_name.setter
    def sector_name(self, value):
        self._sector_name = value


class DutySchedule(Base):
    __tablename__ = "duty_schedule"

    duty_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    sector_id = Column(BigInteger, ForeignKey("sectors.sector_id"), nullable=False)
    duty_date = Column(Date, nullable=False)
    week_start = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(BigInteger, ForeignKey("users.user_id"), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    sector = relationship("Sector", foreign_keys=[sector_id], lazy="selectin")
    created_by_user = relationship("User", foreign_keys=[created_by], lazy="selectin")


class DutyStatistics(Base):
    __tablename__ = "duty_statistics"

    stat_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    sector_id = Column(BigInteger, ForeignKey("sectors.sector_id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_duties = Column(Integer, default=0)
    last_duty_date = Column(Date, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    sector = relationship("Sector", foreign_keys=[sector_id], lazy="selectin")
