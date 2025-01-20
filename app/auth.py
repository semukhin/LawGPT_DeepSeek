from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import timedelta, datetime
from jose import jwt, JWTError
from random import randint
from app import mail_utils, models, schemas, database, config
from app.schemas import CodeVerificationRequest
from app.config import SECRET_KEY, ALGORITHM
from pydantic import BaseModel, EmailStr
from app.mail_utils import send_verification_email
from app.models import TempUser
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from random import randint
from app import models, database, mail_utils
from app.schemas import PasswordResetRequest, PasswordResetConfirm
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

# Настройки JWT
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

# Схема OAuth2 для аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

temp_user_data = {}  # Временное хранилище для данных пользователей

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
) -> models.User:
    """Получает текущего пользователя из JWT токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register")
async def register_user(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    existing_temp_user = db.query(models.TempUser).filter(models.TempUser.email == user.email).first()
    if existing_temp_user:
        raise HTTPException(status_code=400, detail="Пользователь уже проходит регистрацию")

    # Генерация кода верификации
    code = randint(100000, 999999)

    # Сохраняем данные пользователя в таблице TempUser
    temp_user = models.TempUser(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        code=code,
    )
    db.add(temp_user)
    db.commit()  # Убедитесь, что commit вызывается

    # Отправляем код подтверждения на почту
    background_tasks.add_task(mail_utils.send_verification_email, user.email, code)

    # Создание временного JWT токена
    temp_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=15)
    )

    return {
        "message": "Код подтверждения отправлен на вашу почту",
        "temp_token": temp_token
    }

@router.post("/verify")
async def verify_code(
    request: schemas.VerifyRequest,  # Используйте схему для тела запроса
    token: str = Depends(config.oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    """Верификация кода из почты."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Неавторизован")
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    # Получаем временного пользователя
    temp_user = db.query(models.TempUser).filter(models.TempUser.email == email).first()
    if not temp_user:
        raise HTTPException(status_code=404, detail="Регистрация не найдена или истекла")

    # Проверяем код подтверждения
    if temp_user.code != request.code:
        raise HTTPException(status_code=400, detail="Неверный код подтверждения")

    # Создаем запись пользователя в основной таблице
    db_user = models.User(
        email=temp_user.email,
        hashed_password=temp_user.hashed_password,
        first_name=temp_user.first_name,
        last_name=temp_user.last_name,
        is_verified=True
    )
    db.add(db_user)
    db.commit()

    # Удаляем запись из TempUser
    db.delete(temp_user)
    db.commit()

    # Генерация JWT токена
    access_token = create_access_token(data={"sub": db_user.email, "user_id": db_user.id})

    return {
        "message": "Пользователь успешно зарегистрирован",
        "access_token": access_token,
        "token_type": "bearer"
    }

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
    current_user: models.User = Depends(get_current_user)
):
    """Получение профиля текущего пользователя."""
    return current_user

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    """Запрос на восстановление пароля."""
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь с таким email не найден")

    # Генерация кода восстановления
    reset_code = randint(100000, 999999)
    password_reset = models.PasswordReset(email=request.email, code=reset_code)
    db.add(password_reset)
    db.commit()

    # Отправка кода на email
    background_tasks.add_task(mail_utils.send_verification_email, request.email, reset_code)

    return {"message": "Код восстановления отправлен на вашу почту"}

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(database.get_db)
):
    """Подтверждение кода и изменение пароля."""
    reset_entry = db.query(models.PasswordReset).filter(
        models.PasswordReset.email == request.email,
        models.PasswordReset.code == request.code,
        models.PasswordReset.is_used == False
    ).first()

    if not reset_entry:
        raise HTTPException(status_code=400, detail="Неверный или истёкший код восстановления")

    # Найти пользователя
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь с таким email не найден")

    # Изменить пароль пользователя
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    # Отметить код как использованный
    reset_entry.is_used = True
    db.commit()

    return {"message": "Пароль успешно изменён"}

@router.post("/logout")
async def logout():
    """Выход из системы."""
    # В FastAPI токены хранятся на клиенте, так что для "выхода" можно просто уведомить клиента.
    return {"message": "Выход успешно выполнен"}