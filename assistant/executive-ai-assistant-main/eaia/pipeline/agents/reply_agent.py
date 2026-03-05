"""
Reply Agent — LLM-Powered Reply Classification + Auto-Routing
==============================================================
Replaces keyword-based ReplyMatrix with an LLM that understands intent.

Classifications:
  INTERESTED       → Wants to talk. Pause sequence, create task for SDR.
  NOT_INTERESTED   → Hard no. Mark Lost, stop all outreach.
  OBJECTION        → Pushback but not a hard no. Draft rebuttal, continue sequence.
  WARM_HANDOFF     → "Talk to my colleague X" — create new Lead for X, link them.
  UNSUBSCRIBE      → Compliance. Do Not Contact. Remove from everything.
  OOO              → Out of office. Pause sequence, resume after return.
  QUESTION         → Asking for info. Draft answer, keep sequence running.
  UNKNOWN          → Can't classify. Flag for human review.

The LLM also extracts:
  - sentiment (positive/neutral/negative)
  - urgency (high/medium/low)
  - handoff_name + handoff_email (if WARM_HANDOFF)
  - objection_type (competitor/budget/timing/authority if OBJECTION)
  - return_date (if OOO)
"""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


REPLY_CLASSIFICATION_PROMPT = """You are an expert sales reply classifier. Analyze this inbound email reply and classify the prospect's intent.

ORIGINAL EMAIL WE SENT:
Subject: {original_subject}
Body: {original_body}

PROSPECT'S REPLY:
From: {from_email}
Subject: {reply_subject}
Body: {reply_body}

LEAD CONTEXT (from CRM):
Name: {prospect_name}
Company: {company_name}
Score: {lead_score}
Status: {current_status}

CLASSIFICATION RULES:
1. INTERESTED — They want to engage (meeting, call, demo, "sounds good", "let's talk")
2. NOT_INTERESTED — Hard no, explicit rejection ("not interested", "remove me", "no")
3. OBJECTION — Pushback but leaving the door open ("we already use X", "not a priority right now", "budget is tight")
4. WARM_HANDOFF — Redirecting to someone else ("talk to Sarah", "CC'd my colleague", "John handles this")
5. UNSUBSCRIBE — Explicit opt-out request ("stop emailing", "unsubscribe", "cease")
6. OOO — Auto-reply / out of office ("I'm out until", "automatic reply", "on vacation")
7. QUESTION — Asking for more info ("can you send details", "what does your product do", "pricing?")
8. UNKNOWN — Genuinely ambiguous, can't determine intent

CRITICAL DISTINCTIONS:
- "Not a priority RIGHT NOW" = OBJECTION (timing), not NOT_INTERESTED
- "Talk to my colleague" = WARM_HANDOFF, not INTERESTED
- "We use competitor X" = OBJECTION (competitor), not NOT_INTERESTED (unless "and we're happy with them, stop contacting")
- "Send me more info" = QUESTION, not INTERESTED (no commitment to call/meeting yet)
- Short replies like "Thanks" or "Received" = UNKNOWN (not enough signal)

MULTILINGUAL HANDLING:
- Classify based on INTENT regardless of language
- French "je serais ravi d'en discuter" = INTERESTED
- Spanish "no me interesa" = NOT_INTERESTED
- German "bitte entfernen Sie mich" = UNSUBSCRIBE
- If reply is in a non-English language, include the detected language in the reasoning field

Return ONLY valid JSON:
{{
  "classification": "INTERESTED|NOT_INTERESTED|OBJECTION|WARM_HANDOFF|UNSUBSCRIBE|OOO|QUESTION|UNKNOWN",
  "confidence": 0.0-1.0,
  "sentiment": "positive|neutral|negative",
  "urgency": "high|medium|low",
  "reasoning": "One sentence explaining why this classification",
  "handoff_name": "Name of person being handed off to (only if WARM_HANDOFF)",
  "handoff_email": "Email of handoff person if mentioned (only if WARM_HANDOFF)",
  "objection_type": "competitor|budget|timing|authority|other (only if OBJECTION)",
  "return_date": "Extracted return date if OOO, else null",
  "suggested_response": "One-line suggested next action for the SDR"
}}"""


def classify_reply(
    from_email: str,
    reply_subject: str,
    reply_body: str,
    original_subject: str = "",
    original_body: str = "",
    prospect_name: str = "",
    company_name: str = "",
    lead_score: int = 0,
    current_status: str = "",
) -> Dict[str, Any]:
    """Classify a reply using LLM with full context.

    Args:
        from_email: Sender email
        reply_subject: Reply subject line
        reply_body: Reply body text
        original_subject: Subject of the email we sent (context)
        original_body: Body of the email we sent (context)
        prospect_name: Lead name from CRM
        company_name: Company name from CRM
        lead_score: Current lead score
        current_status: Current CRM status

    Returns:
        Dict with classification, confidence, sentiment, urgency, reasoning, etc.
    """
    try:
        from eaia.pipeline.llm import llm_json

        prompt = REPLY_CLASSIFICATION_PROMPT.format(
            original_subject=original_subject or "(not available)",
            original_body=original_body[:500] or "(not available)",
            from_email=from_email,
            reply_subject=reply_subject,
            reply_body=reply_body[:1000],
            prospect_name=prospect_name or "(unknown)",
            company_name=company_name or "(unknown)",
            lead_score=lead_score or "(unknown)",
            current_status=current_status or "(unknown)",
        )

        result = llm_json(prompt)

        # Validate classification
        valid = {
            "INTERESTED", "NOT_INTERESTED", "OBJECTION", "WARM_HANDOFF",
            "UNSUBSCRIBE", "OOO", "QUESTION", "UNKNOWN",
        }
        if result.get("classification") not in valid:
            result["classification"] = "UNKNOWN"

        return result

    except Exception as e:
        logger.error(f"LLM reply classification failed: {e}")
        # Fallback to basic keyword matching
        return _keyword_fallback(reply_subject, reply_body)


def _keyword_fallback(subject: str, body: str) -> Dict[str, Any]:
    """Emergency fallback when LLM is unavailable."""
    full_text = f"{subject} {body}".lower()

    if any(w in full_text for w in ["out of office", "automatic reply", "vacation", "on leave"]):
        return {"classification": "OOO", "confidence": 0.7, "reasoning": "Keyword fallback: OOO detected"}
    if any(w in full_text for w in ["unsubscribe", "stop emailing", "cease", "remove list"]):
        return {"classification": "UNSUBSCRIBE", "confidence": 0.7, "reasoning": "Keyword fallback"}
    if any(w in full_text for w in ["not interested", "no thanks", "pass"]):
        return {"classification": "NOT_INTERESTED", "confidence": 0.5, "reasoning": "Keyword fallback"}
    if any(w in full_text for w in ["talk to", "cc'd", "colleague", "reach out to"]):
        return {"classification": "WARM_HANDOFF", "confidence": 0.5, "reasoning": "Keyword fallback"}
    if any(w in full_text for w in ["how does", "what is", "pricing", "can you explain", "more info", "how much", "tell me more"]):
        return {"classification": "QUESTION", "confidence": 0.5, "reasoning": "Keyword fallback"}
    if any(w in full_text for w in ["we use", "already have", "not a priority", "budget"]):
        return {"classification": "OBJECTION", "confidence": 0.5, "reasoning": "Keyword fallback"}
    if any(w in full_text for w in ["interested", "call", "meeting", "schedule", "sounds good"]):
        return {"classification": "INTERESTED", "confidence": 0.5, "reasoning": "Keyword fallback"}

    return {"classification": "UNKNOWN", "confidence": 0.3, "reasoning": "No signals detected (keyword fallback)"}


async def classify_with_context(from_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Full-context classification: fetches CRM lead + original email, then classifies.

    This is the main entry point for inbound reply processing.
    """
    # 1. Fetch CRM lead context
    prospect_name = ""
    company_name = ""
    lead_score = 0
    current_status = ""
    original_subject = ""
    original_body = ""
    crm_lead_id = ""

    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        # Search by email
        search_result = await client.search_leads(from_email, limit=1)
        leads = search_result.get("leads", search_result.get("result", []))

        if leads:
            lead = leads[0] if isinstance(leads, list) else leads
            crm_lead_id = lead.get("name", "")

            if crm_lead_id:
                # Get full dossier
                dossier = await client.get_lead_dossier(crm_lead_id)
                prospect_name = dossier.get("lead_name", dossier.get("full_name", ""))
                company_name = dossier.get("organization", "")
                lead_score = dossier.get("lead_score", 0)
                current_status = dossier.get("status", "")

                # Try to get the last email we sent (from Communication log)
                comm_result = await client.get_communication_history(crm_lead_id, limit=1)
                comms = comm_result.get("communications", comm_result.get("result", []))
                if comms:
                    last_sent = comms[0] if isinstance(comms, list) else comms
                    original_subject = last_sent.get("subject", "")
                    original_body = last_sent.get("content", "")

    except Exception as e:
        logger.warning(f"Context fetch for reply classification failed: {e}")

    # 2. Classify with full context
    result = classify_reply(
        from_email=from_email,
        reply_subject=subject,
        reply_body=body,
        original_subject=original_subject,
        original_body=original_body,
        prospect_name=prospect_name,
        company_name=company_name,
        lead_score=lead_score,
        current_status=current_status,
    )

    result["crm_lead_id"] = crm_lead_id
    result["from_email"] = from_email

    return result


async def draft_rebuttal(
    objection_type: str,
    original_email_subject: str,
    reply_body: str,
    prospect_name: str,
    company_name: str,
    signals_json: str = "{}",
) -> Dict[str, str]:
    """Draft a rebuttal email for an OBJECTION reply.

    Args:
        objection_type: competitor/budget/timing/authority
        original_email_subject: Subject of our original email
        reply_body: Their objection text
        prospect_name: Lead name
        company_name: Company
        signals_json: Intelligence signals for context
    """
    try:
        from eaia.pipeline.llm import llm_json

        signals = json.loads(signals_json) if isinstance(signals_json, str) else signals_json
        first_name = prospect_name.split()[0]

        prompt = f"""Draft a rebuttal email responding to this objection.

OBJECTION TYPE: {objection_type}
PROSPECT: {prospect_name} (address as "{first_name}")
COMPANY: {company_name}

THEIR REPLY:
{reply_body[:500]}

OUR ORIGINAL EMAIL SUBJECT: {original_email_subject}

INTELLIGENCE ON THEM:
{json.dumps(signals, indent=2)[:500]}

REBUTTAL FRAMEWORK:
- {objection_type.upper()} OBJECTIONS need:
{"- Name their competitor specifically. Acknowledge it's good. Then show the GAP they're missing." if objection_type == "competitor" else "- Agree timing is hard. Show the COST OF WAITING with a specific number from their industry." if objection_type == "timing" else "- Don't sell price. Sell ROI. Show what the problem costs them per month vs. what we cost." if objection_type == "budget" else "- Respect the chain of command. Give them ammo to pitch internally. Offer a brief exec summary."}

RULES:
- Max 3 sentences. Be respectful but persistent.
- Reference a specific signal from intelligence.
- End with a soft CTA ("Would a 15-min call save you time vs. reading more emails?")

Return JSON:
{{
  "subject": "Re: {original_email_subject}",
  "body": "rebuttal text",
  "tone": "respectful|direct|empathetic"
}}"""

        return llm_json(prompt)

    except Exception as e:
        logger.error(f"Rebuttal draft failed: {e}")
        return {
            "subject": f"Re: {original_email_subject}",
            "body": f"Hi {prospect_name.split()[0]}, I understand your concern. Would a quick 15-min call help clarify things?",
            "tone": "empathetic",
        }
