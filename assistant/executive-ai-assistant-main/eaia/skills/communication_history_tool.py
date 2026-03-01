"""
communication_history_tool.py — AI Memory for Nyx

GAP 4 FIX: Nyx can now answer "What did we send to Dr. Smith?"
This tool calls Frappe CRM's get_lead_communication_history endpoint
and returns a clean formatted summary for the agent.

Dependencies: EAIA config must have `frappe_url` and `frappe_api_key` set.
"""
import requests
from langchain_core.tools import tool
from eaia.main.config import get_config


@tool
def get_communication_history(lead_name: str) -> str:
    """
    Get the full communication history for a lead from the CRM.
    Use this before drafting any email or call to understand prior interactions.
    Returns a summary of emails sent, calls made, and outreach sequence status.

    Args:
        lead_name: The CRM Lead or Lead Prospect document name (e.g., 'CRM-LEAD-00001')
    Returns:
        Formatted string summary of all prior communications.
    """
    config = get_config()
    frappe_url = getattr(config, "frappe_url", None)
    api_key = getattr(config, "frappe_api_key", None)
    api_secret = getattr(config, "frappe_api_secret", None)

    if not frappe_url:
        return f"[Memory] No Frappe URL configured. Cannot retrieve history for {lead_name}."

    try:
        resp = requests.get(
            f"{frappe_url.rstrip('/')}/api/method/crm.api.email.get_lead_communication_history",
            params={"lead_name": lead_name, "limit": 10},
            headers={"Authorization": f"token {api_key}:{api_secret}"} if api_key else {},
            timeout=15,
        )

        if resp.status_code != 200:
            return f"[Memory] CRM returned status {resp.status_code} for lead {lead_name}."

        data = resp.json().get("message", {})
        threads = data.get("threads", [])
        total = data.get("total", 0)

        if not threads:
            return f"[Memory] No prior communications found for {lead_name}. This appears to be a fresh contact."

        lines = [f"Communication History for {lead_name} ({total} total interactions):"]
        for i, t in enumerate(threads[:10], 1):
            direction = "→ SENT" if t.get("direction", "").lower() == "sent" else "← RECEIVED"
            date = t.get("date", "Unknown date")[:10]  # Trim to date only
            subject = t.get("subject", "(no subject)")
            snippet = t.get("snippet", "")[:150].replace("\n", " ")
            lines.append(f"  {i}. [{date}] {direction} | {subject} | {snippet}...")

        return "\n".join(lines)

    except Exception as e:
        return f"[Memory] Failed to retrieve communication history for {lead_name}: {str(e)}"


@tool
def get_lead_status_snapshot(lead_name: str) -> str:
    """
    Get a compact real-time status of a lead: their CRM status, recent emails, and call outcomes.
    Use this to understand where a lead stands before taking any action.

    Args:
        lead_name: The CRM Lead or Lead Prospect document name.
    Returns:
        Formatted snapshot string.
    """
    config = get_config()
    frappe_url = getattr(config, "frappe_url", None)
    api_key = getattr(config, "frappe_api_key", None)
    api_secret = getattr(config, "frappe_api_secret", None)

    if not frappe_url:
        return f"[Snapshot] No Frappe URL configured. Cannot retrieve status for {lead_name}."

    try:
        resp = requests.get(
            f"{frappe_url.rstrip('/')}/api/method/crm.api.email.get_lead_outreach_status",
            params={"lead_name": lead_name},
            headers={"Authorization": f"token {api_key}:{api_secret}"} if api_key else {},
            timeout=15,
        )

        if resp.status_code != 200:
            return f"[Snapshot] CRM returned status {resp.status_code} for lead {lead_name}."

        data = resp.json().get("message", {})
        lead = data.get("lead", {})
        comms = data.get("recent_comms", [])
        calls = data.get("recent_calls", [])

        lines = [
            f"Lead Snapshot: {lead_name}",
            f"  Status: {lead.get('status', 'Unknown')}",
            f"  Company: {lead.get('company_name', 'N/A')}",
            f"  Email: {lead.get('email', 'N/A')}",
            f"  Zeta Score: {lead.get('zeta_score', 'Not enriched yet')}",
            f"  Total Emails: {data.get('total_emails', 0)}",
        ]

        if comms:
            lines.append("  Last 3 comms:")
            for c in comms:
                lines.append(f"    - {c.get('date','')[:10]} | {c.get('subject','(no subject)')}")

        if calls:
            lines.append("  Recent calls:")
            for c in calls:
                lines.append(f"    - {str(c.get('creation',''))[:10]} | {c.get('status','')} | {c.get('sams_analysis','')[:80]}")

        return "\n".join(lines)

    except Exception as e:
        return f"[Snapshot] Failed to retrieve status for {lead_name}: {str(e)}"
