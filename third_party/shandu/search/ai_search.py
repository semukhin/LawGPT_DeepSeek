"""
AI-powered search module for Shandu.
Provides search functionality with AI analysis of results.
"""
from typing import List, Dict, Optional, Any, Union
import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from .search import UnifiedSearcher, SearchResult
from ..config import config

@dataclass
class AISearchResult:
    """Container for AI-enhanced search results."""
    query: str
    summary: str
    sources: List[Dict[str, Any]]
    timestamp: datetime = datetime.now()
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        md = [
            f"# Search Results: {self.query}\n",
            f"*Generated on: {timestamp_str}*\n",
            f"## Summary\n{self.summary}\n",
            "## Sources\n"
        ]
        for i, source in enumerate(self.sources, 1):
            title = source.get('title', 'Untitled')
            url = source.get('url', '')
            snippet = source.get('snippet', '')
            source_type = source.get('source', 'Unknown')
            md.append(f"### {i}. {title}")
            if url:
                md.append(f"**URL:** {url}")
            if source_type:
                md.append(f"**Source:** {source_type}")
            if snippet:
                md.append(f"**Snippet:** {snippet}")
            md.append("")
        return "\n".join(md)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "query": self.query,
            "summary": self.summary,
            "sources": self.sources,
            "timestamp": self.timestamp.isoformat()
        }

class AISearcher:
    """
    AI-powered search functionality.
    Combines search results with AI analysis.
    """
    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        searcher: Optional[UnifiedSearcher] = None,
        max_results: int = 10
    ):
        api_base = config.get("api", "base_url")
        api_key = config.get("api", "api_key")
        model = config.get("api", "model")
        temperature = config.get("api", "temperature", 0)
        self.llm = llm or ChatOpenAI(
            base_url=api_base,
            api_key=api_key,
            model=model,
            temperature=temperature
        )
        self.searcher = searcher or UnifiedSearcher(max_results=max_results)
        self.max_results = max_results
    
    async def search(
        self, 
        query: str,
        engines: Optional[List[str]] = None,
        detailed: bool = False
    ) -> AISearchResult:
        """
        Perform AI-enhanced search with current date and time awareness.
        
        Args:
            query: Search query
            engines: List of search engines to use
            detailed: Whether to generate a detailed analysis
            
        Returns:
            AISearchResult object
        """
        timestamp = datetime.now()
        current_datetime = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        search_results = await self.searcher.search(query, engines)
        
        content_text = ""
        sources = []
        
        # Специальная обработка для судебных решений
        legal_keywords = ["суд", "судебный", "арбитражный", "решение", "постановление", "приговор", "определение"]
        is_legal_query = any(keyword in query.lower() for keyword in legal_keywords)
        
        if is_legal_query:
            # Форматируем результаты для юридических документов
            for result in search_results:
                if isinstance(result, SearchResult):
                    # Извлекаем номер дела, если есть
                    case_number = ""
                    if "№" in result.title:
                        case_number = result.title.split("№")[1].split()[0]
                    
                    # Форматируем результат
                    formatted_result = f"\nИсточник: {result.source}\n"
                    if case_number:
                        formatted_result += f"Номер дела: {case_number}\n"
                    formatted_result += f"Заголовок: {result.title}\n"
                    if result.url:
                        formatted_result += f"URL: {result.url}\n"
                    formatted_result += f"Содержание: {result.snippet}\n"
                    
                    content_text += formatted_result
                    sources.append(result.to_dict())
                elif isinstance(result, dict):
                    content_text += f"\nИсточник: {result.get('source', 'Unknown')}\n"
                    content_text += f"Заголовок: {result.get('title', 'Untitled')}\n"
                    if result.get('url'):
                        content_text += f"URL: {result.get('url')}\n"
                    content_text += f"Содержание: {result.get('snippet', '')}\n"
                    sources.append(result)
        else:  # 8 пробелов
            # Стандартная обработка для неюридических запросов  # 12 пробелов
            for result in search_results:  # 12 пробелов
                if isinstance(result, SearchResult):  # 16 пробелов
                    content_text += f"\nИсточник: {result.source}\nЗаголовок: {result.title}\nURL: {result.url}\nСодержание: {result.snippet}\n"  # 20 пробелов
                    sources.append(result.to_dict())  # 20 пробелов
                elif isinstance(result, dict):
                    content_text += f"\nИсточник: {result.get('source', 'Unknown')}\nЗаголовок: {result.get('title', 'Untitled')}\nURL: {result.get('url', '')}\nСодержание: {result.get('snippet', '')}\n"
                    sources.append(result)
        
        if detailed:
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are analyzing search results to provide a comprehensive summary and analysis. The current date and time is {current_datetime}.
Your analysis should be thorough, balanced, and critical.
Focus on extracting factual information while noting potential biases.
Assess the credibility of sources based on expertise, evidence, consistency, and timeliness relative to the current date and time.
Identify any contradictions between sources or within a source.

For legal documents specifically:
1. Verify the jurisdiction (arbitration court vs. court of general jurisdiction)
2. Check the document type (decision, ruling, etc.)
3. Note the court level (first instance, appeal, cassation)
4. Extract key legal arguments and conclusions
5. Identify relevant legal norms and precedents"""),
                ("user", """Analyze the following search results for the query: "{query}"

Content:
{content}

Provide a detailed analysis including:
1. Key findings and facts directly relevant to the query
2. Any contradictions or discrepancies between sources
3. Reliability assessment of sources (expertise, evidence, consistency, timeliness)
4. A comprehensive summary of the information

For legal documents:
- Verify jurisdiction and court type
- Extract key legal arguments
- Note relevant legal norms
- Identify precedents

Be specific and cite the sources when referring to information.
If the search results contain little or no relevant information, explicitly state this.""")
            ])
        else:
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are analyzing search results to provide a concise summary. The current date and time is {current_datetime}.
Your summary should be clear, factual, and directly address the query.
Focus on the most relevant and reliable information from the search results.
Consider the timeliness of the information when appropriate.
Present the information in a neutral, balanced way."""),
                ("user", """Analyze the following search results for the query: "{query}"

Content:
{content}

Provide a concise summary that directly answers the query.
Focus on the most relevant and reliable information.
If the search results don't contain relevant information to answer the query, state this clearly.""")
            ])
        
        analysis_chain = analysis_prompt | self.llm
        analysis = await analysis_chain.ainvoke({
            "current_datetime": current_datetime,
            "query": query,
            "content": content_text
        })
        
        return AISearchResult(
            query=query,
            summary=analysis.content,
            sources=sources,
            timestamp=timestamp
        )
    
    def search_sync(
        self, 
        query: str,
        engines: Optional[List[str]] = None,
        detailed: bool = False
    ) -> AISearchResult:
        """Synchronous version of search method."""
        return asyncio.run(self.search(query, engines, detailed))
