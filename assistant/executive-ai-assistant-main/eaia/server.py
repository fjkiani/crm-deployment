"""
EAIA Server — App Factory
==========================
Previously 1061 lines. Now: app init + router mounting + backward-compat aliases.

Router modules handle all business logic:
  - eaia.api.enrichment  → /pipeline, /bulk-enrich, /crm-leads, /lead/{id}
  - eaia.api.outreach    → /send-email, /fire-sequence, /sequence-status
  - eaia.api.scheduling  → /call, /vapi-call-outcome, /call-log/{id}
  - eaia.api.chat        → /chat (Farfalle SSE)

Old monolith has been deleted — all pipeline logic now in eaia.pipeline.graph.
"""

import os
import sys
import json
import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

# Ensure we can import from eaia
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".secrets/.env"))

from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# APP FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_app() -> FastAPI:
    """Factory function for the EAIA FastAPI application."""
    app = FastAPI(title="Executive AI Assistant (EAIA)")

    # Mount static files correctly
    app.mount("/static", StaticFiles(directory="static"), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
            "http://127.0.0.1:3000", "http://127.0.0.1:3001",
            NyxConfig.FRAPPE_URL, NyxConfig.EAIA_URL, "*"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = create_app()

# ═══════════════════════════════════════════════════════════════════════════════
# MOUNT ROUTERS (new modular endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

from eaia.api.enrichment import router as enrichment_router
from eaia.api.outreach import router as outreach_router
from eaia.api.scheduling import router as scheduling_router
from eaia.api.chat import router as chat_router
from eaia.api.inbound import router as inbound_router
from eaia.api.cron import router as cron_router
from eaia.api.enrich import router as enrich_router
from eaia.api.approve import router as approve_router
from eaia.api.sender_health import router as sender_health_router
from eaia.api.bulk_import import router as bulk_import_router
from eaia.api.analytics import router as analytics_router

app.include_router(enrichment_router)
app.include_router(outreach_router)
app.include_router(scheduling_router)
app.include_router(chat_router)
app.include_router(inbound_router)
app.include_router(cron_router)
app.include_router(enrich_router)
app.include_router(approve_router)
app.include_router(sender_health_router)
app.include_router(bulk_import_router)
app.include_router(analytics_router)


# ═══════════════════════════════════════════════════════════════════════════════
# BACKWARD-COMPAT ALIASES (old URLs → new routers)
# The nyx.html frontend and Farfalle expect these exact paths.
# Once frontend is updated, these can be removed.
# ═══════════════════════════════════════════════════════════════════════════════

from eaia.api.models import (
    PipelineRequest, SendEmailRequest, CallRequest,
    BulkEnrichRequest, FarfalleChatRequest, VapiCallOutcomeRequest,
    FireSequenceRequest,
)

# /pipeline → /enrichment/pipeline
@app.post("/pipeline")
async def pipeline_compat(request: PipelineRequest):
    from eaia.api.enrichment import pipeline_endpoint
    return await pipeline_endpoint(request)

# /send-email → /outreach/send-email
@app.post("/send-email")
async def send_email_compat(request: SendEmailRequest):
    from eaia.api.outreach import send_email_endpoint
    return await send_email_endpoint(request)

# /bulk-enrich → /enrichment/bulk-enrich
@app.post("/bulk-enrich")
async def bulk_enrich_compat(request: BulkEnrichRequest):
    from eaia.api.enrichment import bulk_enrich_endpoint
    return await bulk_enrich_endpoint(request)

# /crm-leads → /enrichment/crm-leads
@app.get("/crm-leads")
async def crm_leads_compat(limit: int = 50, status: str = "", query: str = ""):
    from eaia.api.enrichment import crm_leads_endpoint
    return await crm_leads_endpoint(limit=limit, status=status, query=query)

# /call → /scheduling/call
@app.post("/call")
async def call_compat(request: CallRequest):
    from eaia.api.scheduling import call_endpoint
    return await call_endpoint(request)


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE ENDPOINTS (simple thin wrappers — kept here)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/voice/initiate-call")
async def initiate_call_endpoint(phone: str, topic: str = "General Inquiry"):
    """Initiate an outbound voice call via Vapi."""
    from eaia.skills.voice_tool import voice_call
    result = voice_call.invoke({"phone_number": phone, "objective": topic})
    if "Initiated" in result:
        try:
            call_id = result.split("Call ID: ")[1].split("\n")[0]
        except Exception:
            call_id = "vapi_unknown"
        return {"status": "success", "data": {"call_id": call_id, "provider": "vapi"}}
    else:
        raise HTTPException(status_code=500, detail=f"Vapi Call Failed: {result}")


@app.post("/voice/call-with-context")
async def call_with_context_endpoint(phone: str, company: str, contact_name: str = None):
    """Contextual call endpoint."""
    topic = f"Call regarding {company}"
    if contact_name:
        topic += f" with {contact_name}"
    return await initiate_call_endpoint(phone, topic)


# ═══════════════════════════════════════════════════════════════════════════════
# FIRE-SEQUENCE — 21-Day Siege Engine (kept in server for now — complex logic)
# TODO: Move to eaia/api/outreach.py once Outreach Sequence DocType is wired
# ═══════════════════════════════════════════════════════════════════════════════



@app.post("/fire-sequence")
async def fire_sequence_endpoint(request: FireSequenceRequest):
    """
    21-Day Siege Engine — framework rotation with signal refresh.
    Fetches CRM Leads with status='Contacted', reads their Nyx Intel note,
    determines next sequence step by days elapsed, and fires next email.
    """
    import smtplib
    import re
    import requests as _req
    from datetime import datetime, timezone
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from eaia.agents.zo import CRMClient
    from eaia.pipeline.graph import run_pipeline

    smtp_user = os.getenv("GMAIL_USER", "")
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", "")
    crm_client = CRMClient()

    results = {"fired": [], "skipped": [], "quarantined": [], "errors": []}

    # Fetch all CRM Leads in active outreach
    try:
        resp = _req.get(
            f"{crm_client.base_url}/api/resource/CRM Lead",
            headers=crm_client.headers,
            params={
                "filters": json.dumps([["status", "in", ["Contacted", "New"]]]),
                "fields": json.dumps([
                    "name", "lead_name", "email", "organization",
                    "job_title", "modified", "custom_sequence_step",
                ]),
                "limit": 200,
            },
            timeout=15,
        )
        leads = resp.json().get("data", [])
        logger.info(f"🔥 FIRE-SEQUENCE: {len(leads)} leads in active outreach")
    except Exception as e:
        return {"error": f"Failed to fetch CRM leads: {e}"}

    for lead in leads:
        crm_id = lead["name"]
        lead_email = lead.get("email", "")
        lead_name_full = lead.get("lead_name", "")
        company = lead.get("organization", "")
        first_name = lead_name_full.split()[0] if lead_name_full else lead_name_full

        if not lead_email:
            results["skipped"].append({"lead": crm_id, "reason": "No email address"})
            continue

        # Determine days elapsed
        try:
            modified = datetime.fromisoformat(lead["modified"].replace("Z", "+00:00"))
            days_elapsed = (datetime.now(timezone.utc) - modified).days
        except Exception:
            days_elapsed = 0

        # Determine current sequence step
        current_step = int(lead.get("custom_sequence_step") or 0)
        next_step_idx = current_step

        if next_step_idx >= len(NyxConfig.DEFAULT_SEQUENCE):
            results["skipped"].append({"lead": crm_id, "reason": "Sequence complete"})
            continue

        step = NyxConfig.DEFAULT_SEQUENCE[next_step_idx]

        if days_elapsed < step["day"] and current_step > 0:
            results["skipped"].append({
                "lead": crm_id,
                "reason": f"Too early for {step['label']} (day {days_elapsed}/{step['day']})",
            })
            continue

        # Fetch existing intel from FCRM Note
        intel_data = {}
        try:
            notes_resp = _req.get(
                f"{crm_client.base_url}/api/resource/FCRM Note",
                headers=crm_client.headers,
                params={
                    "filters": json.dumps([
                        ["reference_doctype", "=", "CRM Lead"],
                        ["reference_name", "=", crm_id],
                    ]),
                    "fields": json.dumps(["content", "title"]),
                    "limit": 5,
                    "order_by": "creation desc",
                },
                timeout=10,
            )
            notes = notes_resp.json().get("data", [])
            for note in notes:
                content = note.get("content", "")
                match = re.search(r'<!-- NYX_INTEL_JSON\n(.+?)\n-->', content, re.DOTALL)
                if match:
                    intel_data = json.loads(match.group(1))
                    break
        except Exception as note_e:
            logger.warning(f"Could not load intel note for {crm_id}: {note_e}")

        # Build email draft for this step's framework
        try:
            framework = step["framework"]
            signals = intel_data.get("signals", {})
            enrichment = intel_data.get("enrichment", {})
            email_draft = intel_data.get("email_draft", {})
            ab_subjects = intel_data.get("ab_subjects", [])

            if framework == "breakup":
                subject = BREAKUP_TEMPLATE["subject"]
                body = BREAKUP_TEMPLATE["body"].format(first_name=first_name, company=company)
                ps = BREAKUP_TEMPLATE["ps"]
            elif step["action"] == "send_ab" and ab_subjects:
                subject = ab_subjects[0]
                body = email_draft.get("body", "")
                ps = email_draft.get("ps", "")
            else:
                from eaia.skills.challenger_email_writer import _two_pass_generate
                cohere_key = os.getenv("COHERE_API_KEY", "")

                linkedin_posts = enrichment.get("linkedin_recent_activity", [])
                prospect_info = (
                    f"PROSPECT DOSSIER (SEQUENCE STEP {next_step_idx+1} — {step['label']}):\n"
                    f"Name: {lead_name_full} (address as \"{first_name}\" only)\n"
                    f"Title: {enrichment.get('title', lead.get('job_title', 'Unknown'))}\n"
                    f"Company: {company}\n"
                    f"AUM Signal: {enrichment.get('aum_signal', 'Unknown')}\n"
                    f"LinkedIn Headline: {enrichment.get('headline', 'Unknown')}\n"
                    f"LinkedIn Posts: {' | '.join(linkedin_posts[:2]) if linkedin_posts else 'None'}\n"
                    f"Specific Number: {signals.get('specific_number', 'UNKNOWN')}\n"
                    f"Recent Event: {signals.get('recent_event', 'UNKNOWN')}\n"
                    f"Blind Spot: {signals.get('blind_spot', 'UNKNOWN')}\n"
                    f"\nNOTE: Follow-up #{next_step_idx+1}. Use {framework.upper()} framework."
                )

                result = _two_pass_generate(
                    framework, signals, prospect_info,
                    lead_name_full, company, cohere_key,
                )
                email_obj = result.get("email", {})
                subject = email_obj.get("subject", f"Following up — {company}")
                body = email_obj.get("body", "")
                ps = email_obj.get("ps", "")

            # Signal gate
            if not body or len(body.strip()) < 20:
                results["quarantined"].append({"lead": crm_id, "reason": "Empty body — enrichment failure"})
                continue

            # Fire the email
            if request.dry_run:
                results["fired"].append({
                    "lead": crm_id, "to": lead_email, "step": step["label"],
                    "dry_run": True, "subject": subject, "body": body[:100],
                })
            else:
                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = lead_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body + (f"\n\nPS: {ps}" if ps else ""), "plain"))

                with smtplib.SMTP("smtp.gmail.com", 587) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass)
                    s.sendmail(smtp_user, [lead_email], msg.as_string())

                # Log to CRM
                crm_client.create_communication(
                    lead_name=crm_id, sender=smtp_user,
                    to_email=lead_email, subject=subject,
                    body=body + (f"\n\nPS: {ps}" if ps else ""),
                )
                _req.put(
                    f"{crm_client.base_url}/api/resource/CRM Lead/{crm_id}",
                    headers=crm_client.headers,
                    json={"custom_sequence_step": next_step_idx + 1},
                    timeout=5,
                )

                results["fired"].append({
                    "lead": crm_id, "to": lead_email,
                    "step": step["label"], "subject": subject,
                })
                logger.info(f"🔥 SEQUENCE FIRED: {step['label']} → {lead_email}")

        except Exception as e:
            results["errors"].append({"lead": crm_id, "error": str(e)})
            logger.error(f"Sequence error for {crm_id}: {e}")

    summary = {
        "fired": len(results["fired"]),
        "skipped": len(results["skipped"]),
        "quarantined": len(results["quarantined"]),
        "errors": len(results["errors"]),
        "dry_run": request.dry_run,
        "details": results,
    }
    logger.info(
        f"🔥 SEQUENCE COMPLETE: {summary['fired']} fired | "
        f"{summary['skipped']} skipped | {summary['errors']} errors"
    )
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# VAPI CALL OUTCOME (kept in server — polls Vapi REST + writes to CRM)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/vapi-call-outcome")
async def vapi_call_outcome_endpoint(request: VapiCallOutcomeRequest):
    """
    Poll Vapi REST API for call outcome.
    Extract: status, duration, summary, transcript.
    Write to CRM: Note with transcript + update Lead status.
    """
    import httpx
    from eaia.agents.zo import CRMClient

    vapi_key = os.getenv("VAPI_API_KEY", "")
    if not vapi_key:
        return {"error": "VAPI_API_KEY not set"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.vapi.ai/call/{request.call_id}",
                headers={"Authorization": f"Bearer {vapi_key}"},
                timeout=15,
            )
            if resp.status_code != 200:
                return {"error": f"Vapi API error {resp.status_code}: {resp.text[:200]}"}
            call_data = resp.json()

        status = call_data.get("status", "unknown")
        duration_secs = call_data.get("duration", 0)
        summary = call_data.get("summary", "")
        transcript = call_data.get("transcript", "")
        ended_reason = call_data.get("endedReason", "")
        recording_url = call_data.get("recordingUrl", "")

        # Determine outcome
        if status == "ended":
            if duration_secs > 30:
                outcome = "CONNECTED"
                crm_status = "Interested"
            elif ended_reason in ("voicemail", "no-answer"):
                outcome = "VOICEMAIL"
                crm_status = "Contacted"
            else:
                outcome = "ENDED_EARLY"
                crm_status = "Contacted"
        else:
            outcome = status.upper()
            crm_status = "Contacted"

        # Write to CRM
        if request.crm_prospect_id:
            crm_client = CRMClient()
            note_content = (
                f"## 📞 Vapi Call Outcome — {outcome}\n\n"
                f"**Call ID:** {request.call_id}\n"
                f"**Duration:** {duration_secs}s\n"
                f"**Ended Reason:** {ended_reason}\n"
                f"**Outcome:** {outcome}\n"
                f"{'**Recording:** ' + recording_url if recording_url else ''}\n\n"
                f"---\n\n### AI Summary\n{summary or 'No summary.'}\n\n"
                f"---\n\n### Transcript\n{transcript[:800] if transcript else 'No transcript.'}"
            )
            crm_client.create_note(
                lead_name=request.crm_prospect_id,
                title=f"Vapi Call — {outcome} ({duration_secs}s)",
                content=note_content,
            )

            import requests as _req
            _req.put(
                f"{crm_client.base_url}/api/resource/CRM Lead/{request.crm_prospect_id}",
                headers=crm_client.headers,
                json={"status": crm_status},
                timeout=5,
            )

        return {
            "call_id": request.call_id,
            "outcome": outcome,
            "duration_secs": duration_secs,
            "crm_updated": bool(request.crm_prospect_id),
            "crm_status": crm_status,
            "summary": summary[:300] if summary else "",
        }

    except Exception as e:
        logger.error(f"Vapi call outcome error: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Nyx Agent (Modular)"}


@app.get("/config/current")
def config_current():
    """Expose current NyxConfig for the test console (non-secret values only)."""
    return {
        "sandbox_mode": NyxConfig.SANDBOX_MODE,
        "sandbox_email": NyxConfig.SANDBOX_EMAIL,
        "ab_enabled": NyxConfig.AB_ENABLED,
        "ab_min_sample": NyxConfig.AB_MIN_SAMPLE,
        "llm_fallback_order": NyxConfig.LLM_FALLBACK_ORDER,
        "llm_circuit_breaker_threshold": NyxConfig.LLM_CIRCUIT_BREAKER_THRESHOLD,
        "send_domains": NyxConfig.SEND_DOMAINS,
        "domain_daily_max": NyxConfig.DOMAIN_DAILY_MAX,
        "company_name": NyxConfig.COMPANY_NAME,
        "industry": NyxConfig.INDUSTRY,
    }


@app.get("/")
def root_redirect():
    """Redirect root to the Nyx test console."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/nyx-test.html")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
