from fastapi import APIRouter, HTTPException
from app.services.deepresearch_service import DeepResearchService

# Инициализация роутера для регистрации маршрутов
router = APIRouter()

# Инициализируем сервис DeepResearchService с указанием директории для сохранения результатов
deepresearch_service = DeepResearchService(output_dir="research_results")

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
        result = await deepresearch_service.research(query)  # Выполнение асинхронного исследования
        return {"query": query, "result": result.to_dict()}  # Возврат результата в словаре
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # Обработка и возврат ошибки с кодом 500
