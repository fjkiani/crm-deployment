"""
Frappe MCP Tools — LangChain @tool wrappers
=============================================
Each Frappe MCP tool wrapped as a LangChain tool so agents can .bind_tools() with them.

Usage:
    from eaia.tools.frappe_mcp_tools import crm_get_dossier, crm_update_context, ...
    model = ChatCohere().bind_tools([crm_get_dossier, crm_update_context, ...])
"""

from langchain_core.tools import tool

from eaia.mcp_client import FrappeMCPClient

# Module-level client instance (reused across tool calls)
_mcp = FrappeMCPClient()


# ══════════════════════════════════════════════════════════════════════════════
# LEAD MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════


@tool
async def crm_get_dossier(lead_name: str) -> dict:
    """Fetch full lead intelligence dossier from Frappe CRM.

    Returns score, distilled signals, enrichment data, email drafts, and notes.
    Call this FIRST before doing any research to check what we already know
    and avoid duplicate enrichment work.

    Args:
        lead_name: CRM Lead ID (e.g. 'LT-1772401234')
    """
    return await _mcp.get_lead_dossier(lead_name)


@tool
async def crm_update_context(lead_name: str, context_json: str) -> dict:
    """Write enrichment data to a CRM Lead's additional_data JSON field.

    Use this after gathering new intelligence to persist findings to the CRM.
    The context_json should be a JSON string of the enrichment payload.

    Args:
        lead_name: CRM Lead ID (e.g. 'LT-1772401234')
        context_json: JSON string of enrichment data to write
    """
    return await _mcp.call_tool("update_lead_context", {
        "lead_name": lead_name,
        "context_json": context_json,
    })


@tool
async def crm_search_leads(query: str, status: str = "", limit: int = 20) -> dict:
    """Search CRM for leads by name, company, or status.

    Use to find related contacts at the same company for cross-lead intelligence,
    or to check if a lead already exists before creating a new one.

    Args:
        query: Search term (name, company, or keyword)
        status: Optional status filter (e.g. 'New', 'Contacted', 'Draft Ready')
        limit: Max results to return (default 20)
    """
    return await _mcp.search_leads(query, status=status, limit=limit)


@tool
async def crm_create_lead(
    first_name: str,
    last_name: str,
    email: str,
    organization: str = "",
    job_title: str = "",
) -> dict:
    """Create a new CRM Lead in Frappe.

    The email is used as the dedup key — if a lead with this email exists,
    the existing lead will be updated instead.

    Args:
        first_name: Lead's first name
        last_name: Lead's last name
        email: Lead's email address (dedup key)
        organization: Company name
        job_title: Job title
    """
    return await _mcp.create_lead({
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "organization": organization,
        "job_title": job_title,
    })


# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════


@tool
async def crm_create_note(lead_name: str, title: str, content: str) -> dict:
    """Create a note on a CRM Lead that appears in the lead's timeline.

    Use this to log important findings during enrichment, such as a dossier
    summary, a notable discovery, or a risk signal.

    Args:
        lead_name: CRM Lead ID (e.g. 'LT-1772401234')
        title: Note title (e.g. 'Nyx Intel — John Smith [Tier 1, Score 85]')
        content: Note body (Markdown supported)
    """
    return await _mcp.create_note(lead_name, title, content)


@tool
async def crm_update_score(lead_name: str, score: int, reasoning: str = "") -> dict:
    """Update the lead_score field on a CRM Lead.

    Args:
        lead_name: CRM Lead ID
        score: Numeric score 0-100
        reasoning: Brief explanation of why this score was assigned
    """
    return await _mcp.update_lead_score(lead_name, score, reasoning)


@tool
async def crm_get_portfolio_links(organization: str, email_domain: str = None) -> dict:
    """Find other CRM Leads connected to the same organization or email domain.

    Use this for the Zeta Entanglement Protocol to find "portfolio links" 
    and thread intelligence across multiple leads at the same account.

    Args:
        organization: The company/organization name to search for
        email_domain: The email domain to search for (e.g. '@company.com')
    """
    return await _mcp.get_portfolio_links(organization, email_domain)


@tool
async def crm_get_enrichment_status() -> dict:
    """Health check: how many leads have intel data vs. those missing enrichment.

    Returns total_leads, leads_with_intel, leads_missing_intel, and coverage %.
    Use to assess overall enrichment coverage across the CRM.
    """
    return await _mcp.get_enrichment_status()


@tool
async def crm_get_communication_history(lead_name: str, limit: int = 20) -> dict:
    """Fetch email and call communication history for a lead.

    Returns a list of Communication records showing past interactions.
    Use to understand where we are in the outreach sequence.

    Args:
        lead_name: CRM Lead ID
        limit: Max records to return
    """
    return await _mcp.get_communication_history(lead_name, limit)


# ══════════════════════════════════════════════════════════════════════════════
# OUTREACH
# ══════════════════════════════════════════════════════════════════════════════


@tool
async def crm_approve_send(
    lead_name: str, to_email: str, subject: str, body: str
) -> dict:
    """Approve and send an email to a lead. Records it as a Communication in CRM.

    This logs the email in the lead's timeline. Only call this after SDR approval
    or for leads flagged for auto-send.

    Args:
        lead_name: CRM Lead ID
        to_email: Recipient email address
        subject: Email subject line
        body: Email body (plain text or HTML)
    """
    return await _mcp.approve_and_send(lead_name, to_email, subject, body)


@tool
async def crm_fire_sequence(lead_name: str, dry_run: bool = True) -> dict:
    """Fire the next outreach sequence step for a lead.

    Set dry_run=False to actually fire. When dry_run=True, returns what
    would happen without executing.

    Args:
        lead_name: CRM Lead ID
        dry_run: If True, preview only. If False, execute the step.
    """
    return await _mcp.fire_sequence_step(lead_name, dry_run)


@tool
async def crm_classify_reply(from_email: str, subject: str, body: str) -> dict:
    """Classify an inbound email reply and update CRM status accordingly.

    Classifications: INTERESTED, NOT_INTERESTED, UNSUBSCRIBE, OOO, UNKNOWN.
    Use to automatically route inbound replies to the right workflow.

    Args:
        from_email: Sender's email address
        subject: Email subject
        body: Email body text
    """
    return await _mcp.classify_and_route_reply(from_email, subject, body)


@tool
async def crm_get_lead_snapshot(lead_name: str) -> dict:
    """Get compact real-time lead status: current status, email count, call count.

    A quick health check on a single lead without pulling the full dossier.

    Args:
        lead_name: CRM Lead ID
    """
    return await _mcp.get_lead_status_snapshot(lead_name)


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULING
# ══════════════════════════════════════════════════════════════════════════════


@tool
async def crm_log_call(lead_name: str, outcome: str, notes: str = "") -> dict:
    """Log a voice call outcome to the CRM.

    Args:
        lead_name: CRM Lead ID
        outcome: Call result (e.g. 'connected', 'voicemail', 'no_answer')
        notes: Free-text notes from the call
    """
    return await _mcp.log_call_outcome(lead_name, outcome, notes)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 10: ANALYTICS TOOL
# ══════════════════════════════════════════════════════════════════════════════

@tool
async def crm_get_pipeline_analytics() -> dict:
    """Get pipeline health, funnel metrics, and A/B framework stats from the CRM.

    Returns enrichment coverage, conversion funnel counts, framework distribution,
    entanglement count, and vulture event count.
    """
    return await _mcp.get_pipeline_analytics()


# ══════════════════════════════════════════════════════════════════════════════
# ALL TOOLS — convenience list for agent.bind_tools()
# ══════════════════════════════════════════════════════════════════════════════

ALL_CRM_TOOLS = [
    crm_get_dossier,
    crm_update_context,
    crm_search_leads,
    crm_create_lead,
    crm_create_note,
    crm_update_score,
    crm_get_enrichment_status,
    crm_get_communication_history,
    crm_get_portfolio_links,
    crm_get_pipeline_analytics,
    crm_approve_send,
    crm_fire_sequence,
    crm_classify_reply,
    crm_get_lead_snapshot,
    crm_log_call,
]
