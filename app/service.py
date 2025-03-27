# Новый файл app/services.py
from functools import lru_cache
from app.config import VEXA_INTEGRATION_ENABLED
from vexa.vexa_api_client import VexaApiClient

@lru_cache(maxsize=1)
def get_vexa_client():
    """Ленивая инициализация клиента Vexa"""
    if not VEXA_INTEGRATION_ENABLED:
        return None
    return VexaApiClient()

@lru_cache(maxsize=1)
def get_speech_recognition_model():
    """Ленивая инициализация модели распознавания речи"""
    from app.speech_recognition_ml import LegalSpeechRecognitionModel
    return LegalSpeechRecognitionModel(language='ru')