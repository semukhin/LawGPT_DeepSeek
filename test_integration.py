import pytest
from fastapi.testclient import TestClient
from app.main import app  # Импортируйте ваше FastAPI-приложение
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, Thread, Message
from app.auth import create_access_token

# Настройка тестовой базы данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц в тестовой базе данных
Base.metadata.create_all(bind=engine)

# Фикстура для тестовой сессии базы данных
@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Фикстура для тестового клиента
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

# Фикстура для создания тестового пользователя
@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        email="test@example.com",
        hashed_password="123",  # В реальном тесте используйте хэшированный пароль
        first_name="Test",
        last_name="User",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user

# Фикстура для создания тестового токена
@pytest.fixture(scope="function")
def test_token(test_user):
    return create_access_token(data={"sub": test_user.email, "user_id": test_user.id})

def test_full_chat_flow(client, test_user, test_token):
    # Шаг 1: Регистрация пользователя (уже выполнена в фикстуре test_user)

    # Шаг 2: Создание нового чата
    response = client.post(
        "/api/new_chat",
        headers={"Authorization": f"Bearer {test_token}"},
    )
    assert response.status_code == 200
    thread_id = response.json()["thread_id"]
    assert thread_id is not None

    # Шаг 3: Подключение к WebSocket и обмен сообщениями
    with client.websocket_connect(f"/ws/chat/{thread_id}?token={test_token}") as websocket:
        # Отправляем сообщение от пользователя
        websocket.send_text("Как физлицу вернуть товар продавцу по причине брака?")

        # Получаем ответ от ассистента
        response = websocket.receive_text()
        assert response.strip() != ""  # Проверяем, что ответ не пустой

    # Шаг 4: Проверка истории сообщений
    response = client.get(
        f"/api/thread/{thread_id}/messages",
        headers={"Authorization": f"Bearer {test_token}"},
    )
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 2  # Должно быть два сообщения: от пользователя и от ассистента
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Как физлицу вернуть товар продавцу по причине брака?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"].strip() != ""  # Проверяем, что ответ ассистента не пустой

# Очистка базы данных после каждого теста
@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    yield
    db_session.query(Message).delete()
    db_session.query(Thread).delete()
    db_session.query(User).delete()
    db_session.commit()