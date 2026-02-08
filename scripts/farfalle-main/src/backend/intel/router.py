from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.intel.services import build_intel_service_from_env
from crm.client import CrmClient


router = APIRouter(prefix="/intel", tags=["intel"])


class AnalyzeRequest(BaseModel):
    company: str
    domain: Optional[str] = None
    questions: List[str] = Field(default_factory=list)
    max_results: int = 5


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    service = build_intel_service_from_env()
    qs = req.questions or [
        f"Who are the decision-makers at {req.company}?",
        f"What has {req.company} invested in recently?",
        f"What are {req.company}'s strategic gaps?",
    ]
    return service.analyze(company=req.company, questions=qs, domain=req.domain, max_results=req.max_results)


# ---------- MVP: enrich_lead (normalized + summary) ----------

class EnrichLeadRequest(BaseModel):
    company: str
    domain: Optional[str] = None
    max_results: int = 5


def _normalize_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    norm: List[Dict[str, str]] = []
    for s in sources or []:
        url = s.get("url")
        title = s.get("title") or s.get("url") or ""
        if url:
            norm.append({"title": str(title)[:240], "url": str(url)})
    return norm[:8]


def _summarize(company: str, results: List[Dict[str, Any]]) -> List[str]:
    bullets: List[str] = []
    # Heuristic pick from answers
    for r in results:
        ans = (r.get("answer") or "").strip()
        q = (r.get("question") or "").lower()
        if not ans:
            continue
        if "decision" in q or "executive" in q:
            bullets.append(f"Decision-makers: {ans[:220]}")
        elif "invest" in q or "portfolio" in q:
            bullets.append(f"Recent investments: {ans[:220]}")
        elif "gap" in q or "opportunit" in q:
            bullets.append(f"Gaps/opportunities: {ans[:220]}")
        if len(bullets) >= 3:
            break
    if not bullets:
        # Fallback to first non-empty answers
        for r in results:
            ans = (r.get("answer") or "").strip()
            if ans:
                bullets.append(ans[:240])
            if len(bullets) >= 3:
                break
    # Ensure 3–6 bullets max
    return bullets[:6]


@router.post("/enrich_lead")
def enrich_lead(req: EnrichLeadRequest):
    company = (req.company or "").strip()
    if not company or len(company) > 200:
        raise HTTPException(status_code=400, detail="Invalid company")

    service = build_intel_service_from_env()
    qs = [
        f"Who are the decision-makers at {company}?",
        f"What has {company} invested in recently?",
        f"What are {company}'s strategic gaps?",
    ]

    raw = service.analyze(company=company, questions=qs, domain=req.domain, max_results=max(1, min(req.max_results, 10)))

    # Normalize
    normalized_results: List[Dict[str, Any]] = []
    for r in raw.get("results", []) or []:
        item: Dict[str, Any] = {
            "question": r.get("question") or "",
            "answer": r.get("answer") or "",
            "sources": _normalize_sources(r.get("sources") or []),
        }
        if r.get("extracted_people"):
            item["extracted_people"] = [
                {
                    "name": p.get("name"),
                    "title": p.get("title"),
                    "linkedin_url": p.get("linkedin_url"),
                    "source_url": p.get("source_url"),
                }
                for p in r.get("extracted_people") or []
                if p.get("name") and p.get("title")
            ][:12]
        normalized_results.append(item)

    summary = _summarize(company, normalized_results)

    return {
        "company": company,
        "summary": summary,
        "key_insights": [],
        "results": normalized_results,
        "total_sources": int(raw.get("total_sources", 0)),
    }

