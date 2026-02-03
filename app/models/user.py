from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import relationship
from app.models.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String)
    
    status = relationship("UserStatus", back_populates="user", uselist=False)
    health = relationship("Health", back_populates="user", uselist=False)
    disease = relationship("Disease", back_populates="user", uselist=False)
    fio = relationship("FIO", back_populates="user", uselist=False)

class UserStatus(Base):
    __tablename__ = "id_status"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    enable_report = Column(Boolean, default=True)
    enable_admin = Column(Boolean, default=False)
    sector = Column(BigInteger)
    
    user = relationship("User", back_populates="status")

class FIO(Base):
    __tablename__ = "fio"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    patronymic_name = Column(String)
    
    user = relationship("User", back_populates="fio")

class Health(Base):
    __tablename__ = "health"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    status = Column(String)
    
    user = relationship("User", back_populates="health")

class Disease(Base):
    __tablename__ = "disease"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    disease = Column(String)
    
    user = relationship("User", back_populates="disease")