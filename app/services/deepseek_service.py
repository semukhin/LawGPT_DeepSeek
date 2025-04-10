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
from fastapi import HTTPException


from app.config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL

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
        model: str = "deepseek-reasoner",
        temperature: float = 1.2,
        max_tokens: int = 8192,
        timeout: int = 180
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
        messages: List[Dict[str, Any]],
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        model: Optional[str] = None
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
            model: Явное указание модели (если отличается от умолчательной)
            
        Returns:
            Текст ответа от API или полный ответ API
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
            "model": model or self.model,  # Используем переданную модель или дефолтную
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
            # Устанавливаем фиксированный таймаут в 180 секунд 3 минуты)
            fixed_timeout = 180
            
            logging.info(f"Отправка запроса к DeepSeek API: {url}")
            logging.debug(f"Payload: {json.dumps(payload)}")
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        url, 
                        headers=headers, 
                        json=payload,
                        timeout=fixed_timeout
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
                            logging.debug(f"Ответ API: {json.dumps(response_json)}")
                            
                            # Возвращаем полный ответ для проверки наличия function_call
                            return response_json
                except asyncio.TimeoutError:
                    # Таймаут в 3 минуты превышен
                    logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                    return "Сервис пока не может обработать ваш запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
                
        except Exception as e:
            logging.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
            return f"Ошибка: {str(e)}" 


async def _generate(
    self, 
    messages: List[Dict], 
    functions: Optional[List[Dict]] = None,
    max_tokens: int = 8192
) -> str:
    """
    Внутренний метод генерации ответа с проверкой ограничений.
    
    Args:
        messages: Список сообщений
        functions: Список доступных функций
        max_tokens: Максимальное количество токенов
    """
    # Строгая проверка max_tokens
    max_tokens = max(1, min(max_tokens, 8192))
    
    # Фиксированный таймаут в 180 секунд
    fixed_timeout = 180
    
    payload = {
        "model": self.model,
        "messages": messages,
        "temperature": self.temperature,
        "max_tokens": max_tokens
    }
    
    if functions:
        payload["functions"] = functions
        payload["function_call"] = "auto"
    
    try:
        logging.info(f"Отправка запроса к DeepSeek API: {self.api_base}/chat/completions")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=fixed_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"API Error: {error_text}")
                        raise ValueError(f"API Error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    return result['choices'][0]['message']['content']
            
            except asyncio.TimeoutError:
                logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                return "Сервис пока не может обработать запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
                
    except Exception as e:
        logging.error(f"Ошибка при запросе к DeepSeek API: {str(e)}")
        return f"Ошибка API: {str(e)}"
        
        
        
async def chat_with_functions(
    self,
    messages: List[Dict[str, Any]],
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
    # Включаем более подробную отладку для функциональных вызовов
    logging.info(f"Запрос chat_with_functions, function_call={function_call}")
    
    # Фиксированный таймаут в 180 секунд
    fixed_timeout = 180
    
    # Формируем payload
    url = f"{self.api_base}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}"
    }
    
    payload = {
        "model": self.model,
        "messages": messages,
        "temperature": 1.2,
        "max_tokens": self.max_tokens,
        "functions": functions,
        "function_call": function_call
    }
    
    logging.debug(f"Отправляемый payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        logging.info(f"Отправка запроса к DeepSeek API: {url}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=payload,
                    timeout=fixed_timeout
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logging.error(f"Ошибка DeepSeek API ({response.status}): {response_text[:200]}...")
                        return f"Ошибка API: {response.status} - {response_text[:200]}..."
                    
                    try:
                        response_json = json.loads(response_text)
                        
                        # Проверяем наличие function_call в ответе
                        if 'choices' in response_json and len(response_json['choices']) > 0:
                            choice = response_json['choices'][0]
                            message = choice.get('message', {})
                            
                            if 'function_call' in message:
                                logging.info(f"✅ Function call найден: {message['function_call'].get('name')}")
                            else:
                                logging.warning("⚠️ Function call не найден в ответе")
                        
                        return response_json
                    except json.JSONDecodeError:
                        logging.error(f"Ошибка декодирования JSON ответа: {response_text[:200]}...")
                        return f"Ошибка декодирования ответа API: {response_text[:200]}..."
            
            except asyncio.TimeoutError:
                logging.error(f"Таймаут запроса к DeepSeek API (превышен лимит {fixed_timeout} сек)")
                return "Сервис пока не может обработать запрос. Попытайтесь, пожалуйста, отправить повторный запрос через минуту."
        
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при запросе к DeepSeek API: {str(e)}")
        return f"Ошибка: {str(e)}"