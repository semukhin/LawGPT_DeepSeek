from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
import re
import os
import json
from app.config import ELASTICSEARCH_URL, ES_INDICES as CONFIG_ES_INDICES
from app.utils.logger import get_logger, LogLevel
from app.services.embedding_service import EmbeddingService

# Инициализируем логгер
logger = get_logger()

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
            logger.log("Подключение к Elasticsearch с авторизацией", LogLevel.INFO)
            es = Elasticsearch(
                ELASTICSEARCH_URL,
                basic_auth=(ES_USER, ES_PASS),
                retry_on_timeout=True,
                max_retries=3
            )
        else:
            # Без авторизации
            logger.log("Подключение к Elasticsearch без авторизации", LogLevel.INFO)
            es = Elasticsearch(
                ELASTICSEARCH_URL,
                retry_on_timeout=True,
                max_retries=3
            )
        return es
    except Exception as e:
        logger.log(f"Ошибка подключения к Elasticsearch: {e}", LogLevel.ERROR)
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
            logger.log(f"SmartSearchService: Извлечен номер дела: {case_number}", LogLevel.INFO)

            # Нормализуем год, если он в коротком формате (например, 05 -> 2005)
            parts = case_number.split('/')
            if len(parts) > 1:
                year_part = parts[1].split('-')[0]  # берем год до возможного суффикса
                if len(year_part) == 2:
                    # Преобразуем 2-значный год в 4-значный (05 -> 2005)
                    full_year = f"20{year_part}" if int(year_part) < 50 else f"19{year_part}"
                    case_number = case_number.replace(f"/{year_part}", f"/{full_year}", 1)
                    logger.log(f"SmartSearchService: Нормализован год в номере дела: {case_number}", LogLevel.INFO)

            return case_number
        logger.log(f"SmartSearchService: Номер дела не найден в запросе: '{query}'", LogLevel.INFO)
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
        logger.log(f"🔎 Проверка типа документа для запроса: '{query}'", LogLevel.INFO)
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
                logger.log(f"🔎 Найден тип документа: '{doc_type}'", LogLevel.INFO)
                return doc_type
        logger.log(f"🔎 Тип документа не найден", LogLevel.INFO)
        return None

    def search_by_case_number(self, case_number: str, limit: int = 10) -> List[Dict]:
        """Поиск полного текста судебного решения по номеру дела"""
        logger.log(f"🔍 Поиск по номеру дела: {case_number}", LogLevel.INFO)

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
        logger.log(f"🔍 Варианты номера дела для поиска: {variants}", LogLevel.INFO)

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
            logger.log(f"🔍 Отправляем запрос: {json.dumps(body, ensure_ascii=False)}", LogLevel.INFO)

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

                logger.log(f"🔍 Найдено {len(results)} чанков для дела {case_number} (документы: {len(doc_id_set)})", LogLevel.INFO)
                return results
            else:
                logger.log(f"🔍 Дело {case_number} не найдено", LogLevel.WARNING)
                return []

        except Exception as e:
            logger.log(f"❌ Ошибка при поиске дела {case_number}: {str(e)}", LogLevel.ERROR)
            logger.exception("Stacktrace:")
            return []

    def search_by_company(self, company: str, limit: int = 10) -> List[Dict]:
        """Поиск дел с участием указанной компании"""
        logger.log(f"🔍 Поиск дел с участием компании: {company}", LogLevel.INFO)

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
                logger.log(f"🔍 Найдено {len(results)} дел с участием {company}", LogLevel.INFO)
                return results
            else:
                logger.log(f"🔍 Дела с участием {company} не найдены", LogLevel.WARNING)
                return []

        except Exception as e:
            logger.log(f"❌ Ошибка при поиске компании {company}: {str(e)}", LogLevel.ERROR)
            return []

    def search_by_text_fragment(self, text: str, limit: int = 10) -> List[Dict]:
        """Поиск фрагмента текста с контекстом (предыдущий и следующий чанки)"""
        logger.log(f"🔍 Поиск по фрагменту текста: {text[:100]}...", LogLevel.INFO)

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
                logger.log(f"🔍 Фрагмент текста не найден", LogLevel.WARNING)
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

            logger.log(f"🔍 Найдено {len(results)} фрагментов текста с контекстом", LogLevel.INFO)
            return results

        except Exception as e:
            logger.log(f"❌ Ошибка при поиске фрагмента текста: {str(e)}", LogLevel.ERROR)
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
            logger.log(f"🧠 Определен поиск по номеру дела: {case_number}", LogLevel.INFO)
            results = self.search_by_case_number(case_number, limit)
            return {
                "type": "case_number",
                "query_entity": case_number,
                "results": results
            }

        # Проверяем наличие компании в запросе
        company = self.extract_company_name(query)
        if company:
            logger.log(f"🧠 Определен поиск по компании: {company}", LogLevel.INFO)
            results = self.search_by_company(company, limit)
            return {
                "type": "company",
                "query_entity": company,
                "results": results
            }

        # Проверяем наличие типа процессуального документа
        doc_type = self.extract_document_type(query)
        if doc_type:
            logger.log(f"🧠 Определен поиск по типу документа: {doc_type}", LogLevel.INFO)
            results = search_procedural_forms(query, min(limit, 5))  # Ограничиваем до 5 форм

            if results:
                return {
                    "type": "procedural_form",
                    "query_entity": doc_type,
                    "results": results
                }

        # По умолчанию ищем по тексту запроса
        logger.log(f"🧠 Определен поиск по тексту запроса", LogLevel.INFO)
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
        logger.log(f"Номер дела не найден в запросе: '{query}'", LogLevel.INFO)
        return []

    # Получаем найденный номер дела
    case_number = match.group(0)
    logger.log(f"Извлечен номер дела: {case_number}", LogLevel.INFO)

    variants = [case_number]

    # Создаем вариации с разными буквами А/A
    if case_number.startswith("А"):  # русская А
        latin_variant = "A" + case_number[1:]
        variants.append(latin_variant)
        logger.log(f"Создан латинский вариант: {latin_variant}", LogLevel.INFO)
    elif case_number.startswith("A"):  # латинская A
        russian_variant = "А" + case_number[1:]
        variants.append(russian_variant)
        logger.log(f"Создан русский вариант: {russian_variant}", LogLevel.INFO)

    # Логируем все варианты для отладки
    logger.log(f"Сформированы варианты номера дела: {variants}", LogLevel.INFO)
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
            logger.log(f"🔍 Индекс {index_name} не существует", LogLevel.WARNING)
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
            logger.log(f"🔍 Определен тип документа: {doc_type}", LogLevel.INFO)

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

        logger.log(f"🔍 Найдено {len(results)} процессуальных форм документов", LogLevel.INFO)
        return results

    except Exception as e:
        logger.log(f"❌ Ошибка поиска в индексе procedural_forms_index: {str(e)}", LogLevel.ERROR)
        logger.exception("Подробная информация об ошибке:")
        return []


async def get_query_embedding(query: str) -> List[float]:
    """
    Получает эмбеддинг для текста запроса.
    Использует sentence-transformers через EmbeddingService.
    
    Args:
        query: Текст запроса
        
    Returns:
        List[float]: Вектор эмбеддинга размерности 384
    """
    try:
        embedding_service = EmbeddingService()
        return await embedding_service.get_embedding_async(query)
        
    except Exception as e:
        logger.log(f"❌ Ошибка при получении эмбеддинга: {str(e)}", LogLevel.ERROR)
        return [0.0] * 384  # Возвращаем нулевой вектор в случае ошибки

async def search_law_chunks(query: str, size: int = 5, use_vector: bool = True) -> List[Dict[str, Any]]:
    logger.search("ElasticSearch", query, context={"query": query, "size": size})
    try:
        es = get_es_client()
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "text^3",
                                    "title^2", 
                                    "content^2",
                                    "full_text^2"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "match_phrase": {
                                "text": {
                                    "query": query,
                                    "boost": 2
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "highlight": {
                "fields": {
                    "text": {"fragment_size": 150, "number_of_fragments": 3}
                }
            },
            "size": size
        }
        logger.log(f"[ES] Отправляем запрос: {json.dumps(search_query)[:300]}...", LogLevel.DEBUG)
        response = es.search(
            index="court_decisions_index",
            body=search_query
        )
        hits = response['hits']['hits']
        logger.info(f"Найдено {len(hits)} результатов из Elasticsearch", context={"query": query, "results_count": len(hits)})
        if hits:
            logger.log(f"[ES] Пример первого результата: {json.dumps(hits[0], ensure_ascii=False)[:500]}...", LogLevel.DEBUG)
        else:
            logger.log(f"[ES] Нет результатов по запросу '{query}'", LogLevel.WARNING)
        results = []
        for hit in hits:
            result = {
                "text": hit["_source"].get("text", ""),
                "title": hit["_source"].get("title", ""),
                "score": hit["_score"],
                "highlights": hit.get("highlight", {}).get("text", [])
            }
            results.append(result)
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}", context={"query": query, "error": str(e)})
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
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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
            logger.log(f"🔍 Извлечены варианты номера дела: {case_numbers}", LogLevel.INFO)

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
            logger.log(f"🔍 Поиск по номеру дела: {json.dumps(should_clauses[:2], ensure_ascii=False)}", LogLevel.INFO)
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
        logger.log(f"🔍 Выполняем поиск: {json.dumps(body, ensure_ascii=False)[:200]}...", LogLevel.INFO)
        response = es.search(index=index_name, body=body)
        hits = response["hits"]["hits"]

        # Логируем результаты поиска
        if hits:
            found_case_numbers = [hit["_source"].get("case_number", "N/A") for hit in hits[:3]]
            logger.log(f"🔍 Найдено {len(hits)} результатов. Первые номера дел: {', '.join(found_case_numbers)}", LogLevel.INFO)
        else:
            logger.log(f"🔍 По запросу '{query}' результатов не найдено", LogLevel.WARNING)

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
        logger.log(f"❌ Ошибка поиска в индексе court_decisions_index: {str(e)}", LogLevel.ERROR)
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
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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

        logger.log(f"🔍 Найдено {len(results)} фрагментов законодательства", LogLevel.INFO)
        return results

    except Exception as e:
        logger.log(f"❌ Ошибка поиска в индексе ruslawod_chunks_index: {str(e)}", LogLevel.ERROR)
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
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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

        logger.log(f"🔍 Найдено {len(results)} обзоров судебной практики", LogLevel.INFO)
        return results

    except Exception as e:
        logger.log(f"❌ Ошибка поиска в индексе court_reviews_index: {str(e)}", LogLevel.ERROR)
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
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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

        logger.log(f"🔍 Найдено {len(results)} правовых статей", LogLevel.INFO)
        return results

    except Exception as e:
        logger.log(f"❌ Ошибка поиска в индексе legal_articles_index: {str(e)}", LogLevel.ERROR)
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

        logger.log(f"✅ Индекс {index_name} успешно создан.", LogLevel.INFO)
    else:
        logger.log(f"✅ Индекс {index_name} уже существует.", LogLevel.INFO)

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

        logger.log(f"✅ Индекс {index_name} успешно создан.", LogLevel.INFO)
    else:
        logger.log(f"✅ Индекс {index_name} уже существует.", LogLevel.INFO)

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

        logger.log(f"✅ Индекс {index_name} успешно создан.", LogLevel.INFO)
    else:
        logger.log(f"✅ Индекс {index_name} уже существует.", LogLevel.INFO)

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

        logger.log("✅ Все необходимые индексы проверены или созданы.", LogLevel.INFO)

    except Exception as e:
        logger.log(f"❌ Ошибка при создании индексов: {str(e)}", LogLevel.ERROR)

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
        es: Клиент Elasticsearch (опционально)    """
    if es is None:
        es = get_es_client()

    try:
        index_name = ES_INDICES.get("court_decisions", "court_decisions_index")

        # Проверяем, существует ли индекс
        if not es.indices.exists(index=index_name):
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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

        logger.log(f"✅ Маппинг для индекса {index_name} успешно обновлен.", LogLevel.INFO)
        return True
    except Exception as e:
        logger.log(f"❌ Ошибка при обновлении маппинга для индекса {index_name}: {str(e)}", LogLevel.ERROR)
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
            logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
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

        logger.log(f"✅ Маппинг для индекса {index_name} успешно обновлен.", LogLevel.INFO)
        return True
    except Exception as e:
        logger.log(f"❌ Ошибка при обновлении маппинга для индекса {index_name}: {str(e)}", LogLevel.ERROR)
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
        logger.log(f"❌ Ошибка при обновлении маппингов: {str(e)}", LogLevel.ERROR)
        return False

def search_law_chunks_multi(queries: list[str], size: int = 5) -> list[dict]:
    """
    Выполняет поиск по нескольким запросам в Elasticsearch и объединяет результаты.
    Args:
        queries: Список поисковых запросов
        size: Количество результатов на каждый запрос
    Returns:
        Список уникальных результатов
    """
    all_results = []
    seen = set()
    for q in queries:
        results = search_law_chunks(q, size)
        for r in results:
            # Уникальность по тексту и заголовку
            key = (r.get("text", "")[:100], r.get("title", ""))
            if key not in seen:
                seen.add(key)
                all_results.append(r)
    return all_results

# Универсальная функция для проверки наличия поля embedding в индексе
async def has_embedding_field(es, index_name: str) -> bool:
    try:
        mapping = es.indices.get_mapping(index=index_name)
        props = mapping[index_name]['mappings'].get('properties', {})
        return 'embedding' in props
    except Exception:
        return False

# Универсальная функция поиска по эмбеддингам для любого индекса
async def search_index_with_embeddings(index_name: str, query: str, size: int = 5, use_vector: bool = True) -> list:
    es = get_es_client()
    if not es.indices.exists(index=index_name):
        logger.log(f"⚠️ Индекс {index_name} не существует.", LogLevel.WARNING)
        return []
    # Проверяем наличие поля embedding
    has_embedding = await has_embedding_field(es, index_name)
    # Формируем текстовый запрос
    text_query = {
        "bool": {
            "should": [
                {"multi_match": {
                    "query": query,
                    "fields": ["title^3", "text^2", "content^2", "full_text^2", "subject_matter^2", "category", "subcategory", "body", "description", "keywords"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }}
            ],
            "minimum_should_match": 1
        }
    }
    search_query = {"query": text_query}
    if use_vector and has_embedding:
        query_vector = await get_query_embedding(query)
        search_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": size,
                "num_candidates": size * 2
            },
            "rank_score": 0.4,
            "query": {
                "script_score": {
                    "query": text_query,
                    "script": {"source": "_score * 0.6"}
                }
            }
        }
    # Добавляем подсветку
    search_query["highlight"] = {
        "fields": {
            "text": {"fragment_size": 150, "number_of_fragments": 3},
            "title": {"fragment_size": 150, "number_of_fragments": 2},
            "full_text": {"fragment_size": 150, "number_of_fragments": 2},
            "content": {"fragment_size": 150, "number_of_fragments": 2}
        }
    }
    try:
        response = es.search(index=index_name, body=search_query, size=size)
        hits = response["hits"]["hits"]
        results = []
        for hit in hits:
            source = hit["_source"]
            result = {
                "title": source.get("title", ""),
                "text": source.get("text", source.get("content", source.get("full_text", ""))),
                "score": hit.get("_score"),
                "vector_score": hit.get("_vector_score"),
                "highlights": sum([hit.get("highlight", {}).get(f, []) for f in ["text", "title", "full_text", "content"]], [])
            }
            results.append(result)
        logger.info(f"Найдено {len(results)} результатов по индексу {index_name}", context={"query": query, "results_count": len(results)})
        return results
    except Exception as e:
        logger.error(f"Ошибка поиска по индексу {index_name}: {str(e)}", context={"query": query, "error": str(e)})
        return []

# Обёртки для каждого индекса
async def search_procedural_forms_with_embeddings(query: str, size: int = 5, use_vector: bool = True):
    index_name = ES_INDICES.get("procedural_forms", "procedural_forms_index")
    return await search_index_with_embeddings(index_name, query, size, use_vector)

async def search_court_reviews_with_embeddings(query: str, size: int = 5, use_vector: bool = True):
    index_name = ES_INDICES.get("court_reviews", "court_reviews_index")
    return await search_index_with_embeddings(index_name, query, size, use_vector)

async def search_legal_articles_with_embeddings(query: str, size: int = 5, use_vector: bool = True):
    index_name = ES_INDICES.get("legal_articles", "legal_articles_index")
    return await search_index_with_embeddings(index_name, query, size, use_vector)

async def search_ruslawod_chunks_with_embeddings(query: str, size: int = 5, use_vector: bool = True):
    index_name = ES_INDICES.get("ruslawod_chunks", "ruslawod_chunks_index")
    return await search_index_with_embeddings(index_name, query, size, use_vector)

async def search_court_decisions_with_embeddings(query: str, size: int = 5, use_vector: bool = True):
    index_name = ES_INDICES.get("court_decisions", "court_decisions_index")
    return await search_index_with_embeddings(index_name, query, size, use_vector)

if __name__ == "__main__":
    # Создание индексов при запуске модуля напрямую
    logger.info("Создание индексов Elasticsearch")
    create_indices()

    # Обновляем маппинги для умного поиска
    logger.info("Обновление маппингов для умного поиска")
    update_all_mappings()

    # Пример поиска
    test_query = "А65-28469/2012"
    logger.info(f"Тестовый поиск по запросу: {test_query}")
    results = search_law_chunks(test_query)
    
    if results:
        logger.info("Первый результат:", context={"result": results[0]['text'][:500]})