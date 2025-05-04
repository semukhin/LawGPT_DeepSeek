"""
Search module for Shandu deep research system.
Implements unified search using multiple search engines with caching and parallel processing.
"""
from typing import List, Dict, Optional, Union, Any, Tuple
from langchain_community.tools import DuckDuckGoSearchResults, DuckDuckGoSearchRun
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time
import hashlib
import json
import os
from pathlib import Path
import wikipedia
import arxiv
from ..config import config, get_user_agent
from app.services.tavily_service import TavilyService
import re

class SearchResult:
    """Container for search results from various engines."""
    def __init__(
        self, 
        title: str, 
        url: Union[str, None],  # Allow None but convert it
        snippet: str,
        source: str,
        date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.title = title if title else "Untitled"
        self.url = url if isinstance(url, str) else ""  # Ensure url is a string
        self.snippet = snippet if snippet else ""
        self.source = source if source else "Unknown"
        self.date = date
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"SearchResult(title='{self.title}', url='{self.url}', source='{self.source}')"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "date": self.date,
            "metadata": self.metadata
        }

class SearchCache:
    """Cache for search results to improve performance."""
    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 3600):
        self.cache_dir = cache_dir or os.path.expanduser("~/.shandu/cache/search")
        self.ttl = ttl  # Time to live in seconds
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, query: str, engine: str) -> str:
        """Generate a cache key from query and engine."""
        hash_key = hashlib.md5(f"{query}:{engine}".encode()).hexdigest()
        return hash_key
    
    def _get_cache_path(self, key: str) -> str:
        """Get file path for cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def get(self, query: str, engine: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached results if available and not expired."""
        key = self._get_cache_key(query, engine)
        path = self._get_cache_path(key)
        
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Check if cache is expired
                if time.time() - data['timestamp'] <= self.ttl:
                    return data['results']
            except Exception as e:
                print(f"Error reading cache: {e}")
        
        return None
    
    def set(self, query: str, engine: str, results: List[Any]):
        """Cache search results."""
        try:
            key = self._get_cache_key(query, engine)
            path = self._get_cache_path(key)
            
            # Create serializable results
            serializable_results = []
            for r in results:
                if hasattr(r, 'to_dict'):
                    serializable_results.append(r.to_dict())
                elif isinstance(r, dict):
                    serializable_results.append(r)
                else:
                    # Skip non-serializable results
                    continue
            
            with open(path, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'results': serializable_results
                }, f)
                
        except Exception as e:
            print(f"Error caching search results: {e}")
            # Failures should be silent - don't impact the main functionality

class UnifiedSearcher:
    """
    Unified search interface combining results from multiple search engines.
    Supports Tavily, DuckDuckGo, Wikipedia, and arXiv with caching and parallel processing.
    Uses a shared ThreadPoolExecutor for better resource management.
    """
    # Class-level executor for thread pool reuse
    _executor = None
    _executor_lock = None
    
    def __init__(
        self,
        proxy: Optional[str] = None,
        max_results: int = 10,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: Optional[str] = None,
        backend: str = "news",
        cache_ttl: int = 3600,
        user_agent: Optional[str] = None
    ):
        self.max_results = max_results
        self.proxy = proxy or config.get("scraper", "proxy")
        self.user_agent = user_agent or get_user_agent()
        
        # Initialize DuckDuckGo searchers
        self.ddg_results = DuckDuckGoSearchResults(
            backend=backend,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            max_results=max_results
        )
        self.ddg_run = DuckDuckGoSearchRun()
        
        # Initialize Tavily searcher
        self.tavily = TavilyService()
        
        # Initialize cache
        self.cache = SearchCache(ttl=cache_ttl)
        
        # Use a shared executor for better resource management
        if not hasattr(UnifiedSearcher, '_executor'):
            UnifiedSearcher._executor_lock = threading.Lock()
            with UnifiedSearcher._executor_lock:
                if not hasattr(UnifiedSearcher, '_executor'):
                    UnifiedSearcher._executor = ThreadPoolExecutor(max_workers=6)
        
        self.executor = UnifiedSearcher._executor
        
        # Add request timeout to prevent hanging
        self.request_timeout = 20  # 20 second timeout for all requests

    def _humanize_query(self, query: str) -> str:
        """Make search query more human-like."""
        # Remove special characters and extra whitespace
        query = re.sub(r'[^\w\s]', ' ', query)
        query = ' '.join(query.split())
        return query

    async def search(
        self, 
        query: str,
        engines: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Perform asynchronous search across multiple engines.
        
        Args:
            query: Search query
            engines: List of search engines to use (default: ["tavily", "ddg", "wiki", "arxiv"])
            
        Returns:
            List[SearchResult]: Combined and deduplicated search results
        """
        if not engines:
            engines = ["tavily", "ddg", "wiki", "arxiv"]
            
        tasks = []
        results_per_engine = max(2, self.max_results // len(engines))
        
        # Create search tasks
        if "tavily" in engines:
            tasks.append(self.tavily.search(query))
        if "ddg" in engines:
            tasks.append(self._search_duckduckgo(query))
        if "wiki" in engines:
            tasks.append(self._search_wikipedia(query, results_per_engine))
        if "arxiv" in engines:
            tasks.append(self._search_arxiv(query, results_per_engine))
            
        # Execute all tasks concurrently
        all_results = []
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed_tasks:
            if isinstance(result, Exception):
                print(f"Search error: {result}")
                continue
            if isinstance(result, list):
                all_results.extend(result)
                
        # Merge and deduplicate results
        merged_results = self.merge_results(all_results)
        return merged_results[:self.max_results]

    def search_sync(
        self,
        query: str,
        engines: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Synchronous version of search method."""
        return asyncio.run(self.search(query, engines))

    @staticmethod
    def merge_results(
        results: List[SearchResult],
        strategy: str = "relevance"
    ) -> List[SearchResult]:
        """
        Merge results from different sources with deduplication and ranking.
        
        Args:
            results: List of search results to merge
            strategy: Merging strategy ("relevance" or "source")
            
        Returns:
            List[SearchResult]: Merged and ranked results
        """
        if not results:
            return []
            
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if not result.url or result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            unique_results.append(result)
            
        if strategy == "relevance":
            # Score and sort results
            def score_result(result):
                score = 0
                # Prefer results with non-empty fields
                if result.title:
                    score += 2
                if result.snippet:
                    score += 2
                if result.date:
                    score += 1
                # Prefer certain sources
                if result.source == "tavily":
                    score += 3
                elif result.source == "wikipedia":
                    score += 2
                elif result.source == "arxiv":
                    score += 1
                return score
                
            return sorted(unique_results, key=score_result, reverse=True)
            
        return unique_results

    def get_available_engines(self) -> List[str]:
        """Return list of available search engines."""
        return ["tavily", "ddg", "wiki", "arxiv"]

    async def _search_duckduckgo(self, query: str) -> List[SearchResult]:
        """Perform DuckDuckGo search with caching and error handling."""
        # Check cache first
        cached_results = self.cache.get(query, "duckduckgo")
        if cached_results:
            return [SearchResult(**r) for r in cached_results]
        
        results = []
        
        # Use LangChain's DuckDuckGo tools
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            ddg_results_str = await loop.run_in_executor(
                self.executor,
                lambda: self.ddg_results.run(query)
            )
            
            ddg_results = self._parse_ddg_results(ddg_results_str)
            results.extend(ddg_results)
            
            # Cache results
            if results:
                try:
                    # Ensure we're storing dictionaries, not SearchResult objects
                    result_dicts = []
                    for r in results:
                        if isinstance(r, SearchResult):
                            result_dicts.append(r.to_dict())
                        elif isinstance(r, dict):
                            result_dicts.append(r)
                        else:
                            print(f"Warning: Skipping non-serializable result: {type(r)}")
                    
                    self.cache.set(query, "duckduckgo", result_dicts)
                except Exception as e:
                    print(f"Error caching DuckDuckGo search results: {e}")
                
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            # Fallback to simpler DuckDuckGo run
            try:
                simple_result = await loop.run_in_executor(
                    self.executor,
                    lambda: self.ddg_run.run(query)
                )
                
                results.append(
                    SearchResult(
                        title="DuckDuckGo Result",
                        url="",
                        snippet=simple_result,
                        source="DuckDuckGo"
                    )
                )
            except Exception as e:
                print(f"DuckDuckGo fallback error: {e}")
        
        return results

    def _parse_ddg_results(self, results_str: str) -> List[SearchResult]:
        """Parse DuckDuckGo results with improved error handling."""
        results = []
        if not results_str or "snippet:" not in results_str:
            return results  # Return empty list if input is invalid
        
        entries = results_str.split("snippet:")
        for entry in entries[1:]:  # Skip first empty split
            try:
                snippet_end = entry.find(", title:")
                title_end = entry.find(", link:")
                link_end = entry.find(", date:") if ", date:" in entry else entry.find(", source:") 
                date_end = entry.find(", source:") if ", date:" in entry else -1
                
                snippet = entry[:snippet_end].strip() if snippet_end > 0 else ""
                title = (entry[entry.find(", title:") + len(", title:"):title_end].strip() 
                        if title_end > snippet_end else "Untitled")
                link = (entry[entry.find(", link:") + len(", link:"):link_end].strip() 
                        if link_end > title_end else "")
                
                date = None
                if ", date:" in entry and date_end > link_end:
                    date = entry[entry.find(", date:") + len(", date:"):date_end].strip()
                
                source = "DuckDuckGo"
                
                results.append(SearchResult(
                    title=title,
                    url=link,
                    snippet=snippet,
                    source=source,
                    date=date
                ))
            except Exception as e:
                print(f"Error parsing DuckDuckGo result: {e}")
                continue
        return results
    
    async def _search_wikipedia(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """Search Wikipedia for information."""
        results = []
        
        # Check cache first
        cached_results = self.cache.get(query, "wikipedia")
        if cached_results:
            return [SearchResult(**r) for r in cached_results]
        
        try:
            # Make search more specific for Wikipedia
            search_query = f"{query} information facts"
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                self.executor, 
                lambda: wikipedia.search(search_query, results=max_results)
            )
            
            for title in search_results:
                try:
                    # Get page content with more sentences for better context
                    page_summary = await loop.run_in_executor(
                        self.executor,
                        lambda t=title: wikipedia.summary(t, sentences=5, auto_suggest=False)
                    )
                    
                    # Get page URL
                    page_url = await loop.run_in_executor(
                        self.executor,
                        lambda t=title: wikipedia.page(t, auto_suggest=False).url
                    )
                    
                    # Get full page content for better research
                    try:
                        page_content = await loop.run_in_executor(
                            self.executor,
                            lambda t=title: wikipedia.page(t, auto_suggest=False).content
                        )
                        # Extract first 2000 chars of content for more comprehensive information
                        full_content = page_content[:2000] + "..." if len(page_content) > 2000 else page_content
                    except Exception:
                        full_content = page_summary
                    
                    results.append(SearchResult(
                        title=title,
                        url=page_url,
                        snippet=page_summary,
                        source="Wikipedia",
                        metadata={
                            "type": "encyclopedia",
                            "full_content": full_content
                        }
                    ))
                except (wikipedia.exceptions.DisambiguationError, 
                        wikipedia.exceptions.PageError) as e:
                    print(f"Wikipedia error for '{title}': {e}")
                    continue
                except Exception as e:
                    print(f"Error processing Wikipedia page '{title}': {e}")
                    continue
            
            # Cache results
            if results:
                try:
                    # Ensure we're storing dictionaries, not SearchResult objects
                    result_dicts = []
                    for r in results:
                        if isinstance(r, SearchResult):
                            result_dicts.append(r.to_dict())
                        elif isinstance(r, dict):
                            result_dicts.append(r)
                        else:
                            print(f"Warning: Skipping non-serializable result: {type(r)}")
                    
                    self.cache.set(query, "wikipedia", result_dicts)
                except Exception as e:
                    print(f"Error caching Wikipedia search results: {e}")
                
        except Exception as e:
            print(f"Wikipedia search error: {e}")
            
        return results
    
    async def _search_arxiv(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """Search arXiv for academic papers."""
        results = []
        
        # Check cache first
        cached_results = self.cache.get(query, "arxiv")
        if cached_results:
            return [SearchResult(**r) for r in cached_results]
        
        try:
            # Make search more academic for arXiv
            search_query = f"{query} research paper"
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                self.executor,
                lambda: list(arxiv.Search(
                    query=search_query,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.Relevance
                ).results())
            )
            
            for paper in search_results:
                # Extract full summary for better research
                full_summary = paper.summary
                
                # Create a more comprehensive snippet
                snippet = full_summary[:500] + "..." if len(full_summary) > 500 else full_summary
                
                # Get both PDF and abstract URLs for more flexibility
                pdf_url = paper.pdf_url
                abstract_url = paper.entry_id.replace("http://", "https://") if paper.entry_id else pdf_url
                
                # Use abstract URL as primary since it's more readable in browser
                primary_url = abstract_url
                
                results.append(SearchResult(
                    title=paper.title,
                    url=primary_url,
                    snippet=snippet,
                    source="arXiv",
                    date=paper.published.strftime("%Y-%m-%d") if paper.published else None,
                    metadata={
                        "authors": [author.name for author in paper.authors],
                        "categories": paper.categories,
                        "type": "academic_paper",
                        "pdf_url": pdf_url,
                        "abstract_url": abstract_url,
                        "full_summary": full_summary,
                        "doi": paper.doi
                    }
                ))
            
            # Cache results
            if results:
                try:
                    # Ensure we're storing dictionaries, not SearchResult objects
                    result_dicts = []
                    for r in results:
                        if isinstance(r, SearchResult):
                            result_dicts.append(r.to_dict())
                        elif isinstance(r, dict):
                            result_dicts.append(r)
                        else:
                            print(f"Warning: Skipping non-serializable result: {type(r)}")
                    
                    self.cache.set(query, "arxiv", result_dicts)
                except Exception as e:
                    print(f"Error caching arXiv search results: {e}")
                
        except Exception as e:
            print(f"arXiv search error: {e}")
            
        return results

class TavilyInternetSearcher:
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
    def search(self, query: str) -> List[SearchResult]:
        tavily = TavilyService(query)
        results = tavily.search(max_results=self.max_results)
        return [SearchResult(title=r.get('body','')[:80], url=r['href'], snippet=r.get('body',''), source='tavily') for r in results]
    def search_sync(self, query: str) -> List[SearchResult]:
        return self.search(query)
