"""
Diffbot Client (requests-based)
Optional enrichment using Diffbot Analyze API.

Notes:
- This client is defensive: if token is missing or API errors occur, it returns empty results.
- We avoid assuming full Diffbot schema; we parse common fields and fall back to regex extraction.
"""

from typing import Dict, Any, List, Optional
import requests
import re


class DiffbotClient:
    """Minimal Diffbot Analyze API client"""

    def __init__(self, token: Optional[str], timeout: int = 25):
        self.token = token or ""
        self.timeout = timeout
        self.base_url = "https://api.diffbot.com/v3/analyze"
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.token)

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Call Diffbot Analyze on a URL and return raw JSON (or {})."""
        if not self.is_configured():
            return {}
        try:
            params = {"token": self.token, "url": url}
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}

    def extract_people(self, analyze_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract likely people entities (name/title) from Diffbot analyze output."""
        people: List[Dict[str, Any]] = []
        objects = analyze_json.get("objects", []) if isinstance(analyze_json, dict) else []

        # Heuristic extraction from known fields
        for obj in objects:
            # Try explicit people-like fields
            name = obj.get("author") or obj.get("name")
            title = obj.get("title") if isinstance(obj.get("title"), str) else None
            text = obj.get("text") or obj.get("html") or ""

            # If we have name and title, add directly
            if name and title:
                people.append({"name": name, "title": title})
                continue

            # Fallback: regex from text/title like "Jane Doe, Managing Partner" or "John Smith - CIO"
            candidates = []
            if isinstance(text, str):
                candidates.append(text)
            if isinstance(title, str):
                candidates.append(title)

            for blob in candidates:
                for match in re.finditer(r"([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*[,-]\s*([^\n\r|]+))", blob):
                    pname = match.group(1).strip()
                    ptitle = match.group(2).strip()
                    if len(ptitle) > 2 and len(pname.split()) >= 2:
                        people.append({"name": pname, "title": ptitle})

        # Deduplicate by name+title
        seen = set()
        unique: List[Dict[str, Any]] = []
        for p in people:
            key = (p.get("name", "").lower(), p.get("title", "").lower())
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique


