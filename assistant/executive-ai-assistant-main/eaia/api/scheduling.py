"""
Scheduling API Router
=====================
Voice calls (Vapi REST) + call outcome logging.
Vapi REST stays in FastAPI (async httpx). CRM logging delegates to MCP tools.
"""

import os
import json
import logging
from fastapi import APIRouter, HTTPException

from eaia.api.models import CallRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


# ── Voice Call (Vapi REST + MCP log) ──────────────────────────────────────────

@router.post("/call")
async def call_endpoint(request: CallRequest):
    """Initiate outbound voice call via Vapi REST API."""
    import httpx
    from eaia.agents.zo import CRMClient

    ctx = request.pipeline_context
    signals = ctx.get("distilled_signals", {})
    email = ctx.get("email_draft", {}).get("email", {})

    # ── Pre-call intelligence: fetch real CRM dossier ─────────────────────
    crm_dossier = ""
    try:
        from eaia.skills.context_manager import ContextManager
        ctx_mgr = ContextManager()
        crm_dossier = ctx_mgr.get_dossier(
            email=ctx.get("enrichment", {}).get("apollo_email"),
            lead_id=request.crm_prospect_id,
        )
    except Exception as e:
        logger.warning(f"ContextManager dossier fetch failed (using fallback): {e}")

    # Build dossier for Vapi system message (CRM intel + pipeline context)
    pipeline_dossier = f"""
TARGET DOSSIER — {request.prospect_name} @ {request.company_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORE: {ctx.get('score', 'N/A')}/100 ({ctx.get('framework', 'N/A')} framework)
KEY SIGNAL: {signals.get('specific_number', 'N/A')}
BLIND SPOT: {str(signals.get('blind_spot', 'N/A'))[:200]}
EMAIL SUBJECT: {email.get('subject', 'N/A')}
"""
    # Merge CRM intel with pipeline dossier
    dossier = f"{crm_dossier}\n\n{pipeline_dossier}" if crm_dossier else pipeline_dossier

    system_message = f"""You are Nyx, an AI Executive Assistant for Zeta Intelligence.
You are calling {request.prospect_name} at {request.company_name}.

{dossier}

RULES:
- Be professional, concise, and confident
- Never say "I'm an AI" — say "I'm calling on behalf of our research team"
- If voicemail: leave a 20-second message referencing the email subject
- If they answer: use the blind spot hook to open, then ask for 15 min
"""

    vapi_key = os.getenv("VAPI_API_KEY", "")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "")

    first_message = (
        f"Hi, is this {request.prospect_name}? "
        f"I'm calling on behalf of Zeta Intelligence — we sent you a note about "
        f"\"{email.get('subject', 'our research')}\". Do you have 60 seconds?"
    )

    vapi_payload = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": request.phone_number},
        "assistant": {
            "firstMessage": first_message,
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": system_message}],
                "temperature": 0.7,
                "maxTokens": 250,
            },
            "voice": {"provider": "11labs", "voiceId": "burt"},
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "maxDurationSeconds": 300,
            "silenceTimeoutSeconds": 30,
            "backgroundSound": "office",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.post(
                "https://api.vapi.ai/call",
                headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
                json=vapi_payload,
            )

        if resp.status_code in (200, 201):
            vapi_data = resp.json()
            call_id = vapi_data.get("id", "")
            logger.info(f"📞 CALL: ✅ Vapi REST → {request.phone_number} (call_id={call_id})")

            # Log to CRM via MCP (non-fatal)
            if request.crm_prospect_id:
                try:
                    from eaia.frappe_tool import log_call_outcome
                    log_call_outcome.invoke({
                        "lead_name": request.crm_prospect_id,
                        "call_id": call_id,
                        "outcome": "initiated",
                        "transcript": "",
                        "duration_seconds": 0,
                    })
                except Exception as crm_e:
                    logger.warning(f"CRM call log failed (non-fatal): {crm_e}")

            return {"status": "call_initiated", "call_id": call_id, "to": request.phone_number}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Vapi API error: {str(e)}")


# ── Vapi Call Outcome Webhook ─────────────────────────────────────────────────

@router.post("/vapi-call-outcome")
async def vapi_call_outcome_endpoint(payload: dict):
    """Webhook endpoint for Vapi call outcomes. Logs to CRM via MCP."""
    call_id = payload.get("call_id", payload.get("id", "unknown"))
    outcome = payload.get("status", payload.get("outcome", "unknown"))
    transcript = payload.get("transcript", "")
    duration = payload.get("duration_seconds", payload.get("duration", 0))

    # Find the CRM Lead associated with this call (from custom metadata)
    lead_name = payload.get("metadata", {}).get("crm_prospect_id", "")

    if lead_name:
        from eaia.frappe_tool import log_call_outcome
        result = log_call_outcome.invoke({
            "lead_name": lead_name,
            "call_id": call_id,
            "outcome": outcome,
            "transcript": transcript,
            "duration_seconds": duration,
        })
        return {"status": "logged", "result": result}

    return {"status": "received", "note": "No crm_prospect_id in metadata — not logged to CRM"}


# ── Call Logs + Calendar (MCP) ────────────────────────────────────────────────

@router.get("/call-log/{lead_name}")
async def call_log_endpoint(lead_name: str):
    """Get all call records for a lead via MCP."""
    from eaia.frappe_tool import get_call_log
    return get_call_log.invoke({"lead_name": lead_name})
