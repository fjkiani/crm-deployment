"""
API Integration Layer
Handles external API communications
"""

from typing import Dict, List, Any, Optional
import requests
import logging
import time
from abc import ABC, abstractmethod

class APIClient(ABC):
    """Base API client"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.last_request_time = 0

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limiting"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        min_interval = self.config.get('rate_limit_interval', 1.0)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        try:
            response = self.session.request(method, url, **kwargs)
            self.last_request_time = time.time()

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API request failed: {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}

        except Exception as e:
            self.logger.error(f"API request error: {e}")
            return {"error": str(e)}

class TavilyClient(APIClient):
    """Tavily API client for web search"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.tavily.com/search')

    def search(self, query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
        """Perform web search"""
        if not self.api_key:
            return {"error": "API key not configured"}

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": kwargs.get('include_raw_content', False)
        }

        return self._make_request("POST", self.base_url, json=payload)

    def search_company_info(self, company_name: str) -> Dict[str, Any]:
        """Search for company information - based on our 3EDGE queries"""
        queries = [
            f'"{company_name}" company overview background history',
            f'"{company_name}" leadership team executives management',
            f'"{company_name}" business model products services',
            f'"{company_name}" market position industry standing'
        ]

        results = []
        for query in queries:
            result = self.search(query, max_results=3)
            if "results" in result:
                results.extend(result["results"])

        return {
            "company": company_name,
            "search_results": results,
            "total_results": len(results)
        }

class EnrichmentAPIClient:
    """Client for data enrichment APIs"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("EnrichmentAPI")
        self.tavily = TavilyClient(config.get('tavily', {}))

    def enrich_company_data(self, company_name: str) -> Dict[str, Any]:
        """Enrich company data using multiple sources"""
        self.logger.info(f"Enriching data for: {company_name}")

        # Get basic company info
        search_results = self.tavily.search_company_info(company_name)

        # Extract key information
        enriched = {
            "company_name": company_name,
            "description": self._extract_description(search_results),
            "leadership": self._extract_leadership(search_results),
            "focus_areas": self._extract_focus_areas(search_results),
            "data_sources": ["tavily_search"],
            "enrichment_confidence": self._calculate_confidence(search_results)
        }

        return enriched

    def _extract_description(self, search_results: Dict[str, Any]) -> str:
        """Extract company description from search results"""
        results = search_results.get('search_results', [])

        for result in results:
            content = result.get('content', '')
            title = result.get('title', '')

            # Look for overview/description content
            if 'overview' in title.lower() or 'about' in title.lower():
                return content[:500]  # First 500 chars

        return "Company description not found"

    def _extract_leadership(self, search_results: Dict[str, Any]) -> List[str]:
        """Extract leadership information"""
        results = search_results.get('search_results', [])
        leadership = []

        for result in results:
            content = result.get('content', '')

            # Look for leadership keywords
            if any(keyword in content.lower() for keyword in ['ceo', 'president', 'director', 'chief']):
                # Extract names (simplified)
                leadership.append("Leadership team identified")

        return leadership[:5]  # Limit to 5

    def _extract_focus_areas(self, search_results: Dict[str, Any]) -> List[str]:
        """Extract company focus areas"""
        # Based on our 3EDGE analysis
        focus_keywords = [
            'multi-asset', 'equity', 'fixed income', 'venture capital',
            'technology', 'healthcare', 'financial services'
        ]

        results = search_results.get('search_results', [])
        focus_areas = []

        for result in results:
            content = result.get('content', '').lower()

            for keyword in focus_keywords:
                if keyword in content and keyword not in focus_areas:
                    focus_areas.append(keyword.title())

        return focus_areas[:5]

    def _calculate_confidence(self, search_results: Dict[str, Any]) -> float:
        """Calculate enrichment confidence score"""
        total_results = search_results.get('total_results', 0)

        if total_results == 0:
            return 0.0
        elif total_results < 3:
            return 0.3
        elif total_results < 10:
            return 0.7
        else:
            return 0.9
