#!/usr/bin/env python
"""
Скрипт для настройки интеграции между LawGPT и Vexa.ai
Включает создание необходимых таблиц в БД и настройку подключения к API Vexa
"""
import os
import sys
import argparse
import requests
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Загрузка переменных окружения
load_dotenv()

# Определение аргументов командной строки
parser = argparse.ArgumentParser(description='Настройка интеграции LawGPT с Vexa.ai')
parser.add_argument('--check-only', action='store_true', help='Только проверить соединение с API Vexa')
parser.add_argument('--setup-db', action='store_true', help='Настроить базу данных для интеграции')
parser.add_argument('--vexa-api-key', type=str, help='API ключ для Vexa.ai')
parser.add_argument('--vexa-stream-url', type=str, help='URL для Vexa StreamQueue API')
parser.add_argument('--vexa-engine-url', type=str, help='URL для Vexa Engine API')
args = parser.parse_args()

# Настройка подключения к базе данных LawGPT
DB_URL = os.getenv("DATABASE_URL", "mysql+pymysql://gen_user:63%29%240oJ%5CWRP%5C%24J@194.87.243.188:3306/default_db")

# Настройка подключения к API Vexa
VEXA_API_KEY = args.vexa_api_key or os.getenv("VEXA_API_KEY")
VEXA_STREAM_URL = args.vexa_stream_url or os.getenv("VEXA_STREAM_URL", "https://streamqueue.dev.vexa.ai")
VEXA_ENGINE_URL = args.vexa_engine_url or os.getenv("VEXA_ENGINE_URL", "https://engine.dev.vexa.ai")
VEXA_TRANSCRIPTION_URL = os.getenv("VEXA_TRANSCRIPTION_URL", "https://transcription.dev.vexa.ai")

def check_vexa_api_connection():
    """Проверка соединения с API Vexa"""
    print("Проверка соединения с API Vexa...")
    
    # Проверка API Stream Queue
    try:
        response = requests.get(
            f"{VEXA_STREAM_URL}/api/v1/extension/check-token", 
            headers={"Authorization": f"Bearer {VEXA_API_KEY}"}
        )
        if response.ok:
            print(f"✅ Успешное подключение к Vexa StreamQueue API: {VEXA_STREAM_URL}")
        else:
            print(f"❌ Ошибка при подключении к Vexa StreamQueue API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при подключении к Vexa StreamQueue API: {str(e)}")
        return False
    
    # Проверка API Engine
    try:
        response = requests.get(
            f"{VEXA_ENGINE_URL}/api/health", 
            headers={"Authorization": f"Bearer {VEXA_API_KEY}"}
        )
        if response.ok:
            print(f"✅ Успешное подключение к Vexa Engine API: {VEXA_ENGINE_URL}")
        else:
            print(f"❌ Ошибка при подключении к Vexa Engine API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при подключении к Vexa Engine API: {str(e)}")
        return False
    
    # Проверка API Transcription
    try:
        response = requests.get(
            f"{VEXA_TRANSCRIPTION_URL}/health", 
            headers={"Authorization": f"Bearer {VEXA_API_KEY}"}
        )
        if response.ok:
            print(f"✅ Успешное подключение к Vexa Transcription API: {VEXA_TRANSCRIPTION_URL}")
        else:
            print(f"❌ Ошибка при подключении к Vexa Transcription API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при подключении к Vexa Transcription API: {str(e)}")
        return False
    
    return True

def setup_database():
    """Настройка БД для интеграции с Vexa"""
    print("Настройка базы данных для интеграции с Vexa...")
    
    try:
        engine = create_engine(DB_URL)
        Base = declarative_base()
        metadata = MetaData()
        
        # Определение новых таблиц для интеграции с Vexa
        
        # Таблица для хранения встреч
        class Meeting(Base):
            __tablename__ = 'vexa_meetings'
            
            id = Column(Integer, primary_key=True)
            vexa_meeting_id = Column(String(100), nullable=False, unique=True, index=True)
            user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
            title = Column(String(255), nullable=True)
            start_time = Column(DateTime, nullable=False)
            end_time = Column(DateTime, nullable=True)
            status = Column(String(50), nullable=False, default="active")
            source_type = Column(String(50), nullable=False)  # google_meet, zoom, etc.
            connection_id = Column(String(100), nullable=False)
            metadata = Column(Text, nullable=True)  # JSON с дополнительными метаданными
            
        # Таблица для хранения транскриптов
        class Transcript(Base):
            __tablename__ = 'vexa_transcripts'
            
            id = Column(Integer, primary_key=True)
            meeting_id = Column(Integer, ForeignKey("vexa_meetings.id"), nullable=False)
            vexa_transcript_id = Column(String(100), nullable=False)
            speaker = Column(String(255), nullable=True)
            start_time = Column(DateTime, nullable=False)
            end_time = Column(DateTime, nullable=True)
            text = Column(Text, nullable=False)
            confidence = Column(Integer, nullable=True)
        
        # Таблица для хранения саммари встреч
        class MeetingSummary(Base):
            __tablename__ = 'vexa_meeting_summaries'
            
            id = Column(Integer, primary_key=True)
            meeting_id = Column(Integer, ForeignKey("vexa_meetings.id"), nullable=False, unique=True)
            summary_text = Column(Text, nullable=False)
            key_points = Column(Text, nullable=True)  # JSON с ключевыми моментами
            action_items = Column(Text, nullable=True)  # JSON с задачами
            generated_at = Column(DateTime, nullable=False)
        
        # Таблица для хранения настроек интеграции с Vexa
        class VexaIntegrationSettings(Base):
            __tablename__ = 'vexa_integration_settings'
            
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
            enable_recording = Column(Boolean, default=True)
            enable_summary = Column(Boolean, default=True)
            enable_search = Column(Boolean, default=True)
            vexa_token = Column(String(255), nullable=True)
            browser_extension_installed = Column(Boolean, default=False)
            updated_at = Column(DateTime, nullable=False)
        
        # Создание таблиц
        Base.metadata.create_all(engine)
        print("✅ Таблицы базы данных успешно созданы")
        
        # Сохранение настроек Vexa API в таблицу конфигурации
        try:
            # Импортируем модели напрямую из проекта
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from app.models import User, Thread
            from app.database import SessionLocal
            
            # Создаем сессию
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Добавляем запись в таблицу с настройками
            from datetime import datetime
            settings = {
                "vexa_api_key": VEXA_API_KEY,
                "vexa_stream_url": VEXA_STREAM_URL,
                "vexa_engine_url": VEXA_ENGINE_URL,
                "vexa_transcription_url": VEXA_TRANSCRIPTION_URL,
                "setup_date": datetime.now().isoformat()
            }
            
            # Если есть таблица для хранения настроек приложения, добавляем туда
            try:
                from app.models import AppSettings
                app_settings = session.query(AppSettings).first()
                if not app_settings:
                    app_settings = AppSettings()
                
                # Добавляем настройки Vexa
                app_settings.vexa_settings = json.dumps(settings)
                session.add(app_settings)
                session.commit()
                print("✅ Настройки Vexa API сохранены в базе данных")
            except Exception as e:
                print(f"❗ Не удалось сохранить настройки в таблицу AppSettings: {str(e)}")
                # Создаем таблицу для настроек, если нет существующей
                class AppConfig(Base):
                    __tablename__ = 'app_config'
                    id = Column(Integer, primary_key=True)
                    key = Column(String(255), nullable=False, unique=True)
                    value = Column(Text, nullable=False)
                    
                Base.metadata.create_all(engine, tables=[AppConfig.__table__])
                
                # Добавляем настройки
                for key, value in settings.items():
                    config = AppConfig(key=f"vexa_{key}", value=str(value))
                    session.add(config)
                
                session.commit()
                print("✅ Настройки Vexa API сохранены в таблицу app_config")
            
        except Exception as e:
            print(f"❗ Не удалось сохранить настройки API: {str(e)}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при настройке базы данных: {str(e)}")
        return False

def main():
    """Основная функция настройки интеграции"""
    
    # Проверка наличия необходимых переменных
    if not VEXA_API_KEY:
        print("❌ Отсутствует API ключ Vexa. Укажите через --vexa-api-key или переменную окружения VEXA_API_KEY")
        return False
    
    # Выполнение выбранных действий
    if args.check_only:
        return check_vexa_api_connection()
    
    if args.setup_db:
        return setup_database()
    
    # Если не указаны конкретные действия, выполняем все
    connection_ok = check_vexa_api_connection()
    if connection_ok:
        db_setup_ok = setup_database()
        return db_setup_ok
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
