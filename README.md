# LawGPT на базе DeepSeek API

Юридический ассистент, использующий DeepSeek API для обработки запросов и исследования юридических вопросов. Проект имеет поддержку доступа к внешним базам данных законодательства.

## Особенности

- Интеграция с DeepSeek API для обработки запросов
- Полноценная поддержка функциональных вызовов (Function Calling)
- Многораундовые диалоги с сохранением контекста
- Поддержка загрузки и анализа документов (DOCX, PDF)
- Поиск в базе российского законодательства через Elasticsearch
- Поиск в базе Гарант
- Веб-поиск для актуальной информации
- Глубокий анализ текстов и документов

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/lawgpt.git
cd lawgpt
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv env
# Для Windows
env\Scripts\activate
# Для Linux/Mac
source env/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе файла `.env.example`:
```bash
cp .env.example .env
```

5. Отредактируйте файл `.env` и установите ваш DeepSeek API ключ:
```
DEEPSEEK_API_KEY=your_deepseek_api_key
```

## Настройка

В файле `.env` можно настроить различные параметры:

- `DEEPSEEK_API_KEY` - ваш API ключ DeepSeek
- `DEEPSEEK_API_BASE` - базовый URL API (по умолчанию https://api.deepseek.com/v1)
- `DEEPSEEK_MODEL` - модель DeepSeek для использования
- `DATABASE_URL` - URL для подключения к базе данных

## Запуск

Запустите сервер с помощью uvicorn:

```bash
uvicorn main:app --reload
```

Сервер будет доступен по адресу `http://127.0.0.1:8000`.

## Тестирование DeepSeek API

Для тестирования функциональности DeepSeek API можно использовать скрипт `test_deepseek.py`:

```bash
python test_deepseek.py
```

Скрипт выполнит тесты на:
- Простую генерацию текста
- Многораундовые диалоги
- Function calling

## API Endpoints

### Аутентификация
- `POST /register` - Регистрация нового пользователя
- `POST /verify` - Верификация кода из письма
- `POST /login` - Вход в систему
- `GET /profile` - Получение профиля текущего пользователя
- `POST /forgot-password` - Запрос на восстановление пароля
- `POST /reset-password` - Изменение пароля

### Чат
- `POST /chat/{thread_id}` - Отправка сообщения в тред
- `POST /create_thread` - Создание нового треда
- `GET /chat/threads` - Получение списка тредов пользователя
- `GET /messages/{thread_id}` - Получение сообщений из треда

### Файлы
- `POST /upload_file` - Загрузка файла
- `GET /download/{filename}` - Скачивание документа

## Интеграция с DeepSeek API

Проект интегрирован с DeepSeek API для обработки запросов. Интеграция реализована через класс `DeepSeekService` в файле `app/services/deepseek_service.py`. 

Основные методы:
- `chat_completion()` - Отправка запроса к DeepSeek Chat API
- `generate_text()` - Генерация текста на основе промпта
- `generate_with_system()` - Генерация текста с системным и пользовательским промптами
- `chat_with_functions()` - Специализированный метод для работы с функциональными вызовами

## Function Calling

Система поддерживает следующие функции:
- `search_law_chunks` - Поиск в базе российского законодательства
- `search_garant` - Поиск в базе Гарант
- `search_web` - Поиск в интернете
- `deep_research` - Проведение глубокого исследования

Каждая функция имеет описание, параметры и реализацию в модуле `app/handlers/ai_request.py`.

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add some amazing feature'`)
4. Отправьте изменения в ваш форк (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## Лицензия

Распространяется под лицензией MIT. См. файл `LICENSE` для получения дополнительной информации.