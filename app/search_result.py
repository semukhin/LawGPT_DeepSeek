from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    source: str
    date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 