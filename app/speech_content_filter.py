import re
import nltk
from typing import List, Dict

class SpeechContentFilter:
    def __init__(self, language='ru'):
        """
        Фильтр содержимого речи с поддержкой цензуры и безопасности
        
        :param language: Язык фильтрации
        """
        self.language = language
        self.blacklists = self._load_blacklists()
        self.sensitive_patterns = self._load_sensitive_patterns()
    
    def _load_blacklists(self) -> Dict[str, List[str]]:
        """
        Загрузка списков запрещенных слов
        """
        blacklists = {
            'ru': [
                # Нецензурная лексика
                'бля', 'хуй', 'пизд', 'еба', 'сука', 
                # Оскорбительные термины
                'дура', 'идиот', 'придурок'
            ],
            'en': [
                'fuck', 'shit', 'bitch', 'asshole', 
                'damn', 'cunt', 'dick'
            ]
        }
        return blacklists.get(self.language, [])
    
    def _load_sensitive_patterns(self) -> List[Dict]:
        """
        Загрузка шаблонов для обнаружения чувствительной информации
        """
        return [
            {
                'pattern': r'\b\d{10,}\b',  # Номера телефонов
                'replacement': '[НОМЕР СКРЫТ]'
            },
            {
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                'replacement': '[EMAIL СКРЫТ]'
            },
            {
                'pattern': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP-адреса
                'replacement': '[IP СКРЫТ]'
            }
        ]
    
    def censor_text(self, text: str) -> str:
        """
        Цензурирование текста
        
        :param text: Исходный текст
        :return: Отфильтрованный текст
        """
        # Преобразуем текст в нижний регистр для сравнения
        censored_text = text.lower()
        
        # Замена нецензурной лексики
        for bad_word in self.blacklists:
            # Регулярное выражение для поиска слова с учетом окончаний
            pattern = rf'\b{bad_word}\w*\b'
            censored_text = re.sub(pattern, '[ЦЕНЗУРА]', censored_text)
        
        return censored_text
    
    def anonymize_text(self, text: str) -> str:
        """
        Анонимизация чувствительной информации
        
        :param text: Исходный текст
        :return: Анонимизированный текст
        """
        anonymized_text = text
        
        for sensitive_pattern in self.sensitive_patterns:
            anonymized_text = re.sub(
                sensitive_pattern['pattern'], 
                sensitive_pattern['replacement'], 
                anonymized_text
            )
        
        return anonymized_text
    
    def detect_intent(self, text: str) -> Dict[str, float]:
        """
        Определение намерения пользователя
        
        :param text: Распознанный текст
        :return: Словарь с вероятностями намерений
        """
        # Простая эвристика определения намерения
        intents = {
            'question': 0.0,
            'statement': 0.0,
            'request': 0.0,
            'complaint': 0.0
        }
        
        # Определение вопроса
        if '?' in text:
            intents['question'] = 0.8
        
        # Определение жалобы
        complaint_keywords = ['жалоб', 'недовол', 'пробл', 'наруш']
        if any(keyword in text.lower() for keyword in complaint_keywords):
            intents['complaint'] = 0.7
        
        # Определение запроса
        request_keywords = ['помо', 'нужн', 'хочу', 'треб']
        if any(keyword in text.lower() for keyword in request_keywords):
            intents['request']