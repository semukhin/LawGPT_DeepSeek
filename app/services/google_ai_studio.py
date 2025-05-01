
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
        self.model = GEMINI_MODEL

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

    async def analyze_document(self, document_text: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует текст документа с помощью Gemini.

        Args:
            document_text: Извлеченный текст документа
            document_type: Тип документа (pdf, docx, xlsx и т.д.)

        Returns:
            Dict с результатами анализа документа
        """
        if not self.enabled:
            logging.warning("⚠️ Google AI Studio отключен в настройках")
            return {"text": document_text, "analysis": None}

        try:
            # Для обратной совместимости просто возвращаем текст как есть
            logging.info(f"🔍 Gemini API интеграция теперь используется напрямую")
            return {"text": document_text, "analysis": {"processed_by": "gemini"}}

        except Exception as e:
            logging.error(f"❌ Ошибка при анализе документа: {str(e)}", exc_info=True)
            return {"text": document_text, "analysis": {"error": str(e)}}
