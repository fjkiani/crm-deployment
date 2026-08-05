"""Call Orchestration — grounded call prep + post-call next steps.

prepare_call builds a script/intent from the lead's REAL intel (no hardcoded
script). post_call_next_steps produces DRAFTS (invite + follow-up email) and a
sequence advance — every send stays human-gated. Nothing auto-calls a real KOL.
"""

from __future__ import annotations

import frappe
from frappe import _


def _lead(lead):
    if not frappe.db.exists("CRM Lead", lead):
        frappe.throw(_("Lead not found: {0}").format(lead))
    return frappe.get_doc("CRM Lead", lead)


def _grounding(lead, query):
    """Pull grounded context if the intelligence layer is available."""
    try:
        from crm.api import intelligence
        ctx = intelligence.get_grounding_context(lead, query, 5)
        if isinstance(ctx, dict):
            return ctx.get("context") or ctx.get("text") or ""
        return str(ctx or "")
    except Exception:
        return ""


@frappe.whitelist()
def prepare_call(lead: str):
    """Build a grounded call script + intent + talking points from real intel."""
    doc = _lead(lead)
    name = " ".join(filter(None, [doc.get("first_name"), doc.get("last_name")])) or "there"
    topic = doc.get("aacr_topic") or ""
    focus = doc.get("current_focus") or ""
    pains = doc.get("pain_points") or ""
    fit = doc.get("crispro_fit") or ""
    rationale = doc.get("fit_rationale") or ""
    grounding = _grounding(lead, f"call prep for {name}: {topic}")

    intent = (
        f"Open a scientific dialogue with {name} ({doc.get('organization') or 'their institution'}) "
        f"around {topic or 'their research'}, and qualify interest in an STC-1010 collaboration."
    )
    opener = (
        f"Dr. {doc.get('last_name') or name}, I follow your work on "
        f"{focus or topic or 'MSS colorectal cancer'}. "
        f"The challenge you describe — {pains or 'immune exclusion in MSS CRC'} — "
        f"is exactly what STC-1010 is built to address."
    )
    talking_points = []
    if pains:
        talking_points.append(f"Acknowledge the pain point: {pains}")
    if fit:
        talking_points.append(f"Position the fit: {fit}")
    if rationale:
        talking_points.append(f"Anchor the rationale: {rationale}")
    if grounding:
        talking_points.append(f"Grounded intel: {grounding[:200]}")
    objections = [
        {"objection": "MSS CRC has failed immunotherapy before",
         "response": "STC-1010's haptenation drives epitope spreading to prime de novo T-cell responses, unlike prior single-antigen attempts."},
        {"objection": "No bandwidth for another trial",
         "response": "BreAK CRC-001 runs on a standard mFOLFOX6 backbone, minimizing incremental site burden."},
    ]
    return {
        "ok": True, "lead": lead, "contact": name,
        "organization": doc.get("organization") or "",
        "phone": doc.get("phone") or "",
        "intent": intent, "opener": opener,
        "talking_points": talking_points, "objections": objections,
        "grounded": bool(grounding or pains or fit),
        "can_call": bool(doc.get("phone")),
    }


@frappe.whitelist()
def initiate_call(lead: str, confirm: int = 0):
    """Human-confirmed outbound call. confirm=1 is the explicit human gate."""
    if not int(confirm):
        return {"ok": False, "reason": "confirmation_required",
                "message": "Pass confirm=1 to place the call. Calls are human-gated."}
    doc = _lead(lead)
    if not doc.get("phone"):
        frappe.throw(_("No phone number on lead {0}.").format(lead))
    try:
        from crm.api import vapi
        return vapi.initiate_outbound_call(lead_name=lead)
    except Exception as e:
        return {"ok": False, "reason": "vapi_unavailable", "message": str(e)}


@frappe.whitelist()
def post_call_next_steps(lead: str, outcome: str = "connected", summary: str = "",
                         next_step_days: int = 3):
    """Produce DRAFT next steps after a call: calendar invite + follow-up email.

    Both are drafts (human-approved before send). Also advances the sequence.
    """
    doc = _lead(lead)
    name = " ".join(filter(None, [doc.get("first_name"), doc.get("last_name")])) or "there"
    follow_date = frappe.add_days(frappe.nowdate(), int(next_step_days or 3))

    # Draft calendar invite (as a CRM Task of type meeting — a draft, not sent).
    invite = frappe.get_doc({
        "doctype": "CRM Task",
        "title": f"Follow-up call with {name} ({doc.get('organization') or ''})",
        "status": "Todo", "due_date": follow_date,
        "reference_doctype": "CRM Lead", "reference_docname": lead, "lead": lead,
        "description": f"Draft invite. Outcome: {outcome}. {summary}",
    })
    invite.insert()

    # Draft follow-up email (Communication, delivery_status empty = draft).
    body = (f"Dr. {doc.get('last_name') or name}, thank you for the conversation about "
            f"{doc.get('aacr_topic') or 'your research'}. As discussed, "
            f"{doc.get('crispro_fit') or 'STC-1010'} — I'd like to schedule a follow-up.")
    email = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "sent_or_received": "Sent", "delivery_status": "",
        "reference_doctype": "CRM Lead", "reference_name": lead,
        "recipients": doc.get("email") or "",
        "subject": f"Following up — STC-1010 and {doc.get('aacr_topic') or 'your work'}",
        "content": body, "status": "Linked",
    })
    email.insert()

    # Advance the sequence (call step outcome).
    advanced = {"ok": False, "reason": "no_active_sequence"}
    try:
        from crm.api import sequence_engine as se
        instances = frappe.get_all(
            "Outreach Sequence Instance",
            filters={"prospect": doc.get("prospect_ref")}, pluck="name", limit=1)
        if instances:
            advanced = se.on_channel_event(
                instance_name=instances[0], task_name=None, channel="call",
                outcome=outcome, communication_name=email.name)
    except Exception as e:
        advanced = {"ok": False, "reason": "sequence_advance_failed", "message": str(e)}

    return {
        "ok": True, "lead": lead,
        "draft_invite": invite.name, "draft_email": email.name,
        "follow_up_date": follow_date, "sequence_advance": advanced,
        "sent": False, "note": "Both next steps are drafts; human approves before send.",
    }
