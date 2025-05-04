"""
Сервис для работы с Google AI Studio (Gemini) API.
Раньше этот файл использовался для интеграции с Vertex AI,
теперь используется только для обратной совместимости.
"""
import os
import logging
from typing import Optional, Dict, Any

# Импорт конфигурации
from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_API_ENABLED

import google.generativeai as genai
from google.generativeai import types

MODEL_NAME = "gemini-2.5-flash-preview-04-17"

genai.configure(api_key=GEMINI_API_KEY)

class GoogleAIService:
    """
    Сервис для работы с Google AI Studio (Gemini) API.
    Заглушка для обратной совместимости.
    """
    def __init__(self):
        """
        Инициализирует сервис Google AI с настройками из конфигурации.
        """
        self.enabled = GEMINI_API_ENABLED
        self.api_key = GEMINI_API_KEY
        self.model = MODEL_NAME
        self.client = genai.Client()

        logging.info(f"🔄 Инициализация Google AI Studio: enabled={self.enabled}")
        logging.info(f"🔄 Настройки: model={self.model}")

        if not self.enabled:
            logging.info("⚠️ Google AI Studio сервис отключен в конфигурации.")
            return

        if not self.api_key:
            logging.error("❌ API ключ Google AI Studio не настроен в конфигурации.")
            self.enabled = False
            return

        logging.info("✅ Google AI Studio инициализирован успешно")

    async def analyze_document(self, document_bytes: bytes, document_type: Optional[str] = None, prompt: str = "Summarize this document") -> Dict[str, Any]:
        """
        Анализирует PDF-документ с помощью Gemini (нативная поддержка PDF).
        Args:
            document_bytes: PDF-файл в байтах
            document_type: Тип документа (pdf, docx, xlsx и т.д.)
            prompt: Текстовый промпт для Gemini
        Returns:
            Dict с результатами анализа документа
        """
        if not self.enabled:
            logging.warning("⚠️ Google AI Studio отключен в настройках")
            return {"text": None, "analysis": None}

        try:
            if document_type == 'pdf' or document_type is None:
                part = types.Part.from_bytes(data=document_bytes, mime_type='application/pdf')
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[part, prompt]
                )
                return {"text": response.text, "analysis": {"processed_by": "gemini"}}
            else:
                # Для обратной совместимости просто возвращаем текст как есть
                return {"text": None, "analysis": {"processed_by": "gemini"}}
        except Exception as e:
            logging.error(f"❌ Ошибка при анализе документа: {str(e)}", exc_info=True)
            return {"text": None, "analysis": {"error": str(e)}}
