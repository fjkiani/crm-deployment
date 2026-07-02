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
        fields=["name", "lead_name", "organization", "email_id", "status", "lead_score"],
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
        "email": lead.email_id,
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
        fields=["name", "lead_name", "organization", "email_id", "status", "lead_score", "source"],
        order_by="lead_score desc",
        limit=limit,
    )
    return leads


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
    """For each lead in active sequences: current step, days elapsed, next fire date.

    Args:
        lead_name: Optional — filter to one lead. Empty = all active.
    """
    filters = {"status": "Active"}
    if lead_name:
        # Look for the lead's sequence membership via additional_data
        lead = frappe.get_doc("CRM Lead", lead_name)
        intel = json.loads(lead.additional_data) if lead.additional_data else {}
        seq_data = intel.get("sequence", {})
        return {
            "lead": lead_name,
            "sequence": seq_data,
            "lead_status": lead.status,
        }

    # Return all Outreach Sequences that are active
    sequences = frappe.get_all(
        "Outreach Sequence",
        filters=filters,
        fields=["name", "sequence_name", "channel", "status", "max_daily_sends"],
    )
    return sequences


@mcp.tool()
def fire_sequence_step(lead_name: str, step_index: int = -1, dry_run: bool = True):
    """Fire the next sequence step for one lead. Reads sequence config from DocType.

    Args:
        lead_name: CRM Lead ID.
        step_index: Which step to fire (-1 = auto-detect next).
        dry_run: If True, returns what WOULD happen without sending.
    """
    lead = frappe.get_doc("CRM Lead", lead_name)
    intel = json.loads(lead.additional_data) if lead.additional_data else {}
    seq_data = intel.get("sequence", {})

    current_step = seq_data.get("current_step", 0)
    if step_index >= 0:
        current_step = step_index

    # Default sequence schedule (will be replaced by DocType config)
    steps = [
        {"day": 0, "framework": "challenger", "label": "Day 0 — Initial Strike"},
        {"day": 3, "framework": "challenger", "label": "Day 3 — A/B Subject Pivot"},
        {"day": 7, "framework": "pas", "label": "Day 7 — Framework Switch (PAS)"},
        {"day": 14, "framework": "aida", "label": "Day 14 — Framework Switch (AIDA)"},
        {"day": 21, "framework": "breakup", "label": "Day 21 — Breakup"},
    ]

    if current_step >= len(steps):
        return {"status": "completed", "message": f"All {len(steps)} steps exhausted for {lead_name}"}

    step = steps[current_step]

    if dry_run:
        return {
            "status": "dry_run",
            "lead": lead_name,
            "step": step,
            "next_step_index": current_step,
            "message": f"Would fire: {step['label']} using {step['framework']} framework",
        }

    # Update sequence state in lead's additional_data
    seq_data["current_step"] = current_step + 1
    seq_data["last_fired"] = str(frappe.utils.now())
    seq_data["last_framework"] = step["framework"]
    intel["sequence"] = seq_data
    lead.additional_data = json.dumps(intel)
    lead.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "fired",
        "lead": lead_name,
        "step": step,
        "next_step_index": current_step + 1,
    }


@mcp.tool()
def pause_sequence(lead_name: str):
    """Pause the outreach sequence for a lead.

    Args:
        lead_name: CRM Lead ID.
    """
    lead = frappe.get_doc("CRM Lead", lead_name)
    intel = json.loads(lead.additional_data) if lead.additional_data else {}
    seq_data = intel.get("sequence", {})
    seq_data["paused"] = True
    seq_data["paused_at"] = str(frappe.utils.now())
    intel["sequence"] = seq_data
    lead.additional_data = json.dumps(intel)
    lead.save(ignore_permissions=True)
    frappe.db.commit()
    return f"Sequence paused for {lead_name}"


@mcp.tool()
def approve_and_send(
    lead_name: str,
    to_email: str,
    subject: str,
    body: str,
    sender: str = "",
):
    """Approve a draft email and log it as Communication on the CRM Lead.
    Actual SMTP send happens from the EAIA side — this records the send in CRM.

    Args:
        lead_name: CRM Lead ID.
        to_email: Recipient email.
        subject: Email subject.
        body: Email body text.
        sender: Sender email (optional, defaults to system).
    """
    try:
        comm = frappe.get_doc({
            "doctype": "Communication",
            "communication_type": "Communication",
            "communication_medium": "Email",
            "subject": subject,
            "content": body,
            "sender": sender or frappe.session.user,
            "recipients": to_email,
            "reference_doctype": "CRM Lead",
            "reference_name": lead_name,
            "sent_or_received": "Sent",
            "status": "Linked",
        })
        comm.insert(ignore_permissions=True)

        # Update lead status
        frappe.db.set_value("CRM Lead", lead_name, "status", "Contacted")
        frappe.db.commit()

        return {
            "status": "sent",
            "communication": comm.name,
            "lead": lead_name,
            "to": to_email,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@mcp.tool()
def create_outreach_sequence(
    sequence_name: str,
    channel: str = "Email",
    description: str = "",
    max_daily_sends: int = 50,
):
    """Create a new Outreach Sequence in CRM.

    Args:
        sequence_name: Name for the sequence.
        channel: Channel type (Email, Call, LinkedIn, Multi-Channel).
        description: Optional description.
        max_daily_sends: Daily send cap.
    """
    try:
        doc = frappe.get_doc({
            "doctype": "Outreach Sequence",
            "sequence_name": sequence_name,
            "channel": channel,
            "description": description,
            "status": "Draft",
            "max_daily_sends": max_daily_sends,
            "owner": frappe.session.user,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "name": doc.name, "sequence_name": sequence_name}
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
# MCP ENDPOINT — exposes all tools above
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.register()
def handle_mcp():
    """
    MCP Entry Point.
    URL: /api/method/crm.api.mcp_server.handle_mcp
    """
    pass
