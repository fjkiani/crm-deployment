"""Outreach helpers — per-step draft bodies + next-step preview for the Outreach tab.

Additive to lead_tabs._outreach. Real data, no caching.
"""

from __future__ import annotations

import frappe
from frappe import _


def _merge(template: str, doc) -> str:
    """Fill merge fields from the lead's real data."""
    if not template:
        return ""
    out = template
    fields = {
        "first_name": doc.get("first_name") or "",
        "last_name": doc.get("last_name") or "",
        "name": " ".join(filter(None, [doc.get("first_name"), doc.get("last_name")])),
        "organization": doc.get("organization") or "",
        "institution": doc.get("organization") or "",
        "aacr_topic": doc.get("aacr_topic") or "",
        "current_focus": doc.get("current_focus") or "",
        "pain_points": doc.get("pain_points") or "",
        "crispro_fit": doc.get("crispro_fit") or "",
        "tier": doc.get("tier") or "",
    }
    for k, v in fields.items():
        out = out.replace("{" + k + "}", str(v))
    return out


@frappe.whitelist()
def next_step_preview(lead: str, instance_name: str):
    """Preview the next sequence step's email with merge fields filled (a draft)."""
    if not frappe.db.exists("CRM Lead", lead):
        frappe.throw(_("Lead not found"))
    doc = frappe.get_doc("CRM Lead", lead)
    inst = frappe.get_doc("Outreach Sequence Instance", instance_name)
    seq = frappe.get_doc("Outreach Sequence", inst.get("outreach_sequence"))
    subject = _merge(seq.get("subject_template"), doc)
    body = _merge(seq.get("body_template"), doc)
    return {
        "ok": True, "instance": instance_name,
        "current_step": inst.get("current_step"), "total_steps": inst.get("total_steps"),
        "subject": subject, "body": body, "recipients": doc.get("email") or "",
        "is_draft": True,
    }


@frappe.whitelist()
def draft_step_email(lead: str, instance_name: str):
    """Create the next step's DRAFT email (Communication, delivery_status empty)."""
    prev = next_step_preview(lead, instance_name)
    comm = frappe.get_doc({
        "doctype": "Communication", "communication_type": "Communication",
        "sent_or_received": "Sent", "delivery_status": "",
        "reference_doctype": "CRM Lead", "reference_name": lead,
        "recipients": prev["recipients"], "subject": prev["subject"],
        "content": prev["body"], "status": "Linked",
    })
    comm.insert()
    return {"ok": True, "draft": comm.name, "subject": prev["subject"],
            "sent": False}
