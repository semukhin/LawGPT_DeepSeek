"""
Сервис для работы с DeepSeek API.
Обеспечивает интерфейс для генерации текста с использованием моделей DeepSeek.
Поддерживает function calling и многораундовые диалоги.
"""
import os
import logging
import json
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Union, Literal

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DeepSeekService:
    """
    Сервис для выполнения запросов к DeepSeek API.
    Поддерживает вызов функций и многораундовые диалоги.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 60
    ):
        """
        Инициализирует сервис с параметрами API DeepSeek.
        
        Args:
            api_key: API ключ DeepSeek (если None, берется из конфигурации)
            api_base: Базовый URL API (если None, берется из конфигурации)
            model: Имя модели для использования
            temperature: Параметр температуры для генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
            timeout: Таймаут запроса в секундах
        """
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_base = api_base or DEEPSEEK_API_BASE or "https://api.deepseek.com/v1"
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            logging.warning("DeepSeek API ключ не указан. API не будет работать.")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None
    ) -> Union[str, Dict[str, Any]]:
        """
        Отправляет запрос к DeepSeek Chat API и возвращает ответ.
        
        Args:
            messages: Список сообщений в формате [{role: "user|system|assistant|function", content: "текст"}]
            functions: Список доступных функций в формате JSON Schema
            function_call: Настройка вызова функций ("auto", "none" или {"name": "имя_функции"})
            temperature: Параметр температуры (переопределяет значение из конструктора)
            max_tokens: Максимальное количество токенов (переопределяет значение из конструктора)
            stream: Использовать потоковый режим ответа
            top_p: Параметр top-p сэмплинга
            presence_penalty: Штраф за повторение тем
            frequency_penalty: Штраф за повторение токенов
            
        Returns:
            Текст ответа от API или полный ответ API (если return_full_response=True)
        """
        if not self.api_key:
            return "Ошибка: API ключ DeepSeek не настроен"
        
        url = f"{self.api_base}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Формируем payload с обязательными параметрами
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": stream
        }
        
        # Добавляем опциональные параметры
        if functions:
            payload["functions"] = functions
        
        if function_call:
            payload["function_call"] = function_call
            
        if top_p is not None:
            payload["top_p"] = top_p
            
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
            
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        
        try:
            logging.info(f"Отправка запроса к DeepSeek API: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Ошибка DeepSeek API ({response.status}): {error_text}")
                        return f"Ошибка API: {response.status} - {error_text}"
                    
                    if stream:
                        # Обработка потокового ответа
                        full_response = ""
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: ') and line != 'data: [DONE]':
                                json_str = line[6:]  # Убираем 'data: '
                                try:
                                    chunk = json.loads(json_str)
                                    content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                    if content:
                                        full_response += content
                                except json.JSONDecodeError:
                                    logging.error(f"Ошибка декодирования JSON из потока: {line}")
                        return full_response
                    else:
                        # Обработка обычного ответа
                        response_json = await response.json()
                        
                        # Проверка наличия вызова функции в ответе
                        choice = response_json['choices'][0]
                        if 'function_call' in choice.get('message', {}):
                            logging.info("Обнаружен вызов функции в ответе DeepSeek")
                            return response_json
                        
                        # Возвращаем только содержимое сообщения, если нет вызова функции
                        return choice['message']['content']
                        
        except asyncio.TimeoutError:
            logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {self.timeout} сек)")
            return "Ошибка: превышен таймаут запроса к API"
        except Exception as e:
            logging.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
            return f"Ошибка: {str(e)}"

    async def generate_text(self, prompt: str) -> str:
        """
        Генерирует текст на основе промпта.
        
        Args:
            prompt: Текстовый промпт для генерации
            
        Returns:
            Сгенерированный текст
        """
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages)
        if isinstance(response, dict):
            return response.get('choices', [{}])[0].get('message', {}).get('content', 'Ошибка получения текста')
        return response
    
    async def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        Генерирует текст с использованием системного и пользовательского промпта.
        
        Args:
            system_prompt: Системный промпт для задания контекста
            user_prompt: Пользовательский промпт
            
        Returns:
            Сгенерированный текст
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = await self.chat_completion(messages)
        if isinstance(response, dict):
            return response.get('choices', [{}])[0].get('message', {}).get('content', 'Ошибка получения текста')
        return response
        
    async def chat_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Union[Literal["auto"], Literal["none"], Dict[str, str]] = "auto"
    ) -> Dict[str, Any]:
        """
        Отправляет запрос к DeepSeek с поддержкой вызова функций.
        
        Args:
            messages: История диалога
            functions: Описание функций в формате JSON Schema
            function_call: Режим вызова функций
            
        Returns:
            Полный ответ API, включая возможный вызов функции
        """
        return await self.chat_completion(
            messages=messages,
            functions=functions,
            function_call=function_call,
            # Возвращаем полный ответ для обработки возможного вызова функции
        )