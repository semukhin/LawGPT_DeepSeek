# app/handlers/deepresearch.py
from fastapi import APIRouter, HTTPException
from app.services.research_factory import ResearchAdapter
from app.config import USE_SHANDU_RESEARCH_AGENT

router = APIRouter()

# Условная инициализация нужного провайдера
if USE_SHANDU_RESEARCH_AGENT:
    from third_party.shandu.agents.agent import ResearchAgent
    # Для OpenAI нужны другие параметры
    deepresearch_service = ResearchAgent(
        max_depth=3,    # Глубина рекурсивного исследования
        breadth=4       # Количество параллельных запросов
    )
else:
    from app.services.deepresearch_service import DeepResearchService
    deepresearch_service = DeepResearchService(output_dir="research_results")



# Инициализируем сервис через адаптер
deepresearch_service = ResearchAdapter(output_dir="research_results")

@router.get("/deep_research")
async def perform_deep_research(query: str):
    """
    Эндпоинт для выполнения глубокого исследования.
    
    Параметры:
        query (str): Запрос для проведения исследования.
    
    Возвращает:
        dict: Содержит исходный запрос и результат исследования.
    """
    try:
        result = await deepresearch_service.research(query)
        return {"query": query, "result": result.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))