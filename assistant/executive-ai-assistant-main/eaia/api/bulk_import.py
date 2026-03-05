"""
Bulk Import API Router
======================
Upload CSV of leads → create CRM Leads → batch enrich.

Flow:
  POST /import/csv (multipart form) → parse CSV → create leads via MCP → return IDs
  POST /import/enrich-all (body: lead_ids) → SSE stream of enrichment progress
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])


class BulkEnrichRequest(BaseModel):
    lead_ids: List[str]
    max_concurrent: int = 3


# ── CSV Import ────────────────────────────────────────────────────────────────

@router.post("/csv")
async def import_csv_endpoint(file: UploadFile = File(...)):
    """Upload a CSV of leads and create them in CRM.

    Expected CSV columns (flexible matching):
    - name / lead_name / full_name (required)
    - email (required)
    - company / organization (optional)
    - phone (optional)
    - source (optional)

    Returns list of created lead IDs.
    """
    contents = await file.read()
    text = contents.decode("utf-8")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))
    created = []
    errors = []

    for i, row in enumerate(reader):
        # Flexible column matching
        name = (
            row.get("name") or row.get("lead_name") or row.get("full_name")
            or row.get("Name") or row.get("Lead Name") or row.get("Full Name")
            or ""
        )
        email = (
            row.get("email") or row.get("Email") or row.get("email_address")
            or ""
        )
        company = (
            row.get("company") or row.get("organization") or row.get("Company")
            or row.get("Organization") or ""
        )
        phone = row.get("phone") or row.get("Phone") or row.get("mobile") or ""
        source = row.get("source") or row.get("Source") or "CSV Import"

        if not name or not email:
            errors.append({"row": i + 1, "error": "Missing name or email", "data": dict(row)})
            continue

        try:
            from eaia.mcp_client import FrappeMCPClient
            client = FrappeMCPClient()

            result = await client.create_lead({
                "lead_name": name,
                "email": email,
                "organization": company,
                "phone": phone,
                "source": source,
            })

            lead_id = ""
            if isinstance(result, dict):
                lead_id = result.get("name", result.get("lead_name", ""))

            created.append({
                "row": i + 1,
                "name": name,
                "email": email,
                "lead_id": lead_id,
            })
        except Exception as e:
            errors.append({"row": i + 1, "name": name, "error": str(e)})

    return {
        "status": "completed",
        "total_rows": len(created) + len(errors),
        "created": len(created),
        "errors": len(errors),
        "leads": created,
        "error_details": errors,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Bulk Enrich with SSE ─────────────────────────────────────────────────────

@router.post("/enrich-all")
async def bulk_enrich_endpoint(request: BulkEnrichRequest):
    """Enrich multiple leads with SSE progress streaming.

    Processes leads with configurable concurrency (default 3 parallel workers).
    Streams per-lead progress events via Server-Sent Events.

    SSE Event Format:
      data: {"lead_id": "CRM-LEAD-001", "status": "enriching", "progress": "3/10"}
      data: {"lead_id": "CRM-LEAD-001", "status": "scored", "score": 72, "framework": "challenger"}
      data: {"lead_id": "CRM-LEAD-001", "status": "error", "detail": "..."}
      data: {"type": "summary", "total": 10, "enriched": 8, "errors": 2}
    """
    import asyncio

    async def generate():
        semaphore = asyncio.Semaphore(request.max_concurrent)
        total = len(request.lead_ids)
        results = {"enriched": 0, "errors": 0}

        async def enrich_one(idx: int, lead_id: str):
            async with semaphore:
                # Emit start event
                event = {"lead_id": lead_id, "status": "enriching", "progress": f"{idx + 1}/{total}"}
                yield f"data: {json.dumps(event)}\n\n"

                try:
                    from eaia.mcp_client import FrappeMCPClient
                    client = FrappeMCPClient()

                    # Get lead info for enrichment
                    dossier = await client.get_lead_dossier(lead_id)
                    prospect_name = dossier.get("lead_name", dossier.get("full_name", ""))
                    company = dossier.get("organization", "")

                    # Run enrichment
                    from eaia.pipeline.agents.enrichment_agent import run_enrichment
                    result = await run_enrichment(
                        prospect_name=prospect_name,
                        company_name=company,
                        lead_name=lead_id,
                    )

                    score = result.get("score", 0)
                    framework = result.get("framework", "")

                    event = {
                        "lead_id": lead_id,
                        "status": "scored",
                        "score": score,
                        "framework": framework,
                        "progress": f"{idx + 1}/{total}",
                    }
                    results["enriched"] += 1

                except Exception as e:
                    event = {
                        "lead_id": lead_id,
                        "status": "error",
                        "detail": str(e)[:200],
                        "progress": f"{idx + 1}/{total}",
                    }
                    results["errors"] += 1

                yield f"data: {json.dumps(event)}\n\n"

        # Process all leads
        for idx, lead_id in enumerate(request.lead_ids):
            async for event in enrich_one(idx, lead_id):
                yield event

        # Final summary
        summary = {
            "type": "summary",
            "total": total,
            "enriched": results["enriched"],
            "errors": results["errors"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        yield f"data: {json.dumps(summary)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
