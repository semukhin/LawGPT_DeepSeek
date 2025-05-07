import os
import logging
from typing import Optional, Dict, Any, Union

import google.generativeai as genai
# from google.generativeai import types  # больше не нужен

# Импортируем ключ из конфига или переменных окружения
try:
    from app.config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-2.5-flash-preview-04-17"

genai.configure(api_key=GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        api_key = GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY не установлен в переменных окружения")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(MODEL_NAME)

    def is_available(self) -> bool:
        return self.model is not None

    async def extract_text_from_pdf(self, pdf_bytes: bytes, prompt: str = "Извлеки текст из этого документа") -> dict:
        """Извлекает текст из PDF с помощью Gemini Vision (нативная поддержка PDF)."""
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}
        try:
            response = self.model.generate_content([
                {"mime_type": "application/pdf", "data": pdf_bytes},
                prompt
            ])
            return {"success": True, "text": response.text}
        except Exception as e:
            logging.error(f"❌ Ошибка при извлечении текста из PDF: {str(e)}")
            return {"success": False, "error": str(e)}

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str, prompt: str = "Извлеки текст из этого изображения") -> dict:
        """Извлекает текст из изображения с помощью Gemini Vision."""
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}
        try:
            response = self.model.generate_content([
                {"mime_type": mime_type, "data": image_bytes},
                prompt
            ])
            return {"success": True, "text": response.text}
        except Exception as e:
            logging.error(f"❌ Ошибка при извлечении текста из изображения: {str(e)}")
            return {"success": False, "error": str(e)}

# Экземпляр для использования в приложении
gemini_service = GeminiService()