"""
Tavily Client Service (requests-based)
Reusable semantic search client leveraging Tavily's built-in LLM answers
"""

from typing import Dict, Any, List, Optional
import requests


class TavilyClient:
    """Lightweight Tavily API client"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.tavily.com/search",
        timeout: int = 30,
        default_exclude_domains: Optional[List[str]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.default_exclude_domains = (
            default_exclude_domains
            if default_exclude_domains is not None
            else ["wikipedia.org", "dictionary.com", "thefreedictionary.com"]
        )

    def search(
        self,
        query: str,
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False,
        search_type: str = "general",
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_type": search_type,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }
        if exclude_domains is None:
            payload["exclude_domains"] = self.default_exclude_domains
        elif exclude_domains:
            payload["exclude_domains"] = exclude_domains

        resp = self.session.post(self.base_url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


