"""
Voice call tool (LangChain) — THIN PROXY to the canonical CRM voice spine.

Consolidation note (voice-prod audit): this file used to build its own Vapi
`/call` payload with a HARDCODED api key + phoneNumberId and no call logging,
governor, or reliable grounding. Those responsibilities now live in ONE place:

    crm.api.vapi.initiate_outbound_call

which is dossier/KB-grounded, writes Vapi Call Log + CRM Call Log, enforces the
per-lead call governor, and reads Vapi credentials from tenant config (never
hardcoded). This wrapper simply forwards to it so every agent-placed call is
tracked and grounded identically to UI-placed calls.
"""

import json
import os

import requests
from langchain_core.tools import tool

FRAPPE_SITE = os.getenv("FRAPPE_SITE_URL", "https://alpha-crm.v.frappe.cloud").rstrip("/")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")


def _post(method: str, payload: dict) -> dict:
    url = f"{FRAPPE_SITE}/api/method/{method}"
    headers = {"Content-Type": "application/json"}
    if API_KEY and API_SECRET:
        headers["Authorization"] = f"token {API_KEY}:{API_SECRET}"
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", data)


@tool
def voice_call(phone_number: str, objective: str, lead_name: str = None):
    """
    Place a phone call to a lead to achieve an objective (e.g. schedule a meeting,
    verify interest). The call is grounded in the lead's CRM dossier / knowledge
    base and automatically logged; if no verified background exists the agent is
    constrained to avoid inventing facts.

    Args:
        phone_number: The phone number to call (e.g. +14155551234)
        objective: The goal of the call (e.g. "Confirm interest in the STC-1010 program")
        lead_name: Optional CRM Lead id for dossier grounding + call tracking.
    """
    try:
        result = _post(
            "crm.api.vapi.initiate_outbound_call",
            {"to_number": phone_number, "objective": objective, "lead_name": lead_name},
        )
    except Exception as e:
        return f"❌ Call Failed: {e}"

    call_id = result.get("call_id") or result.get("vapi_call_id")
    if call_id:
        return f"✅ Call Initiated. Call ID: {call_id}\nObjective: {objective}"
    return f"❌ Call Failed. Response: {json.dumps(result)}"
