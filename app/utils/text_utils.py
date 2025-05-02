import json
import logging
import chardet
from typing import Union, Dict, Any, List, Tuple
import re
from collections import Counter

def detect_encoding(text: Union[str, bytes]) -> Tuple[str, str, float]:
    """
    Определяет кодировку текста.
    
    Args:
        text: Текст для определения кодировки
        
    Returns:
        tuple: (encoding, confidence)
            - encoding: обнаруженная кодировка
            - confidence: уверенность в определении кодировки (0-1)
    """
    if isinstance(text, str):
        raw = text.encode('raw_unicode_escape')
    else:
        raw = text
        
    result = chardet.detect(raw)
    return result['encoding'], result['confidence']

def decode_unicode(text: str) -> str:
    """Декодирует Unicode escape sequences в читаемый текст"""
    try:
        # Сначала пробуем через json.loads
        return json.loads(f'"{text}"')
    except json.JSONDecodeError:
        try:
            # Если не получилось, пробуем через encode/decode
            return text.encode('utf-8').decode('unicode-escape').encode('latin1').decode('utf-8')
        except Exception:
            # Если и это не сработало, возвращаем исходный текст
            return text

def ensure_correct_encoding(text: Union[str, bytes, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """
    Проверяет и исправляет кодировку текста из любого источника.
    
    Args:
        text: Текст или словарь для проверки кодировки
        
    Returns:
        Union[str, Dict[str, Any]]: Текст или словарь с исправленной кодировкой
    """
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            # Определяем кодировку
            encoding, confidence = detect_encoding(text)
            if encoding and confidence > 0.8:
                try:
                    return text.decode(encoding)
                except Exception as e:
                    logging.error(f"Ошибка декодирования с определенной кодировкой {encoding}: {e}")
            
            # Если не удалось определить кодировку или декодировать, пробуем запасные варианты
            try:
                return text.decode('latin1').encode('utf-8').decode('utf-8')
            except Exception as e:
                logging.error(f"Ошибка декодирования bytes: {e}")
                return text.decode('utf-8', errors='ignore')
    
    elif isinstance(text, str):
        try:
            # Проверяем, является ли текст уже UTF-8
            text.encode('utf-8').decode('utf-8')
            # Если текст содержит escape-последовательности, декодируем их
            if '\\u' in text or '\\x' in text:
                return decode_unicode(text)
            return text
        except UnicodeError:
            try:
                # Определяем кодировку
                encoding, confidence = detect_encoding(text)
                if encoding and confidence > 0.8:
                    raw = text.encode('raw_unicode_escape')
                    try:
                        return raw.decode(encoding).encode('utf-8').decode('utf-8')
                    except Exception as e:
                        logging.error(f"Ошибка конвертации в UTF-8 из {encoding}: {e}")
                
                # Если не удалось определить кодировку или конвертировать, пробуем запасные варианты
                return text.encode('latin1').decode('utf-8')
            except Exception as e:
                logging.error(f"Ошибка обработки строки: {e}")
                return decode_unicode(text)
    
    elif isinstance(text, dict):
        return {k: ensure_correct_encoding(v) if isinstance(v, (str, bytes, dict)) else v 
                for k, v in text.items()}
    
    return text

def sanitize_search_results(results: list) -> list:
    """
    Обрабатывает результаты поиска, исправляя кодировку во всех текстовых полях.
    
    Args:
        results: Список результатов поиска
        
    Returns:
        list: Список результатов с исправленной кодировкой
    """
    sanitized = []
    for item in results:
        if isinstance(item, dict):
            sanitized_item = ensure_correct_encoding(item)
            sanitized.append(sanitized_item)
        elif isinstance(item, (str, bytes)):
            sanitized.append(ensure_correct_encoding(item))
        else:
            sanitized.append(item)
    return sanitized

def validate_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Проверяет и исправляет кодировку во всех сообщениях.
    
    Args:
        messages: Список сообщений для проверки
        
    Returns:
        List[Dict[str, Any]]: Список исправленных сообщений
    """
    validated_messages = []
    
    for message in messages:
        if not isinstance(message, dict):
            continue
            
        validated_message = message.copy()
        if 'content' in message and isinstance(message['content'], str):
            validated_message['content'] = ensure_correct_encoding(message['content'])
            
        validated_messages.append(validated_message)
        
    return validated_messages

def validate_context(context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Проверяет и исправляет кодировку во всем контексте.
    
    Args:
        context: Список контекстных данных
        
    Returns:
        List[Dict[str, Any]]: Список исправленного контекста
    """
    validated_context = []
    
    for item in context:
        if not isinstance(item, dict):
            continue
            
        validated_item = item.copy()
        if 'data' in item and isinstance(item['data'], str):
            validated_item['data'] = ensure_correct_encoding(item['data'])
            
        validated_context.append(validated_item)
        
    return validated_context 

def extract_keywords_ru(text: str, top_n: int = 12) -> str:
    """
    Извлекает ключевые слова из русского текста для формирования поискового запроса.
    Args:
        text (str): Исходный текст
        top_n (int): Сколько ключевых слов вернуть
    Returns:
        str: Строка из ключевых слов для поискового запроса
    """
    # Простейшая токенизация и фильтрация
    stopwords = set([
        'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его',
        'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от',
        'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже',
        'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом',
        'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их',
        'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда',
        'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти',
        'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при',
        'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про',
        'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
        'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно',
        'всю', 'между'
    ])
    # Оставляем только слова, убираем числа и спецсимволы
    words = re.findall(r"[а-яА-ЯёЁa-zA-Z]{3,}", text.lower())
    words = [w for w in words if w not in stopwords and len(w) > 3]
    freq = Counter(words)
    most_common = [w for w, _ in freq.most_common(top_n)]
    return " ".join(most_common) 