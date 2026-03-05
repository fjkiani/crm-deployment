"""
Inbound API Router
===================
Handles inbound email replies. The #1 revenue leak:
Nyx sends emails → people reply → replies go to void.

Flow (upgraded Phase 6):
  Gmail Webhook/Poll → /inbound/process-reply → reply_agent (LLM)
    ├── INTERESTED      → CRM "Interested" → pause sequence → create task
    ├── NOT_INTERESTED  → CRM "Lost" → stop sequence
    ├── OBJECTION       → Draft rebuttal → keep sequence → create note   [NEW]
    ├── WARM_HANDOFF    → Create new Lead for handoff → link → note      [NEW]
    ├── QUESTION        → Draft answer → keep sequence → create note     [NEW]
    ├── UNSUBSCRIBE     → CRM "Do Not Contact" → compliance removal
    ├── OOO             → CRM unchanged → pause sequence → resume later
    └── UNKNOWN         → CRM unchanged → flag for human review
"""

import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbound", tags=["inbound"])


# ── Models ────────────────────────────────────────────────────────────────────

class InboundReplyRequest(BaseModel):
    from_email: str
    to_email: str = ""
    subject: str = ""
    body: str
    raw_headers: dict = {}


class InboundReplyResponse(BaseModel):
    classification: str
    confidence: float = 0.0
    sentiment: str = ""
    action_taken: str
    crm_lead_id: str = ""
    details: dict = {}


# ── Classification + Routing ──────────────────────────────────────────────────

@router.post("/process-reply", response_model=InboundReplyResponse)
async def process_reply_endpoint(request: InboundReplyRequest):
    """
    Process an inbound email reply using LLM classification:
    1. Fetch CRM Lead + original email context
    2. LLM classifies intent (8 types) with confidence + reasoning
    3. Auto-route: update CRM, pause/stop sequences, draft rebuttals, create handoff leads
    """
    from eaia.pipeline.agents.reply_agent import classify_with_context

    # 1. LLM Classify with full context
    result = await classify_with_context(
        from_email=request.from_email,
        subject=request.subject,
        body=request.body,
    )

    classification = result.get("classification", "UNKNOWN")
    confidence = result.get("confidence", 0.0)
    sentiment = result.get("sentiment", "neutral")
    crm_lead_id = result.get("crm_lead_id", "")

    logger.info(
        f"📨 INBOUND: from={request.from_email} | class={classification} | "
        f"conf={confidence} | sentiment={sentiment}"
    )

    # 2. Route based on classification
    action_taken = "none"
    details = {
        "from": request.from_email,
        "subject": request.subject,
        "body_preview": request.body[:200],
        "classification": classification,
        "confidence": confidence,
        "sentiment": sentiment,
        "reasoning": result.get("reasoning", ""),
        "suggested_response": result.get("suggested_response", ""),
        "timestamp": datetime.utcnow().isoformat(),
    }

    if classification == "INTERESTED":
        action_taken = await _handle_interested(crm_lead_id, request)
        details["next_step"] = "Schedule call or send calendar link"

    elif classification == "NOT_INTERESTED":
        action_taken = await _handle_not_interested(crm_lead_id, request)
        details["next_step"] = "Lead marked as Lost. Sequence stopped."

    elif classification == "OBJECTION":
        action_taken = await _handle_objection(crm_lead_id, request, result)
        details["next_step"] = "Rebuttal drafted. Sequence continues."
        details["objection_type"] = result.get("objection_type", "")

    elif classification == "WARM_HANDOFF":
        action_taken = await _handle_warm_handoff(crm_lead_id, request, result)
        details["next_step"] = "New lead created for handoff contact."
        details["handoff_name"] = result.get("handoff_name", "")
        details["handoff_email"] = result.get("handoff_email", "")

    elif classification == "QUESTION":
        action_taken = await _handle_question(crm_lead_id, request)
        details["next_step"] = "Question logged. Sequence continues. SDR should respond."

    elif classification == "UNSUBSCRIBE":
        action_taken = await _handle_unsubscribe(crm_lead_id, request)
        details["next_step"] = "Lead marked Do Not Contact. COMPLIANCE."

    elif classification == "OOO":
        action_taken = await _handle_ooo(crm_lead_id, request, result)
        details["next_step"] = "Sequence paused. Will resume after return."
        details["return_date"] = result.get("return_date")

    else:  # UNKNOWN
        action_taken = await _handle_unknown(crm_lead_id, request, result)
        details["next_step"] = "Flagged for human review."

    return InboundReplyResponse(
        classification=classification,
        confidence=confidence,
        sentiment=sentiment,
        action_taken=action_taken,
        crm_lead_id=crm_lead_id,
        details=details,
    )


# ── Handlers ─────────────────────────────────────────────────────────────────

async def _handle_interested(crm_lead_id: str, request: InboundReplyRequest) -> str:
    """Lead is interested → update CRM, pause sequence, log."""
    if not crm_lead_id:
        return "interested_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        await client.update_lead_context(crm_lead_id, {
            "status": "Interested",
            "reply_classification": "INTERESTED",
            "reply_date": datetime.utcnow().isoformat(),
            "reply_subject": request.subject,
            "email_status": "Reply Received",
        })
        await client.pause_outreach(crm_lead_id)
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"📨 INTERESTED Reply — {request.subject[:50]}",
            content=(
                f"**Classification:** INTERESTED (LLM)\n"
                f"**From:** {request.from_email}\n"
                f"**Subject:** {request.subject}\n\n"
                f"**Body:**\n{request.body[:500]}\n\n"
                f"---\n**Action:** Sequence paused. Schedule call."
            ),
        )
        return "crm_updated_interested_sequence_paused"
    except Exception as e:
        logger.error(f"Handle interested failed: {e}")
        return f"error: {str(e)}"


async def _handle_not_interested(crm_lead_id: str, request: InboundReplyRequest) -> str:
    """Lead says no → mark Lost, stop sequence."""
    if not crm_lead_id:
        return "not_interested_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        await client.update_lead_context(crm_lead_id, {
            "status": "Lost",
            "reply_classification": "NOT_INTERESTED",
            "reply_date": datetime.utcnow().isoformat(),
            "lost_reason": request.body[:200],
            "email_status": "Rejected",
        })
        await client.pause_outreach(crm_lead_id)
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"❌ NOT INTERESTED — {request.subject[:50]}",
            content=(
                f"**Classification:** NOT_INTERESTED (LLM)\n"
                f"**From:** {request.from_email}\n\n"
                f"**Body:**\n{request.body[:500]}\n\n"
                f"---\n**Action:** Marked Lost. Sequence stopped."
            ),
        )
        return "crm_updated_lost_sequence_stopped"
    except Exception as e:
        logger.error(f"Handle not-interested failed: {e}")
        return f"error: {str(e)}"


async def _handle_objection(
    crm_lead_id: str,
    request: InboundReplyRequest,
    classification: dict,
) -> str:
    """OBJECTION: Draft a rebuttal, keep sequence running, log the objection."""
    if not crm_lead_id:
        return "objection_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        from eaia.pipeline.agents.reply_agent import draft_rebuttal

        client = FrappeMCPClient()
        objection_type = classification.get("objection_type", "other")

        # Get dossier for signals context
        dossier = await client.get_lead_dossier(crm_lead_id)
        intel = dossier.get("intel", {})
        signals = intel.get("distilled_signals", {})

        # Draft rebuttal
        rebuttal = await draft_rebuttal(
            objection_type=objection_type,
            original_email_subject=request.subject,
            reply_body=request.body,
            prospect_name=dossier.get("lead_name", ""),
            company_name=dossier.get("organization", ""),
            signals_json=json.dumps(signals),
        )

        # Save rebuttal as draft in CRM
        await client.update_lead_context(crm_lead_id, {
            "reply_classification": "OBJECTION",
            "objection_type": objection_type,
            "reply_date": datetime.utcnow().isoformat(),
            "email_status": "Rebuttal Draft Ready",
            "email_draft": rebuttal,
        })

        # Log
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"🔄 OBJECTION ({objection_type}) — Rebuttal Drafted",
            content=(
                f"**Classification:** OBJECTION ({objection_type}) (LLM)\n"
                f"**From:** {request.from_email}\n\n"
                f"**Their objection:**\n{request.body[:300]}\n\n"
                f"**Rebuttal draft:**\n{rebuttal.get('body', '')[:300]}\n\n"
                f"---\n**Action:** Rebuttal drafted. Sequence continues. SDR review rebuttal."
            ),
        )
        return "objection_rebuttal_drafted_sequence_continues"
    except Exception as e:
        logger.error(f"Handle objection failed: {e}")
        return f"error: {str(e)}"


async def _handle_warm_handoff(
    crm_lead_id: str,
    request: InboundReplyRequest,
    classification: dict,
) -> str:
    """WARM_HANDOFF: Create a new Lead for the referred contact, link them."""
    if not crm_lead_id:
        return "handoff_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        handoff_name = classification.get("handoff_name", "Unknown Contact")
        handoff_email = classification.get("handoff_email", "")

        # Get original lead's dossier for company context
        dossier = await client.get_lead_dossier(crm_lead_id)
        company = dossier.get("organization", "")

        # Create new Lead for the handoff contact
        new_lead_result = await client.create_lead({
            "lead_name": handoff_name,
            "email": handoff_email,
            "organization": company,
            "source": "Warm Handoff",
            "notes": f"Referred by {dossier.get('lead_name', '')} ({request.from_email})",
        })

        new_lead_id = ""
        if isinstance(new_lead_result, dict):
            new_lead_id = new_lead_result.get("name", new_lead_result.get("lead_name", ""))

        # Log on original lead
        await client.update_lead_context(crm_lead_id, {
            "reply_classification": "WARM_HANDOFF",
            "reply_date": datetime.utcnow().isoformat(),
            "handoff_to": handoff_name,
            "handoff_lead_id": new_lead_id,
            "email_status": "Handoff Received",
        })
        await client.pause_outreach(crm_lead_id)

        await client.create_note(
            lead_name=crm_lead_id,
            title=f"🤝 WARM HANDOFF → {handoff_name}",
            content=(
                f"**Classification:** WARM_HANDOFF (LLM)\n"
                f"**From:** {request.from_email}\n"
                f"**Handed off to:** {handoff_name} ({handoff_email})\n\n"
                f"**Body:**\n{request.body[:300]}\n\n"
                f"**New Lead created:** {new_lead_id}\n\n"
                f"---\n**Action:** Sequence paused on original. New lead created for {handoff_name}."
            ),
        )
        return f"handoff_new_lead_created_{new_lead_id}"
    except Exception as e:
        logger.error(f"Handle warm handoff failed: {e}")
        return f"error: {str(e)}"


async def _handle_question(crm_lead_id: str, request: InboundReplyRequest) -> str:
    """QUESTION: Log the question, keep sequence running, flag for SDR response."""
    if not crm_lead_id:
        return "question_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        await client.update_lead_context(crm_lead_id, {
            "reply_classification": "QUESTION",
            "reply_date": datetime.utcnow().isoformat(),
            "email_status": "Question Received",
        })
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"❓ QUESTION — SDR should respond",
            content=(
                f"**Classification:** QUESTION (LLM)\n"
                f"**From:** {request.from_email}\n"
                f"**Subject:** {request.subject}\n\n"
                f"**Body:**\n{request.body[:500]}\n\n"
                f"---\n**Action:** Sequence continues. SDR should respond to their question."
            ),
        )
        return "question_logged_sequence_continues"
    except Exception as e:
        logger.error(f"Handle question failed: {e}")
        return f"error: {str(e)}"


async def _handle_unsubscribe(crm_lead_id: str, request: InboundReplyRequest) -> str:
    """Compliance: mark Do Not Contact, remove from all sequences."""
    if not crm_lead_id:
        return "unsubscribe_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        await client.update_lead_context(crm_lead_id, {
            "status": "Do Not Contact",
            "reply_classification": "UNSUBSCRIBE",
            "unsubscribe_date": datetime.utcnow().isoformat(),
            "unsubscribe_source": "email_reply",
            "email_status": "Unsubscribed",
        })
        await client.pause_outreach(crm_lead_id)
        await client.create_note(
            lead_name=crm_lead_id,
            title="🛑 UNSUBSCRIBE REQUEST — COMPLIANCE",
            content=(
                f"**Classification:** UNSUBSCRIBE (LLM)\n"
                f"**From:** {request.from_email}\n\n"
                f"**Body:**\n{request.body[:300]}\n\n"
                f"---\n**Action:** Do Not Contact. ALL outreach stopped. COMPLIANCE."
            ),
        )
        return "crm_updated_do_not_contact_compliance"
    except Exception as e:
        logger.error(f"Handle unsubscribe failed: {e}")
        return f"error: {str(e)}"


async def _handle_ooo(crm_lead_id: str, request: InboundReplyRequest, classification: dict) -> str:
    """Out of office → pause sequence, note return date if found."""
    if not crm_lead_id:
        return "ooo_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        return_date = classification.get("return_date")

        await client.update_lead_context(crm_lead_id, {
            "reply_classification": "OOO",
            "ooo_return_date": return_date or "",
            "email_status": "OOO",
        })
        await client.pause_outreach(crm_lead_id)
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"🏖️ OOO Auto-Reply{f' — back {return_date}' if return_date else ''}",
            content=(
                f"**Classification:** OOO (LLM)\n"
                f"**From:** {request.from_email}\n"
                f"**Return date:** {return_date or 'Not specified'}\n\n"
                f"**Body:**\n{request.body[:300]}\n\n"
                f"---\n**Action:** Sequence paused. Resume when they return."
            ),
        )
        return "sequence_paused_ooo"
    except Exception as e:
        logger.error(f"Handle OOO failed: {e}")
        return f"error: {str(e)}"


async def _handle_unknown(crm_lead_id: str, request: InboundReplyRequest, classification: dict) -> str:
    """Ambiguous reply → flag for human review."""
    if not crm_lead_id:
        return "unknown_no_crm_lead"
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        await client.update_lead_context(crm_lead_id, {
            "reply_classification": "UNKNOWN",
            "reply_date": datetime.utcnow().isoformat(),
            "email_status": "Needs Review",
        })
        await client.create_note(
            lead_name=crm_lead_id,
            title=f"⚠️ UNCLASSIFIED Reply — Needs Human Review",
            content=(
                f"**Classification:** UNKNOWN (LLM, conf={classification.get('confidence', 0)})\n"
                f"**From:** {request.from_email}\n"
                f"**Subject:** {request.subject}\n\n"
                f"**Body:**\n{request.body[:500]}\n\n"
                f"**LLM reasoning:** {classification.get('reasoning', 'N/A')}\n\n"
                f"---\n**Action:** Flagged for human review. Sequence unchanged."
            ),
        )
        return "flagged_for_human_review"
    except Exception as e:
        logger.error(f"Handle unknown failed: {e}")
        return f"error: {str(e)}"


# ── Pending Replies ──────────────────────────────────────────────────────────

@router.get("/pending")
async def pending_replies_endpoint(limit: int = 20):
    """List leads that have unprocessed or flagged-for-review replies."""
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()
        result = await client.search_leads("", status="Interested", limit=limit)
        return {"pending": result}
    except Exception as e:
        logger.error(f"Pending replies error: {e}")
        return {"pending": [], "error": str(e)}
