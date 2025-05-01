import logging
from typing import Dict, Any
from app.handlers.es_law_search import search_law_chunks
from app.handlers.web_search import search_and_scrape
import asyncio
import time
import re
import chardet
from app.handlers.web_search import run_multiple_searches

def ensure_correct_encoding(text: str) -> str:
    """
    Проверяет и исправляет кодировку текста, обеспечивая UTF-8.
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Текст в корректной кодировке UTF-8
    """
    if not text:
        return ""

    # Если текст уже в виде строки
    if isinstance(text, str):
        try:
            # Пробуем сначала исправить кириллицу в URL-кодировке
            text = re.sub(r'%D0%[89AB][0-9A-F]%D0%[89AB][0-9A-F]', 
                         lambda m: bytes.fromhex(m.group(0).replace('%', '')).decode('utf-8'), 
                         text)
            text = re.sub(r'%D0%[89AB][0-9A-F]', 
                         lambda m: bytes.fromhex(m.group(0).replace('%', '')).decode('utf-8'), 
                         text)
            
            # Исправляем неправильно декодированные символы
            replacements = {
                'Ð°': 'а', 'Ð±': 'б', 'Ð²': 'в', 'Ð³': 'г', 'Ð´': 'д',
                'Ðµ': 'е', 'Ñ': 'ё', 'Ð¶': 'ж', 'Ð·': 'з', 'Ð¸': 'и',
                'Ð¹': 'й', 'Ðº': 'к', 'Ð»': 'л', 'Ð¼': 'м', 'Ð½': 'н',
                'Ð¾': 'о', 'Ð¿': 'п', 'Ñ€': 'р', 'Ñ': 'с', 'Ñ‚': 'т',
                'Ñƒ': 'у', 'Ñ„': 'ф', 'Ñ…': 'х', 'Ñ†': 'ц', 'Ñ‡': 'ч',
                'Ñˆ': 'ш', 'Ñ‰': 'щ', 'ÑŠ': 'ъ', 'Ñ‹': 'ы', 'ÑŒ': 'ь',
                'Ñ': 'э', 'Ñž': 'ю', 'Ñ': 'я'
            }
            
            # Применяем все замены
            for wrong, correct in replacements.items():
                text = text.replace(wrong, correct)
            
            # Пробуем перекодировать через bytes для исправления возможных проблем
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            
            # Удаляем оставшиеся проблемные символы и нормализуем пробелы
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
        except Exception as e:
            logging.error(f"Ошибка при обработке кодировки: {e}")
            return text
            
    # Если текст в bytes
    if isinstance(text, bytes):
        try:
            # Определяем кодировку
            detected = chardet.detect(text)
            if detected and detected['encoding']:
                # Пробуем декодировать с обнаруженной кодировкой
                return text.decode(detected['encoding'], errors='ignore')
        except Exception as e:
            logging.error(f"Ошибка при определении кодировки bytes: {e}")
            pass
            
        # Если не удалось определить кодировку, пробуем UTF-8
        try:
            return text.decode('utf-8', errors='ignore')
        except UnicodeError:
            # В крайнем случае используем Latin-1
            return text.decode('latin1', errors='ignore')
            
    # Если текст другого типа, преобразуем в строку
    return str(text)

async def run_parallel_search(query: str) -> Dict[str, Any]:
    """
    Выполняет параллельный поиск в разных источниках.
    """
    logging.info(f"🚀 Запуск параллельного поиска для запроса: '{query}'")
    
    # Результаты поиска
    search_results = {}
    combined_context = ""
    start_time = time.time()
    
    try:
        # 1. Поиск в Elasticsearch
        logging.info("⏳ Поиск в Elasticsearch...")
        try:
            es_results = search_law_chunks(query)
            if es_results:
                search_results["elasticsearch"] = es_results
                combined_context += "\n\n## Российское законодательство:\n\n"
                # Преобразуем результаты в строки, если они словари
                formatted_results = []
                
                # Определяем, содержит ли запрос номер судебного дела
                case_number_pattern = r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*'
                has_case_number = bool(re.search(case_number_pattern, query))
                
                for result in es_results:
                    if isinstance(result, dict):
                        # Если это судебное решение и в запросе есть номер дела,
                        # берем полный текст без ограничений
                        if has_case_number and result.get('source') == 'court_decisions':
                            text = result.get('text', '')
                        else:
                            # Для остальных результатов увеличиваем лимит до 5000 символов
                            text = result.get('text', '')[:5000]
                        
                        source = result.get('source', '')
                        formatted_text = f"Источник: {source}\n{text}" if source else text
                        formatted_results.append(formatted_text)
                    else:
                        formatted_results.append(str(result))
                
                # Берем больше результатов для судебной практики
                max_results = 10 if has_case_number else 7
                combined_context += "\n\n---\n\n".join(formatted_results[:max_results])
                
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в Elasticsearch: {e}")
            
        # 2. Поиск в интернете
        logging.info("⏳ Поиск в интернете...")
        try:
            from app.handlers.web_search import run_multiple_searches
            web_results = await run_multiple_searches(query, [])
            if web_results and isinstance(web_results, dict):
                search_results["web"] = web_results
                if web_results.get("general"):
                    combined_context += "\n\n## Интернет-источники:\n\n"
                    for result in web_results["general"][:10]:  # Увеличиваем до топ-10 результатов
                        if isinstance(result, dict) and result.get("url") and result.get("text"):
                            # Проверяем кодировку текста
                            text = ensure_correct_encoding(result['text'])
                            combined_context += f"### Источник: {result['url']}\n\n"
                            combined_context += f"{text[:5000]}\n\n---\n\n"  # Увеличиваем лимит до 5000 символов
        except Exception as e:
            logging.error(f"❌ Ошибка при поиске в интернете: {e}")
            
        # Добавляем результаты в общий контекст
        search_results["combined_context"] = combined_context
        
        # Логируем время выполнения
        elapsed_time = time.time() - start_time
        logging.info(f"✅ Параллельный поиск завершен за {elapsed_time:.2f} секунд")
        
        return search_results
        
    except Exception as e:
        logging.error(f"❌ Ошибка при параллельном поиске: {e}")
        return {"error": str(e)}