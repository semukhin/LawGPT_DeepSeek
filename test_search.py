import asyncio
import logging
from app.handlers.web_search import WebSearchHandler

async def test_search():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    
    # Создаем обработчик поиска
    search_handler = WebSearchHandler()
    
    # Примеры запросов разной сложности
    queries = [
        "новости о законодательстве РФ",
        "как правильно составить исковое заявление в суд общей юрисдикции по гражданскому делу о взыскании долга",
        "последние изменения в налоговом кодексе РФ 2024 года и их влияние на малый бизнес"
    ]
    
    for query in queries:
        logger.info(f"\n=== Тестирование запроса: {query} ===")
        
        # Выполняем поиск
        results = await search_handler.search_internet(query, max_results=5)
        
        # Выводим результаты
        logger.info(f"Найдено результатов: {len(results)}")
        for i, result in enumerate(results, 1):
            logger.info(f"\nРезультат {i}:")
            logger.info(f"URL: {result.url}")
            logger.info(f"Заголовок: {result.title}")
            logger.info(f"Сниппет: {result.snippet[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_search()) 