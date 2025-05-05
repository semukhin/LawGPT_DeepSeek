# app/services/research_factory.py

from app.config import USE_SHANDU_RESEARCH_AGENT
from typing import Union, Any

def create_research_service(output_dir: str = None) -> Any:
    """
    Фабричный метод для создания сервиса исследования.
    
    Args:
        output_dir: Директория для сохранения результатов (только для DeepSeek)
    
    Returns:
        Экземпляр ResearchAgent или DeepResearchService
    """
    if USE_SHANDU_RESEARCH_AGENT:
        from third_party.shandu.agents.agent import ResearchAgent
        return ResearchAgent(
            max_depth=3,
            breadth=4
        )
    else:
        from app.services.deepresearch_service import DeepResearchService
        return DeepResearchService(output_dir=output_dir or "research_results")

# Адаптер для унификации интерфейса
class ResearchAdapter:
    """
    Адаптер для унификации интерфейса между ResearchAgent и DeepResearchService.
    Позволяет использовать их взаимозаменяемо.
    """
    def __init__(self, output_dir: str = None):
        self.service = create_research_service(output_dir)
        self.is_shandu = USE_SHANDU_RESEARCH_AGENT
    
    async def research(self, query: str, thread_id: str = None, user_id: int = None, db = None, message_id: int = None):
        """Универсальный метод исследования с поддержкой сохранения в БД."""
        if self.is_shandu:
            # ResearchAgent не поддерживает сохранение в БД, просто вызываем sync-метод
            return self.service.research_sync(query)
        else:
            # DeepResearchService поддерживает все параметры
            return await self.service.research(query, thread_id=thread_id, user_id=user_id, db=db, message_id=message_id)