"""
Сервис для работы с эмбеддингами.
Использует sentence-transformers для генерации векторных представлений текста.
"""
import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import torch
import logging
from app.utils.logger import get_logger, LogLevel

logger = get_logger()

class EmbeddingService:
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._initialize_model()
    
    def _initialize_model(self):
        """Инициализирует модель для создания эмбеддингов."""
        try:
            # Используем модель paraphrase-multilingual-mpnet-base-v2 для поддержки русского языка
            model_name = "paraphrase-multilingual-mpnet-base-v2"
            logger.log(f"🔄 Загрузка модели {model_name}...", LogLevel.INFO)
            
            # Проверяем наличие CUDA
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.log(f"🖥️ Используется устройство: {device}", LogLevel.INFO)
            
            self._model = SentenceTransformer(model_name, device=device)
            logger.log("✅ Модель успешно загружена", LogLevel.INFO)
            
        except Exception as e:
            logger.log(f"❌ Ошибка при инициализации модели: {str(e)}", LogLevel.ERROR)
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для текста.
        
        Args:
            text: Входной текст
            
        Returns:
            List[float]: Вектор эмбеддинга
        """
        try:
            # Проверяем инициализацию модели
            if self._model is None:
                self._initialize_model()
            
            # Получаем эмбеддинг
            embedding = self._model.encode(text, convert_to_tensor=False)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.log(f"❌ Ошибка при получении эмбеддинга: {str(e)}", LogLevel.ERROR)
            # Возвращаем нулевой вектор в случае ошибки
            return [0.0] * 384
    
    async def get_embedding_async(self, text: str) -> List[float]:
        """
        Асинхронная версия получения эмбеддинга.
        
        Args:
            text: Входной текст
            
        Returns:
            List[float]: Вектор эмбеддинга
        """
        return self.get_embedding(text)  # Синхронный вызов в асинхронной обертке
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Получает эмбеддинги для списка текстов.
        
        Args:
            texts: Список текстов
            
        Returns:
            List[List[float]]: Список векторов эмбеддингов
        """
        try:
            if self._model is None:
                self._initialize_model()
            
            embeddings = self._model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
            
        except Exception as e:
            logger.log(f"❌ Ошибка при получении пакетных эмбеддингов: {str(e)}", LogLevel.ERROR)
            return [[0.0] * 384] * len(texts) 