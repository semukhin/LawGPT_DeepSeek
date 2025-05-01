import google.generativeai as genai
import os
import base64  # Добавлен обратно для работы с версией 0.3.1
import logging
import asyncio
import tempfile
import shutil  # Для создания временной директории
import time  # Для временных меток
import aiofiles  # Для асинхронной работы с файлами
from typing import Optional, Dict, Any, List, Tuple

# Импорт специфических исключений Google API
from google.api_core import exceptions as google_exceptions

# Корректный импорт PyMuPDF
try:
    import fitz
except ImportError:
    logging.error("❌ Ошибка импорта: PyMuPDF не установлен. OCR для PDF может работать некорректно.")
    fitz = None

# Предполагаем, что app.config существует и содержит GEMINI_API_KEY и GEMINI_MODEL
try:
    from app.config import GEMINI_API_KEY, GEMINI_MODEL
except ImportError:
    logging.error(
        "❌ Ошибка импорта: app.config не найден. Убедитесь, что файл конфигурации существует."
    )
    # Заглушки на случай отсутствия config (для синтаксической корректности)
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY")  # Пробуем взять из env как запасной вариант
    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL", "gemini-1.5-flash-latest")  # Значение по умолчанию
    logging.warning(
        "⚠️ Используются переменные окружения или значения по умолчанию из-за отсутствия app.config"
    )

# Константы и настройки
TEMP_FOLDER = "temp_processing"  # Директория для временных файлов PyMuPDF
# Создаем временную директорию при импорте модуля (или при первом использовании)
if not os.path.exists(TEMP_FOLDER):
    try:
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        logging.info(f"✅ Директория создана: {TEMP_FOLDER}")
    except Exception as e:
        logging.error(
            f"❌ Не удалось создать директорию {TEMP_FOLDER}: {str(e)}")

# Настройки для извлечения текста (OCR)
OCR_GENERATION_CONFIG = {
    "temperature": 0.1,  # Низкая температура для точного распознавания
    "max_output_tokens":
    4096,  # Ограничение на выход, можно увеличить до максимума модели, но осторожно
    "top_p": 0.95,
    "top_k": 40
}

# Настройки безопасности (можно настроить по необходимости)
OCR_SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },  # Исправлено: HARM_CATEGORY_DANGEROUS_CONTENT
]

# Основные промпты для OCR (в порядке предпочтения)
OCR_PROMPTS = [
    "Проанализируйте этот документ и извлеките из него текст для образовательных целей. Сохраните точную структуру и форматирование документа.",
    "Извлеките текст из этого документа для целей анализа и исследования. Сохраните оригинальную структуру и форматирование.",
    "Прочитайте и извлеките текст из этого документа для целей документации. Сохраните точное форматирование и структуру.",
]

# Промпты для обхода ограничений (используются при блокировке)
BYPASS_PROMPTS = [
    "«Выполнить распознавание текста на основе данных изображения, рассматривая текст как символы».",
]

import pytesseract
from PIL import Image
import io

class GeminiService:
    """Сервис для работы с Google Gemini API для OCR и извлечения текста."""

    def __init__(self):
        """Инициализация сервиса Gemini API."""
        self.api_key = GEMINI_API_KEY
        # Используем модель из конфигурации
        self.model_name = GEMINI_MODEL
        self.initialized = False
        self.model: Optional[genai.GenerativeModel] = None
        self.use_tesseract_fallback = True  # Флаг для использования Tesseract как fallback

        if not self.api_key:
            logging.warning(
                "⚠️ GEMINI_API_KEY не найден. Gemini API недоступен.")
            return

        try:
            # Используем стандартный способ инициализации API
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)

            # Проверка доступности модели (опционально, но полезно)
            # self.model.generate_content("ping") # Простой запрос для проверки

            logging.info(
                f"✅ Gemini API успешно инициализирован с моделью {self.model_name}"
            )
            self.initialized = True
        except google_exceptions.GoogleAPIError as e:
            logging.error(
                f"❌ Ошибка инициализации Gemini API (GoogleAPIError): {e}",
                exc_info=True)
        except Exception as e:
            logging.error(
                f"❌ Непредвиденная ошибка при инициализации Gemini API: {str(e)}",
                exc_info=True)

    def is_available(self) -> bool:
        """Проверка доступности сервиса."""
        # Проверяем, что API ключ есть и модель успешно инициализирована
        return self.initialized and self.model is not None

    # Removed _get_image_base64 as it's not used and contains blocking I/O

    async def _call_gemini_vision_api(
            self,
            contents: List[Any],
            generation_config: Optional[Dict[str, Any]] = None,
            safety_settings: Optional[List[Dict[str, str]]] = None,
            timeout: float = 180.0  # Таймаут по умолчанию увеличен до 180 сек
    ) -> Dict[str, Any]:
        """
        Внутренний метод для вызова Gemini Vision API с обработкой стандартных ошибок.
        Возвращает структурированный результат.
        """
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}

        try:
            logging.info(
                f"🌐 Отправка запроса в Gemini API ({self.model_name})...")
            # В версии 0.3.1 нет асинхронного метода, выполняем в отдельном потоке
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    contents=contents,
                    generation_config=generation_config
                    or OCR_GENERATION_CONFIG,
                    safety_settings=safety_settings or OCR_SAFETY_SETTINGS
                ),
                timeout=timeout
            )

            # Проверка на ошибки блокировки - в версии 0.3.1 другая структура ответа
            if hasattr(response, "error") and response.error:
                logging.warning(f"⚠️ Запрос заблокирован: {response.error}")
                return {
                    "success": False,
                    "error": f"Запрос заблокирован: {response.error}",
                    "block_reason": "SAFETY"
                }

            # В версии 0.3.1 другая структура ответа
            # У нас нет candidates и finish_reason как в новых версиях
            # Просто проверяем, есть ли текст в ответе

            # Проверка на успешный ответ и наличие текста - в версии 0.3.1 другая структура
            if response and isinstance(response, str):
                # Если ответ является строкой
                logging.info("✅ Gemini API вернул текст (строка).")
                return {"success": True, "text": response}
            elif hasattr(response, "text"):
                try:
                    # Если ответ имеет атрибут text
                    if response.text and response.text.strip():
                        logging.info("✅ Gemini API вернул текст (объект).")
                        return {"success": True, "text": response.text}
                except (AttributeError, IndexError) as e:
                    logging.warning(
                        f"⚠️ Ошибка при получении текста из ответа: {e}")
                    # Продолжаем проверку других форматов
            elif hasattr(response,
                         "prompt_feedback") and response.prompt_feedback:
                # Проверяем наличие обратной связи по промпту (может указывать на блокировку)
                feedback_msg = str(response.prompt_feedback)
                logging.warning(
                    f"⚠️ Получена обратная связь от API: {feedback_msg}")
                return {
                    "success": False,
                    "error": f"Запрос заблокирован: {feedback_msg}",
                    "block_reason": "SAFETY"
                }
            elif hasattr(response, "candidates") and response.candidates:
                # Если есть кандидаты (для совместимости с другими версиями)
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and candidate.content:
                        try:
                            parts = None
                            # Сначала проверяем наличие атрибута parts
                            if hasattr(candidate.content, "parts"):
                                parts = candidate.content.parts
                                if parts and len(parts) > 0:
                                    # Безопасное получение текста из parts
                                    if hasattr(parts[0], "text"):
                                        text = parts[0].text
                                    else:
                                        text = str(parts[0])
                                else:
                                    text = str(candidate.content)
                            else:
                                text = str(candidate.content)

                            if text and text.strip():
                                logging.info(
                                    "✅ Gemini API вернул текст (из кандидата)."
                                )
                                return {"success": True, "text": text}
                        except (AttributeError, IndexError) as e:
                            logging.warning(
                                f"⚠️ Ошибка при обработке кандидата: {e}")
                            continue

            # Пытаемся получить хоть какую-то информацию из ответа
            try:
                response_str = str(response)
                if response_str and "error" not in response_str.lower():
                    logging.info("✅ Получен неструктурированный ответ от API.")
                    text_content = response_str

                    # Логирование размера текста для отладки
                    logging.info(f"📏 Размер полученного текста: {len(text_content)} символов")

                    # Проверка на целостность текста
                    if len(text_content) > 100:
                        logging.info(f"🔬 Начало текста: '{text_content[:100]}...'")
                        logging.info(f"🔬 Конец текста: '...{text_content[-100:]}'")

                    return {"success": True, "text": text_content}
            except Exception as e:
                logging.warning(
                    f"⚠️ Не удалось получить строковое представление ответа: {e}"
                )

            # Если ничего не подошло
            logging.warning("⚠️ Gemini API не вернул текст.")
            return {"success": False, "error": "Gemini API не вернул текст."}

        except asyncio.TimeoutError:
            logging.warning(
                f"⏱️ Таймаут запроса к Gemini API ({timeout} сек).")
            return {
                "success": False,
                "error": f"Таймаут запроса к Gemini API ({timeout} сек)."
            }
        except Exception as e:
            if "BlockedContent" in str(e) or "blocked" in str(e).lower():
                logging.warning(f"⚠️ Запрос заблокирован: {e}")
                return {
                    "success": False,
                    "error": f"Контент заблокирован: {e}",
                    "block_reason": "SAFETY"
                }
            else:
                logging.error(f"❌ Ошибка при вызове Gemini API: {e}",
                              exc_info=True)
                return {
                    "success": False,
                    "error": f"Ошибка при вызове Gemini API: {str(e)}"
                }
        except google_exceptions.RateLimitError as e:
            logging.error(f"❌ Превышен лимит запросов к Gemini API: {e}")
            return {
                "success": False,
                "error":
                f"Превышен лимит запросов к Gemini API. Попробуйте позже."
            }
        except google_exceptions.GoogleAPIError as e:
            logging.error(f"❌ Ошибка API при вызове Gemini: {e}",
                          exc_info=True)
            return {
                "success": False,
                "error": f"Ошибка при вызове Gemini API: {e}"
            }
        except Exception as e:
            logging.error(
                f"❌ Непредвиденная ошибка при вызове Gemini API: {str(e)}",
                exc_info=True)
            return {
                "success": False,
                "error":
                f"Непредвиденная ошибка при вызове Gemini API: {str(e)}"
            }

    async def _extract_text_with_tesseract(self, image_bytes: bytes) -> Dict[str, Any]:
        """Извлечение текста с помощью Tesseract OCR"""
        try:
            # Открываем изображение из байтов
            image = Image.open(io.BytesIO(image_bytes))
            
            # Извлекаем текст с помощью Tesseract
            text = pytesseract.image_to_string(image, lang='rus+eng')
            
            if text and text.strip():
                logging.info("✅ Tesseract OCR успешно извлек текст")
                return {"success": True, "text": text.strip()}
            else:
                logging.warning("⚠️ Tesseract OCR не смог извлечь текст")
                return {"success": False, "error": "Tesseract OCR не смог извлечь текст"}
                
        except Exception as e:
            logging.error(f"❌ Ошибка при извлечении текста с помощью Tesseract: {str(e)}")
            return {"success": False, "error": f"Ошибка Tesseract OCR: {str(e)}"}

    async def extract_text_from_image(
            self,
            file_bytes: bytes,
            mime_type: str,
            custom_prompt: Optional[str] = None,
            custom_timeout: float = 180.0) -> Dict[str, Any]:
        """Извлечение текста из изображения с использованием Gemini API и fallback на Tesseract"""
        if not self.is_available():
            return {"success": False, "error": "Gemini API не инициализирован"}

        try:
            # Пробуем сначала Gemini
            result = await self._call_gemini_vision_api(
                contents=[{"mime_type": mime_type, "data": base64.b64encode(file_bytes).decode('utf-8')}],
                timeout=custom_timeout
            )

            # Если Gemini вернул ошибку из-за авторских прав или другой ошибки
            if not result["success"] and self.use_tesseract_fallback:
                logging.warning("⚠️ Gemini отказал в обработке. Пробуем Tesseract OCR...")
                return await self._extract_text_with_tesseract(file_bytes)

            return result

        except Exception as e:
            logging.error(f"❌ Ошибка при извлечении текста: {str(e)}")
            if self.use_tesseract_fallback:
                logging.warning("⚠️ Пробуем Tesseract OCR после ошибки...")
                return await self._extract_text_with_tesseract(file_bytes)
            return {"success": False, "error": str(e)}

    async def _extract_text_from_pdf_text_layer_async(
            self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Извлекает текстовый слой из PDF с помощью PyMuPDF в отдельном потоке.
        Использует несколько методов извлечения для максимальной полноты текста.
        """
        if fitz is None:
            return {"success": False, "error": "PyMuPDF не установлен."}

        try:
            # fitz.open и get_text() могут быть блокирующими
            def extract_sync():
                doc = fitz.open("pdf", pdf_bytes)
                combined_text = ""
                page_count = len(doc)

                # Метод 1: Стандартное извлечение через get_text() для каждой страницы
                for page_num in range(page_count):
                    page = doc[page_num]
                    # Используем разные опции для извлечения текста
                    text = page.get_text()  # Стандартный текст
                    combined_text += f"\n--- Страница {page_num+1} ---\n"
                    combined_text += text

                    # Дополнительно проверяем наличие таблиц и извлекаем их в текстовом формате
                    try:
                        tables_text = page.get_text("blocks")
                        if tables_text and isinstance(tables_text, list) and len(tables_text) > 0:
                            tables_extracted = "\n".join([str(block[4]) for block in tables_text if block[0] == 1])
                            if tables_extracted and len(tables_extracted) > 10:  # Если извлекли полезное содержимое
                                combined_text += "\n--- Табличное содержимое ---\n"
                                combined_text += tables_extracted
                    except Exception as e:
                        logging.warning(f"⚠️ Не удалось извлечь табличное содержимое: {e}")

                # Метод 2: Извлечение всего документа целиком
                try:
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text()
                except Exception as e:
                    logging.warning(f"⚠️ Не удалось извлечь полный текст документа: {e}")
                    full_text = combined_text  # Используем уже собранный текст

                # Сравниваем результаты и выбираем более полный
                if len(full_text) > len(combined_text):
                    final_text = full_text
                    logging.info(f"✅ Использовано полное извлечение документа (более полное)")
                else:
                    final_text = combined_text
                    logging.info(f"✅ Использовано постраничное извлечение (более полное)")

                doc.close()  # Убедимся, что документ закрыт
                return final_text

            text = await asyncio.to_thread(extract_sync)

            if text and text.strip():
                # Проверка на "заметный" объем текста (не просто несколько символов)
                if len(text.strip()) > 100:
                    logging.info(
                        f"✅ Текст успешно извлечен из PDF с помощью PyMuPDF. Символов: {len(text)}"
                    )
                    return {"success": True, "text": text}
                else:
                    logging.info(
                        f"📄 Текстовый слой извлечен, но слишком мал ({len(text)} символов). Возможно, требуется OCR."
                    )

            logging.info("📄 Текстовый слой отсутствует или слишком мал в PDF.")
            return {
                "success": False,
                "error": "Текстовый слой отсутствует или слишком мал."
            }

        except Exception as e:
            logging.warning(
                f"⚠️ Ошибка при извлечении текстового слоя с помощью PyMuPDF: {str(e)}",
                exc_info=True)
            return {"success": False, "error": f"Ошибка PyMuPDF: {str(e)}"}

    async def _extract_text_from_pdf_direct_api_async(
            self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Попытка прямого извлечения текста из PDF с помощью Gemini API.
        """
        pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
        
        try:
            # Кодируем PDF в base64
            encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Создаем multimodal контент
            contents = [
                {
                    "mime_type": "application/pdf",
                    "data": encoded_pdf
                },
                """Извлеките весь текст из этого PDF документа. 
                Особое внимание уделите:
                1. Нумерации страниц
                2. Заголовкам и подзаголовкам
                3. Таблицам и спискам
                4. Датам и номерам документов
                5. Подписям и печатям
                6. Всем юридическим терминам и формулировкам
                
                Сохраните точную структуру документа и форматирование.
                """
            ]

            # Настраиваем параметры генерации
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 32768,
                "top_p": 0.95,
                "top_k": 40
            }

            # Увеличиваем таймаут для больших файлов
            timeout = 600.0 if pdf_size_mb >= 20 else 180.0

            logging.info(f"🌐 Отправка PDF в Gemini API (размер: {pdf_size_mb:.2f} МБ, таймаут: {timeout} сек)")
            result = await self._call_gemini_vision_api(
                contents, 
                timeout=timeout,
                generation_config=generation_config
            )

            if result["success"]:
                text_length = len(result.get("text", ""))
                expected_min_chars = pdf_size_mb * 10000  # Примерная оценка: 10000 символов на 1 МБ
                
                if text_length < expected_min_chars:
                    logging.warning(
                        f"⚠️ Извлеченный текст может быть неполным: {text_length} символов при размере файла {pdf_size_mb:.2f} МБ"
                    )
                    logging.warning(f"⚠️ Ожидалось примерно {int(expected_min_chars)} символов")
                    
                    # Пробуем альтернативный промпт
                    contents_alt = [
                        {
                            "mime_type": "application/pdf",
                            "data": encoded_pdf
                        },
                        """Это юридический документ. Извлеките весь текст, сохраняя структуру и форматирование.
                        Включите все детали, цифры, даты, номера документов, подписи и печати.
                        Особое внимание уделите юридическим терминам и формулировкам."""
                    ]
                    
                    alt_result = await self._call_gemini_vision_api(
                        contents_alt,
                        timeout=timeout,
                        generation_config=generation_config
                    )
                    
                    if alt_result["success"] and len(alt_result.get("text", "")) > text_length:
                        logging.info(f"✅ Альтернативный метод дал больше текста: {len(alt_result.get('text', ''))} символов")
                        # Добавляем информацию о пути сохранения
                        alt_result["output_path"] = os.path.abspath(os.path.join("output_documents", f"{os.path.splitext(os.path.basename(result.get('filename', 'output')))[0]}_recognized.txt"))
                        return alt_result
                
                logging.info(f"✅ Успешно обработан PDF ({pdf_size_mb:.2f} МБ)")
                # Добавляем информацию о пути сохранения
                result["output_path"] = os.path.abspath(os.path.join("output_documents", f"{os.path.splitext(os.path.basename(result.get('filename', 'output')))[0]}_recognized.txt"))
                return result
            else:
                logging.warning(f"⚠️ Gemini не смог обработать PDF: {result.get('error', 'Неизвестная ошибка')}")
                return {
                    "success": False,
                    "error": f"Gemini не смог обработать PDF размером {pdf_size_mb:.2f} МБ: {result.get('error', 'Неизвестная ошибка')}"
                }

        except Exception as e:
            logging.error(f"❌ Ошибка при обработке PDF: {str(e)}")
            return {
                "success": False,
                "error": f"Ошибка при обработке PDF ({pdf_size_mb:.2f} МБ): {str(e)}"
            }

    async def _extract_text_from_pdf_page_ocr_async(
            self, pdf_bytes: bytes, thread_id: str = None) -> Dict[str, Any]:
        """
        Постраничная обработка PDF как изображений с помощью Gemini OCR.
        """
        if fitz is None:
            return {
                "success": False,
                "error": "PyMuPDF не установлен для постраничной обработки."
            }
        if not self.is_available():
            return {
                "success": False,
                "error": "Gemini API не инициализирован для постраничной обработки."
            }

        start_time = time.time()
        status_updates = []

        def add_status(message: str, progress: float):
            current_time = time.time() - start_time
            status = {
                "message": message,
                "progress": progress,
                "time_elapsed": current_time
            }
            status_updates.append(status)
            return status

        try:
            # Добавляем первый статус
            add_status("Начало обработки PDF документа", 0)

            # Создаем временную директорию для изображений страниц
            temp_dir = os.path.join(
                TEMP_FOLDER,
                f"pdf_pages_{os.getpid()}_{id(self)}_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            add_status("Подготовка к извлечению страниц", 5)

            # Открываем PDF в отдельном потоке
            doc = await asyncio.to_thread(fitz.open, "pdf", pdf_bytes)
            max_pages = min(50, doc.page_count)
            total_pages_to_process = max_pages
            
            add_status(f"Документ содержит {doc.page_count} страниц, будет обработано {max_pages}", 10)

            # Сохраняем страницы как изображения
            temp_image_paths = []
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    temp_img_path = os.path.join(temp_dir, f"page_{page_num:04d}.png")
                    await asyncio.to_thread(pix.save, temp_img_path)
                    temp_image_paths.append(temp_img_path)
                    progress = 10 + (30 * (page_num + 1) / max_pages)
                    add_status(f"Подготовлена страница {page_num + 1} из {max_pages}", progress)
                except Exception as e:
                    logging.error(f"Ошибка при подготовке страницы {page_num + 1}: {str(e)}")

            await asyncio.to_thread(doc.close)

            if not temp_image_paths:
                return {
                    "success": False,
                    "error": "Не удалось подготовить изображения страниц для OCR.",
                    "status_updates": status_updates
                }

            add_status("Начало распознавания текста", 40)

            # Обрабатываем каждое изображение страницы через Gemini
            combined_text = []
            success_count = 0

            for page_num, img_path in enumerate(temp_image_paths):
                try:
                    async with aiofiles.open(img_path, "rb") as img_file:
                        img_bytes = await img_file.read()

                    ocr_result = await self._call_gemini_vision_api(
                        contents=[{
                            "mime_type": "image/png",
                            "data": base64.b64encode(img_bytes).decode('utf-8')
                        }],
                        timeout=60.0
                    )

                    if ocr_result["success"] and ocr_result.get("text", "").strip():
                        combined_text.append(f"\n\n--- Страница {page_num + 1} ---\n\n")
                        combined_text.append(ocr_result["text"].strip())
                        success_count += 1
                        progress = 40 + (50 * (page_num + 1) / len(temp_image_paths))
                        add_status(f"Распознана страница {page_num + 1} из {len(temp_image_paths)}", progress)
                    else:
                        add_status(f"Ошибка распознавания страницы {page_num + 1}", progress)

                except Exception as e:
                    logging.error(f"Ошибка при обработке страницы {page_num + 1}: {str(e)}")
                    add_status(f"Ошибка обработки страницы {page_num + 1}: {str(e)}", progress)

            # Формируем финальный результат
            if success_count > 0:
                final_text = "".join(combined_text)
                end_time = time.time()
                total_time = end_time - start_time
                
                result = {
                    "success": True,
                    "text": final_text,
                    "pages_processed": total_pages_to_process,
                    "pages_success": success_count,
                    "processing_time": total_time,
                    "status_updates": status_updates
                }

                # Если передан thread_id, сохраняем результат как сообщение
                if thread_id:
                    try:
                        from app.models import Message
                        from app.database import get_db

                        # Создаем сообщение с результатом и ссылкой на скачивание
                        message_text = f"""Документ успешно распознан
Обработано страниц: {success_count}/{total_pages_to_process}
Время обработки: {total_time:.1f} секунд

[Скачать распознанный текст](/download/{thread_id}/latest)"""

                        async with get_db() as db:
                            message = Message(
                                thread_id=thread_id,
                                role="assistant",
                                content=message_text,
                                metadata={
                                    "recognized_text": final_text,
                                    "processing_time": total_time,
                                    "pages_processed": total_pages_to_process,
                                    "pages_success": success_count
                                }
                            )
                            db.add(message)
                            await db.commit()
                            
                    except Exception as e:
                        logging.error(f"Ошибка при сохранении результата в базу данных: {str(e)}")

                add_status("Обработка завершена успешно", 100)
                return result
            else:
                add_status("Не удалось распознать текст ни на одной странице", 100)
                return {
                    "success": False,
                    "error": "Не удалось распознать текст ни на одной странице.",
                    "status_updates": status_updates
                }

        except Exception as e:
            error_msg = f"Непредвиденная ошибка при постраничной обработке PDF: {str(e)}"
            add_status(error_msg, 100)
            return {
                "success": False,
                "error": error_msg,
                "status_updates": status_updates
            }
        finally:
            # Удаляем временную директорию
            if os.path.exists(temp_dir):
                try:
                    await asyncio.to_thread(shutil.rmtree, temp_dir)
                except Exception as e:
                    logging.error(f"Ошибка при удалении временной директории: {str(e)}")

    async def extract_text_from_pdf(self, pdf_bytes: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Главная функция извлечения текста из PDF.
        Пробует методы в порядке предпочтения: текстовый слой, прямой API, постраничный OCR.
        """
        if not self.is_available() and fitz is None:
            return {
                "success": False,
                "error": "Gemini API не инициализирован и PyMuPDF не установлен."
            }

        pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
        logging.info(f"📏 Размер PDF: {pdf_size_mb:.2f} МБ")

        # Сохраняем имя файла для использования в путях
        if filename:
            result = {"filename": filename}
        else:
            result = {}

        # Для файлов больше 20 МБ сразу используем Gemini
        if pdf_size_mb >= 20:
            logging.info("📄 Файл большой, используем прямой метод Gemini API")
            result.update(await self._extract_text_from_pdf_direct_api_async(pdf_bytes))
            if result.get("output_path"):
                logging.info(f"💾 Результат будет сохранен в: {result['output_path']}")
            return result

        logging.info("🎬 Начинаем извлечение текста из PDF...")

        # 1. Попробуем извлечь текстовый слой с помощью PyMuPDF
        text_layer_result = await self._extract_text_from_pdf_text_layer_async(
            pdf_bytes)
        if text_layer_result["success"]:
            logging.info("✅ Извлечение текстового слоя успешно.")
            return text_layer_result

        logging.info(
            "▶️ Переход к методам OCR (текстовый слой отсутствует или пуст).")

        # 2. Попробуем прямой метод с Gemini API
        direct_api_result = await self._extract_text_from_pdf_direct_api_async(
            pdf_bytes)
        if direct_api_result["success"]:
            logging.info("✅ Прямой метод Gemini API успешно.")
            return direct_api_result

        # 3. Если оба метода не сработали, пробуем постраничную обработку
        page_ocr_result = await self._extract_text_from_pdf_page_ocr_async(
            pdf_bytes)
        if page_ocr_result["success"]:
            logging.info("✅ Постраничный OCR успешно.")
            return page_ocr_result

        logging.error("❌ Не удалось извлечь текст из PDF всеми методами.")
        return {
            "success": False,
            "error": "Не удалось извлечь текст из PDF всеми доступными методами."
        }


# Создаем экземпляр сервиса при импорте модуля
gemini_service = GeminiService()

# Пример использования (должно вызываться из асинхронной функции)
# async def main():
#     # Предполагаем, что у вас есть pdf_bytes или img_bytes
#     # Для теста можно прочитать небольшой файл
#     # with open("test.pdf", "rb") as f:
#     #     pdf_bytes = f.read()
#     # result = await gemini_service.extract_text_from_pdf(pdf_bytes)
#     # print(result)

#     # with open("test.jpg", "rb") as f:
#     #      img_bytes = f.read()
#     # result = await gemini_service.extract_text_from_image(img_bytes, "image/jpeg")
#     # print(result)

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     # asyncio.run(main()) # Запускать только если это корневой скрипт