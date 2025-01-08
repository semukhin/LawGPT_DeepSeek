from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from app.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="verification_code")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    verification_code = relationship("VerificationCode", back_populates="user", uselist=False)

class TempUser(Base):
    __tablename__ = "temp_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)  # Длина 255 для email
    hashed_password = Column(String(255), nullable=False)  # Длина 255 для хэша пароля
    first_name = Column(String(50), nullable=False)  # Длина 50 для имени
    last_name = Column(String(50), nullable=False)  # Длина 50 для фамилии
    code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=False, index=True)
    code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)