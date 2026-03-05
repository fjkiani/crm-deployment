"""
Frappe MCP Tool Wrappers
========================
LangChain @tool wrappers that call the Frappe MCP server via HTTP JSON-RPC.

Each function here maps 1:1 to a @mcp.tool() in crm/api/mcp_server.py.
The EAIA agent imports these as LangChain tools for use in chat/pipeline.
"""

import os
import requests
import json
from typing import Optional
from langchain_core.tools import tool

FRAPPE_SITE = os.getenv("FRAPPE_SITE_URL", "https://jedilabs2.v.frappe.cloud")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")

_request_counter = 0


def _call_mcp(method: str, params: dict = None):
    """Send a JSON-RPC tools/call request to the Frappe MCP endpoint."""
    global _request_counter
    _request_counter += 1

    url = f"{FRAPPE_SITE}/api/method/crm.api.mcp_server.handle_mcp"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json",
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": method, "arguments": params or {}},
        "id": _request_counter,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()

    if "error" in result:
        raise Exception(f"MCP Error: {result['error']}")

    return result.get("result")


# ═══════════════════════════════════════════════════════════════════════════════
# FOUNDATION
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def crm_echo(message: str):
    """Checks connection to CRM Agent."""
    return _call_mcp("echo", {"message": message})


@tool
def create_new_lead(
    first_name: str,
    last_name: str,
    organization: str,
    title: Optional[str] = None,
    email: Optional[str] = None,
    source: str = "Nyx Pipeline",
):
    """Creates a new Lead in the CRM."""
    return _call_mcp("create_lead", {
        "first_name": first_name,
        "last_name": last_name,
        "organization": organization,
        "title": title or "",
        "email": email or "",
        "source": source,
    })


@tool
def update_context(lead_name: str, context_json: str):
    """Updates the Flexible Context (JSON) of a Lead. Use to save enriched data."""
    return _call_mcp("update_lead_context", {"lead_name": lead_name, "context": context_json})


@tool
def list_leads(limit: int = 5):
    """Fetches a batch of leads to process."""
    return _call_mcp("get_leads_batch", {"limit": limit})


@tool
def delete_all_leads(confirm: bool = False):
    """Deletes ALL leads in CRM. Requires confirm=True."""
    return _call_mcp("cleanup_leads", {"confirm": confirm})


# ═══════════════════════════════════════════════════════════════════════════════
# ENRICHMENT PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def get_lead_dossier(lead_name: str):
    """Fetch full lead data with latest FCRM Note + intel data."""
    return _call_mcp("get_lead_dossier", {"lead_name": lead_name})


@tool
def search_leads(query: str = "", status: str = "", score_min: int = 0, limit: int = 20):
    """Search leads by name, company, status, or minimum score."""
    return _call_mcp("search_leads", {
        "query": query,
        "status": status,
        "score_min": score_min,
        "limit": limit,
    })


@tool
def get_enrichment_status():
    """Health check: counts leads by enrichment completeness."""
    return _call_mcp("get_enrichment_status", {})


# ═══════════════════════════════════════════════════════════════════════════════
# OUTREACH PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def get_sequence_status(lead_name: str = ""):
    """Get sequence status for a lead or all active sequences."""
    return _call_mcp("get_sequence_status", {"lead_name": lead_name})


@tool
def fire_sequence_step(lead_name: str, step_index: int = -1, dry_run: bool = True):
    """Fire the next outreach sequence step for a lead."""
    return _call_mcp("fire_sequence_step", {
        "lead_name": lead_name,
        "step_index": step_index,
        "dry_run": dry_run,
    })


@tool
def pause_outreach(lead_name: str):
    """Pause the outreach sequence for a lead."""
    return _call_mcp("pause_sequence", {"lead_name": lead_name})


@tool
def approve_and_send_email(
    lead_name: str,
    to_email: str,
    subject: str,
    body: str,
    sender: str = "",
):
    """Approve a draft email and log it on the CRM Lead."""
    return _call_mcp("approve_and_send", {
        "lead_name": lead_name,
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "sender": sender,
    })


@tool
def create_sequence(
    sequence_name: str,
    channel: str = "Email",
    description: str = "",
    max_daily_sends: int = 50,
):
    """Create a new Outreach Sequence in CRM."""
    return _call_mcp("create_outreach_sequence", {
        "sequence_name": sequence_name,
        "channel": channel,
        "description": description,
        "max_daily_sends": max_daily_sends,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULING PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def get_call_log(lead_name: str):
    """Get all phone call records for a lead."""
    return _call_mcp("get_call_log", {"lead_name": lead_name})


@tool
def log_call_outcome(
    lead_name: str,
    call_id: str,
    outcome: str,
    transcript: str = "",
    duration_seconds: int = 0,
):
    """Log a Vapi call outcome to CRM (Communication + FCRM Note)."""
    return _call_mcp("log_call_outcome", {
        "lead_name": lead_name,
        "call_id": call_id,
        "outcome": outcome,
        "transcript": transcript,
        "duration_seconds": duration_seconds,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def get_communication_history(lead_name: str, limit: int = 20):
    """Get all Communication records for a lead (emails + calls)."""
    return _call_mcp("get_communication_history", {"lead_name": lead_name, "limit": limit})


@tool
def update_lead_score(lead_name: str, score: int, reasoning: str = ""):
    """Update a lead's score and optionally log reasoning."""
    return _call_mcp("update_lead_score", {
        "lead_name": lead_name,
        "score": score,
        "reasoning": reasoning,
    })


@tool
def create_crm_note(lead_name: str, title: str, content: str):
    """Create an FCRM Note on a lead — appears in lead timeline."""
    return _call_mcp("create_note", {
        "lead_name": lead_name,
        "title": title,
        "content": content,
    })


@tool
def get_lead_status_snapshot(lead_name: str):
    """Get compact real-time status: CRM status, emails sent, calls, sequence step."""
    return _call_mcp("get_lead_status_snapshot", {"lead_name": lead_name})


@tool
def classify_and_route_reply(from_email: str, subject: str, body: str):
    """Classify inbound reply and auto-route in CRM: INTERESTED/NOT_INTERESTED/UNSUBSCRIBE/OOO."""
    return _call_mcp("classify_and_route_reply", {
        "from_email": from_email,
        "subject": subject,
        "body": body,
    })
