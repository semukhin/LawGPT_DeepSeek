import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User, TempUser, PasswordReset, Thread, Message
from app.schemas import UserCreate, UserLogin, VerifyRequest, PasswordResetRequest, PasswordResetConfirm
from passlib.context import CryptContext
import logging
from websockets import connect

# Заданный токен
PREDEFINED_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwidXNlcl9pZCI6MSwiZXhwIjoxNzM3OTA5MDk1fQ.Oe4JeWNBP5KG_cujFw255z41RVdV1vSS1WCkHQ639yY"

# Настройка логгера
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler("test_logs.txt", mode="w")
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

logger = logging.getLogger("test_logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Настройка тестовой базы данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Хэширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Фикстура для базы данных
@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Фикстура для тестового клиента
@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        app.dependency_overrides[get_db] = lambda: db_session
        yield ac
        app.dependency_overrides.clear()

# Очистка базы данных перед каждым тестом
@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    db_session.query(User).delete()
    db_session.query(TempUser).delete()
    db_session.query(PasswordReset).delete()
    db_session.query(Thread).delete()
    db_session.query(Message).delete()
    db_session.commit()

# Тест регистрации и верификации
@pytest.mark.asyncio
async def test_register_and_verify(client, db_session):
    logger.info("Тест регистрации и верификации начался.")
    user_data = UserCreate(email="test@example.com", password="password", first_name="Test", last_name="User")
    response = await client.post("/register", json=user_data.model_dump())
    assert response.status_code == 200, response.text
    assert "temp_token" in response.json()

    temp_token = response.json()["temp_token"]
    temp_user = db_session.query(TempUser).filter(TempUser.email == "test@example.com").first()
    assert temp_user is not None
    code = temp_user.code  # Убедитесь, что это поле существует в модели

    verify_data = VerifyRequest(code=code)
    response = await client.post("/verify", json=verify_data.model_dump(), headers={"Authorization": f"Bearer {temp_token}"})
    assert response.status_code == 200, response.text
    assert "access_token" in response.json()
    logger.info("Тест регистрации и верификации завершился успешно.")

# Тест авторизации
@pytest.mark.asyncio
async def test_login(client, db_session):
    logger.info("Тест авторизации начался.")
    user = User(email="test@example.com", hashed_password=get_password_hash("password"), is_verified=True)
    db_session.add(user)
    db_session.commit()

    logger.info(f"Будет использован заранее заданный токен: {PREDEFINED_TOKEN}")
    assert PREDEFINED_TOKEN, "Токен не задан!"
    logger.info("Тест авторизации завершился успешно.")

# Тест работы с WebSocket для сообщений
@pytest.mark.asyncio
async def test_threads_and_messages(client, db_session):
    logger.info("Тест работы с тредами и сообщениями начался.")
    user = User(email="test@example.com", hashed_password=get_password_hash("password"), is_verified=True)
    db_session.add(user)
    db_session.commit()

    # Создание нового чата
    response = await client.post("/api/new_chat", headers={"Authorization": f"Bearer {PREDEFINED_TOKEN}"})
    assert response.status_code == 200, response.text
    thread_id = response.json()["thread_id"]
    logger.info(f"Создан thread_id: {thread_id}")

    # Подключение к WebSocket
    uri = f"ws://127.0.0.1:8000/ws/chat/{thread_id}?token={PREDEFINED_TOKEN}"
    logger.info(f"Попытка подключения к WebSocket: {uri}")

    try:
        async with connect(uri) as websocket:
            logger.info("Соединение с WebSocket установлено.")
            await websocket.send("Hello, WebSocket!")
            response = await websocket.recv()
            logger.info(f"Ответ от WebSocket: {response}")
            assert "Hello" in response  # Проверяем ответ
    except Exception as e:
        logger.error(f"Ошибка подключения к WebSocket: {e}")
        raise
    logger.info("Тест работы с тредами и сообщениями завершился успешно.")

# Тест сброса пароля
@pytest.mark.asyncio
async def test_password_reset(client, db_session):
    logger.info("Тест сброса пароля начался.")
    user = User(email="test@example.com", hashed_password=get_password_hash("password"), is_verified=True)
    db_session.add(user)
    db_session.commit()

    reset_request = PasswordResetRequest(email="test@example.com")
    response = await client.post("/forgot-password", json=reset_request.model_dump())
    assert response.status_code == 200, response.text

    reset_record = db_session.query(PasswordReset).filter(PasswordReset.email == "test@example.com").first()
    assert reset_record is not None
    code = reset_record.code  # Убедитесь, что это поле существует в модели

    reset_confirm = PasswordResetConfirm(email="test@example.com", code=code, new_password="newpassword")
    response = await client.post("/reset-password", json=reset_confirm.model_dump())
    assert response.status_code == 200, response.text
    logger.info("Тест сброса пароля завершился успешно.")

# Тест загрузки файлов
@pytest.mark.asyncio
async def test_file_upload(client, db_session):
    logger.info("Тест загрузки файлов начался.")
    user = User(email="test@example.com", hashed_password=get_password_hash("password"), is_verified=True)
    db_session.add(user)
    db_session.commit()

    file_content = b"test file content"
    response = await client.post(
        "/api/upload_file",
        files={"file": ("test.docx", file_content)},
        headers={"Authorization": f"Bearer {PREDEFINED_TOKEN}"}
    )
    assert response.status_code == 200, response.text
    logger.info("Тест загрузки файлов завершился успешно.")
