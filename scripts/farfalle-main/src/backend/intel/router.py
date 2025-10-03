from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.intel.services import build_intel_service_from_env


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


