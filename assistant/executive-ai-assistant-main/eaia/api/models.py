"""
Shared Pydantic Models for all API routers.
Extracted from server.py to avoid duplication.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# ── Enrichment ────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    prospect_name: str
    company_name: str


class BulkEnrichRequest(BaseModel):
    leads: List[Dict[str, Any]]  # Each dict has prospect_name + company_name at minimum


# ── Outreach ──────────────────────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    crm_prospect_id: str = ""


class FireSequenceRequest(BaseModel):
    """Request body for firing sequence steps (optional overrides)."""
    lead_name: str = ""
    dry_run: bool = True


# ── Scheduling ────────────────────────────────────────────────────────────────

class CallRequest(BaseModel):
    prospect_name: str
    company_name: str
    phone_number: str
    crm_prospect_id: str = ""
    pipeline_context: Dict[str, Any] = {}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


# Farfalle-compatible model (the frontend actually sends this)
class Message(BaseModel):
    role: str
    content: str


class FarfalleChatRequest(BaseModel):
    query: str
    history: List[Message] = []
    model: Optional[str] = "command-r-plus"
    pro_search: Optional[bool] = False
    thread_id: Optional[str] = None


class VapiCallOutcomeRequest(BaseModel):
    call_id: str
    crm_prospect_id: str = ""
    prospect_name: str = ""
