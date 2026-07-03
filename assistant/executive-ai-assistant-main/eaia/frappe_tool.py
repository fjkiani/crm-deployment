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

# Default corrected to the live alpha-crm site (was jedilabs2 — a stale/wrong tenant).
# Override via FRAPPE_SITE_URL for other deployments.
FRAPPE_SITE = os.getenv("FRAPPE_SITE_URL", "https://alpha-crm.v.frappe.cloud")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")

_request_counter = 0


def _call_mcp(method: str, params: dict = None):
    """Send a JSON-RPC tools/call request to the Frappe MCP endpoint.

    If the MCP endpoint (crm.api.mcp_server.handle_mcp) is unavailable — which is
    the case until the frappe_mcp app is installed on the site (returns 404/417) —
    fall back to native Frappe REST for the subset of tools the pipeline needs.
    This keeps the agent functional against a stock Frappe CRM with no MCP app.
    """
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

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        # 404/417 → MCP app not installed on this site; use native REST fallback
        if response.status_code in (404, 417):
            return _native_rest_fallback(method, params or {}, headers)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            raise Exception(f"MCP Error: {result['error']}")
        return result.get("result")
    except requests.exceptions.RequestException:
        # connection/timeout — try native REST before giving up
        return _native_rest_fallback(method, params or {}, headers)


def _native_rest_fallback(method: str, args: dict, headers: dict):
    """Native Frappe REST implementations for core tools when MCP is absent."""
    base = f"{FRAPPE_SITE}/api/resource"

    if method == "echo":
        return {"echo": args.get("message", ""), "via": "native_rest_fallback"}

    if method == "create_lead":
        body = {
            "lead_name":   f"{args.get('first_name','')} {args.get('last_name','')}".strip(),
            "first_name":  args.get("first_name", ""),
            "last_name":   args.get("last_name", ""),
            "organization": args.get("organization", ""),
            "job_title":   args.get("title", ""),
            "email":       args.get("email", ""),
            "status":      "New",
        }
        body = {k: v for k, v in body.items() if v}
        r = requests.post(f"{base}/CRM Lead", headers=headers, json=body, timeout=20)
        r.raise_for_status()
        return {"name": r.json()["data"]["name"]}

    if method == "update_lead_context":
        lead = args["lead_name"]
        body = {"additional_data": args.get("context", "{}")}
        r = requests.put(f"{base}/CRM Lead/{lead}", headers=headers, json=body, timeout=20)
        r.raise_for_status()
        return {"name": lead, "updated": True}

    if method == "update_lead_score":
        lead = args["lead_name"]
        # CRM Lead has no native score field in stock schema — persist into additional_data
        body = {"additional_data": json.dumps({"nyx_score": args.get("score"),
                                               "reasoning": args.get("reasoning", "")})}
        r = requests.put(f"{base}/CRM Lead/{lead}", headers=headers, json=body, timeout=20)
        r.raise_for_status()
        return {"name": lead, "score": args.get("score")}

    if method == "create_note":
        body = {
            "doctype": "FCRM Note",
            "title": args.get("title", "Note"),
            "content": args.get("content", ""),
            "reference_doctype": "CRM Lead",
            "reference_name": args.get("lead_name"),
        }
        r = requests.post(f"{base}/FCRM Note", headers=headers, json=body, timeout=20)
        r.raise_for_status()
        return {"name": r.json()["data"]["name"]}

    if method == "get_leads_batch":
        limit = args.get("limit", 5)
        r = requests.get(f"{base}/CRM Lead?limit_page_length={limit}"
                         f'&fields=["name","lead_name","email","organization","status"]',
                         headers=headers, timeout=20)
        r.raise_for_status()
        return {"leads": r.json().get("data", [])}

    if method == "search_leads_faceted":
        facet_filters = {}
        if args.get("has_competitive_intel"):
            facet_filters["has_competitive_intel"] = 1
        if args.get("has_gtm_narrative"):
            facet_filters["has_gtm_narrative"] = 1
        if args.get("min_opportunities"):
            facet_filters["n_opportunities"] = [">", int(args["min_opportunities"])]
        if args.get("session_slug"):
            facet_filters["session_slug"] = args["session_slug"]
        body = {
            "q": args.get("query", ""),
            "tier": args.get("tier", ""),
            "page_length": args.get("limit", 20),
        }
        if args.get("score_min"):
            body["score_min"] = args["score_min"]
        if facet_filters:
            body["facet_filters"] = json.dumps(facet_filters)
        r = requests.post(f"{FRAPPE_SITE}/api/method/crm.api.intel_facets.search_leads",
                          headers=headers, json=body, timeout=30)
        r.raise_for_status()
        msg = r.json().get("message", {})
        return {"rows": msg.get("rows", []), "total_count": msg.get("total_count", 0)}

    if method == "list_tasks":
        body = {k: v for k, v in {
            "lead": args.get("lead", ""),
            "deal": args.get("deal", ""),
            "status": args.get("status", ""),
            "assigned_to": args.get("assigned_to", ""),
            "limit": args.get("limit", 50),
        }.items() if v}
        r = requests.post(f"{FRAPPE_SITE}/api/method/crm.api.tasks.get_tasks",
                          headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return {"tasks": r.json().get("message", [])}

    if method == "create_task":
        body = {k: v for k, v in {
            "title": args.get("title", ""),
            "lead": args.get("lead", ""),
            "deal": args.get("deal", ""),
            "priority": args.get("priority", "Medium"),
            "status": args.get("status", "Todo"),
            "due_date": args.get("due_date", ""),
            "description": args.get("description", ""),
            "assigned_to": args.get("assigned_to", ""),
        }.items() if v}
        r = requests.post(f"{FRAPPE_SITE}/api/method/crm.api.tasks.create_task",
                          headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return {"name": r.json().get("message"), "created": True}

    if method == "update_task_status":
        r = requests.post(f"{FRAPPE_SITE}/api/method/crm.api.tasks.set_status",
                          headers=headers,
                          json={"name": args["name"], "status": args["status"]},
                          timeout=20)
        r.raise_for_status()
        return r.json().get("message", {})

    if method == "convert_task":
        body = {"name": args["name"]}
        if args.get("target"):
            body["target"] = args["target"]
        r = requests.post(f"{FRAPPE_SITE}/api/method/crm.api.tasks.convert_task",
                          headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json().get("message", {})

    raise Exception(f"MCP unavailable and no native REST fallback for tool '{method}'. "
                    f"Install the frappe_mcp app on the site to enable it.")


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
def search_leads_faceted(
    query: str = "",
    tier: str = "",
    score_min: float = 0,
    has_competitive_intel: int = 0,
    has_gtm_narrative: int = 0,
    min_opportunities: int = 0,
    session_slug: str = "",
    limit: int = 20,
):
    """RICH facet-aware lead search (CRM Lead JOIN Lead Intel Facets). Prefer this
    over `search_leads` when you need intelligence facets: tier, opportunity /
    vulnerability counts, competitive intel, GTM narrative, or source session.

    Args:
        query: Free-text over name / organization / email / source_ref_id.
        tier: 'Tier 1' | 'Tier 2' | 'Tier 3'.
        score_min: Minimum lead_score.
        has_competitive_intel: 1 to require competitive intel.
        has_gtm_narrative: 1 to require a GTM narrative.
        min_opportunities: Require n_opportunities greater than this value.
        session_slug: Restrict to a given intel session.
        limit: Max rows.
    """
    return _call_mcp("search_leads_faceted", {
        "query": query,
        "tier": tier,
        "score_min": score_min,
        "has_competitive_intel": has_competitive_intel,
        "has_gtm_narrative": has_gtm_narrative,
        "min_opportunities": min_opportunities,
        "session_slug": session_slug,
        "limit": limit,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TASKS  (typed lead/deal links + configurable conversion)
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def list_tasks(lead: str = "", deal: str = "", status: str = "",
               assigned_to: str = "", limit: int = 50):
    """List CRM Tasks, optionally scoped to a lead or deal. Understands both the
    typed lead/deal links and the legacy dynamic reference. Use before creating
    follow-ups to avoid duplicates.

    Args:
        lead: CRM Lead name to scope to.
        deal: CRM Deal name to scope to.
        status: Backlog | Todo | In Progress | Done | Canceled.
        assigned_to: User email to filter by owner.
        limit: Max rows.
    """
    return _call_mcp("list_tasks", {
        "lead": lead, "deal": deal, "status": status,
        "assigned_to": assigned_to, "limit": limit,
    })


@tool
def create_task(title: str, lead: str = "", deal: str = "", priority: str = "Medium",
                status: str = "Todo", due_date: str = "", description: str = "",
                assigned_to: str = ""):
    """Create a CRM Task linked to a lead or deal (sets typed + dynamic links).

    Args:
        title: Task title (required).
        lead: CRM Lead to link.
        deal: CRM Deal to link.
        priority: Low | Medium | High.
        status: Backlog | Todo | In Progress | Done | Canceled.
        due_date: ISO datetime (e.g. '2026-07-10 17:00:00').
        description: Free-text detail.
        assigned_to: User email to assign to.
    """
    return _call_mcp("create_task", {
        "title": title, "lead": lead, "deal": deal, "priority": priority,
        "status": status, "due_date": due_date, "description": description,
        "assigned_to": assigned_to,
    })


@tool
def update_task_status(name: str, status: str):
    """Move a CRM Task to a new status (Backlog|Todo|In Progress|Done|Canceled)."""
    return _call_mcp("update_task_status", {"name": name, "status": status})


@tool
def convert_task(name: str, target: str = ""):
    """Convert a task's linked lead into a Deal OR append an AACR Intel
    Opportunity, then mark the task Done. Omit `target` to use the site default.

    Args:
        name: CRM Task name.
        target: 'deal' | 'opportunity' (optional).
    """
    return _call_mcp("convert_task", {"name": name, "target": target})


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
