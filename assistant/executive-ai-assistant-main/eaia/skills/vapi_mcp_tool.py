"""
Vapi MCP call tool — THIN PROXY to the canonical CRM voice spine.

Consolidation note (voice-prod audit): this file previously shelled out to
`npx mcp-remote https://mcp.vapi.ai/mcp` with a HARDCODED api key and rebuilt the
Vapi assistant payload by hand ("we don't know the schema, this might fail").
That is now replaced by a forward to the single canonical endpoint:

    crm.api.vapi.initiate_outbound_call

which is dossier/KB-grounded, logs to Vapi Call Log + CRM Call Log, enforces the
per-lead governor, and reads credentials from tenant config (never hardcoded).

The public symbols ``_invoke_mcp_create_call`` (async) and ``vapi_mcp_call``
(tool) are kept for backward compatibility with existing importers such as
``eaia.tools.outreach_tools``.
"""

import asyncio
import json
import os

import requests
from langchain_core.tools import tool

FRAPPE_SITE = os.getenv("FRAPPE_SITE_URL", "https://alpha-crm.v.frappe.cloud").rstrip("/")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")


def _initiate(phone_number: str, objective: str, override_context: str = None, lead_name: str = None) -> dict:
    url = f"{FRAPPE_SITE}/api/method/crm.api.vapi.initiate_outbound_call"
    headers = {"Content-Type": "application/json"}
    if API_KEY and API_SECRET:
        headers["Authorization"] = f"token {API_KEY}:{API_SECRET}"
    payload = {"to_number": phone_number, "objective": objective, "lead_name": lead_name}
    if override_context:
        payload["context"] = override_context
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", data)


async def _invoke_mcp_create_call(phone_number: str, objective: str, override_context: str = None):
    """Backward-compatible async entrypoint. Forwards to the canonical endpoint
    (grounding + logging + governor inherited). ``override_context`` is passed
    through as extra call context."""
    return await asyncio.to_thread(_initiate, phone_number, objective, override_context)


@tool
def vapi_mcp_call(phone_number: str, objective: str, lead_name: str = None):
    """
    Place a phone call to a lead. The call is grounded in the CRM dossier /
    knowledge base and automatically logged; unknown contacts trigger a strict
    no-fabrication mode.

    Args:
        phone_number: The phone number to call.
        objective: The goal of the call.
        lead_name: Optional CRM Lead id for grounding + tracking.
    """
    try:
        result = _initiate(phone_number, objective, lead_name=lead_name)
    except Exception as e:
        return f"❌ Call Failed: {e}"
    call_id = result.get("call_id") or result.get("vapi_call_id")
    if call_id:
        return f"✅ Call Initiated. Call ID: {call_id}\nObjective: {objective}"
    return f"❌ Call Failed. Response: {json.dumps(result)}"
