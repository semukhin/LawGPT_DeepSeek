# LawGPT API

API-сервис для юридического ассистента с возможностью глубокого поиска по законодательству, судебным решениям и правовым ресурсам.

## Обзор проекта

LawGPT API - это бэкенд для юридического ассистента, который предоставляет следующие возможности:

- **Диалоговый интерфейс**: Многораундовые диалоги с сохранением контекста
- **Глубокий поиск**: Интеграция с Elasticsearch для поиска в законодательстве
- **Веб-поиск**: Получение актуальной информации из интернета
- **Обработка документов**: Анализ загруженных документов (DOCX, PDF)
- **Аутентификация**: Регистрация, авторизация, верификация по email
- **DeepResearch**: Глубокий анализ правовой информации

## Архитектура системы

Система построена на основе FastAPI и использует следующие ключевые компоненты:

- **FastAPI**: Веб-фреймворк для API
- **SQLAlchemy**: ORM для работы с базой данных
- **Elasticsearch**: Хранение и поиск по юридическим документам
- **DeepSeek API**: Генерация ответов с помощью LLM
- **Shandu**: Компонент для глубокого поиска и скрапинга веб-ресурсов

## Установка и запуск

### Требования

- Python 3.9+
- Elasticsearch 8.x
- MySQL/PostgreSQL (опционально)
- Доступ к DeepSeek API

### Установка зависимостей

У проекта есть несколько вариантов управления зависимостями:

#### Через pip:

```bash
pip install -r requirements.txt
```

#### Через Pipenv:

```bash
pipenv install
```

#### Через Poetry:

```bash
poetry install
```

### Настройка окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```
# Основные настройки
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./lawgpt.db
# или DATABASE_URL=mysql+pymysql://user:password@host:port/dbname

# DeepSeek API
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-reasoner

# Elasticsearch 
ELASTICSEARCH_URL=http://localhost:9200

# Почтовые настройки
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=noreply@example.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False

# Google Search (опционально) 
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CX=your-google-cx
```

### Запуск

#### Базовый запуск
```bash
uvicorn main:app --reload
```

#### Запуск с указанием хоста и порта
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Запуск через Pipenv
```bash
pipenv run uvicorn main:app --reload
```

#### Запуск через Poetry
```bash
poetry run uvicorn main:app --reload
```

Сервер будет доступен по адресу: `http://127.0.0.1:8000`

### Миграции базы данных

Проект использует Alembic для управления миграциями базы данных:

```bash
# Создание новой миграции
alembic revision --autogenerate -m "название миграции"

# Выполнение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

## Структура проекта

```
├── alembic/                  # Миграции базы данных
│   ├── versions/             # Версии миграций
│   ├── env.py                # Окружение для миграций
│   └── script.py.mako        # Шаблон скрипта миграции
├── alembic.ini               # Конфигурация Alembic
├── app/                      # Основной код приложения
│   ├── __init__.py
│   ├── config.py             # Конфигурация и настройки
│   ├── database.py           # Настройка подключения к БД
│   ├── models.py             # SQLAlchemy модели
│   ├── schemas.py            # Pydantic схемы
│   ├── auth.py               # Аутентификация и авторизация
│   ├── chat.py               # Обработка диалогов
│   ├── mail_utils.py         # Отправка почты
│   ├── context_manager.py    # Управление контекстом сообщений
│   ├── utils.py              # Вспомогательные функции
│   └── handlers/             # Обработчики различных запросов
│       ├── ai_request.py     # Обработка запросов к DeepSeek API
│       ├── deepresearch.py   # Интерфейс к DeepResearch
│       ├── deepresearch_audit.py # Аудит использования DeepResearch
│       ├── es_law_search.py  # Поиск в Elasticsearch
│       ├── parallel_search.py # Параллельный поиск в разных источниках
│       ├── web_search.py     # Поиск в интернете
│       └── user_doc_request.py # Обработка документов пользователя
│   └── services/             # Сервисные компоненты
│       ├── deepresearch_service.py # Сервис DeepResearch
│       ├── deepseek_service.py    # Сервис DeepSeek API
│       └── research_factory.py    # Фабрика исследовательских сервисов
├── deepresearch_audit/       # Каталог аудита DeepResearch
│   └── usage_stats.json      # Статистика использования
├── documents_docx/           # Каталог для docx документов
├── documents_html/           # Каталог для html документов
├── research_results/         # Результаты исследований
├── scripts/                  # Скрипты для обслуживания системы
│   ├── check_deepresearch.py  # Проверка DeepResearch
│   └── init_deepresearch_stats.py # Инициализация статистики
├── static/                   # Статические файлы
├── third_party/              # Сторонние компоненты
│   └── shandu/               # Система глубокого исследования
│       ├── agents/           # Агенты для исследования
│       │   ├── agent.py      # Реализация агента
│       │   ├── __init__.py
│       │   └── langgraph_agent.py # Агент на основе LangGraph
│       ├── research/         # Компоненты исследования
│       │   ├── __init__.py
│       │   └── researcher.py # Реализация исследователя
│       ├── search/           # Поисковые компоненты
│       │   ├── ai_search.py  # Поиск на основе AI
│       │   ├── __init__.py
│       │   └── search.py     # Основной поисковый модуль
│       ├── scraper/          # Компоненты для скрапинга
│       │   ├── __init__.py
│       │   └── scraper.py    # Веб-скрапер
│       ├── cli.py            # Интерфейс командной строки
│       ├── config.py         # Конфигурация Shandu
│       ├── __init__.py
│       ├── LICENSE           # Лицензия компонента
│       ├── MANIFEST.in       # Manifest для установки
│       ├── README.md         # Документация компонента
│       └── requirements.txt  # Зависимости компонента
├── uploads/                  # Загруженные пользователем файлы
├── law_gpt_frontend.html     # Пример фронтенда
├── main.py                   # Точка входа приложения
├── custom_requirements.txt   # Дополнительные зависимости
├── requirements.txt          # Основные зависимости проекта
├── Pipfile                   # Файл Pipenv
├── Pipfile.lock              # Lock-файл Pipenv
├── pyproject.toml            # Конфигурация Poetry
└── poetry.lock               # Lock-файл Poetry
```

## API Endpoints

### Аутентификация

- `POST /register` - Регистрация нового пользователя
- `POST /verify` - Подтверждение аккаунта по коду
- `POST /login` - Авторизация пользователя
- `GET /profile` - Получение профиля пользователя
- `POST /forgot-password` - Запрос на восстановление пароля
- `POST /reset-password` - Сброс пароля
- `POST /logout` - Выход из системы

### Чат

- `POST /create_thread` - Создание нового треда
- `POST /chat/{thread_id}` - Отправка сообщения в тред
- `GET /chat/threads` - Получение списка тредов
- `GET /messages/{thread_id}` - Получение сообщений треда

### Файлы

- `POST /upload_file` - Загрузка файла
- `GET /download/{filename}` - Скачивание файла

### Исследования

- `GET /deep_research` - Глубокое исследование по запросу

## Основные компоненты

### DeepResearch

Модуль для глубокого анализа юридической информации. Использует:

1. Elasticsearch для поиска в законодательстве
2. Веб-поиск для получения актуальной информации
3. DeepSeek API для аналитики и генерации ответов

### ScrapedContent и WebScraper

Компоненты для эффективного извлечения контента из веб-страниц с кэшированием и обработкой ошибок.

### ContextManager

Управление контекстом диалога с учетом ограничений на количество токенов.

### Handlers

Различные обработчики для поиска информации в разных источниках (Elasticsearch, веб, Гарант и т.д.)

## Оптимизации и особенности

1. **Таймауты**: Установлены оптимальные таймауты (120 секунд) для предотвращения зависания запросов
2. **Кэширование**: Результаты скрапинга и поиска кэшируются для ускорения работы
3. **Параллельные запросы**: Поиск выполняется параллельно в разных источниках
4. **Обработка кодировок**: Корректная обработка различных кодировок при скрапинге
5. **Валидация номеров судебных дел**: Проверка и нормализация номеров дел для точности ответов

## Масштабирование и доработка

1. **Горизонтальное масштабирование**: Добавление поддержки нескольких экземпляров через Docker/Docker Compose
2. **Новые источники данных**: Возможность добавления новых источников через интерфейс в `handlers/`
3. **Расширение системы хранения**: Добавление векторного поиска для семантического поиска
4. **Увеличение эффективности**: Оптимизация работы с памятью и процессором
5. **Фронтенд**: Разработка полноценного фронтенда на основе `law_gpt_frontend.html`
6. **Поддержка новых форматов документов**: Расширение возможностей обработки других форматов файлов

## Интеграция с внешними системами

1. **DeepSeek API**: Используется для генерации ответов и анализа контента через `services/deepseek_service.py`
2. **Google API**: Опциональная интеграция для расширенного поиска в интернете
3. **Email-сервисы**: Для отправки уведомлений и верификации через `mail_utils.py`
4. **Elasticsearch**: Для поиска по юридическим документам через `handlers/es_law_search.py`

## Мониторинг и аудит

Система включает компоненты для:

1. Логирования всех действий в структурированном формате
2. Измерения времени выполнения функций (через декоратор `measure_time`)
3. Отслеживания использования DeepResearch через модуль `deepresearch_audit`
4. Сбора статистики в `deepresearch_audit/usage_stats.json`
5. Управления статистикой через скрипты в директории `scripts/`

## Скрипты и утилиты

В директории `scripts/` находятся вспомогательные скрипты:

1. **check_deepresearch.py** - Проверка работы DeepResearch
2. **init_deepresearch_stats.py** - Инициализация статистики использования

Пример запуска:

```bash
python scripts/check_deepresearch.py
```

## Лицензия

Этот проект лицензируется под MIT License - см. файл LICENSE для деталей.