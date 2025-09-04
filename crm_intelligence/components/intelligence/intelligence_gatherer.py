"""
Intelligence Gatherer Component
Focused on gathering intelligence data from external sources
Single responsibility: API interaction and raw data collection
"""

import os
import json
import time
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class IntelligenceGatherer:
    """Focused component for gathering raw intelligence data"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('tavily_api_key') or os.getenv('TAVILY_API_KEY')
        self.session = requests.Session()
        self.logger = logging.getLogger("IntelligenceGatherer")

        if not self.api_key:
            raise ValueError("Tavily API key not configured")

    def search(self, query: str, search_type: str = "general",
               max_results: int = 5, include_raw: bool = True) -> Dict[str, Any]:
        """
        Core search functionality - single responsibility
        """
        try:
            response = self.session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_type": search_type,
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": include_raw,
                    "include_domains": [],
                    "exclude_domains": []
                },
                timeout=20
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Tavily search failed for '{query}': {e}")
            return {"results": []}

    def gather_company_overview(self, company_name: str) -> List[Dict[str, Any]]:
        """Gather basic company overview information"""
        queries = [
            f'"{company_name}" company overview background history',
            f'"{company_name}" business model products services',
            f'"{company_name}" market position industry standing'
        ]

        results = []
        for query in queries:
            self.logger.info(f"Searching: {query}")
            search_results = self.search(query, "general", 3)
            results.extend(search_results.get("results", []))
            time.sleep(1)  # Rate limiting

        return results

    def gather_executive_info(self, company_name: str) -> List[Dict[str, Any]]:
        """Gather executive and leadership information"""
        queries = [
            f'"{company_name}" leadership team executives management board directors',
            f'"{company_name}" CEO founder chief executive officer',
            f'"{company_name}" key personnel senior management'
        ]

        results = []
        for query in queries:
            self.logger.info(f"Searching executives: {query}")
            search_results = self.search(query, "general", 3)
            results.extend(search_results.get("results", []))
            time.sleep(1)

        return results

    def gather_investment_info(self, company_name: str) -> List[Dict[str, Any]]:
        """Gather investment portfolio information"""
        queries = [
            f'"{company_name}" investments portfolio companies',
            f'"{company_name}" investment strategy focus areas',
            f'"{company_name}" portfolio companies acquisitions'
        ]

        results = []
        for query in queries:
            self.logger.info(f"Searching investments: {query}")
            search_results = self.search(query, "general", 3)
            results.extend(search_results.get("results", []))
            time.sleep(1)

        return results

    def gather_news_info(self, company_name: str) -> List[Dict[str, Any]]:
        """Gather recent news and developments"""
        queries = [
            f'"{company_name}" news updates press release',
            f'"{company_name}" company announcements developments',
            f'"{company_name}" milestones achievements awards'
        ]

        results = []
        for query in queries:
            self.logger.info(f"Searching news: {query}")
            search_results = self.search(query, "news", 4)
            results.extend(search_results.get("results", []))
            time.sleep(1)

        return results

    def gather_partnership_info(self, company_name: str) -> List[Dict[str, Any]]:
        """Gather partnership and network information"""
        queries = [
            f'"{company_name}" partnerships collaborations alliances',
            f'"{company_name}" strategic partners joint ventures',
            f'"{company_name}" industry associations memberships'
        ]

        results = []
        for query in queries:
            self.logger.info(f"Searching partnerships: {query}")
            search_results = self.search(query, "general", 3)
            results.extend(search_results.get("results", []))
            time.sleep(1)

        return results
