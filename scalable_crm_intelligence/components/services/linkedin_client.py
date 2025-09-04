"""
LinkedIn RapidAPI Client (requests-based)
Minimal wrapper around linkedin-data-api.p.rapidapi.com endpoints.

Notes:
- Endpoints and response shapes may vary by plan. This client is defensive and
  returns empty results on errors. Callers should handle missing fields.
"""

from typing import Dict, Any, Optional
import requests


DEFAULT_HOST = "linkedin-data-api.p.rapidapi.com"


class LinkedInClient:
    def __init__(self, api_key: str, host: str = DEFAULT_HOST, timeout: int = 20):
        self.api_key = api_key
        self.host = host
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
        }

    def is_configured(self) -> bool:
        return bool(self.api_key and self.host)

    def get_company_by_domain(self, domain: str) -> Dict[str, Any]:
        """GET /get-company-by-domain?domain=example.com"""
        if not self.is_configured() or not domain:
            return {}
        try:
            url = f"https://{self.host}/get-company-by-domain"
            resp = self.session.get(url, params={"domain": domain}, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}

    def get_company_employees(self, company_id: str, page: int = 1) -> Dict[str, Any]:
        """Best-effort: GET /get-company-employees?companyId=...&page=... (endpoint name may vary)"""
        if not self.is_configured() or not company_id:
            return {}
        try:
            # Endpoint name may differ; adjust if your RapidAPI plan uses a different path
            url = f"https://{self.host}/get-company-employees"
            resp = self.session.get(url, params={"companyId": company_id, "page": page}, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}


