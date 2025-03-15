FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libmagic-dev \
    build-essential \
    tesseract-ocr \
    wget \
    gnupg \
    default-libmysqlclient-dev \ 
    pkg-config \ 
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements первым слоем для кэширования
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir wheel setuptools \
    && pip install --no-cache-dir pymysql mysqlclient cryptography \
    && pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Устанавливаем зависимости playwright
RUN playwright install-deps && \
    playwright install chromium

# Открываем порт
EXPOSE 8000

# Запускаем приложение с логированием отладки
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
