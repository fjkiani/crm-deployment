"""
Enrich API Router — Agentic enrichment endpoint
=================================================
POST /enrich — Runs the LLM-driven enrichment agent for a single lead.
POST /enrich/batch — Bulk enrichment (processes leads sequentially with SSE updates).
"""

import json
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrich", tags=["enrichment-agent"])


# ── Request Models ────────────────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    prospect_name: str = Field(..., description="Full name of the prospect")
    company_name: str = Field(..., description="Company/organization name")
    lead_name: str = Field("", description="CRM Lead ID (optional)")
    write_email: bool = Field(False, description="If True, also write email draft (Phase 3)")


class BulkEnrichRequest(BaseModel):
    leads: List[dict] = Field(..., description="List of {prospect_name, company_name, lead_name}")


# ── Single Enrichment ─────────────────────────────────────────────────────────

@router.post("")
async def enrich_endpoint(request: EnrichRequest):
    """Run the agentic enrichment engine for a single prospect.

    The agent will:
    1. Check CRM for existing data
    2. Research the prospect across multiple sources
    3. Reason about which additional sources to query
    4. Distill and score the lead
    5. Write findings to CRM
    """
    from eaia.pipeline.agents.enrichment_agent import run_enrichment

    result = await run_enrichment(
        prospect_name=request.prospect_name,
        company_name=request.company_name,
        lead_name=request.lead_name,
    )

    return result


# ── Bulk Enrichment (SSE) ─────────────────────────────────────────────────────

@router.post("/batch")
async def bulk_enrich_endpoint(request: BulkEnrichRequest):
    """Run enrichment on multiple leads — streams progress via SSE."""
    from eaia.pipeline.agents.enrichment_agent import run_enrichment

    async def event_generator():
        yield f"data: {json.dumps({'event': 'batch-start', 'count': len(request.leads)})}\n\n"

        for i, lead in enumerate(request.leads):
            prospect = lead.get("prospect_name", f"Lead-{i}")
            company = lead.get("company_name", "Unknown")
            lead_name = lead.get("lead_name", "")

            yield f"data: {json.dumps({'event': 'lead-start', 'index': i, 'prospect': prospect})}\n\n"

            try:
                result = await run_enrichment(prospect, company, lead_name)
                yield f"data: {json.dumps({'event': 'lead-complete', 'index': i, 'prospect': prospect, 'score': result.get('score'), 'framework': result.get('framework')})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event': 'lead-error', 'index': i, 'prospect': prospect, 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'event': 'batch-complete', 'total': len(request.leads)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
