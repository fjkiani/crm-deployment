"""
Outreach API Router
====================
Email sending + sequence management.
SMTP stays in FastAPI (needs env vars). CRM logging delegates to MCP tools.
"""

import os
import json
import logging
from fastapi import APIRouter

from eaia.api.models import SendEmailRequest, FireSequenceRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outreach", tags=["outreach"])


# ── Send Email (SMTP + MCP log) ──────────────────────────────────────────────

@router.post("/send-email")
async def send_email_endpoint(request: SendEmailRequest):
    """Fires a single email via SendGrid/SMTP and logs it to CRM via MCP.

    Uses the same provider fallback chain as /approve: SendGrid → SMTP.
    """
    if not request.to_email:
        return {"sent": False, "error": "No to_email provided"}

    try:
        from eaia.api.approve import send_email
        result = await send_email(request.to_email, request.subject, request.body)
        logger.info(f"📧 SEND-EMAIL: ✅ → {request.to_email} | {request.subject[:50]} via {result.get('provider')}")

        # Log to CRM via MCP tool (non-fatal)
        if request.crm_prospect_id:
            try:
                from eaia.frappe_tool import approve_and_send_email
                approve_and_send_email.invoke({
                    "lead_name": request.crm_prospect_id,
                    "to_email": request.to_email,
                    "subject": request.subject,
                    "body": request.body,
                    "sender": os.getenv("FROM_EMAIL", os.getenv("GMAIL_USER", "")),
                })
            except Exception as crm_e:
                logger.warning(f"CRM communication log failed (non-fatal): {crm_e}")

        return {"sent": True, "to": request.to_email, "provider": result.get("provider")}
    except Exception as e:
        logger.error(f"📧 SEND-EMAIL error: {e}")
        return {"sent": False, "error": str(e)}


# ── Sequence Management (delegates to MCP) ────────────────────────────────────

@router.post("/fire-sequence")
async def fire_sequence_endpoint(request: FireSequenceRequest):
    """Fire next sequence step for a lead or all active leads."""
    from eaia.frappe_tool import fire_sequence_step
    return fire_sequence_step.invoke({
        "lead_name": request.lead_name,
        "dry_run": request.dry_run,
    })


@router.get("/sequence-status")
async def sequence_status_endpoint(lead_name: str = ""):
    """Get sequence status for a lead or all active sequences."""
    from eaia.frappe_tool import get_sequence_status
    return get_sequence_status.invoke({"lead_name": lead_name})


@router.post("/pause-sequence/{lead_name}")
async def pause_sequence_endpoint(lead_name: str):
    """Pause outreach sequence for a lead."""
    from eaia.frappe_tool import pause_outreach
    return pause_outreach.invoke({"lead_name": lead_name})
