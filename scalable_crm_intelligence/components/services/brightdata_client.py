"""
Bright Data Client (generic HTTP wrapper, optional)

This client is intentionally generic because Bright Data products vary by account.
Configure via env/constructor:
 - base_url: e.g., your SERP/news endpoint proxy
 - api_token: auth token if required (sent as header 'Authorization: Bearer <token>')

Expected response: JSON with a list of results containing title/url/content fields.
If your endpoint responds differently, adapt _format_results accordingly.
"""

from typing import Dict, Any, List, Optional
import requests


class BrightDataClient:
    def __init__(self, base_url: Optional[str], api_token: Optional[str], timeout: int = 25):
        self.base_url = base_url or ""
        self.api_token = api_token or ""
        self.timeout = timeout
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_token)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def search_news(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Generic search endpoint; adapt params to your Bright Data pipeline."""
        if not self.is_configured() or not query:
            return {"results": []}
        try:
            resp = self.session.get(
                self.base_url,
                params={"q": query, "limit": limit},
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json() or {}
            return {"results": self._format_results(data)}
        except Exception:
            return {"results": []}

    def _format_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Attempt to normalize common fields
        items = []
        raw = data.get("results") or data.get("data") or data.get("items") or []
        for r in raw:
            items.append({
                "title": r.get("title") or r.get("headline") or "",
                "url": r.get("url") or r.get("link") or "",
                "content": r.get("content") or r.get("snippet") or "",
            })
        return items


