from typing import Any, Dict, List, Optional, Callable
import os
import requests


class TavilySimple:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.base_url = "https://api.tavily.com/search"

    def search(self, query: str, max_results: int = 5, exclude_domains: Optional[List[str]] = None, include_answer: bool = True) -> Dict[str, Any]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": include_answer,
        }
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        resp = self.session.post(self.base_url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()


class DiffbotSimple:
    def __init__(self, token: Optional[str]):
        self.token = token or ""
        self.session = requests.Session()
        self.base_url = "https://api.diffbot.com/v3/analyze"

    def is_enabled(self) -> bool:
        return bool(self.token)

    def analyze(self, url: str) -> Dict[str, Any]:
        if not self.is_enabled():
            return {}
        try:
            resp = self.session.get(self.base_url, params={"token": self.token, "url": url}, timeout=25)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}


class LinkedInSimple:
    def __init__(self, api_key: Optional[str], host: str = "linkedin-data-api.p.rapidapi.com"):
        self.api_key = api_key or ""
        self.host = host
        self.session = requests.Session()

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def get_company_by_domain(self, domain: str) -> Dict[str, Any]:
        if not self.is_enabled() or not domain:
            return {}
        try:
            url = f"https://{self.host}/get-company-by-domain"
            resp = self.session.get(url, params={"domain": domain}, headers={
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.host,
            }, timeout=20)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}

    def get_company_employees(self, company_id: str, page: int = 1) -> Dict[str, Any]:
        if not self.is_enabled() or not company_id:
            return {}
        try:
            url = f"https://{self.host}/get-company-employees"
            resp = self.session.get(url, params={"companyId": company_id, "page": page}, headers={
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.host,
            }, timeout=20)
            resp.raise_for_status()
            return resp.json() or {}
        except Exception:
            return {}


class IntelligenceService:
    def __init__(self, tavily_key: str, diffbot_token: Optional[str] = None, linkedin_key: Optional[str] = None):
        self.tavily = TavilySimple(tavily_key)
        self.diffbot = DiffbotSimple(diffbot_token)
        self.linkedin = LinkedInSimple(linkedin_key)

    def analyze(self, company: str, questions: List[str], domain: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        total_sources = 0
        for q in questions:
            res = self.tavily.search(q, max_results=max_results, include_answer=True)
            sources = res.get("results", [])
            answer = res.get("answer", "")
            enriched: Dict[str, Any] = {"question": q, "answer": answer, "sources": sources}

            # Diffbot escalation
            if self.diffbot.is_enabled() and sources:
                people: List[Dict[str, Any]] = []
                for s in sources[:3]:
                    url = s.get("url")
                    if not url:
                        continue
                    dj = self.diffbot.analyze(url)
                    objs = dj.get("objects", []) if isinstance(dj, dict) else []
                    for obj in objs:
                        name = obj.get("author") or obj.get("name")
                        title = obj.get("title") if isinstance(obj.get("title"), str) else None
                        if name and title:
                            people.append({"name": name, "title": title, "source_url": url})
                if people:
                    enriched["extracted_people"] = people

            # LinkedIn decision-makers
            if self.linkedin.is_enabled() and domain:
                try:
                    li_company = self.linkedin.get_company_by_domain(domain)
                    data = li_company.get("data", {}) if isinstance(li_company, dict) else {}
                    company_id = data.get("companyId") or li_company.get("companyId") if isinstance(li_company, dict) else None
                    if company_id:
                        li_people: List[Dict[str, Any]] = []
                        for page in range(1, 4):
                            emps = self.linkedin.get_company_employees(company_id, page=page)
                            items = emps.get("employees") or emps.get("data") or []
                            for itm in items:
                                name = itm.get("fullName") or itm.get("name")
                                title = itm.get("title") or itm.get("position")
                                if name and title:
                                    li_people.append({
                                        "name": name,
                                        "title": title,
                                        "linkedin_url": itm.get("profileUrl") or itm.get("url"),
                                        "source_url": "linkedin_api",
                                    })
                        if li_people:
                            existing = enriched.get("extracted_people", [])
                            enriched["extracted_people"] = existing + li_people
                except Exception:
                    pass

            results.append(enriched)
            total_sources += len(sources)

        return {
            "company": company,
            "questions": questions,
            "total_sources": total_sources,
            "results": results,
        }


def build_intel_service_from_env() -> IntelligenceService:
    return IntelligenceService(
        tavily_key=os.getenv("TAVILY_API_KEY", ""),
        diffbot_token=os.getenv("DIFFBOT_TOKEN"),
        linkedin_key=os.getenv("LINKEDIN_RAPIDAPI_KEY"),
    )


