import logging
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
import re
import os
import json
from app.config import ELASTICSEARCH_URL, ES_INDICES as CONFIG_ES_INDICES

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USER = os.getenv("ES_USER", None)
ES_PASS = os.getenv("ES_PASS", None)


# Индексы в Elasticsearch с возможностью переопределения из конфигурации
DEFAULT_ES_INDICES = {
    "court_decisions": "court_decisions_index",
    "court_reviews": "court_reviews_index",
    "legal_articles": "legal_articles_index",
    "ruslawod_chunks": "ruslawod_chunks_index",
    "procedural_forms": "procedural_forms_index"
}

# Используем индексы из конфигурации или значения по умолчанию
ES_INDICES = CONFIG_ES_INDICES or DEFAULT_ES_INDICES

def get_es_client():
    """
    Создает и возвращает клиент Elasticsearch.
    
    Returns:
        Elasticsearch: Клиент Elasticsearch
    """
    try:
        # Проверяем, нужна ли авторизация
        if ES_USER and ES_PASS and ES_USER.lower() != 'none' and ES_PASS.lower() != 'none':
            # С авторизацией
            logger.info("Подключение к Elasticsearch с авторизацией")
            es = Elasticsearch(
                ELASTICSEARCH_URL,
                basic_auth=(ES_USER, ES_PASS),
                retry_on_timeout=True,
                max_retries=3
            )
        else:
            # Без авторизации
            logger.info("Подключение к Elasticsearch без авторизации")
            es = Elasticsearch(
                ELASTICSEARCH_URL,
                retry_on_timeout=True,
                max_retries=3
            )
        return es
    except Exception as e:
        logging.error(f"Ошибка подключения к Elasticsearch: {e}")
        raise


# Умный поиск - новый класс для интеллектуального поиска
class SmartSearchService:
    """Сервис для интеллектуального поиска в Elasticsearch"""
    
    def __init__(self, es_client):
        self.es = es_client
        self.court_decisions_index = ES_INDICES.get("court_decisions", "court_decisions_index")
        self.court_reviews_index = ES_INDICES.get("court_reviews", "court_reviews_index")
        self.legal_articles_index = ES_INDICES.get("legal_articles", "legal_articles_index")
        self.ruslawod_chunks_index = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
        self.procedural_forms_index = ES_INDICES.get("procedural_forms", "procedural_forms_index")
    

    def extract_case_number(self, query: str) -> Optional[str]:
        """Извлекает номер дела из текста запроса"""
        # Расширенный шаблон для поиска номеров дел различных форматов
        pattern = r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*'
        
        # Обеспечиваем, что текст запроса в правильной кодировке
        if isinstance(query, bytes):
            query = query.decode('utf-8')
        
        match = re.search(pattern, query)
        if match:
            case_number = match.group(0)
            logger.info(f"SmartSearchService: Извлечен номер дела: {case_number}")
            
            # Нормализуем год, если он в коротком формате (например, 05 -> 2005)
            parts = case_number.split('/')
            if len(parts) > 1:
                year_part = parts[1].split('-')[0]  # берем год до возможного суффикса
                if len(year_part) == 2:
                    # Преобразуем 2-значный год в 4-значный (05 -> 2005)
                    full_year = f"20{year_part}" if int(year_part) < 50 else f"19{year_part}"
                    case_number = case_number.replace(f"/{year_part}", f"/{full_year}", 1)
                    logger.info(f"SmartSearchService: Нормализован год в номере дела: {case_number}")
            
            return case_number
        logger.info(f"SmartSearchService: Номер дела не найден в запросе: '{query}'")
        return None
    

    def extract_company_name(self, query: str) -> Optional[str]:
        """Извлекает название компании из запроса"""
        # Поиск по шаблонам "ООО", "ЗАО", "ОАО", "ПАО" и т.д.
        patterns = [
            r'ООО\s+[«"]?([^»"]+)[»"]?',
            r'ЗАО\s+[«"]?([^»"]+)[»"]?',
            r'ОАО\s+[«"]?([^»"]+)[»"]?',
            r'ПАО\s+[«"]?([^»"]+)[»"]?',
            r'ИП\s+([А-Яа-я\s]+)',
            r'ОГРН\s+(\d{13}|\d{15})',
            r'ИНН\s+(\d{10}|\d{12})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        return None
    
    def extract_document_type(self, query: str) -> Optional[str]:
        """Извлекает тип документа из запроса"""
        logger.info(f"🔎 [DEBUG] Проверка типа документа для запроса: '{query}'")
        doc_types = [
                "исковое заявление", "иск", "претензия", "отзыв", "отзыв на исковое заявление", 
                "ходатайство", "апелляционная жалоба", "кассационная жалоба", 
                "заявление", "возражение", "договор", "соглашение", "жалоба", "мировое соглашение",
                "согласие", "административное исковое заявление", "замечаение", "ответ", "приложение к исковому заявлению",
                "расписка", "расчет", "контррасчет", "ответ на претензию", "замечания на протокол", "независимая гарантия",
                "ответ на определение суда", "расчет исковых требований", "расчет убытков"
            ]
        
        for doc_type in doc_types:
            if doc_type.lower() in query.lower():
                logger.info(f"🔎 [DEBUG] Найден тип документа: '{doc_type}'")
                return doc_type
        logger.info(f"🔎 [DEBUG] Тип документа не найден")
        return None
    
    def search_by_case_number(self, case_number: str, limit: int = 10) -> List[Dict]:
        """Поиск полного текста судебного решения по номеру дела"""
        logger.info(f"🔍 Поиск по номеру дела: {case_number}")
        
        # Разбираем номер дела на составные части
        full_case_number = case_number
        
        # Получаем базовую часть номера дела (без суффиксов после года)
        base_parts = full_case_number.split('-')
        court_code = base_parts[0]  # A40 или А40
        
        # Создаем варианты с разными алфавитами
        variants = []
        
        # Добавляем полный номер с обоими вариантами буквы А/A
        variants.append(full_case_number)
        if 'А' in full_case_number:
            variants.append(full_case_number.replace('А', 'A'))
        else:
            variants.append(full_case_number.replace('A', 'А'))
        
        # Если есть суффиксы после года, добавляем варианты без них
        if len(base_parts) > 2:
            year_parts = base_parts[1].split('/')
            if len(year_parts) > 1:
                base_case_number = f"{court_code}-{base_parts[1]}"
                variants.append(base_case_number)
                if 'А' in base_case_number:
                    variants.append(base_case_number.replace('А', 'A'))
                else:
                    variants.append(base_case_number.replace('A', 'А'))
        
        # Удаляем дубликаты
        variants = list(set(variants))
        logger.info(f"🔍 Варианты номера дела для поиска: {variants}")
        
        # Формируем запрос с учетом всех вариантов
        should_clauses = []
        for variant in variants:
            should_clauses.append({"term": {"case_number": variant}})
            should_clauses.append({"match_phrase": {"full_text": variant}})
        
        body = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "size": limit,
            "sort": [
                {"doc_id": {"order": "asc"}},
                {"chunk_id": {"order": "asc"}}
            ]
        }
        
        try:
            # Логируем запрос для отладки
            logger.info(f"🔍 DEBUG: Отправляем запрос: {json.dumps(body, ensure_ascii=False)}")
            
            response = self.es.search(index=self.court_decisions_index, body=body)
            hits = response["hits"]["hits"]
            
            if hits:
                # Собираем все чанки документа
                results = []
                doc_id_set = set()
                
                for hit in hits:
                    source = hit["_source"]
                    doc_id = source.get("doc_id", "")
                    doc_id_set.add(doc_id)
                    results.append(source)
                
                logger.info(f"🔍 Найдено {len(results)} чанков для дела {case_number} (документы: {len(doc_id_set)})")
                return results
            else:
                logger.warning(f"🔍 Дело {case_number} не найдено")
                return []
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске дела {case_number}: {str(e)}")
            logger.exception("Stacktrace:")
            return []
    
    def search_by_company(self, company: str, limit: int = 10) -> List[Dict]:
        """Поиск дел с участием указанной компании"""
        logger.info(f"🔍 Поиск дел с участием компании: {company}")
        
        body = {
            "size": limit,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"claimant": company}},
                        {"match": {"defendant": company}},
                        {"match": {"full_text": company}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "collapse": {
                "field": "doc_id"  # Группировка по документам
            },
            "_source": ["doc_id", "case_number", "court_name", "date", "subject", "claimant", "defendant"]
        }
        
        try:
            response = self.es.search(index=self.court_decisions_index, body=body)
            hits = response["hits"]["hits"]
            
            if hits:
                results = [hit["_source"] for hit in hits]
                logger.info(f"🔍 Найдено {len(results)} дел с участием {company}")
                return results
            else:
                logger.warning(f"🔍 Дела с участием {company} не найдены")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске компании {company}: {str(e)}")
            return []
    
    def search_by_text_fragment(self, text: str, limit: int = 10) -> List[Dict]:
        """Поиск фрагмента текста с контекстом (предыдущий и следующий чанки)"""
        logger.info(f"🔍 Поиск по фрагменту текста: {text[:100]}...")
        
        body = {
            "size": limit,
            "query": {
                "match_phrase": {
                    "full_text": text
                }
            },
            "highlight": {
                "fields": {
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                }
            }
        }
        
        try:
            response = self.es.search(index=self.court_decisions_index, body=body)
            hits = response["hits"]["hits"]
            
            if not hits:
                logger.warning(f"🔍 Фрагмент текста не найден")
                return []
            
            results = []
            
            for hit in hits:
                source = hit["_source"]
                doc_id = source.get("doc_id", "")
                chunk_id = source.get("chunk_id", 0)
                
                # Находим предыдущий и следующий чанки
                prev_chunk = self._get_adjacent_chunk(doc_id, chunk_id - 1)
                next_chunk = self._get_adjacent_chunk(doc_id, chunk_id + 1)
                
                # Добавляем контекст
                result = {
                    "current": source,
                    "highlight": hit.get("highlight", {}).get("full_text", []),
                    "prev": prev_chunk,
                    "next": next_chunk
                }
                
                results.append(result)
            
            logger.info(f"🔍 Найдено {len(results)} фрагментов текста с контекстом")
            return results
                
        except Exception as e:
            logger.error(f"❌ Ошибка при поиске фрагмента текста: {str(e)}")
            return []
    
    def _get_adjacent_chunk(self, doc_id: str, chunk_id: int) -> Optional[Dict]:
        """Получает смежный чанк документа"""
        if chunk_id < 1:
            return None
            
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"doc_id": doc_id}},
                        {"term": {"chunk_id": chunk_id}}
                    ]
                }
            }
        }
        
        try:
            response = self.es.search(index=self.court_decisions_index, body=body)
            hits = response["hits"]["hits"]
            
            if hits:
                return hits[0]["_source"]
            return None
                
        except Exception:
            return None
    
    def smart_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Умный анализ запроса и выбор подходящего метода поиска"""
        # Проверяем наличие номера дела в запросе
        case_number = self.extract_case_number(query)
        if case_number:
            logger.info(f"🧠 Определен поиск по номеру дела: {case_number}")
            results = self.search_by_case_number(case_number, limit)
            return {
                "type": "case_number",
                "query_entity": case_number,
                "results": results
            }
        
        # Проверяем наличие компании в запросе
        company = self.extract_company_name(query)
        if company:
            logger.info(f"🧠 Определен поиск по компании: {company}")
            results = self.search_by_company(company, limit)
            return {
                "type": "company",
                "query_entity": company,
                "results": results
            }
        
        # Проверяем наличие типа процессуального документа
        doc_type = self.extract_document_type(query)
        if doc_type:
            logger.info(f"🧠 Определен поиск по типу документа: {doc_type}")
            results = search_procedural_forms(query, min(limit, 5))  # Ограничиваем до 5 форм
            
            if results:
                return {
                    "type": "procedural_form",
                    "query_entity": doc_type,
                    "results": results
                }
        
        # По умолчанию ищем по тексту запроса
        logger.info(f"🧠 Определен поиск по тексту запроса")
        results = self.search_by_text_fragment(query, limit)
        return {
            "type": "text_fragment",
            "query_entity": query,
            "results": results
        }


# Инициализация сервиса умного поиска
_smart_search_service = None

def get_smart_search_service():
    """Синглтон для доступа к сервису умного поиска"""
    global _smart_search_service
    if _smart_search_service is None:
        _smart_search_service = SmartSearchService(get_es_client())
    return _smart_search_service


# Новая функция для извлечения номеров дел вне класса SmartSearchService
def extract_case_numbers_from_query(query: str) -> List[str]:
    """
    Извлекает номера дел из текста запроса и возвращает список возможных вариантов.
    
    Args:
        query: Текст запроса пользователя
        
    Returns:
        List[str]: Список вариантов номеров дел
    """
    # Расширенный шаблон для поиска номеров дел различных форматов
    pattern = r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*'
    
    # Обеспечиваем, что текст запроса в правильной кодировке
    if isinstance(query, bytes):
        query = query.decode('utf-8')
            
    match = re.search(pattern, query)
    
    if not match:
        logger.info(f"Номер дела не найден в запросе: '{query}'")
        return []
    
    # Получаем найденный номер дела
    case_number = match.group(0)
    logger.info(f"Извлечен номер дела: {case_number}")
    
    variants = [case_number]
    
    # Создаем вариации с разными буквами А/A
    if case_number.startswith("А"):  # русская А
        latin_variant = "A" + case_number[1:]
        variants.append(latin_variant)
        logger.info(f"Создан латинский вариант: {latin_variant}")
    elif case_number.startswith("A"):  # латинская A
        russian_variant = "А" + case_number[1:]
        variants.append(russian_variant)
        logger.info(f"Создан русский вариант: {russian_variant}")
    
    # Логируем все варианты для отладки
    logger.info(f"Сформированы варианты номера дела: {variants}")
    return variants


def search_procedural_forms(query: str, limit: int = 5) -> List[str]:
    """
    Поиск в индексе procedural_forms_index (процессуальные формы документов).
    
    Args:
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        es = get_es_client()
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("procedural_forms", "procedural_forms_index")
        
        # Проверяем существование индекса
        if not es.indices.exists(index=index_name):
            logger.warning(f"🔍 Индекс {index_name} не существует")
            return []
        
        # Валидация параметра limit
        size = max(1, limit)  # Гарантируем, что size будет положительным
        
        # Определяем тип документа из запроса
        smart_search = get_smart_search_service()
        doc_type = smart_search.extract_document_type(query)
        
        # Создаем поисковый запрос
        should_clauses = [
            {"match": {"full_text": {"query": query, "boost": 1.0}}},
            {"match": {"title": {"query": query, "boost": 3.0}}},
            {"match": {"subject_matter": {"query": query, "boost": 2.0}}},
            {"match": {"category": {"query": query, "boost": 1.5}}},
            {"match": {"subcategory": {"query": query, "boost": 1.5}}}
        ]
        
        # Если нашли тип документа, добавляем его в запрос
        if doc_type:
            should_clauses.append({"match": {"doc_type": {"query": doc_type, "boost": 4.0}}})
            logger.info(f"🔍 Определен тип документа: {doc_type}")
        
        body = {
            "size": size,
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "title": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                }
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            title = source.get("title", "")
            doc_type = source.get("doc_type", "")
            category = source.get("category", "")
            subcategory = source.get("subcategory", "")
            jurisdiction = source.get("jurisdiction", "")
            stage = source.get("stage", "")
            subject_matter = source.get("subject_matter", "")
            full_text = source.get("full_text", "")
            template_vars = source.get("template_variables", {})
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["title", "full_text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"ПРОЦЕССУАЛЬНАЯ ФОРМА: {title}\n"
            result += f"Тип документа: {doc_type}\n"
            
            if jurisdiction:
                result += f"Юрисдикция: {jurisdiction}\n"
            
            if category:
                result += f"Категория: {category}\n"
            
            if subcategory:
                result += f"Подкатегория: {subcategory}\n"
            
            if stage:
                result += f"Стадия: {stage}\n"
            
            if subject_matter:
                result += f"Предмет: {subject_matter}\n"
            
            # Добавляем информацию о шаблонных переменных, если они есть
            if template_vars and isinstance(template_vars, dict) and template_vars:
                result += f"\nШаблонные переменные для заполнения:\n"
                for key, value in template_vars.items():
                    if isinstance(value, list):
                        result += f"• {key}: [{', '.join(value)}]\n"
                    else:
                        result += f"• {key}: {value}\n"
            
            if highlight_text:
                result += f"\nРелевантные фрагменты:\n{highlight_text}\n\n"
            
            result += f"\nПолный текст документа:\n{full_text[:2000]}"
            if len(full_text) > 2000:
                result += "...[текст сокращен]"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} процессуальных форм документов")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе procedural_forms_index: {str(e)}")
        logger.exception("Подробная информация об ошибке:")
        return []


def search_law_chunks(query: str, top_n: int = 3) -> List[str]:
    """
    Поиск в Elasticsearch по всем индексам с учетом различных форматов номеров дел.
    
    Args:
        query: Текст запроса
        top_n: Максимальное количество результатов
        
    Returns:
        List[str]: Список найденных фрагментов законодательства
    """
    try:
        logger.info(f"🔍 [ES] Начало поиска в Elasticsearch для запроса: '{query}'")
        es = get_es_client()
        
        # Прямая попытка найти номер дела
        logger.info(f"🔍 [ES] Ищем номер дела напрямую")
        # Расширенный шаблон для поиска номеров дел различных форматов
        pattern = r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*'
        match = re.search(pattern, query)
        
        if match:
            # Если нашли номер дела, ищем по нему напрямую
            full_case_number = match.group(0)
            # Получаем базовую часть номера дела (без суффиксов)
            base_parts = full_case_number.split('-')
            if len(base_parts) >= 2:
                court_num_and_case = base_parts[0] + '-' + base_parts[1]
                year_parts = base_parts[1].split('/')
                if len(year_parts) > 1:
                    base_case_number = f"{court_num_and_case}/{year_parts[1].split('-')[0]}"
                    logger.info(f"🔍 [ES] Основная часть номера дела: {base_case_number}")
                else:
                    base_case_number = full_case_number
            else:
                base_case_number = full_case_number
            
            # Создаем русский и латинский варианты
            if base_case_number[0] == 'А':  # кириллическая А
                russian_version = base_case_number
                latin_version = 'A' + base_case_number[1:]
            else:  # латинская A
                latin_version = base_case_number
                russian_version = 'А' + base_case_number[1:]
                
            logger.info(f"🔍 [ES] Варианты номера дела - полный: {full_case_number}, базовый: {base_case_number}")
            logger.info(f"🔍 [ES] Варианты номера дела - рус: {russian_version}, лат: {latin_version}")
            
            # Прямой поиск по номеру дела включая полный формат и основную часть
            direct_query = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"case_number": full_case_number}},
                            {"term": {"case_number": full_case_number.replace("А", "A")}},
                            {"term": {"case_number": full_case_number.replace("A", "А")}},
                            {"term": {"case_number": base_case_number}},
                            {"term": {"case_number": base_case_number.replace("А", "A")}},
                            {"term": {"case_number": base_case_number.replace("A", "А")}},
                            {"match_phrase": {"full_text": full_case_number}},
                            {"match_phrase": {"full_text": full_case_number.replace("А", "A")}},
                            {"match_phrase": {"full_text": full_case_number.replace("A", "А")}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": top_n,
                "sort": [
                    {"doc_id": {"order": "asc"}},
                    {"chunk_id": {"order": "asc"}}
                ]
            }
            
            try:
                logger.info(f"🔍 [ES] Отправляем прямой запрос по номеру дела: {json.dumps(direct_query, ensure_ascii=False)}")
                direct_result = es.search(index="court_decisions_index", body=direct_query)
                direct_hits = direct_result["hits"]["hits"]
                
                if direct_hits:
                    logger.info(f"🔍 [ES] Прямой поиск успешен! Найдено {len(direct_hits)} документов")
                    
                    # Собираем результаты
                    formatted_results = []
                    
                    # Группируем по doc_id
                    docs = {}
                    for hit in direct_hits:
                        source = hit["_source"]
                        doc_id = source.get("doc_id", "unknown")
                        
                        if doc_id not in docs:
                            docs[doc_id] = {
                                "parts": [],
                                "metadata": {
                                    "case_number": source.get("case_number", ""),
                                    "court_name": source.get("court_name", ""),
                                    "date": source.get("date", ""),
                                    "subject": source.get("subject", ""),
                                    "claimant": source.get("claimant", ""),
                                    "defendant": source.get("defendant", "")
                                }
                            }
                        
                        docs[doc_id]["parts"].append({
                            "chunk_id": source.get("chunk_id", 0),
                            "text": source.get("full_text", "")
                        })
                    
                    # Формируем результат для каждого документа
                    for doc_id, doc in docs.items():
                        parts = sorted(doc["parts"], key=lambda x: x["chunk_id"])
                        metadata = doc["metadata"]
                        
                        result_text = f"Судебное дело № {metadata['case_number']}\n"
                        result_text += f"Суд: {metadata['court_name']}\n"
                        result_text += f"Дата: {metadata['date']}\n"
                        result_text += f"Предмет спора: {metadata['subject']}\n"
                        result_text += f"Истец: {metadata['claimant']}\n"
                        result_text += f"Ответчик: {metadata['defendant']}\n\n"
                        
                        full_text = ""
                        for part in parts:
                            full_text += part["text"]
                        
                        result_text += f"Полный текст решения:\n{full_text}"
                        formatted_results.append(result_text)
                    
                    logger.info(f"🔍 [ES] Дополнительно ищем в процессуальных формах")
                    procedural_forms_results = search_procedural_forms(query, min(3, top_n))
                    if procedural_forms_results:
                        formatted_results.extend(procedural_forms_results)
                        logger.info(f"🔍 [ES] Добавлено {len(procedural_forms_results)} процессуальных форм")
                    
                    logger.info(f"🔍 [ES] Возвращаем {len(formatted_results)} отформатированных документов")
                    return formatted_results
                else:
                    logger.warning(f"🔍 [ES] Дело {full_case_number} не найдено при прямом поиске")
            except Exception as e:
                logger.error(f"❌ Ошибка при прямом поиске: {str(e)}")
                logger.exception("Stacktrace:")
        
        # Если прямой поиск не сработал, пробуем через SmartSearchService
        logger.info(f"🔍 [ES] Пробуем поиск через SmartSearchService")
        smart_search = get_smart_search_service()
        case_number = smart_search.extract_case_number(query)
        company_name = smart_search.extract_company_name(query)
        doc_type = smart_search.extract_document_type(query)
        logger.info(f"🔍 [ES DEBUG] Результаты анализа запроса: case_number={case_number}, company_name={company_name}, doc_type={doc_type}")


        if case_number:
            logger.info(f"🔍 [ES] SmartSearchService обнаружил номер дела: {case_number}")
            search_results = smart_search.smart_search(query, top_n)
            
            if search_results["type"] == "case_number" and search_results["results"]:
                logger.info(f"🔍 [ES] SmartSearchService нашел {len(search_results['results'])} результатов")
                
                # Форматируем результаты
                formatted_results = []
                
                # Форматирование результатов полного текста дела
                case_number = search_results["query_entity"]
                results = search_results["results"]
                
                if results:
                    # Собираем полный текст дела
                    full_text_parts = []
                    metadata = None
                    
                    for result in sorted(results, key=lambda x: x.get("chunk_id", 0)):
                        if not metadata:
                            metadata = {
                                "case_number": result.get("case_number", ""),
                                "court_name": result.get("court_name", ""),
                                "date": result.get("date", ""),
                                "subject": result.get("subject", ""),
                                "claimant": result.get("claimant", ""),
                                "defendant": result.get("defendant", "")
                            }
                        
                        full_text_parts.append(result.get("full_text", ""))
                    
                    # Форматируем результат
                    result_text = f"Судебное дело № {metadata['case_number']}\n"
                    result_text += f"Суд: {metadata['court_name']}\n"
                    result_text += f"Дата: {metadata['date']}\n"
                    result_text += f"Предмет спора: {metadata['subject']}\n"
                    result_text += f"Истец: {metadata['claimant']}\n"
                    result_text += f"Ответчик: {metadata['defendant']}\n\n"
                    result_text += f"Полный текст решения:\n{''.join(full_text_parts)}"
                    
                    formatted_results.append(result_text)
                
                # Возвращаем отформатированные результаты
                if formatted_results:
                    logger.info(f"🔍 [ES] SmartSearchService: успешно отформатировано {len(formatted_results)} результатов")
                    
                    logger.info(f"🔍 [ES] Дополнительно ищем в процессуальных формах")
                    procedural_forms_results = search_procedural_forms(query, min(3, top_n))
                    if procedural_forms_results:
                        formatted_results.extend(procedural_forms_results)
                        logger.info(f"🔍 [ES] Добавлено {len(procedural_forms_results)} процессуальных форм")
                    
                    return formatted_results
        
        # Если найден тип документа, проверяем процессуальные формы
        if doc_type:
            logger.info(f"🔍 [ES] Найден тип документа: {doc_type}. Ищем в процессуальных формах")
            procedural_forms = search_procedural_forms(query, min(top_n, 3))
            
            if procedural_forms:
                logger.info(f"🔍 [ES] Найдено {len(procedural_forms)} процессуальных форм")
                
                # Форматируем результаты процессуальных форм
                formatted_results = []
                
                for form in procedural_forms:
                    formatted_results.append(form)
                
                # Если нашли процессуальные формы, возвращаем их + дополняем результатами из других источников
                if formatted_results:
                    logger.info(f"🔍 [ES] Возвращаем {len(formatted_results)} процессуальных форм")
                    
                    # Оставляем место для результатов из других источников
                    other_results_limit = top_n - len(formatted_results)
                    
                    # Если нужно, ищем еще и в других источниках
                    if other_results_limit > 0:
                        logger.info(f"🔍 [ES] Дополняем результаты из других источников (лимит: {other_results_limit})")
                        # Добавим результаты стандартного поиска к процессуальным формам
                        other_results = []
                        
                        # Разделим оставшееся количество между индексами
                        per_index_limit = max(1, other_results_limit // 3)
                        
                        # Поиск в остальных индексах
                        results1 = search_court_decisions(es, query, per_index_limit)
                        if results1:
                            other_results.extend(results1)
                        
                        results2 = search_ruslawod_chunks(es, query, per_index_limit)
                        if results2:
                            other_results.extend(results2)
                        
                        results3 = search_legal_articles(es, query, per_index_limit)
                        if results3:
                            other_results.extend(results3)
                        
                        # Объединяем результаты, сначала процессуальные формы
                        if other_results:
                            formatted_results.extend(other_results[:other_results_limit])
                            logger.info(f"🔍 [ES] Добавлено {len(other_results[:other_results_limit])} результатов из других источников")
                    
                    return formatted_results
        
        # Если все специальные методы не сработали, используем стандартный поиск
        logger.info(f"🔍 [ES] Используем стандартный поиск")
        
        # Распределяем количество результатов между разными индексами
        court_decisions_limit = max(2, top_n // 5)
        court_reviews_limit = max(1, top_n // 5)
        legal_articles_limit = max(1, top_n // 5)
        ruslawod_chunks_limit = max(1, top_n // 5)
        procedural_forms_limit = top_n - court_decisions_limit - court_reviews_limit - legal_articles_limit - ruslawod_chunks_limit
        
        # 1. Поиск в индексе court_decisions_index (судебные решения)
        logger.info(f"🔍 [ES] Выполняем стандартный поиск в court_decisions_index")
        court_decision_results = search_court_decisions(es, query, court_decisions_limit)
        results = court_decision_results.copy() if court_decision_results else []
        
        # 2. Поиск в индексе ruslawod_chunks_index (чанки законодательства)
        logger.info(f"🔍 [ES] Выполняем стандартный поиск в ruslawod_chunks_index")
        ruslawod_chunks_results = search_ruslawod_chunks(es, query, ruslawod_chunks_limit)
        if ruslawod_chunks_results:
            results.extend(ruslawod_chunks_results)
        
        # 3. Поиск в индексе court_reviews_index (обзоры судебных решений)
        logger.info(f"🔍 [ES] Выполняем стандартный поиск в court_reviews_index")
        court_reviews_results = search_court_reviews(es, query, court_reviews_limit)
        if court_reviews_results:
            results.extend(court_reviews_results)
        
        # 4. Поиск в индексе legal_articles_index (правовые статьи)
        logger.info(f"🔍 [ES] Выполняем стандартный поиск в legal_articles_index")
        legal_articles_results = search_legal_articles(es, query, legal_articles_limit)
        if legal_articles_results:
            results.extend(legal_articles_results)
        
        # 5. Поиск в индексе procedural_forms_index (процессуальные формы)
        logger.info(f"🔍 [ES] Выполняем стандартный поиск в procedural_forms_index")
        procedural_forms_results = search_procedural_forms(query, procedural_forms_limit)
        if procedural_forms_results:
            results.extend(procedural_forms_results)
        
        # Ограничиваем результаты по длине текста
        max_result_length = 4000  # максимальная длина одного фрагмента
        truncated_results = []
        
        for result in results:
            if len(result) > max_result_length:
                truncated_result = result[:max_result_length] + "... [текст обрезан из-за ограничений размера]"
                truncated_results.append(truncated_result)
            else:
                truncated_results.append(result)
        
        logger.info(f"🔍 [ES] Стандартный поиск: найдено всего {len(truncated_results)} релевантных результатов")
        return truncated_results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в Elasticsearch: {str(e)}")
        logger.exception("Stacktrace:")
        return []
    

def search_court_decisions(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе court_decisions_index (судебные решения).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем ПРАВИЛЬНОЕ имя индекса напрямую
        index_name = "court_decisions_index"
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Извлекаем номер дела из запроса с помощью регулярного выражения
        case_number_pattern = r'[АA]\d{1,2}-\d+/\d{2,4}(?:-[А-Яа-яA-Za-z0-9]+)*'
        case_number_matches = re.findall(case_number_pattern, query)
        
        case_numbers = []
        for number in case_number_matches:
            # Добавляем оригинальный номер
            case_numbers.append(number)
            # Добавляем вариант с другой буквой (А/A)
            if 'А' in number:
                case_numbers.append(number.replace('А', 'A'))
            else:
                case_numbers.append(number.replace('A', 'А'))
        
        if case_numbers:
            logger.info(f"🔍 [ES] Извлечены варианты номера дела: {case_numbers}")
            
            # Создаем поисковый запрос с альтернативными вариантами номера дела
            should_clauses = []
            for case_number in case_numbers:
                should_clauses.append({
                    "term": {
                        "case_number": case_number
                    }
                })
                # Добавляем также поиск по полному тексту для номеров дел
                should_clauses.append({
                    "match_phrase": {
                        "full_text": case_number
                    }
                })
            
            body = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1
                    }
                }
            }
            logger.info(f"🔍 [ES] Поиск по номеру дела: {json.dumps(should_clauses[:2], ensure_ascii=False)}")
        else:
            # Для остальных запросов используем обычный multi_match
            body = {
                "size": limit,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "case_number^5",
                            "judges^3",
                            "claimant^3",
                            "defendant^3",
                            "subject^2",
                            "arguments",
                            "conclusion",
                            "full_text"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
            }
        
        # Добавляем подсветку для любого типа запроса
        body["highlight"] = {
            "fields": {
                "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
            },
            "fragment_size": 300,
            "number_of_fragments": 3
        }
        
        # Выполняем поиск
        logger.info(f"🔍 [ES] Выполняем поиск: {json.dumps(body, ensure_ascii=False)[:200]}...")
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        # Логируем результаты поиска
        if hits:
            found_case_numbers = [hit["_source"].get("case_number", "N/A") for hit in hits[:3]]
            logger.info(f"🔍 [ES] Найдено {len(hits)} результатов. Первые номера дел: {', '.join(found_case_numbers)}")
        else:
            logger.warning(f"🔍 [ES] По запросу '{query}' результатов не найдено")
        
        results = []
        for hit in hits:
            source = hit["_source"]
            case_number = source.get("case_number", "")
            subject = source.get("subject", "")
            judges = source.get("judges", "")
            claimant = source.get("claimant", "")
            defendant = source.get("defendant", "")
            full_text = source.get("full_text", "")
            
            highlights = hit.get("highlight", {}).get("full_text", [])
            highlight_text = "...\n".join(highlights)
            
            result = f"Судебное дело № {case_number}\n"
            result += f"Судьи: {judges}\nИстец: {claimant}\nОтветчик: {defendant}\nПредмет: {subject}\n"
            
            if highlights:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            result += f"Полный текст:\n{full_text[:2000]}..."
            
            results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе court_decisions_index: {str(e)}")
        logger.exception("Подробная информация об ошибке:")
        return []


def search_ruslawod_chunks(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе ruslawod_chunks_index (чанки законодательства).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "text^3",
                        "content^3",
                        "full_text^2",
                        "law_name",
                        "section_name",
                        "article_name"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            law_name = source.get("law_name", "")
            section = source.get("section_name", source.get("section", ""))
            article = source.get("article_name", source.get("article", ""))
            content = source.get("content", source.get("text", source.get("full_text", "")))
            
            # Получаем дополнительные поля (если есть)
            document_id = source.get("document_id", "")
            chunk_id = source.get("chunk_id", "")
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["text", "content", "full_text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Законодательство: {law_name}\n"
            
            if section:
                result += f"Раздел: {section}\n"
            
            if article:
                result += f"Статья: {article}\n"
            
            if document_id and chunk_id:
                result += f"ID документа: {document_id}, ID фрагмента: {chunk_id}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Текст:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} фрагментов законодательства")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе ruslawod_chunks_index: {str(e)}")
        return []

def search_court_reviews(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе court_reviews_index (обзоры судебных решений).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("court_reviews", "court_reviews_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "content^3",
                        "description^2",
                        "text",
                        "full_text"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "title": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "full_text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            title = source.get("title", "Обзор судебной практики")
            content = source.get("content", source.get("text", source.get("full_text", "")))
            author = source.get("author", "")
            publication_date = source.get("publication_date", source.get("date", ""))
            source_name = source.get("source", "")
            
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["title", "content", "text", "full_text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Обзор судебной практики: {title}\n"
            
            if author:
                result += f"Автор: {author}\n"
            
            if publication_date:
                result += f"Дата публикации: {publication_date}\n"
            
            if source_name:
                result += f"Источник: {source_name}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Содержание:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} обзоров судебной практики")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе court_reviews_index: {str(e)}")
        return []

def search_legal_articles(es, query: str, limit: int) -> List[str]:
    """
    Поиск в индексе legal_articles_index (правовые статьи).
    
    Args:
        es: Клиент Elasticsearch
        query: Текст запроса
        limit: Максимальное количество результатов
        
    Returns:
        List[str]: Форматированные результаты
    """
    try:
        # Используем индекс из глобальной переменной или по умолчанию
        index_name = ES_INDICES.get("legal_articles", "legal_articles_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return []
        
        # Создаем поисковый запрос
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "content^3",
                        "description^2",
                        "body",
                        "text"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "title": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "content": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "body": {"pre_tags": ["<b>"], "post_tags": ["</b>"]},
                    "text": {"pre_tags": ["<b>"], "post_tags": ["</b>"]}
                },
                "fragment_size": 300,
                "number_of_fragments": 3
            }
        }
        
        # Выполняем поиск
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            
            # Получаем основные поля
            title = source.get("title", "Правовая статья")
            content = source.get("content", source.get("body", source.get("text", "")))
            author = source.get("author", "")
            publication_date = source.get("publication_date", source.get("date", ""))
            source_name = source.get("source", "")
            tags = source.get("tags", source.get("keywords", ""))
            # Получаем подсвеченные фрагменты
            highlights = []
            for field in ["title", "content", "body", "text"]:
                if hit.get("highlight", {}).get(field):
                    highlights.extend(hit["highlight"][field])
            
            highlight_text = "...\n".join(highlights) if highlights else ""
            
            # Формируем результат
            result = f"Правовая статья: {title}\n"
            
            if author:
                result += f"Автор: {author}\n"
            
            if publication_date:
                result += f"Дата публикации: {publication_date}\n"
            
            if source_name:
                result += f"Источник: {source_name}\n"
            
            if tags:
                tags_str = tags if isinstance(tags, str) else ", ".join(tags)
                result += f"Теги: {tags_str}\n"
            
            if highlight_text:
                result += f"Релевантные фрагменты:\n{highlight_text}\n\n"
            
            # Ограничиваем размер полного текста
            if content:
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                result += f"Содержание:\n{content_preview}"
            
            results.append(result)
        
        logger.info(f"🔍 [ES] Найдено {len(results)} правовых статей")
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в индексе legal_articles_index: {str(e)}")
        return []

def create_court_decisions_index(es):
    """
    Создает индекс court_decisions в Elasticsearch, если он не существует.
    
    Args:
        es: Клиент Elasticsearch
    """
    index_name = ES_INDICES.get("court_decisions", "court_decisions_index")
    
    # Проверяем, существует ли индекс
    if not es.indices.exists(index=index_name):
        # Определяем маппинг для индекса
        mappings = {
            "properties": {
                "case_number": {"type": "text", "analyzer": "russian"},
                "judges": {"type": "text", "analyzer": "russian"},
                "claimant": {"type": "text", "analyzer": "russian"},
                "defendant": {"type": "text", "analyzer": "russian"},
                "subject": {"type": "text", "analyzer": "russian"},
                "arguments": {"type": "text", "analyzer": "russian"},
                "conclusion": {"type": "text", "analyzer": "russian"},
                "full_text": {"type": "text", "analyzer": "russian"}
            }
        }
        
        # Создаем индекс
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "russian": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_morphology", "russian_stop"]
                            }
                        }
                    }
                },
                "mappings": mappings
            }
        )
        
        logger.info(f"✅ Индекс {index_name} успешно создан.")
    else:
        logger.info(f"✅ Индекс {index_name} уже существует.")

def create_ruslawod_chunks_index(es):
    """
    Создает индекс ruslawod_chunks_index в Elasticsearch, если он не существует.
    
    Args:
        es: Клиент Elasticsearch
    """
    index_name = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
    
    # Проверяем, существует ли индекс
    if not es.indices.exists(index=index_name):
        # Определяем маппинг для индекса
        mappings = {
            "properties": {
                "law_name": {"type": "text", "analyzer": "russian"},
                "section_name": {"type": "text", "analyzer": "russian"},
                "article_name": {"type": "text", "analyzer": "russian"},
                "document_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "content": {"type": "text", "analyzer": "russian"},
                "text": {"type": "text", "analyzer": "russian"},
                "full_text": {"type": "text", "analyzer": "russian"}
            }
        }
        
        # Создаем индекс
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "russian": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_morphology", "russian_stop"]
                            }
                        }
                    }
                },
                "mappings": mappings
            }
        )
        
        logger.info(f"✅ Индекс {index_name} успешно создан.")
    else:
        logger.info(f"✅ Индекс {index_name} уже существует.")

def create_procedural_forms_index(es):
    """
    Создает индекс procedural_forms_index в Elasticsearch, если он не существует.
    
    Args:
        es: Клиент Elasticsearch
    """
    index_name = ES_INDICES.get("procedural_forms", "procedural_forms_index")
    
    # Проверяем, существует ли индекс
    if not es.indices.exists(index=index_name):
        # Определяем маппинг для индекса
        mappings = {
            "properties": {
                "id": {"type": "integer"},
                "doc_id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "russian", 
                        "fields": {"keyword": {"type": "keyword"}}},
                "doc_type": {"type": "keyword"},
                "court_type": {"type": "keyword"},
                "target_court": {"type": "text", "analyzer": "russian"},
                "jurisdiction": {"type": "keyword"},
                "category": {"type": "keyword"},
                "subcategory": {"type": "keyword"},
                "applicant_type": {"type": "keyword"},
                "respondent_type": {"type": "keyword"},
                "third_parties": {"type": "keyword"},  # Массив строк
                "stage": {"type": "keyword"},
                "subject_matter": {"type": "text", "analyzer": "russian"},
                "keywords": {"type": "keyword"},  # Массив строк
                "legal_basis": {"type": "keyword"},  # Массив строк
                "full_text": {"type": "text", "analyzer": "russian"},
                "template_variables": {"type": "object"},  # JSONB
                "source_file": {"type": "keyword"},
                "creation_date": {"type": "date"},
                "last_updated": {"type": "date"},
                # Поля для обратной совместимости
                "content": {"type": "text", "analyzer": "russian", "copy_to": "full_text"},
                "text": {"type": "text", "analyzer": "russian", "copy_to": "full_text"},
                "indexed_at": {"type": "date"}
            }
        }
        
        # Создаем индекс
        es.indices.create(
            index=index_name,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "russian": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "russian_morphology", "russian_stop"]
                            }
                        }
                    }
                },
                "mappings": mappings
            }
        )
        
        logger.info(f"✅ Индекс {index_name} успешно создан.")
    else:
        logger.info(f"✅ Индекс {index_name} уже существует.")

def create_indices():
    """
    Создает все необходимые индексы в Elasticsearch.
    """
    try:
        es = get_es_client()
        
        # Создаем индексы
        create_court_decisions_index(es)
        create_ruslawod_chunks_index(es)
        create_procedural_forms_index(es)  # Добавлено создание индекса процессуальных форм
        
        # Также можно создать индексы для court_reviews_index и legal_articles_index
        # но пока оставим их без явного создания
        
        logger.info("✅ Все необходимые индексы проверены или созданы.")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании индексов: {str(e)}")

def index_court_decisions():
    """
    Индексирует данные судебных решений в Elasticsearch.
    Для совместимости с предыдущей версией.
    """
    create_indices()

def update_court_decisions_mapping(es=None):
    """
    Обновляет маппинг для индекса судебных решений, добавляя поддержку
    для точного поиска по номеру дела и компании.
    
    Args:
        es: Клиент Elasticsearch (опционально)
    """
    if es is None:
        es = get_es_client()
    
    try:
        index_name = ES_INDICES.get("court_decisions", "court_decisions_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return False
        
        # Обновляем маппинг для индекса
        mapping_update = {
            "properties": {
                "case_number": { 
                    "type": "keyword",
                    "fields": {
                        "text": { "type": "text", "analyzer": "russian" }
                    }
                },
                "defendant": { 
                    "type": "text", 
                    "analyzer": "russian",
                    "fields": {
                        "keyword": { "type": "keyword" }
                    }
                },
                "claimant": { 
                    "type": "text", 
                    "analyzer": "russian",
                    "fields": {
                        "keyword": { "type": "keyword" }
                    }
                },
                "doc_id": { "type": "keyword" },
                "chunk_id": { "type": "integer" }
            }
        }
        
        # Обновляем маппинг
        es.indices.put_mapping(
            index=index_name,
            body=mapping_update
        )
        
        logger.info(f"✅ Маппинг для индекса {index_name} успешно обновлен.")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении маппинга для индекса {index_name}: {str(e)}")
        return False

def update_procedural_forms_mapping(es=None):
    """
    Обновляет маппинг для индекса процессуальных форм, добавляя поддержку
    для эффективного поиска.
    
    Args:
        es: Клиент Elasticsearch (опционально)
    """
    if es is None:
        es = get_es_client()
    
    try:
        index_name = ES_INDICES.get("procedural_forms", "procedural_forms_index")
        
        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.warning(f"⚠️ Индекс {index_name} не существует.")
            return False
        
        # Обновляем маппинг для индекса
        mapping_update = {
            "properties": {
                "title": { 
                    "type": "text", 
                    "analyzer": "russian",
                    "fields": {
                        "keyword": { "type": "keyword" }
                    }
                },
                "doc_type": { "type": "keyword" },
                "category": { "type": "keyword" },
                "subcategory": { "type": "keyword" },
                "subject_matter": { 
                    "type": "text", 
                    "analyzer": "russian" 
                },
                "keywords": { "type": "keyword" },
                "doc_id": { "type": "keyword" }
            }
        }
        
        # Обновляем маппинг
        es.indices.put_mapping(
            index=index_name,
            body=mapping_update
        )
        
        logger.info(f"✅ Маппинг для индекса {index_name} успешно обновлен.")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении маппинга для индекса {index_name}: {str(e)}")
        return False

def update_all_mappings():
    """
    Обновляет маппинги для всех индексов для оптимизации умного поиска.
    """
    try:
        es = get_es_client()
        
        # Обновляем маппинги для всех индексов
        success1 = update_court_decisions_mapping(es)
        success2 = update_procedural_forms_mapping(es)
        
        # Добавьте обновление других индексов по мере необходимости
        
        return success1 and success2
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении маппингов: {str(e)}")
        return False

if __name__ == "__main__":
    # Создание индексов при запуске модуля напрямую
    create_indices()
    
    # Обновляем маппинги для умного поиска
    update_all_mappings()
    
    # Пример поиска
    test_query = "А65-28469/2012"
    results = search_law_chunks(test_query)
    print(f"Поиск по запросу '{test_query}': найдено {len(results)} результатов")
    
    if results:
        print("\nПервый результат:")
        print(results[0][:500] + "...")