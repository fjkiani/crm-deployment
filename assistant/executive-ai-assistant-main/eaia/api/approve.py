"""
Approve API Router — Draft Hold + Approval Flow
=================================================
POST /approve/{lead_name} — Approve a draft email, send it via SMTP/SendGrid, log to CRM.
GET  /approve/queue       — Get all leads with pending drafts (Draft Ready status).

Email Sending Priority:
  1. SendGrid API (if SENDGRID_API_KEY set)
  2. Gmail SMTP SSL (if GMAIL_USER + GMAIL_APP_PASSWORD set)
  3. Generic SMTP STARTTLS (if SMTP_HOST set)
  4. Error — no email provider configured
"""

import os
import json
import random
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approve", tags=["approval"])


# ── Request Models ────────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    override_subject: Optional[str] = Field(None, description="Override email subject")
    override_body: Optional[str] = Field(None, description="Override email body")


# ── Draft Queue ───────────────────────────────────────────────────────────────

@router.get("/queue")
async def get_draft_queue():
    """Get all leads with status 'Draft Ready' — pending SDR approval.

    Returns list of leads with their email drafts ready for review.
    """
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    # Search for leads with Draft Ready status
    result = await client.search_leads("", status="Draft Ready", limit=100)
    return result


# ── Email Provider Abstraction ────────────────────────────────────────────────

def _build_headers(to_email: str, subject: str) -> dict:
    """Build standard email headers including CAN-SPAM compliance."""
    unsubscribe_email = os.getenv("UNSUBSCRIBE_EMAIL", "")
    unsubscribe_url = os.getenv("UNSUBSCRIBE_URL", "")

    headers = {}
    if unsubscribe_email:
        headers["List-Unsubscribe"] = f"<mailto:{unsubscribe_email}?subject=unsubscribe>"
    elif unsubscribe_url:
        headers["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    if unsubscribe_url:
        headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    return headers


async def _send_via_sendgrid(to_email: str, subject: str, body: str, from_email: str) -> dict:
    """Send email via SendGrid API."""
    import httpx

    api_key = os.getenv("SENDGRID_API_KEY", "")
    if not api_key:
        raise ValueError("SENDGRID_API_KEY not configured")

    headers_extra = _build_headers(to_email, subject)

    sg_headers = []
    for k, v in headers_extra.items():
        sg_headers.append({"key": k, "value": v})

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }

    if sg_headers:
        payload["headers"] = {h["key"]: h["value"] for h in sg_headers}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    if resp.status_code not in (200, 201, 202):
        raise ValueError(f"SendGrid error {resp.status_code}: {resp.text}")

    return {"provider": "sendgrid", "status_code": resp.status_code}


def _send_via_smtp(to_email: str, subject: str, body: str, from_email: str) -> dict:
    """Send email via SMTP (Gmail SSL or generic STARTTLS)."""
    smtp_user = os.getenv("GMAIL_USER", os.getenv("SMTP_USER", ""))
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", os.getenv("SMTP_PASS", ""))
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not smtp_user or not smtp_pass:
        raise ValueError("SMTP credentials not configured (GMAIL_USER + GMAIL_APP_PASSWORD)")

    headers_extra = _build_headers(to_email, subject)

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email or smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add CAN-SPAM headers
    for k, v in headers_extra.items():
        msg[k] = v

    msg.attach(MIMEText(body, "plain"))

    # Gmail uses SSL on 465, others use STARTTLS on 587
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.sendmail(smtp_user, to_email, msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.sendmail(smtp_user, to_email, msg.as_string())

    return {"provider": "smtp", "host": smtp_host}


async def send_email(to_email: str, subject: str, body: str) -> dict:
    """Send email with provider fallback: SendGrid → Gmail SMTP → Error.

    SANDBOX MODE: When NyxConfig.SANDBOX_MODE is True, all emails redirect
    to NyxConfig.SANDBOX_EMAIL (fjkiani1@gmail.com). Original recipient is
    logged in the subject line for traceability.
    """
    # ── Sandbox Guard ─────────────────────────────────────────────────────
    original_to = to_email
    if NyxConfig.SANDBOX_MODE:
        to_email = NyxConfig.SANDBOX_EMAIL
        subject = f"[SANDBOX → {original_to}] {subject}"
        logger.info(f"🔒 SANDBOX: Redirecting {original_to} → {to_email}")

    from_email = os.getenv("FROM_EMAIL", os.getenv("GMAIL_USER", ""))

    # ── Domain Pool Route (Sprint 15) ─────────────────────────────────────
    # When SEND_DOMAINS configured, use deliverability engine w/ rotation
    if NyxConfig.SEND_DOMAINS:
        try:
            from eaia.pipeline.deliverability import send_with_deliverability
            result = await send_with_deliverability(
                to_email=to_email,
                subject=subject,
                body=body,
                reply_to=from_email,
            )
            logger.info(f"✅ Email sent via domain pool ({result.get('domain', '?')}) → {to_email}")
            result["original_to"] = original_to
            result["sandbox"] = NyxConfig.SANDBOX_MODE
            return result
        except Exception as e:
            logger.warning(f"Domain pool failed, falling back to direct send: {e}")

    # Try SendGrid first
    if os.getenv("SENDGRID_API_KEY"):
        try:
            result = await _send_via_sendgrid(to_email, subject, body, from_email)
            logger.info(f"✅ Email sent via SendGrid → {to_email}")
            result["original_to"] = original_to
            result["sandbox"] = NyxConfig.SANDBOX_MODE
            return result
        except Exception as e:
            logger.warning(f"SendGrid failed, falling back to SMTP: {e}")

    # Try SMTP
    if os.getenv("GMAIL_USER") or os.getenv("SMTP_USER"):
        try:
            result = _send_via_smtp(to_email, subject, body, from_email)
            logger.info(f"✅ Email sent via SMTP → {to_email}")
            result["original_to"] = original_to
            result["sandbox"] = NyxConfig.SANDBOX_MODE
            return result
        except Exception as e:
            logger.error(f"SMTP also failed: {e}")
            raise HTTPException(status_code=500, detail=f"All email providers failed. Last error: {e}")

    raise HTTPException(
        status_code=500,
        detail="No email provider configured. Set SENDGRID_API_KEY or GMAIL_USER + GMAIL_APP_PASSWORD"
    )


# ── Approve + Send ────────────────────────────────────────────────────────────

@router.post("/{lead_name}")
async def approve_and_send_endpoint(lead_name: str, request: ApproveRequest = None):
    """Approve a draft email and send it.

    Reads the email draft from CRM Lead's additional_data,
    sends via SendGrid/SMTP, logs as Communication in CRM, updates status.

    Args:
        lead_name: CRM Lead ID (e.g., 'LT-1772401234')
    """
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    # 1. Fetch the lead dossier to get the draft
    dossier = await client.get_lead_dossier(lead_name)

    if "error" in dossier:
        raise HTTPException(status_code=404, detail=f"Lead not found: {dossier['error']}")

    intel = dossier.get("intel", {})
    draft = intel.get("email_draft", {})

    if not draft or draft.get("quarantined"):
        raise HTTPException(
            status_code=400,
            detail="No approvable draft found. Lead may be quarantined or not enriched."
        )

    # Check signal gate — reject quarantined leads
    if intel.get("quarantined") or intel.get("email_status") == "Quarantined":
        raise HTTPException(
            status_code=400,
            detail=f"Lead is quarantined: {intel.get('quarantine_reason', 'Insufficient signal quality')}. "
                   f"Run deeper enrichment before attempting to send."
        )

    to_email = dossier.get("email") or draft.get("prospect_email")
    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient email found")

    # Allow SDR overrides
    subject = (request and request.override_subject) or draft.get("subject", "")
    body = (request and request.override_body) or draft.get("body", "")

    if not subject or not body:
        raise HTTPException(status_code=400, detail="Draft missing subject or body")

    # ── A/B Variant Selection ─────────────────────────────────────────────
    ab_variant = None
    ab_subjects = intel.get("ab_subject_variants") or draft.get("ab_subject_variants")
    if NyxConfig.AB_ENABLED and ab_subjects and len(ab_subjects) >= 2:
        ab_variant = random.choice(["A", "B"])
        subject = ab_subjects[0] if ab_variant == "A" else ab_subjects[1]
        logger.info(f"🧪 A/B Test: Using variant {ab_variant} → \"{subject}\"")

    # 2. Send email (SendGrid → SMTP fallback)
    send_result = await send_email(to_email, subject, body)

    # 3. Log as Communication in CRM via MCP
    await client.approve_and_send(lead_name, to_email, subject, body)

    # 4. Update lead status
    update_fields = {
        "email_status": "Sent",
        "email_sent_to": send_result.get("original_to", to_email),
        "email_sent_subject": subject,
        "email_sent_at": datetime.utcnow().isoformat(),
        "email_provider": send_result.get("provider", "unknown"),
    }
    if ab_variant:
        update_fields["nyx_ab_variant"] = ab_variant

    await client.update_lead_context(lead_name, update_fields)

    return {
        "status": "sent",
        "lead_name": lead_name,
        "to_email": send_result.get("original_to", to_email),
        "actual_recipient": to_email if NyxConfig.SANDBOX_MODE else send_result.get("original_to", to_email),
        "sandbox": NyxConfig.SANDBOX_MODE,
        "subject": subject,
        "ab_variant": ab_variant,
        "provider": send_result.get("provider"),
    }
