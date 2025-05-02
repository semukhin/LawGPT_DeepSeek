import os
import logging
import asyncio
from typing import Optional, Dict, Any
import base64

import google.generativeai as genai

# Импортируем ключ из конфига или переменных окружения
try:
    from app.config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "models/gemini-2.5-flash-preview-04-17"

genai.configure(api_key=GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = MODEL_NAME
        if not self.api_key:
            logging.error("❌ GEMINI_API_KEY не найден. Сервис Gemini недоступен.")
            self.model = None
        else:
            self.model = genai.GenerativeModel(self.model_name)
            logging.info(f"✅ Gemini GenerativeModel инициализирован с моделью {self.model_name}")

    def is_available(self) -> bool:
        return self.model is not None

    async def extract_text_from_pdf(self, pdf_bytes: bytes, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Извлечение текста из PDF через Gemini API (актуальный синтаксис).
        Для файлов <20 МБ — через словарь с base64, для больших — NotImplementedError.
        """
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}
        pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
        prompt = prompt or "Извлеките весь текст из этого документа, сохраняя структуру и форматирование."
        try:
            if pdf_size_mb < 20:
                part = {
                    "mime_type": "application/pdf",
                    "data": base64.b64encode(pdf_bytes).decode("utf-8")
                }
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    [part, prompt]
                )
                return {"success": True, "text": response.text}
            else:
                raise NotImplementedError("File API для больших PDF (>20 МБ) не поддерживается в текущей версии SDK. Используйте REST API или уменьшите размер файла.")
        except Exception as e:
            logging.error(f"❌ Ошибка при обработке PDF через Gemini: {str(e)}")
            return {"success": False, "error": str(e)}

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str = 'image/png', prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Извлечение текста с изображения через Gemini API (актуальный синтаксис).
        """
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}
        prompt = prompt or "Извлеките весь текст с этого изображения."
        try:
            part = {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
            response = await asyncio.to_thread(
                self.model.generate_content,
                [part, prompt]
            )
            return {"success": True, "text": response.text}
        except Exception as e:
            logging.error(f"❌ Ошибка при обработке изображения через Gemini: {str(e)}")
            return {"success": False, "error": str(e)}

# Экземпляр для использования в приложении

gemini_service = GeminiService()