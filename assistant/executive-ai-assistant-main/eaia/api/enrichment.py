"""
Enrichment API Router
=====================
SSE streaming endpoints for pipeline execution and bulk enrichment.
These stay in FastAPI because they need async SSE — can't run in WSGI Frappe.
"""

import os
import json
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from eaia.api.models import PipelineRequest, BulkEnrichRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


# ── Pipeline (SSE) ────────────────────────────────────────────────────────────

@router.post("/pipeline")
async def pipeline_endpoint(request: PipelineRequest):
    """Autonomous outreach pipeline — streams node progress via SSE."""
    from eaia.pipeline.graph import run_pipeline

    events_queue = asyncio.Queue()

    async def collect_progress(node: str, status: str, data: dict):
        await events_queue.put({"node": node, "status": status, **data})

    async def event_generator():
        yield f"data: {json.dumps({'event': 'pipeline-start', 'prospect': request.prospect_name, 'company': request.company_name})}\n\n"

        pipeline_task = asyncio.create_task(run_pipeline(
            request.prospect_name,
            request.company_name,
            callback=collect_progress,
        ))

        while not pipeline_task.done() or not events_queue.empty():
            try:
                evt = await asyncio.wait_for(events_queue.get(), timeout=0.1)
                evt_type = "node-thought" if evt.get("status") == "thought" else "node-complete"
                yield f"data: {json.dumps({'event': evt_type, 'data': evt})}\n\n"
            except asyncio.TimeoutError:
                continue

        result = pipeline_task.result()
        final = {
            "prospect_name": result.get("prospect_name"),
            "company_name": result.get("company_name"),
            "score": result.get("score"),
            "framework": result.get("framework"),
            "score_reasoning": result.get("score_reasoning"),
            "distilled_signals": result.get("distilled_signals"),
            "email_draft": result.get("email_draft"),
            "ab_subjects": result.get("ab_subjects"),
            "review_result": result.get("review_result"),
            "review_feedback": result.get("review_feedback"),
            "apollo_data": result.get("apollo_data"),
            "attempt": result.get("attempt"),
            "crm_synced": result.get("crm_synced", False),
            "crm_prospect_id": result.get("crm_prospect_id", ""),
            "email_sent": result.get("email_sent", False),
            "email_error": result.get("email_error", ""),
        }
        yield f"data: {json.dumps({'event': 'pipeline-complete', 'data': final})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Bulk Enrich (SSE) ────────────────────────────────────────────────────────

@router.post("/bulk-enrich")
async def bulk_enrich_endpoint(request: BulkEnrichRequest):
    """Run pipeline on multiple leads — streams progress via SSE."""
    from eaia.pipeline.graph import run_pipeline

    async def event_generator():
        yield f"data: {json.dumps({'event': 'bulk-start', 'count': len(request.leads)})}\n\n"

        for i, lead in enumerate(request.leads):
            prospect = lead.get("prospect_name", f"Lead-{i}")
            company = lead.get("company_name", "Unknown")

            yield f"data: {json.dumps({'event': 'lead-start', 'index': i, 'prospect': prospect, 'company': company})}\n\n"

            try:
                result = await run_pipeline(prospect, company, callback=None)
                yield f"data: {json.dumps({'event': 'lead-complete', 'index': i, 'prospect': prospect, 'score': result.get('score'), 'crm_synced': result.get('crm_synced', False)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event': 'lead-error', 'index': i, 'prospect': prospect, 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'event': 'bulk-complete', 'total': len(request.leads)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── CRM Leads (delegates to MCP) ─────────────────────────────────────────────

@router.get("/crm-leads")
async def crm_leads_endpoint(limit: int = 50, status: str = "", query: str = ""):
    """Fetch leads from CRM via MCP tool."""
    from eaia.frappe_tool import search_leads
    result = search_leads.invoke({"query": query, "status": status, "limit": limit})
    return result


@router.get("/lead/{crm_id}")
async def get_lead_endpoint(crm_id: str):
    """Fetch full lead dossier via MCP tool."""
    from eaia.frappe_tool import get_lead_dossier
    return get_lead_dossier.invoke({"lead_name": crm_id})


@router.get("/pipeline-status")
async def pipeline_status_endpoint():
    """Enrichment health check via MCP tool."""
    from eaia.frappe_tool import get_enrichment_status
    return get_enrichment_status.invoke({})
