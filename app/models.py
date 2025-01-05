from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)  # Указываем длину
    hashed_password = Column(String(255))  # Указываем длину
    first_name = Column(String(100))  # Указываем длину
    last_name = Column(String(100))  # Указываем длину
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
