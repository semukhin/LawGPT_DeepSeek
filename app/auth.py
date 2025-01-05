from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import timedelta, datetime
from jose import jwt, JWTError
from random import randint
from app import mail_utils, models, schemas, database, config
from app.schemas import VerificationRequest
from app.config import SECRET_KEY, ALGORITHM
from pydantic import BaseModel, EmailStr
import email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

# Настройки JWT
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register", response_model=schemas.UserOut)
async def register_user(
    user: schemas.UserCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(database.get_db)
):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        first_name=user.first_name, 
        last_name=user.last_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Генерация кода верификации
    code = randint(100000, 999999)
    verification_code = models.VerificationCode(user_id=db_user.id, code=code)
    db.add(verification_code)
    db.commit()

    # Создание JWT-токена
    access_token = create_access_token(data={"sub": db_user.email})

    # Отправка письма с кодом
    background_tasks.add_task(email.send_verification_email, db_user.email, code)

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify")
async def verify_code(
    code: int,
    token: str = Depends(config.oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    """Верификация кода из почты."""
    try:
        # Декодируем токен и получаем email
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Неавторизован")
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    # Получаем пользователя по email
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем код верификации
    verification_code = db.query(models.VerificationCode).filter(
        models.VerificationCode.user_id == user.id,
        models.VerificationCode.code == code,
        models.VerificationCode.is_used == False
    ).first()

    if not verification_code:
        raise HTTPException(status_code=400, detail="Неверный код верификации")

    # Помечаем код как использованный и обновляем статус пользователя
    verification_code.is_used = True
    user.is_verified = True
    db.commit()

    return {"message": "Пользователь успешно верифицирован"}



@router.post("/login")
async def login(user: schemas.UserLogin, db: Session = Depends(database.get_db)):
    """Авторизация пользователя."""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Пользователь не верифицирован")
    
    # Обновляем is_active
    db_user.is_active = True
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(data={"sub": db_user.email, "user_id": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/profile", response_model=schemas.UserOut)
async def get_profile(
    db: Session = Depends(database.get_db), 
    token: str = Depends(config.oauth2_scheme)
):
    """Получение профиля текущего пользователя по ID."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Неавторизован")
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return db_user

@router.post("/logout")
async def logout():
    """Выход из системы."""
    # В FastAPI токены хранятся на клиенте, так что для "выхода" можно просто уведомить клиента.
    return {"message": "Выход успешно выполнен"}
