"""
Nyx MCP Server — CRM Agent Tools
=================================
Registered at: /api/method/crm.api.mcp_server.handle_mcp

This file exposes all Frappe-side CRM operations as MCP tools.
The EAIA agent calls these via HTTP JSON-RPC through frappe_tool.py.
Adding a new tool = one @mcp.tool() decorator here + one wrapper in frappe_tool.py.
"""

import frappe
import json
from frappe_mcp import MCP

mcp = MCP("crm-agent")

# ═══════════════════════════════════════════════════════════════════════════════
# FOUNDATION TOOLS (already existed, cleaned up)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def echo(message: str):
    """Echoes back the message. Useful for testing connectivity.

    Args:
        message: Any string to echo back.
    """
    return f"CRM Agent received: {message}"


@mcp.tool()
def create_lead(
    first_name: str,
    last_name: str,
    organization: str,
    title: str = "",
    email: str = "",
    source: str = "Nyx Pipeline",
):
    """Creates a new Lead in the CRM.

    Args:
        first_name: Lead's first name.
        last_name: Lead's last name.
        organization: Company / organization name.
        title: Job title (optional).
        email: Email address (optional).
        source: Lead source label.
    """
    try:
        doc = frappe.get_doc({
            "doctype": "CRM Lead",
            "first_name": first_name,
            "last_name": last_name,
            "organization": organization,
            "job_title": title,
            "email_id": email,
            "source": source,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return f"Created Lead: {doc.name} ({first_name} {last_name})"
    except Exception as e:
        return f"Error creating lead: {str(e)}"


@mcp.tool()
def update_lead_context(lead_name: str, context: str):
    """Updates the Flexible Context (additional_data) of a Lead.

    Args:
        lead_name: CRM Lead ID (e.g. CRM-LEAD-2024-001).
        context: JSON string of key-value pairs to upsert.
    """
    try:
        new_data = json.loads(context)
    except json.JSONDecodeError:
        return "Error: Context must be valid JSON string."

    lead = frappe.get_doc("CRM Lead", lead_name)
    current = json.loads(lead.additional_data) if lead.additional_data else {}
    current.update(new_data)
    lead.additional_data = json.dumps(current)
    lead.save(ignore_permissions=True)
    frappe.db.commit()
    return f"Updated context for {lead_name}. Keys: {list(new_data.keys())}"


@mcp.tool()
def get_leads_batch(limit: int = 5):
    """Fetches a batch of leads for processing.

    Args:
        limit: Max number of leads to return.
    """
    return frappe.get_all(
        "CRM Lead",
        fields=["name", "lead_name", "organization", "email", "status", "lead_score"],
        limit=limit,
    )


@mcp.tool()
def cleanup_leads(confirm: bool = False):
    """Deletes ALL leads in the system. Use with EXTREME CAUTION.

    Args:
        confirm: Must be True to execute.
    """
    if not confirm:
        return "Operation cancelled. Set confirm=True."
    leads = frappe.get_all("CRM Lead", pluck="name")
    count = len(leads)
    for name in leads:
        frappe.delete_doc("CRM Lead", name, force=1, ignore_permissions=True)
    frappe.db.commit()
    return f"Deleted {count} leads."


# ═══════════════════════════════════════════════════════════════════════════════
# ENRICHMENT PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_lead_dossier(lead_name: str):
    """Fetch full lead data with latest FCRM Note + intel data.

    Args:
        lead_name: CRM Lead ID.
    """
    lead = frappe.get_doc("CRM Lead", lead_name)

    # Get latest FCRM Note (enrichment intel lives here)
    notes = frappe.get_all(
        "FCRM Note",
        filters={"reference_doctype": "CRM Lead", "reference_docname": lead_name},
        fields=["name", "title", "content", "creation"],
        order_by="creation desc",
        limit=3,
    )

    # Get additional_data (enrichment JSON)
    intel = {}
    if lead.additional_data:
        try:
            intel = json.loads(lead.additional_data)
        except json.JSONDecodeError:
            intel = {"raw": lead.additional_data}

    return {
        "lead_name": lead.name,
        "full_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "organization": lead.organization,
        "email": lead.email,
        "status": lead.status,
        "job_title": lead.job_title,
        "lead_score": getattr(lead, "lead_score", None),
        "source": lead.source,
        "intel": intel,
        "notes": [{"title": n.title, "content": n.content[:500], "created": str(n.creation)} for n in notes],
    }


@mcp.tool()
def search_leads(query: str = "", status: str = "", score_min: int = 0, limit: int = 20):
    """Search leads by name, company, status, or minimum score.

    Args:
        query: Search text (matches lead_name or organization).
        status: Filter by status (New, Contacted, Interested, etc).
        score_min: Minimum lead_score to include.
        limit: Max results.
    """
    filters = {}
    if status:
        filters["status"] = status
    if score_min:
        filters["lead_score"] = [">=", score_min]

    or_filters = {}
    if query:
        or_filters = {
            "lead_name": ["like", f"%{query}%"],
            "organization": ["like", f"%{query}%"],
        }

    leads = frappe.get_all(
        "CRM Lead",
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name", "lead_name", "organization", "email", "status", "lead_score", "source"],
        order_by="lead_score desc",
        limit=limit,
    )
    return leads


@mcp.tool()
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
    """Facet-aware lead search over CRM Lead JOIN Lead Intel Facets — the RICH
    search. Prefer this over `search_leads` when you need intelligence facets:
    tier, opportunity/vulnerability counts, competitive intel, GTM narrative, or
    the source session. Free-text `query` matches name/org/email/source_ref_id.

    Args:
        query: Free-text over lead_name / organization / email / source_ref_id.
        tier: 'Tier 1' | 'Tier 2' | 'Tier 3' (convenience facet shortcut).
        score_min: Minimum lead_score.
        has_competitive_intel: 1 to require competitive (Schema B) intel.
        has_gtm_narrative: 1 to require a GTM narrative.
        min_opportunities: Require n_opportunities greater than this value.
        session_slug: Restrict to leads sourced from a given intel session.
        limit: Max rows (capped at 100 server-side).
    """
    facet_filters = {}
    if has_competitive_intel:
        facet_filters["has_competitive_intel"] = 1
    if has_gtm_narrative:
        facet_filters["has_gtm_narrative"] = 1
    if min_opportunities:
        facet_filters["n_opportunities"] = [">", int(min_opportunities)]
    if session_slug:
        facet_filters["session_slug"] = session_slug

    from crm.api.intel_facets import search_leads as _facet_search

    res = _facet_search(
        q=query,
        facet_filters=facet_filters or None,
        tier=tier or "",
        score_min=score_min or None,
        page_length=limit,
    )
    # Return the rows + count in an LLM-friendly shape (drop the columns metadata).
    rows = res.get("rows") if isinstance(res, dict) else res
    return {"rows": rows or [], "total_count": (res.get("total_count") if isinstance(res, dict) else len(rows or []))}


@mcp.tool()
def list_tasks(
    lead: str = "",
    deal: str = "",
    status: str = "",
    assigned_to: str = "",
    limit: int = 50,
):
    """List CRM Tasks, optionally scoped to a lead or deal. Understands the
    typed `lead`/`deal` links AND the legacy dynamic reference. Use this to see
    what follow-ups exist for a prospect before creating new ones.

    Args:
        lead: CRM Lead name to scope tasks to.
        deal: CRM Deal name to scope tasks to.
        status: Backlog | Todo | In Progress | Done | Canceled.
        assigned_to: User email to filter by owner.
        limit: Max rows (capped server-side).
    """
    from crm.api.tasks import get_tasks as _get_tasks

    return {
        "tasks": _get_tasks(
            lead=lead or None,
            deal=deal or None,
            status=status or None,
            assigned_to=assigned_to or None,
            limit=limit,
        )
    }


@mcp.tool()
def create_task(
    title: str,
    lead: str = "",
    deal: str = "",
    priority: str = "Medium",
    status: str = "Todo",
    due_date: str = "",
    description: str = "",
    assigned_to: str = "",
):
    """Create a CRM Task. Sets BOTH the typed link and the legacy dynamic
    reference so old and new consumers both see it. Provide `lead` (or `deal`)
    to link the follow-up to a prospect.

    Args:
        title: Task title (required).
        lead: CRM Lead to link.
        deal: CRM Deal to link.
        priority: Low | Medium | High.
        status: Backlog | Todo | In Progress | Done | Canceled.
        due_date: ISO datetime string (e.g. '2026-07-10 17:00:00').
        description: Free-text detail.
        assigned_to: User email to assign to.
    """
    from crm.api.tasks import create_task as _create_task

    name = _create_task(
        title=title,
        lead=lead or None,
        deal=deal or None,
        priority=priority or "Medium",
        status=status or "Todo",
        due_date=due_date or None,
        description=description or None,
        assigned_to=assigned_to or None,
    )
    return {"name": name, "created": True}


@mcp.tool()
def update_task_status(name: str, status: str):
    """Move a CRM Task to a new status (Backlog|Todo|In Progress|Done|Canceled)."""
    from crm.api.tasks import set_status as _set_status

    return _set_status(name, status)


@mcp.tool()
def convert_task(name: str, target: str = ""):
    """Convert a task's linked lead into a Deal OR append an AACR Intel
    Opportunity, then mark the task Done.

    Args:
        name: CRM Task name.
        target: 'deal' | 'opportunity'. Omit to use the site's configured
                default (site config key nyx_task_convert_default).
    """
    from crm.api.tasks import convert_task as _convert_task

    return _convert_task(name, target=target or None)


@mcp.tool()
def search_crm_knowledge(query: str, limit: int = 10):
    """Search CRM Notes and lead intel for voice assistant / knowledge context."""
    from crm.api.intelligence import search_crm_knowledge as _search

    return _search(query, limit)


@mcp.tool()
def get_enrichment_status():
    """Health check: counts leads by enrichment completeness.
    Returns counts of leads with intel data vs without.
    """
    total = frappe.db.count("CRM Lead")
    with_intel = frappe.db.count("CRM Lead", {"additional_data": ["is", "set"]})
    with_notes = frappe.db.sql(
        """SELECT COUNT(DISTINCT reference_docname) FROM `tabFCRM Note`
           WHERE reference_doctype='CRM Lead'""",
        as_list=True,
    )[0][0]

    return {
        "total_leads": total,
        "leads_with_intel": with_intel,
        "leads_without_intel": total - with_intel,
        "leads_with_notes": with_notes,
        "coverage_pct": round(with_intel / max(total, 1) * 100, 1),
    }


@mcp.tool()
def get_draft_queue():
    """Get all leads with pending email drafts awaiting SDR approval.
    Returns leads with status 'Draft Ready' and their email draft data.
    """
    leads = frappe.get_list(
        "CRM Lead",
        filters={"custom_email_status": "Draft Ready"},
        fields=[
            "name", "lead_name", "email", "organization",
            "job_title", "lead_score", "additional_data",
        ],
        limit=100,
        order_by="modified desc",
    )

    queue = []
    for lead in leads:
        entry = {
            "lead_name": lead.name,
            "full_name": lead.lead_name,
            "email": lead.email,
            "organization": lead.organization,
            "score": lead.lead_score,
        }
        # Extract email draft from additional_data JSON
        try:
            data = frappe.parse_json(lead.additional_data or "{}")
            entry["email_draft"] = data.get("email_draft", {})
        except Exception:
            entry["email_draft"] = {}
        queue.append(entry)

    return {"count": len(queue), "drafts": queue}


# ═══════════════════════════════════════════════════════════════════════════════
# OUTREACH PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_sequence_status(lead_name: str = ""):
    """Real sequence status from Outreach Sequence Instance + CRM Task + Communication.

    Args:
        lead_name: Optional — filter to one lead. Empty = all instances.
    """
    from crm.api.sequence_engine import get_sequence_state
    filters = {}
    if lead_name:
        # Outreach Sequence Instance has NO `lead` column; it links to a lead only
        # indirectly via `prospect` (Lead Prospect -> promoted_to_lead). Resolve the
        # lead's prospect(s) and filter instances by prospect, else this raises an
        # unknown-column error on a non-empty lead_name.
        prospects = frappe.get_all(
            "Lead Prospect",
            filters={"promoted_to_lead": lead_name},
            pluck="name",
            limit=500,
        )
        if not prospects:
            return {"count": 0, "instances": [], "lead": lead_name,
                    "note": "No Lead Prospect linked to this lead."}
        filters["prospect"] = ["in", prospects]
    instances = frappe.get_all(
        "Outreach Sequence Instance",
        filters=filters,
        fields=["name", "outreach_sequence", "prospect", "status",
                "current_step", "total_steps", "next_send_date", "emails_sent",
                "last_email_sent"],
        order_by="modified desc",
        limit=100,
    )
    out = []
    for inst in instances:
        state = get_sequence_state(inst["name"])
        out.append({
            "instance": inst["name"],
            "sequence": inst.get("outreach_sequence"),
            "status": inst.get("status"),
            "current_step": inst.get("current_step"),
            "total_steps": inst.get("total_steps"),
            "next_send_date": str(inst.get("next_send_date") or ""),
            "emails_sent": inst.get("emails_sent"),
            "next_step": state.get("next_step"),
        })
    return {"count": len(out), "instances": out}


@mcp.tool()
def fire_sequence_step(instance_name: str = "", task_name: str = "", dry_run: bool = True):
    """Advance a sequence instance one step via the sequence_engine (human-gated).

    The engine NEVER sends email; it only transitions state after verifying the
    step's Communication is delivery_status=="Sent" and the recipient is
    deliverable. dry_run returns the gate evaluation without mutating.

    Args:
        instance_name: Outreach Sequence Instance name.
        task_name: CRM Task name for the step (optional; resolved from instance).
        dry_run: If True, report what WOULD happen without advancing.
    """
    from crm.api import sequence_engine as se
    if dry_run:
        state = se.get_sequence_state(instance_name) if instance_name else {"ok": False, "reason": "no_instance"}
        return {"status": "dry_run", "instance": instance_name, "state": state,
                "message": "Would advance via sequence_engine.advance_sequence_instance after human send + assert_deliverable."}
    result = se.advance_sequence_instance(instance_name=instance_name or None,
                                          task_name=task_name or None)
    return result


@mcp.tool()
def pause_sequence(instance_name: str):
    """Pause an Outreach Sequence Instance (real status field, not additional_data).

    Args:
        instance_name: Outreach Sequence Instance name.
    """
    if not frappe.db.exists("Outreach Sequence Instance", instance_name):
        return {"ok": False, "reason": "instance_not_found", "instance": instance_name}
    frappe.db.set_value("Outreach Sequence Instance", instance_name, "status", "Paused")
    frappe.db.commit()
    return {"ok": True, "instance": instance_name, "status": "Paused"}


@mcp.tool()
def approve_and_send(
    communication_name: str,
    lead_name: str = "",
):
    """Approve a DRAFT Communication and send it via the real SMTP path.

    Routes through crm.api.email.send, which calls assert_deliverable BEFORE
    frappe.sendmail and only stamps delivery_status="Sent" after a real send.
    This tool CANNOT mark a lead Contacted without a genuine SMTP send — the
    status flip happens only on send success.

    Args:
        communication_name: The draft Communication to send.
        lead_name: Optional CRM Lead to mark Contacted on success.
    """
    from crm.api import email as email_api
    comm = frappe.get_doc("Communication", communication_name)
    if (comm.delivery_status or "") == "Sent":
        return {"status": "already_sent", "communication": communication_name}
    # send() raises via assert_deliverable on placeholder recipients and only
    # sets delivery_status="Sent" after frappe.sendmail succeeds.
    email_api.send(communication_name)
    if lead_name and frappe.db.exists("CRM Lead", lead_name):
        frappe.db.set_value("CRM Lead", lead_name, "status", "Contacted")
        frappe.db.commit()
    return {"status": "sent", "communication": communication_name, "lead": lead_name}


@mcp.tool()
def create_outreach_sequence(
    sequence_name: str,
    tier: str = "",
    subject_template: str = "",
    body_template: str = "",
    sender_email: str = "",
    follow_up_days: int = 3,
    max_follow_ups: int = 4,
):
    """Create an Outreach Sequence matching the REAL DocType schema.

    The live Outreach Sequence has: sequence_name, tier, subject_template,
    body_template, follow_up_days, max_follow_ups, sender_email, status, active.
    It has NO channel / max_daily_sends / description fields — those were the
    fake-tool landmines. Created as Draft (active=0); arm via arm_sequence.

    Args:
        sequence_name: Name for the sequence.
        tier: Target tier label.
        subject_template: Email subject template.
        body_template: Email body template.
        sender_email: Sender address.
        follow_up_days: Days between follow-ups.
        max_follow_ups: Max follow-up count.
    """
    try:
        doc = frappe.get_doc({
            "doctype": "Outreach Sequence",
            "sequence_name": sequence_name,
            "tier": tier,
            "subject_template": subject_template,
            "body_template": body_template,
            "sender_email": sender_email,
            "follow_up_days": str(follow_up_days),
            "max_follow_ups": max_follow_ups,
            "status": "Draft",
            "active": 0,
            "owner": frappe.session.user,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "name": doc.name, "sequence_name": sequence_name,
                "note": "Draft/inactive. Arm with arm_sequence to activate."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULING PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_call_log(lead_name: str):
    """All Communication records of type Phone for a lead.

    Args:
        lead_name: CRM Lead ID.
    """
    calls = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "CRM Lead",
            "reference_name": lead_name,
            "communication_medium": "Phone",
        },
        fields=["name", "subject", "content", "creation", "status", "sender"],
        order_by="creation desc",
        limit=20,
    )
    return calls


@mcp.tool()
def log_call_outcome(
    lead_name: str,
    call_id: str,
    outcome: str,
    transcript: str = "",
    duration_seconds: int = 0,
):
    """Write a call outcome to CRM — creates Communication + FCRM Note.

    Args:
        lead_name: CRM Lead ID.
        call_id: External call ID (e.g. Vapi call ID).
        outcome: Call outcome (answered, voicemail, no_answer, meeting_booked, rejected).
        transcript: Call transcript text (optional).
        duration_seconds: Call duration in seconds.
    """
    try:
        # Log as Phone Communication
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Phone",
            "subject": f"Call: {outcome} (ID: {call_id[:12]})",
            "content": transcript or f"Call outcome: {outcome}",
            "reference_doctype": "CRM Lead",
            "reference_name": lead_name,
            "sent_or_received": "Sent",
            "status": "Linked",
        })
        comm.insert(ignore_permissions=True)

        # Also create FCRM Note for visibility in CRM Lead timeline
        note = frappe.get_doc({
            "doctype": "FCRM Note",
            "title": f"📞 Call: {outcome}",
            "content": f"**Call ID:** {call_id}\n**Outcome:** {outcome}\n**Duration:** {duration_seconds}s\n\n{transcript[:1000] if transcript else 'No transcript'}",
            "reference_doctype": "CRM Lead",
            "reference_docname": lead_name,
        })
        note.insert(ignore_permissions=True)

        # Update lead status based on outcome
        status_map = {
            "meeting_booked": "Interested",
            "answered": "Contacted",
            "voicemail": "Contacted",
            "rejected": "Do Not Contact",
            "no_answer": lead_name,  # keep current
        }
        new_status = status_map.get(outcome)
        if new_status and new_status != lead_name:
            frappe.db.set_value("CRM Lead", lead_name, "status", new_status)

        frappe.db.commit()
        return {"status": "logged", "communication": comm.name, "note": note.name}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE PILLAR
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_communication_history(lead_name: str, limit: int = 20):
    """All Communication records for a lead (emails + calls + notes).

    Args:
        lead_name: CRM Lead ID.
        limit: Max records to return.
    """
    comms = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "CRM Lead",
            "reference_name": lead_name,
        },
        fields=[
            "name", "subject", "content", "communication_medium",
            "sent_or_received", "creation", "sender", "recipients",
        ],
        order_by="creation desc",
        limit=limit,
    )
    return comms


@mcp.tool()
def update_lead_score(lead_name: str, score: int, reasoning: str = ""):
    """Update a lead's score and optionally log reasoning.

    Args:
        lead_name: CRM Lead ID.
        score: Numeric score (0-100).
        reasoning: Optional reasoning for the score.
    """
    frappe.db.set_value("CRM Lead", lead_name, "lead_score", score)

    if reasoning:
        intel = {}
        lead = frappe.get_doc("CRM Lead", lead_name)
        if lead.additional_data:
            intel = json.loads(lead.additional_data)
        intel["score_reasoning"] = reasoning
        intel["score_updated"] = str(frappe.utils.now())
        lead.additional_data = json.dumps(intel)
        lead.save(ignore_permissions=True)

    frappe.db.commit()
    return f"Score updated to {score} for {lead_name}"


@mcp.tool()
def create_note(lead_name: str, title: str, content: str):
    """Create an FCRM Note on a lead — appears in the lead timeline.

    Args:
        lead_name: CRM Lead ID.
        title: Note title.
        content: Note body (markdown supported).
    """
    try:
        note = frappe.get_doc({
            "doctype": "FCRM Note",
            "title": title,
            "content": content,
            "reference_doctype": "CRM Lead",
            "reference_docname": lead_name,
        })
        note.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "note": note.name, "lead": lead_name}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@mcp.tool()
def get_lead_status_snapshot(lead_name: str):
    """Get a compact real-time status snapshot: CRM status, emails sent, calls made, sequence step.

    Args:
        lead_name: CRM Lead ID (e.g. CRM-LEAD-00001).
    """
    try:
        lead = frappe.get_doc("CRM Lead", lead_name)
        data = {
            "lead_name": lead.name,
            "full_name": lead.lead_name,
            "status": lead.status,
            "email": lead.email,
            "organization": lead.organization,
            "job_title": lead.job_title,
            "sequence_step": getattr(lead, "custom_sequence_step", 0),
            "zeta_score": getattr(lead, "custom_zeta_score", None),
            "modified": str(lead.modified),
        }

        # Recent communications
        comms = frappe.get_all(
            "Communication",
            filters={
                "reference_doctype": "CRM Lead",
                "reference_name": lead_name,
            },
            fields=["subject", "communication_date", "sent_or_received"],
            order_by="communication_date desc",
            limit=5,
        )
        data["recent_communications"] = comms

        # Recent notes
        notes = frappe.get_all(
            "FCRM Note",
            filters={
                "reference_doctype": "CRM Lead",
                "reference_docname": lead_name,
            },
            fields=["title", "creation"],
            order_by="creation desc",
            limit=3,
        )
        data["recent_notes"] = [n.title for n in notes]

        return data
    except frappe.DoesNotExistError:
        return {"error": f"Lead {lead_name} not found"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def classify_and_route_reply(from_email: str, subject: str, body: str):
    """Classify an inbound email reply using LLM intelligence and update CRM Lead.

    Classification buckets (LLM-powered):
    INTERESTED, NOT_INTERESTED, OBJECTION, WARM_HANDOFF,
    UNSUBSCRIBE, OOO, QUESTION, UNKNOWN.

    The LLM sees the original email we sent + lead dossier for context-aware classification.
    Falls back to keyword matching if LLM/EAIA is unavailable.

    Args:
        from_email: Sender email address.
        subject: Email subject line.
        body: Email body text.
    """
    import requests as req

    eaia_url = os.environ.get("EAIA_URL", "http://localhost:8001")

    # 1. Try LLM classification via EAIA
    classification = "UNKNOWN"
    confidence = 0.0
    sentiment = "neutral"
    reasoning = ""
    handoff_name = ""
    objection_type = ""

    try:
        resp = req.post(
            f"{eaia_url}/inbound/process-reply",
            json={
                "from_email": from_email,
                "subject": subject,
                "body": body,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            classification = data.get("classification", "UNKNOWN")
            confidence = data.get("confidence", 0.0)
            sentiment = data.get("sentiment", "neutral")
            details = data.get("details", {})
            reasoning = details.get("reasoning", "")
            handoff_name = details.get("handoff_name", "")
            objection_type = details.get("objection_type", "")
            # EAIA already handled CRM updates — return result
            return {
                "classification": classification,
                "confidence": confidence,
                "sentiment": sentiment,
                "reasoning": reasoning,
                "lead_name": data.get("crm_lead_id", ""),
                "action_taken": data.get("action_taken", ""),
                "source": "llm",
            }
    except Exception as e:
        frappe.logger().warning(f"EAIA LLM classification failed, falling back to keywords: {e}")

    # 2. Keyword fallback (same as before, but with new categories)
    full_text = f"{subject} {body}".lower()

    ooo_kw = ["out of office", "automatic reply", "vacation", "on leave", "limited access"]
    unsub_kw = ["unsubscribe", "remove list", "stop emailing", "cease"]
    not_int_kw = ["not interested", "no thanks", "pass", "spam"]
    handoff_kw = ["talk to", "cc'd", "colleague", "reach out to", "handles this"]
    obj_kw = ["we use", "already have", "not a priority", "budget", "not right now"]
    int_kw = ["interested", "meet", "meeting", "call", "schedule", "calendar",
              "talk", "chat", "available", "sounds good", "send more info"]
    q_kw = ["how does", "what is", "pricing", "can you explain", "more info", "how much"]

    for w in ooo_kw:
        if w in full_text:
            classification = "OOO"
            break
    if classification == "UNKNOWN":
        for w in unsub_kw:
            if w in full_text:
                classification = "UNSUBSCRIBE"
                break
    if classification == "UNKNOWN":
        for w in not_int_kw:
            if w in full_text:
                classification = "NOT_INTERESTED"
                break
    if classification == "UNKNOWN":
        for w in handoff_kw:
            if w in full_text:
                classification = "WARM_HANDOFF"
                break
    if classification == "UNKNOWN":
        for w in obj_kw:
            if w in full_text:
                classification = "OBJECTION"
                break
    if classification == "UNKNOWN":
        for w in q_kw:
            if w in full_text:
                classification = "QUESTION"
                break
    if classification == "UNKNOWN":
        for w in int_kw:
            if w in full_text:
                classification = "INTERESTED"
                break

    # 3. Find CRM Lead by email
    leads = frappe.get_all("CRM Lead", filters={"email": from_email}, limit=1)
    if not leads:
        return {
            "classification": classification,
            "action": "no_crm_lead_found",
            "email": from_email,
            "source": "keyword_fallback",
        }

    lead_name = leads[0].name

    # 4. Route
    status_map = {
        "INTERESTED": "Interested",
        "NOT_INTERESTED": "Lost",
        "UNSUBSCRIBE": "Do Not Contact",
    }

    if classification in status_map:
        lead = frappe.get_doc("CRM Lead", lead_name)
        lead.status = status_map[classification]
        lead.save(ignore_permissions=True)

    # Pause sequence for most reply types
    pause_types = {"INTERESTED", "NOT_INTERESTED", "UNSUBSCRIBE", "OOO", "WARM_HANDOFF"}
    if classification in pause_types:
        try:
            lead = frappe.get_doc("CRM Lead", lead_name)
            if hasattr(lead, "custom_sequence_paused"):
                lead.custom_sequence_paused = 1
                lead.save(ignore_permissions=True)
        except Exception:
            pass

    # Log note with classification details
    emoji_map = {
        "INTERESTED": "📨", "NOT_INTERESTED": "❌", "OBJECTION": "🔄",
        "WARM_HANDOFF": "🤝", "UNSUBSCRIBE": "🛑", "OOO": "🏖️",
        "QUESTION": "❓", "UNKNOWN": "⚠️",
    }
    try:
        note = frappe.get_doc({
            "doctype": "FCRM Note",
            "title": f"{emoji_map.get(classification, '📨')} Reply: {classification} — {subject[:50]}",
            "content": (
                f"**From:** {from_email}\n"
                f"**Classification:** {classification} (keyword fallback)\n\n"
                f"{body[:500]}"
            ),
            "reference_doctype": "CRM Lead",
            "reference_docname": lead_name,
        })
        note.insert(ignore_permissions=True)
    except Exception:
        pass

    frappe.db.commit()
    return {
        "classification": classification,
        "lead_name": lead_name,
        "action_taken": status_map.get(classification, "logged"),
        "source": "keyword_fallback",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: ANALYTICS + OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_pipeline_analytics() -> str:
    """Fetch pipeline health, funnel metrics, and framework A/B stats."""
    try:
        # Funnel / Status counts
        status_counts = frappe.db.sql("""
            SELECT status, count(*) as count
            FROM `tabCRM Lead` 
            GROUP BY status
        """, as_dict=True)
        
        funnel = {row['status'] or "Unknown": row['count'] for row in status_counts}
        
        # Load JSON from additional_data to calculate A/B metrics and coverage
        leads = frappe.get_all("CRM Lead", fields=["name", "additional_data"])
        frameworks = {"challenger": 0, "pas": 0, "aida": 0, "unknown": 0}
        total_enriched = 0
        total_entangled = 0
        total_vulture = 0
        
        for l in leads:
            if not l.additional_data:
                continue
            try:
                data = json.loads(l.additional_data)
                
                # Enriched coverage
                if "score" in data or "signals" in data:
                    total_enriched += 1
                
                # Framework testing
                fw = data.get("framework") or data.get("sequence_framework")
                if fw:
                    fw = fw.lower()
                    if fw in frameworks:
                        frameworks[fw] += 1
                    else:
                        frameworks["unknown"] += 1
                        
                # Phase 9 stats
                if data.get("entangled"):
                    total_entangled += 1
                if data.get("vulture_event_detected"):
                    total_vulture += 1
            except Exception:
                pass
                
        metrics = {
            "total_leads": len(leads),
            "total_enriched": total_enriched,
            "enrichment_coverage": round((total_enriched / len(leads) * 100), 1) if leads else 0,
            "total_entangled": total_entangled,
            "total_vulture_events": total_vulture,
        }
        
        return json.dumps({
            "funnel": funnel,
            "frameworks": frameworks,
            "metrics": metrics
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: ZETA PROTOCOLS (ENTANGLEMENT & VULTURE)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_portfolio_links(organization: str, email_domain: str = None) -> str:
    """
    Find other CRM Leads connected to the same organization or email domain.
    Used by the Entanglement Protocol to find "portfolio links" for multi-threading.
    """
    try:
        conditions = []
        if organization:
            conditions.append(["organization", "like", f"%{organization}%"])
        if email_domain:
            conditions.append(["email", "like", f"%@{email_domain}"])
            
        if not conditions:
            return json.dumps({"error": "Must provide organization or email_domain"})
            
        # If both are provided, we want OR logic. Frappe's get_all uses AND for list of lists.
        # So we'll run two queries and merge if both are provided.
        leads = []
        
        if organization:
            org_leads = frappe.get_all(
                "CRM Lead",
                filters={"organization": ["like", f"%{organization}%"]},
                fields=["name", "lead_name", "organization", "job_title", "email", "status"]
            )
            leads.extend(org_leads)
            
        if email_domain:
            domain_leads = frappe.get_all(
                "CRM Lead",
                filters={"email": ["like", f"%@{email_domain}"]},
                fields=["name", "lead_name", "organization", "job_title", "email", "status"]
            )
            leads.extend(domain_leads)
            
        # Deduplicate
        seen = set()
        unique_leads = []
        for l in leads:
            if l.name not in seen:
                seen.add(l.name)
                unique_leads.append(l)

        if not unique_leads:
            return json.dumps({"message": "No portfolio links found", "leads": []})

        return json.dumps({
            "message": f"Found {len(unique_leads)} connected leads",
            "leads": unique_leads
        })

    except Exception as e:
        frappe.log_error("MCP Tool Error: get_portfolio_links", str(e))
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE PILLAR — agent-facing outbound calling (grounded + logged + governed)
# All three delegate to crm.api.vapi so agents place calls the SAME way the UI
# does: dossier/KB grounding, Vapi Call Log + CRM Call Log, and the per-lead call
# governor are all inherited. Agents never build a raw Vapi payload.
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_call_queue(limit: int = 25, tier: str = None, min_score: float = None):
    """Return the prioritised who-to-call list (leads with a phone, not converted,
    passing the call governor; ordered by lead_score/tier).

    Args:
        limit: Max leads to return.
        tier: Optional tier filter (e.g. Tier1).
        min_score: Optional minimum lead_score.
    """
    from crm.api.vapi import get_call_queue as _q

    return _q(limit=limit, tier=tier, min_score=min_score)


@mcp.tool()
def place_call(phone_number: str, lead_name: str = None, objective: str = None):
    """Place an outbound AI voice call to a lead. Grounded in the lead's CRM
    dossier / knowledge base; if no verified background exists the assistant is
    constrained to avoid inventing facts. The call is logged automatically.

    Args:
        phone_number: Number to dial (E.164, e.g. +14155551234).
        lead_name: CRM Lead ID for grounding + tracking (strongly recommended).
        objective: Goal of the call (e.g. "Confirm interest in STC-1010").
    """
    from crm.api.vapi import initiate_outbound_call

    return initiate_outbound_call(
        to_number=phone_number, lead_name=lead_name, objective=objective
    )


@mcp.tool()
def run_call_campaign(limit: int = 5, tier: str = None, min_score: float = None,
                      objective: str = None, dry_run: int = 1):
    """Dial the top N leads from the call queue (governor + grounding inherited).
    Defaults to dry_run=1 (preview only) so the agent must opt in to real dialing.

    Args:
        limit: How many leads to dial.
        tier: Optional tier filter.
        min_score: Optional minimum lead_score.
        objective: Call objective applied to the batch.
        dry_run: 1 = preview who would be called; 0 = actually place calls.
    """
    from crm.api.vapi import run_call_campaign as _run

    return _run(limit=limit, tier=tier, min_score=min_score, topic=objective, dry_run=dry_run)


# ═══════════════════════════════════════════════════════════════════════════════
# MCP ENDPOINT — exposes all tools above
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.register()
def handle_mcp():
    """
    MCP Entry Point.
    URL: /api/method/crm.api.mcp_server.handle_mcp
    """
    pass

# ═══════════════════════════════════════════════════════════════════════════════
# §7.2 ORCHESTRATION TOOLS (delegate to sequence_engine — the W1 contract)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def generate_engagement_plan(subject_type: str = "Lead", subject_key: str = "", option: str = "A"):
    """Generate a multi-touch engagement plan for a lead/prospect (no seeding).

    Args:
        subject_type: "Lead" or "Prospect".
        subject_key: The lead/prospect key.
        option: Plan option label.
    """
    from crm.api import plan_generator as pg
    return pg.generate_plan(subject_type=subject_type, subject_key=subject_key, option=option)


@mcp.tool()
def seed_engagement_plan(subject_type: str = "Lead", subject_key: str = "", option: str = "A", use_enrich: int = 0):
    """Generate AND seed an engagement plan (creates OS + OSI + Tasks + draft Comms).

    Args:
        subject_type: "Lead" or "Prospect".
        subject_key: The lead/prospect key.
        option: Plan option label.
        use_enrich: Whether to enrich before seeding.
    """
    from crm.api import plan_generator as pg
    return pg.generate_and_seed_plan(subject_type=subject_type, subject_key=subject_key,
                                     option=option, use_enrich=use_enrich)


@mcp.tool()
def arm_sequence(sequence_name: str):
    """Arm a Draft Outreach Sequence: Draft->Active and rebuild step due_dates.

    Args:
        sequence_name: Outreach Sequence name.
    """
    from crm.api.sequence_engine import arm_sequence as _arm
    return _arm(sequence_name)


@mcp.tool()
def get_today_worklist(user: str = "", channel: str = "", limit: int = 50):
    """The 360 aggregator: due email/call/whatsapp, needs_approval, blocked, waiting.

    Args:
        user: Optional assignee filter.
        channel: Optional channel filter (Email/Call/WhatsApp/LinkedIn).
        limit: Max items per bucket.
    """
    from crm.api.sequence_engine import get_today_worklist as _wl
    return _wl(user=user or None, channel=channel or None, limit=limit)


@mcp.tool()
def human_approval_queue(user: str = "", limit: int = 50):
    """Draft Communications awaiting human approval (delivery_status empty).

    Args:
        user: Optional owner filter.
        limit: Max items.
    """
    from crm.api.sequence_engine import get_today_worklist as _wl
    wl = _wl(user=user or None, limit=limit)
    return {"ok": True, "needs_approval": wl.get("needs_approval", []),
            "count": len(wl.get("needs_approval", []))}


@mcp.tool()
def advance_sequence_step(instance_name: str = "", task_name: str = "", communication_name: str = ""):
    """Advance a sequence instance one step (human-gated, engine-verified).

    Args:
        instance_name: Outreach Sequence Instance name.
        task_name: CRM Task name for the step.
        communication_name: Communication name for the step.
    """
    from crm.api.sequence_engine import advance_sequence_instance as _adv
    return _adv(instance_name=instance_name or None, task_name=task_name or None,
                communication_name=communication_name or None)


@mcp.tool()
def mark_step_complete(task_name: str, outcome: str = ""):
    """Human marks a step's task done; routes to advance if the channel completed.

    Args:
        task_name: CRM Task name.
        outcome: Optional outcome label (e.g. "sent", "completed", "no-answer").
    """
    from crm.api.sequence_engine import mark_step_complete as _msc
    return _msc(task_name, outcome=outcome or None)


@mcp.tool()
def execute_call_step(task_name: str, call_outcome: str = "", instance_name: str = ""):
    """Advance a Call step after a completed Vapi Call Log (never places a call).

    Args:
        task_name: CRM Task name for the call step.
        call_outcome: Optional explicit human outcome.
        instance_name: Optional Outreach Sequence Instance name.
    """
    from crm.api.sequence_engine import advance_call_step as _acs
    return _acs(task_name=task_name, call_outcome=call_outcome or None,
                instance_name=instance_name or None)


@mcp.tool()
def draft_whatsapp_message(instance_name: str = "", task_name: str = "", body: str = ""):
    """Draft a WhatsApp message for a sequence step (gated on WA enabled + phone).

    Args:
        instance_name: Outreach Sequence Instance name.
        task_name: CRM Task name for the WhatsApp step.
        body: Optional message body override.
    """
    from crm.api.whatsapp import draft_sequence_whatsapp as _wa
    return _wa(task_name=task_name, instance_name=instance_name or None, body=body or None)


@mcp.tool()
def assert_communication_deliverable(communication_name: str):
    """Check a Communication's recipients are deliverable (raises on placeholder).

    Args:
        communication_name: The Communication to check.
    """
    from crm.api.email import assert_deliverable
    comm = frappe.get_doc("Communication", communication_name)
    recipients = [r.strip() for r in (comm.recipients or "").split(",") if r.strip()]
    cc = [r.strip() for r in (comm.cc or "").split(",") if r.strip()]
    bcc = [r.strip() for r in (comm.bcc or "").split(",") if r.strip()]
    assert_deliverable(recipients, cc, bcc)
    return {"ok": True, "communication": communication_name, "deliverable": True}


@mcp.tool()
def get_sequence_360(instance_name: str):
    """Full 360 state for one sequence instance (engine read-only).

    Args:
        instance_name: Outreach Sequence Instance name.
    """
    from crm.api.sequence_engine import get_sequence_state as _gs
    return _gs(instance_name)
