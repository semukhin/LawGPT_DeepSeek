# app/services/vexa_client.py
"""
Клиент для работы с API Vexa.ai
Обеспечивает взаимодействие с сервисами транскрибации и управления знаниями
"""
import os
import logging
import json
import time
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Модели данных Pydantic
class MeetingInfo(BaseModel):
    meeting_id: str
    title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    source_type: str
    connection_id: str
    metadata: Optional[Dict[str, Any]] = None

class TranscriptSegment(BaseModel):
    transcript_id: str
    meeting_id: str
    speaker: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    text: str
    confidence: Optional[int] = None

class MeetingSummary(BaseModel):
    meeting_id: str
    summary_text: str
    key_points: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    generated_at: datetime

class VexaApiClient:
    """Клиент для работы с API Vexa.ai"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        stream_url: Optional[str] = None,
        engine_url: Optional[str] = None,
        transcription_url: Optional[str] = None
    ):
        """
        Инициализирует клиент Vexa API
        
        Args:
            api_key: API ключ для доступа к Vexa
            stream_url: URL для StreamQueue API
            engine_url: URL для Engine API
            transcription_url: URL для Transcription API
        """
        self.api_key = api_key or os.getenv("VEXA_API_KEY")
        if not self.api_key:
            raise ValueError("API ключ Vexa не указан")
        
        self.stream_url = stream_url or os.getenv("VEXA_STREAM_URL", "https://streamqueue.dev.vexa.ai")
        self.engine_url = engine_url or os.getenv("VEXA_ENGINE_URL", "https://engine.dev.vexa.ai")
        self.transcription_url = transcription_url or os.getenv("VEXA_TRANSCRIPTION_URL", "https://transcription.dev.vexa.ai")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Инициализирован клиент Vexa API с URL: Stream={self.stream_url}, Engine={self.engine_url}")
        self.session = None
        
    async def __aenter__(self):
        """Инициализация сессии для использования с context manager"""
        self.session = aiohttp.ClientSession()
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе из context manager"""
        if self.session:
            await self.session.close()
            self.session = None


    async def _get_session(self):
        """Получение существующей или создание новой сессии"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session


    async def check_connection(self):
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.stream_url}/api/v1/extension/check-token", 
                headers=self.headers,
                timeout=10
            ) as response:
                if response.status != 200:
                    logger.error(f"Ошибка соединения с StreamQueue API: {response.status}")
                    return False
                
                # Проверка Engine API
                async with session.get(
                    f"{self.engine_url}/api/health",
                    headers=self.headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка соединения с Engine API: {response.status}")
                        return False
                
                # Проверка Transcription API
                async with session.get(
                    f"{self.transcription_url}/health",
                    headers=self.headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка соединения с Transcription API: {response.status}")
                        return False
                    
            logger.info("Успешная проверка соединения с API Vexa")
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения с API Vexa: {str(e)}")
            return False



    async def register_user(self, user_id: str, user_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Регистрирует пользователя в Vexa и возвращает токен для расширения браузера
        
        Args:
            user_id: Идентификатор пользователя
            user_email: Email пользователя (опционально)
            
        Returns:
            Словарь с информацией о регистрации и токеном
        """
        try:
            token = f"lawgpt_{user_id}_{int(time.time())}"
            
            # Регистрация токена пользователя в StreamQueue
            payload = {
                "token": token,
                "user_id": str(user_id),
                "enable_status": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.stream_url}/api/v1/users/add-token",
                    headers=self.headers,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при регистрации пользователя в StreamQueue: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка регистрации в Vexa: {error_text}")
                    
                    result = await response.json()
            
            # Регистрация пользователя в Engine
            engine_payload = {
                "user_id": str(user_id),
                "user_name": user_email or f"lawgpt_user_{user_id}",
                "user_email": user_email or f"user_{user_id}@lawgpt.example.com"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.engine_url}/api/v1/users",
                    headers=self.headers,
                    json=engine_payload,
                    timeout=10
                ) as response:
                    # Допускаем как 200, так и 409 (пользователь уже существует)
                    if response.status not in [200, 201, 409]:
                        error_text = await response.text()
                        logger.error(f"Ошибка при регистрации пользователя в Engine: {error_text}")
                        # Продолжаем, так как главное - это токен для StreamQueue
            
            logger.info(f"Пользователь {user_id} успешно зарегистрирован в Vexa")
            return {
                "user_id": str(user_id),
                "token": token,
                "registered_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя в Vexa: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка регистрации в Vexa: {str(e)}")

    async def start_meeting(self, meeting_info: MeetingInfo) -> Dict[str, Any]:
        """
        Создает новую встречу в Vexa
        
        Args:
            meeting_info: Информация о встрече
            
        Returns:
            Информация о созданной встрече
        """
        try:
            # Создаем встречу в Engine API
            payload = {
                "meeting_id": meeting_info.meeting_id,
                "user_id": meeting_info.meeting_metadata.get("user_id") if meeting_info.meeting_metadata else None,
                "title": meeting_info.title or f"Meeting {meeting_info.meeting_id}",
                "start_timestamp": int(meeting_info.start_time.timestamp()),
                "source": meeting_info.source_type
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.engine_url}/api/v1/meetings",
                    headers=self.headers,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"Ошибка при создании встречи в Engine: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка создания встречи: {error_text}")
                    
                    result = await response.json()
            
            logger.info(f"Встреча {meeting_info.meeting_id} успешно создана в Vexa")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при создании встречи в Vexa: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка создания встречи: {str(e)}")

    async def end_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Завершает встречу в Vexa
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Информация о завершенной встрече
        """
        try:
            # Завершаем встречу в Engine API
            payload = {
                "meeting_id": meeting_id,
                "end_timestamp": int(datetime.now().timestamp())
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.engine_url}/api/v1/meetings/{meeting_id}/end",
                    headers=self.headers,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при завершении встречи в Engine: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка завершения встречи: {error_text}")
                    
                    result = await response.json()
            
            logger.info(f"Встреча {meeting_id} успешно завершена в Vexa")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при завершении встречи в Vexa: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка завершения встречи: {str(e)}")

    async def get_meeting_transcripts(self, meeting_id: str) -> List[TranscriptSegment]:
        """
        Получает транскрипты встречи из Vexa
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Список сегментов транскрипта
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.engine_url}/api/v1/meetings/{meeting_id}/transcript",
                    headers=self.headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при получении транскриптов: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка получения транскриптов: {error_text}")
                    
                    data = await response.json()
            
            # Преобразуем данные в модель TranscriptSegment
            transcript_segments = []
            for segment in data.get("segments", []):
                transcript_segments.append(TranscriptSegment(
                    transcript_id=segment.get("id", f"segment_{len(transcript_segments)}"),
                    meeting_id=meeting_id,
                    speaker=segment.get("speaker"),
                    start_time=datetime.fromtimestamp(segment.get("start_time", 0)),
                    end_time=datetime.fromtimestamp(segment.get("end_time", 0)) if segment.get("end_time") else None,
                    text=segment.get("text", ""),
                    confidence=segment.get("confidence")
                ))
            
            logger.info(f"Получено {len(transcript_segments)} сегментов транскрипта для встречи {meeting_id}")
            return transcript_segments
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскриптов встречи: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка получения транскриптов: {str(e)}")

    async def generate_meeting_summary(self, meeting_id: str) -> MeetingSummary:
        """
        Генерирует саммари встречи
        
        Args:
            meeting_id: ID встречи
            
        Returns:
            Саммари встречи
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.engine_url}/api/v1/meetings/{meeting_id}/summary",
                    headers=self.headers,
                    timeout=30  # Увеличенный таймаут для генерации
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при генерации саммари: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка генерации саммари: {error_text}")
                    
                    data = await response.json()
            
            # Преобразуем данные в модель MeetingSummary
            summary = MeetingSummary(
                meeting_id=meeting_id,
                summary_text=data.get("summary", ""),
                key_points=data.get("key_points", []),
                action_items=data.get("action_items", []),
                generated_at=datetime.now()
            )
            
            logger.info(f"Сгенерировано саммари для встречи {meeting_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Ошибка при генерации саммари встречи: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка генерации саммари: {str(e)}")

    async def search_transcripts(self, query: str, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ищет в транскриптах встреч по запросу
        
        Args:
            query: Поисковый запрос
            user_id: ID пользователя (для фильтрации по встречам пользователя)
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных сегментов транскриптов
        """
        try:
            payload = {
                "query": query,
                "limit": limit
            }
            
            if user_id:
                payload["user_id"] = str(user_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.engine_url}/api/v1/search",
                    headers=self.headers,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при поиске в транскриптах: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка поиска в транскриптах: {error_text}")
                    
                    data = await response.json()
            
            results = data.get("results", [])
            logger.info(f"Найдено {len(results)} результатов по запросу '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске в транскриптах: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка поиска в транскриптах: {str(e)}")

    async def upload_audio_chunk(self, connection_id: str, chunk_index: int, audio_data: bytes, meeting_id: Optional[str] = None, source: str = "google_meet") -> Dict[str, Any]:
        """
        Загружает чанк аудио через Stream API Vexa
        
        Args:
            connection_id: ID соединения
            chunk_index: Индекс чанка
            audio_data: Бинарные данные аудио
            meeting_id: ID встречи (опционально)
            source: Источник аудио (google_meet, zoom, etc.)
            
        Returns:
            Информация о загруженном чанке
        """
        # Формируем URL с параметрами
        url = f"{self.stream_url}/api/v1/extension/audio?i={chunk_index}&connection_id={connection_id}&source={source}"
        
        if meeting_id:
            url += f"&meeting_id={meeting_id}"
        
        # Используем _make_request вместо прямой работы с сессией
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Для бинарных данных важно не устанавливать Content-Type
        result = await self._make_request("put", url, headers=headers, data=audio_data, timeout=5)
        
        # Возвращаем результат в согласованном формате
        if result.get("success"):
            return {"success": True, "result": result.get("data", {})}
        else:
            logger.error(f"Ошибка при загрузке аудиочанка: {result.get('error')}")
            return {"success": False, "error": result.get("error")}

    async def update_speakers(self, connection_id: str, speakers_data: Dict[str, Any], meeting_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Обновляет информацию о говорящих
        
        Args:
            connection_id: ID соединения
            speakers_data: Данные о говорящих
            meeting_id: ID встречи (опционально)
            
        Returns:
            Результат обновления
        """
        try:
            url = f"{self.stream_url}/api/v1/extension/speakers?connection_id={connection_id}"
            
            if meeting_id:
                url += f"&meeting_id={meeting_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=speakers_data,
                    timeout=5
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при обновлении информации о говорящих: {error_text}")
                        return {"success": False, "error": error_text}
                    
                    result = await response.json()
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о говорящих: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_meetings(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Получает список встреч пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество результатов
            offset: Смещение для пагинации
            
        Returns:
            Список встреч пользователя
        """
        try:
            params = {
                "user_id": str(user_id),
                "limit": limit,
                "offset": offset
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.engine_url}/api/v1/meetings",
                    headers=self.headers,
                    params=params,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при получении списка встреч: {error_text}")
                        raise HTTPException(status_code=500, detail=f"Ошибка получения списка встреч: {error_text}")
                    
                    data = await response.json()
            
            meetings = data.get("meetings", [])
            logger.info(f"Получено {len(meetings)} встреч для пользователя {user_id}")
            return meetings
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка встреч: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка получения списка встреч: {str(e)}")
            
    # Дополнительный метод для поиска релевантной информации из транскриптов для контекста LLM
    async def get_relevant_context(self, query: str, user_id: Optional[str] = None, limit: int = 5) -> str:
        """
        Ищет релевантную информацию в транскриптах для контекста запроса к LLM
        
        Args:
            query: Запрос пользователя
            user_id: ID пользователя (для фильтрации)
            limit: Максимальное количество релевантных фрагментов
            
        Returns:
            Строка с релевантным контекстом или пустая строка
        """
        try:
            # Поиск релевантных фрагментов
            search_results = await self.search_transcripts(query, user_id, limit)
            
            if not search_results:
                return ""
            
            # Форматирование результатов для контекста
            context_parts = []
            
            for result in search_results:
                meeting_title = result.get("meeting_title", "Встреча без названия")
                meeting_date = datetime.fromtimestamp(result.get("meeting_timestamp", 0)).strftime("%d.%m.%Y")
                speaker = result.get("speaker", "Участник")
                text = result.get("text", "")
                
                context_part = f"Из встречи '{meeting_title}' ({meeting_date}), {speaker}: {text}"
                context_parts.append(context_part)
            
            context = "\n\n".join(context_parts)
            return context
            
        except Exception as e:
            logger.error(f"Ошибка при получении релевантного контекста: {str(e)}")
            return ""  # В случае ошибки возвращаем пустую строку, а не исключение


    # Улучшенная версия _make_request в vexa_api_client.py
    async def _make_request(self, method, url, **kwargs):
        """Универсальный метод для выполнения запросов с повторными попытками"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with getattr(session, method.lower())(url, **kwargs) as response:
                        if response.status == 429:  # Too Many Requests
                            retry_after = int(response.headers.get('Retry-After', retry_delay))
                            logger.warning(f"Rate limit hit. Retrying after {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue
                            
                        if response.status >= 500:  # Server error
                            logger.warning(f"Server error {response.status}. Attempt {attempt+1}/{max_retries}")
                            await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                            continue
                            
                        # Проверка на ошибки аутентификации
                        if response.status == 401:
                            logger.error("Authentication error: Invalid API key")
                            return {"success": False, "status": response.status, "error": "Invalid API key"}
                            
                        if not response.ok:
                            error_text = await response.text()
                            logger.error(f"API Error ({response.status}): {error_text}")
                            return {"success": False, "status": response.status, "error": error_text}
                        
                        data = await response.json() if response.headers.get('Content-Type', '').startswith('application/json') else await response.text()
                        return {"success": True, "data": data, "status": response.status}
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                    return {"success": False, "error": str(e)}
                
                logger.warning(f"Request failed. Attempt {attempt+1}/{max_retries}: {str(e)}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
        
        return {"success": False, "error": "Maximum retries exceeded"}