"""Content Engine — generate outreach content from a lead's REAL intel.

Delegates to `notebooklm_engine` (real NotebookLM / Gemini Notebook backends).
There is NO local synthesis fallback: if no live backend has its credential,
`generate_content` throws with the exact unblock instructions rather than
faking a deck with python-pptx or espeak. Artifacts are saved as a Frappe File
attached to the lead; `attach_to_email` only ever attaches to a DRAFT
Communication (never sends).
"""

from __future__ import annotations

import os

import frappe
from frappe import _

FUNNEL_STAGES = ["first_touch", "follow_up", "deep_dive", "proposal"]
CONTENT_KINDS = {"slides": "slides", "audio": "audio", "video": "video"}


def _lead(lead):
    if not frappe.db.exists("CRM Lead", lead):
        frappe.throw(_("Lead not found: {0}").format(lead))
    return frappe.get_doc("CRM Lead", lead)


def _brief(doc, lead, funnel_stage, point_of_discussion, crispro_value):
    """Grounded content brief from the lead's real intel (engine schema)."""
    name = " ".join(filter(None, [doc.get("first_name"), doc.get("last_name")])) or "there"
    stage = funnel_stage if funnel_stage in FUNNEL_STAGES else "first_touch"
    return {
        "slug": str(lead).replace("/", "_"),
        "contact": name,
        "company": doc.get("organization") or "",
        "title": doc.get("job_title") or doc.get("designation") or "",
        "topic": point_of_discussion or doc.get("aacr_topic") or "",
        "current_focus": doc.get("current_focus") or "",
        "pain_points": doc.get("pain_points") or "",
        "crispro_fit": crispro_value or doc.get("crispro_fit") or "",
        "fit_rationale": doc.get("fit_rationale") or "",
        "funnel_stage": stage,
        "point_of_discussion": point_of_discussion or "",
        "crispro_value": crispro_value or "",
    }


def _save_file(lead, path, label):
    """Register a real artifact as a Frappe File attached to the lead."""
    fname = os.path.basename(path)
    size = os.path.getsize(path) if os.path.exists(path) else 0
    fdoc = frappe.get_doc({
        "doctype": "File", "file_name": fname,
        "file_url": f"/private/files/{fname}", "file_size": size,
        "attached_to_doctype": "CRM Lead", "attached_to_name": lead,
        "is_private": 1, "content_label": label,
    })
    fdoc.insert()
    return fdoc.name


@frappe.whitelist()
def content_providers():
    """Which NotebookLM backends are live in this environment, and what's missing."""
    from crm.api import notebooklm_engine as nblm
    return {"ok": True, "providers": nblm.available_providers()}


@frappe.whitelist()
def generate_content(lead: str, content_type: str = "slides",
                     funnel_stage: str = "first_touch",
                     point_of_discussion: str = "", crispro_value: str = "",
                     provider: str = "auto"):
    """Generate real content through a NotebookLM backend, grounded in lead intel.

    No fallback: raises (frappe.throw) with the exact credential unblock if no
    live backend is available for the requested content_type.
    """
    from crm.api import notebooklm_engine as nblm

    doc = _lead(lead)
    kind = CONTENT_KINDS.get(content_type)
    if not kind:
        frappe.throw(_("Unknown content_type: {0}").format(content_type))
    brief = _brief(doc, lead, funnel_stage, point_of_discussion, crispro_value)
    out_dir = "/tmp/crm_content"

    try:
        result = nblm.generate(kind, brief, provider=provider, out_dir=out_dir)
    except nblm.NotebookLMCredentialError as e:
        # Fail loud with the precise unblock — never a faked artifact.
        frappe.throw(_("NotebookLM not configured: {0}").format(str(e)))
    except nblm.NotebookLMUnsupportedKind as e:
        frappe.throw(str(e))
    except nblm.NotebookLMError as e:
        frappe.throw(_("Content generation failed: {0}").format(str(e)))

    file_name = None
    if result.get("path"):
        file_name = _save_file(lead, result["path"], "{}:{}".format(result["provider"], kind))

    return {
        "ok": True, "lead": lead, "content_type": content_type,
        "provider": result.get("provider"), "grounded": result.get("meta", {}).get("grounded", True),
        "produced": [{"type": kind, "path": result.get("path"), "file": file_name,
                      "meta": result.get("meta", {}), "notebook_id": result.get("notebook_id")}],
    }


@frappe.whitelist()
def list_content(lead: str):
    _lead(lead)
    files = frappe.get_all(
        "File", filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead},
        fields=["name", "file_name", "file_url", "file_size", "content_label", "creation"],
        order_by="creation desc", limit=100)
    return {"ok": True, "lead": lead, "count": len(files), "files": files}


@frappe.whitelist()
def attach_to_email(lead: str, file_name: str, communication: str = ""):
    """Attach a generated file to a DRAFT Communication (never sends)."""
    _lead(lead)
    if not frappe.db.exists("File", file_name):
        frappe.throw(_("File not found: {0}").format(file_name))
    if communication:
        comm = frappe.get_doc("Communication", communication)
        if comm.get("delivery_status"):
            frappe.throw(_("Can only attach to a draft (unsent) Communication."))
    fdoc = frappe.get_doc("File", file_name)
    fdoc.set("attached_to_doctype", "Communication" if communication else "CRM Lead")
    fdoc.set("attached_to_name", communication or lead)
    fdoc.save()
    return {"ok": True, "file": file_name, "attached_to": communication or lead,
            "sent": False}
