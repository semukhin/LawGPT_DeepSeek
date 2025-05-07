"""
Модели для работы с результатами веб-скрапинга.
"""
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from urllib.parse import urlparse
import hashlib

@dataclass
class ScrapedContent:
    """Контейнер для результатов скрапинга веб-страницы."""
    url: str
    title: str
    text: str
    html: Optional[str] = None
    images: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now()
    error: Optional[str] = None
    
    def __post_init__(self):
        """Валидация после инициализации."""
        self._validate_url()
        self._validate_timestamp()
        self._init_metadata()
    
    def _validate_url(self) -> None:
        """Проверяет корректность URL."""
        parsed = urlparse(self.url)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"Некорректный URL: {self.url}")
    
    def _validate_timestamp(self) -> None:
        """Проверяет и конвертирует timestamp."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        elif not isinstance(self.timestamp, datetime):
            raise ValueError(f"Некорректный timestamp: {self.timestamp}")
    
    def _init_metadata(self) -> None:
        """Инициализирует метаданные."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata.update({
            "domain": urlparse(self.url).netloc,
            "content_length": len(self.text),
            "has_html": bool(self.html),
            "images_count": len(self.images) if self.images else 0,
            "scrape_timestamp": self.timestamp.isoformat()
        })
    
    def is_successful(self) -> bool:
        """Проверяет, успешно ли выполнен скрапинг."""
        return bool(self.text.strip() and not self.error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует результат в словарь."""
        data = asdict(self)
        data["timestamp"] = data["timestamp"].isoformat()
        return data
    
    def to_json(self) -> str:
        """Сериализует объект в JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapedContent':
        """Создает объект из словаря."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ScrapedContent':
        """Создает объект из JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_summary(self, max_length: int = 200) -> str:
        """Возвращает краткое описание результата скрапинга."""
        if self.error:
            return f"Error: {self.error}"
        text_preview = self.text[:max_length] + "..." if len(self.text) > max_length else self.text
        return f"Title: {self.title}\nURL: {self.url}\nPreview: {text_preview}"
    
    def get_content_hash(self) -> str:
        """Возвращает хеш контента для сравнения."""
        content = f"{self.title}{self.text}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def __eq__(self, other: object) -> bool:
        """Сравнивает два результата скрапинга."""
        if not isinstance(other, ScrapedContent):
            return NotImplemented
        return self.get_content_hash() == other.get_content_hash()
    
    def merge(self, other: 'ScrapedContent') -> 'ScrapedContent':
        """Объединяет два результата скрапинга."""
        if self.url != other.url:
            raise ValueError("Нельзя объединить результаты с разными URL")
            
        return ScrapedContent(
            url=self.url,
            title=self.title or other.title,
            text=f"{self.text}\n\n{other.text}".strip(),
            html=self.html or other.html,
            images=list(set(self.images or [] + other.images or [])),
            metadata={**self.metadata, **other.metadata},
            timestamp=max(self.timestamp, other.timestamp),
            error=None
        ) 