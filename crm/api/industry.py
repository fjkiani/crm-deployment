"""
Industry Engagements API.

Maps the CrisPRO industry outreach strategies (10 pharma/biotech engagements)
onto the CRM's dormant multi-step outreach engine, and materializes each
strategy into a sequenced, draft-rendered outreach PLAN:

  Engagement (.mdc strategy, bundled as JSON = the knowledge base)
    -> Email Template  (one per message step; populates core Frappe Email Template)
    -> Outreach Sequence (plan container; tier from priority rank)
    -> Lead Prospect     (primary contact, if not already present)
    -> Outreach Sequence Instance (links prospect -> sequence)
    -> CRM Task          (one per step; rendered draft in `description`,
                          staggered `due_date` by delay_days)
    -> Communication draft (save_draft -> Human Inbox pipeline)

All reference data ships bundled in crm/industry_data/engagements.json. Live
rows are written only when a seed endpoint is called.
"""
from __future__ import annotations

import json
import os
import re
import datetime
from typing import Any, Dict, List, Optional

import frappe
from frappe import _

# Sender identity for seeded Outreach Sequences. The engagement strategies are
# LinkedIn-first and most contacts have no verified email, but the Outreach
# Sequence doctype requires a sender_email. Use the CrisPRO.ai org outreach
# address (the domain used throughout the strategies). Sequences are seeded in
# Draft/inactive state and are NOT auto-transmitted.
OUTREACH_SENDER_EMAIL = "outreach@crispro.ai"

# ---------------------------------------------------------------------------
# Bundled knowledge-base loader
# ---------------------------------------------------------------------------
_INDUSTRY_CACHE: Optional[List[dict]] = None


def _industry_data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "industry_data")


def _load_industry_json() -> List[dict]:
    """Load and cache the bundled parsed engagements."""
    global _INDUSTRY_CACHE
    if _INDUSTRY_CACHE is None:
        path = os.path.join(_industry_data_dir(), "engagements.json")
        with open(path, "r", encoding="utf-8") as fh:
            _INDUSTRY_CACHE = json.load(fh)
    return _INDUSTRY_CACHE


def _engagement(slug: str) -> Optional[dict]:
    for e in _load_industry_json():
        if e.get("slug") == slug:
            return e
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rank_to_tier(rank: Any) -> str:
    """Map outreach_priority_rank (1..10) -> Tier 1/2/3."""
    try:
        r = int(rank)
    except (TypeError, ValueError):
        return "Tier 3"
    if r <= 3:
        return "Tier 1"
    if r <= 6:
        return "Tier 2"
    return "Tier 3"


def _clean_name(display: str) -> str:
    """'Mark Chao, MD, PhD — CEO, Inhibrx' -> 'Mark Chao'."""
    if not display:
        return ""
    # cut at em/en dash (title separator) then strip credential suffixes
    head = re.split(r"\s+[—–-]\s+", display)[0]
    head = re.split(r",\s*(MD|PhD|MBA|DO|MSc|MS|PharmD)", head)[0]
    return head.strip()


def _placeholder_email(name: str) -> str:
    """RFC 2606 .invalid placeholder for contacts without a verified email."""
    slug = re.sub(r"[^a-z0-9]+", ".", (name or "contact").lower()).strip(".")
    return f"{slug or 'contact'}@needs-backfill.invalid"


def _text_to_html(text: str) -> str:
    """Blank-line-separated paragraphs -> <p>, single newlines -> <br>."""
    if not text:
        return ""
    blocks = re.split(r"\n\s*\n", text.strip())
    out = []
    for b in blocks:
        b = b.strip().replace("\n", "<br>")
        out.append(f"<p>{b}</p>")
    return "".join(out)


def _step_task_title(company: str, step: dict, contact: str) -> str:
    return f"Step {step['step_number']}: {step.get('sender','')} → {contact} ({company})"


def _render_plan_html(engagement: dict, option: str = "A") -> str:
    """Render the full sequenced outreach plan as HTML (for the CRM detail view / Task)."""
    fm = engagement.get("front_matter", {})
    fit = engagement.get("fit", {})
    contacts = engagement.get("contacts", {})
    steps = engagement.get("message_options", {}).get(f"option_{option.lower()}", {}).get("steps", [])
    primary = contacts.get("primary", {})
    parts = [
        f"<h3>{fm.get('company','')} — Outreach Plan (Option {option})</h3>",
        f"<p><b>Lead drug:</b> {fm.get('lead_drug','')}<br>"
        f"<b>Target:</b> {fm.get('target','')}<br>"
        f"<b>Trial:</b> {fm.get('trial','')}<br>"
        f"<b>Claim posture:</b> {fm.get('claim_posture','')} | "
        f"<b>Priority rank:</b> {fm.get('outreach_priority_rank','')} | "
        f"<b>CrisPRO fit:</b> {fit.get('composite','')}</p>",
        f"<p><b>Primary contact:</b> {primary.get('name','')} — {primary.get('title','')}, "
        f"{primary.get('institution','')}<br>"
        f"<b>Preferred channel:</b> {contacts.get('preferred_channel','')}</p>",
        f"<p><b>Sharpest hook:</b> {fit.get('sharpest_hook','')}</p>",
        "<hr><h4>Sequenced messages</h4>",
    ]
    for s in steps:
        when = "Day 0 (immediately)" if s["delay_days"] == 0 else f"Day +{s['delay_days']}"
        parts.append(
            f"<p><b>{when} — {s.get('sender','')}</b> "
            f"<i>({s.get('channel_note','')})</i></p>"
            f"<blockquote>{_text_to_html(s.get('body',''))}</blockquote>"
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------
@frappe.whitelist()
def industry_dashboard() -> Dict[str, Any]:
    """List all industry engagements with summary + live seed status."""
    data = _load_industry_json()
    rows = []
    for e in data:
        fm = e.get("front_matter", {})
        fit = e.get("fit", {})
        primary = e.get("contacts", {}).get("primary", {})
        slug = e.get("slug")
        company = fm.get("company", slug)
        # live seed status: does a sequence exist for this engagement?
        seq_name = _find_sequence(slug, company)
        seq_exists = bool(seq_name)
        n_tasks = frappe.db.count("CRM Task", {"reference_doctype": "Outreach Sequence",
                                               "reference_docname": seq_name}) if seq_exists else 0
        rows.append({
            "slug": slug,
            "company": fm.get("company"),
            "lead_drug": fm.get("lead_drug"),
            "target": fm.get("target"),
            "trial": fm.get("trial"),
            "phase": fm.get("phase"),
            "priority_rank": fm.get("outreach_priority_rank"),
            "claim_posture": fm.get("claim_posture"),
            "composite_fit": fit.get("composite"),
            "tier": _rank_to_tier(fm.get("outreach_priority_rank")),
            "primary_contact": primary.get("name"),
            "primary_institution": primary.get("institution"),
            "preferred_channel": e.get("contacts", {}).get("preferred_channel"),
            "tags": fm.get("tags", []),
            "seeded": bool(seq_exists),
            "sequence_name": seq_name if seq_exists else None,
            "task_count": n_tasks,
        })
    # sort by priority rank asc (1 = highest)
    rows.sort(key=lambda r: int(r["priority_rank"]) if str(r["priority_rank"]).isdigit() else 99)
    return {"count": len(rows), "engagements": rows}


@frappe.whitelist()
def engagement_detail(slug: str, option: str = "A") -> Dict[str, Any]:
    """Full parsed strategy + rendered plan + linked live artifacts for one engagement."""
    e = _engagement(slug)
    if not e:
        frappe.throw(_("Engagement not found: {0}").format(slug))
    company = e.get("front_matter", {}).get("company", slug)
    seq_name = _find_sequence(slug, company)
    seeded = bool(seq_name)
    tasks = []
    drafts = []
    if seeded:
        tasks = frappe.get_all(
            "CRM Task",
            filters={"reference_doctype": "Outreach Sequence", "reference_docname": seq_name},
            fields=["name", "title", "status", "due_date", "priority"],
            order_by="due_date asc",
        )
        # drafts linked to those tasks
        for t in tasks:
            d = frappe.get_all(
                "Communication",
                filters={"reference_doctype": "CRM Task", "reference_name": t["name"]},
                fields=["name", "subject", "recipients", "status"],
            )
            drafts.extend(d)
    return {
        "engagement": e,
        "rendered_plan_html": _render_plan_html(e, option),
        "seeded": seeded,
        "sequence_name": seq_name if seeded else None,
        "tasks": tasks,
        "drafts": drafts,
    }


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------
# NOTE: Outreach Sequence / Instance / Lead Prospect use `naming_series:` so a
# custom document name passed on insert is IGNORED (auto-named OS-/OSI-/LP-).
# We therefore identify a seeded sequence by its `sequence_name` FIELD (unique
# per engagement) and thread the resulting auto-name through to child rows.
# Email Template uses field-based naming, so its deterministic name IS kept.

def _sequence_label(slug: str, company: str) -> str:
    """The unique `sequence_name` field value for an engagement's sequence."""
    return f"{company} — CrisPRO Outreach"


def _find_sequence(slug: str, company: str) -> Optional[str]:
    """Return the auto-named doc name of the engagement's Outreach Sequence, or None."""
    rows = frappe.get_all("Outreach Sequence",
                          filters={"sequence_name": _sequence_label(slug, company)},
                          fields=["name"], limit=1)
    return rows[0]["name"] if rows else None


def _company_for_slug(slug: str) -> str:
    e = _engagement(slug)
    return (e.get("front_matter", {}).get("company", slug)) if e else slug


def _email_template_name(slug: str, step_number: int) -> str:
    return f"eng-{slug}-step-{step_number}"


# ---------------------------------------------------------------------------
# Seed endpoints  (write live rows)
# ---------------------------------------------------------------------------
def _seed_one(engagement: dict, option: str = "A") -> Dict[str, Any]:
    """Materialize one engagement into Email Templates + Sequence + Prospect +
    Instance + Tasks + Inbox drafts. Idempotent per (slug, option)."""
    fm = engagement.get("front_matter", {})
    slug = engagement.get("slug")
    company = fm.get("company", slug)
    contacts = engagement.get("contacts", {})
    primary = contacts.get("primary", {})
    contact_display = primary.get("name", "")
    contact_clean = _clean_name(contact_display)
    steps = engagement.get("message_options", {}).get(f"option_{option.lower()}", {}).get("steps", [])
    fit = engagement.get("fit", {})

    created = {"email_templates": [], "sequence": None, "prospect": None,
               "instance": None, "tasks": [], "drafts": []}

    # ---- 1. Email Templates (one per step) --------------------------------
    subject_base = f"CrisPRO — {fm.get('trial','').split('(')[0].strip() or company}"
    for s in steps:
        et_name = _email_template_name(slug, s["step_number"])
        subject = f"{subject_base} (msg {s['step_number']})"
        html = _text_to_html(s.get("body", ""))
        if frappe.db.exists("Email Template", et_name):
            et = frappe.get_doc("Email Template", et_name)
            et.subject = subject
            et.response_html = html
            et.response = html
            et.use_html = 1
            et.save(ignore_permissions=True)
        else:
            et = frappe.get_doc({
                "doctype": "Email Template",
                "name": et_name,
                "subject": subject,
                "use_html": 1,
                "response_html": html,
                "response": html,
            })
            et.insert(ignore_permissions=True)
        created["email_templates"].append(et.name)

    # ---- 2. Outreach Sequence (plan container) ----------------------------
    # Identify by sequence_name FIELD (naming_series ignores custom doc names).
    step1_body = _text_to_html(steps[0]["body"]) if steps else ""
    last_delay = steps[-1]["delay_days"] if steps else 0
    existing_seq = _find_sequence(slug, company)
    if existing_seq:
        seq = frappe.get_doc("Outreach Sequence", existing_seq)
    else:
        seq = frappe.get_doc({"doctype": "Outreach Sequence"})
    seq.sequence_name = _sequence_label(slug, company)
    seq.tier = _rank_to_tier(fm.get("outreach_priority_rank"))
    seq.subject_template = subject_base
    seq.body_template = step1_body
    seq.follow_up_days = str(last_delay)
    seq.max_follow_ups = len(steps)
    seq.sender_email = OUTREACH_SENDER_EMAIL
    seq.unsubscribe_link = 0
    seq.status = "Draft"
    seq.active = 0
    if existing_seq:
        seq.save(ignore_permissions=True)
    else:
        seq.insert(ignore_permissions=True)
    seq_name = seq.name  # auto-named OS-YYYY-NNNNN
    created["sequence"] = seq_name

    # ---- 3. Lead Prospect (primary contact) -------------------------------
    prospect_name = None
    if contact_clean:
        existing = frappe.get_all("Lead Prospect", filters={"pi_name": contact_clean}, limit=1)
        if existing:
            prospect_name = existing[0]["name"]
        else:
            email = _placeholder_email(contact_clean)
            # cancer_type: the 10 curated engagements are all MSS CRC by design and
            # carry no explicit cancer_type key -> default to Colorectal Cancer for
            # backward compatibility. A GENERATED card (any indication) sets
            # front_matter.cancer_type explicitly so a non-CRC lead is never
            # silently mislabeled as colorectal.
            prospect = frappe.get_doc({
                "doctype": "Lead Prospect",
                "pi_name": contact_clean,
                "pi_email": email,
                "institution": primary.get("institution", ""),
                "cancer_type": fm.get("cancer_type") or "Colorectal Cancer",
                "tier": _rank_to_tier(fm.get("outreach_priority_rank")),
                "source": "Manual Entry",
                "source_ref_id": f"engagement::{slug}",
                "outreach_status": "Not Contacted",
                "notes": f"Industry engagement primary contact — {company}. "
                         f"Preferred channel: {contacts.get('preferred_channel','')}.",
            })
            prospect.insert(ignore_permissions=True)
            prospect_name = prospect.name
    created["prospect"] = prospect_name

    # ---- 4. Outreach Sequence Instance ------------------------------------
    if prospect_name:
        inst_exists = frappe.get_all("Outreach Sequence Instance",
                                     filters={"prospect": prospect_name, "outreach_sequence": seq_name}, limit=1)
        if inst_exists:
            created["instance"] = inst_exists[0]["name"]
        else:
            inst = frappe.get_doc({
                "doctype": "Outreach Sequence Instance",
                "prospect": prospect_name,
                "outreach_sequence": seq_name,
                "status": "Not Started",
                "total_steps": len(steps),
                "current_step": 0,
            })
            inst.insert(ignore_permissions=True)
            created["instance"] = inst.name

    # ---- 5. CRM Tasks (one per step) + 6. Inbox drafts --------------------
    today = datetime.date.today()
    recipient = _placeholder_email(contact_clean)
    for s in steps:
        task_title = _step_task_title(company, s, contact_clean or contact_display)
        due = today + datetime.timedelta(days=int(s["delay_days"]))
        # idempotency: match by title + reference
        existing_t = frappe.get_all("CRM Task", filters={
            "title": task_title, "reference_doctype": "Outreach Sequence",
            "reference_docname": seq_name}, limit=1)
        draft_html = (
            f"<p><b>Channel:</b> {s.get('channel_note','')}</p>"
            f"<p><b>Send:</b> {'Day 0' if s['delay_days']==0 else 'Day +'+str(s['delay_days'])} "
            f"(after prior step)</p>"
            f"<hr><blockquote>{_text_to_html(s.get('body',''))}</blockquote>"
        )
        if existing_t:
            task = frappe.get_doc("CRM Task", existing_t[0]["name"])
            task.description = draft_html
            task.due_date = datetime.datetime.combine(due, datetime.time(9, 0))
            task.save(ignore_permissions=True)
        else:
            task = frappe.get_doc({
                "doctype": "CRM Task",
                "title": task_title,
                "priority": "High" if _rank_to_tier(fm.get("outreach_priority_rank")) == "Tier 1" else "Medium",
                "status": "Todo",
                "start_date": today,
                "due_date": datetime.datetime.combine(due, datetime.time(9, 0)),
                "description": draft_html,
                "reference_doctype": "Outreach Sequence",
                "reference_docname": seq_name,
            })
            task.insert(ignore_permissions=True)
        created["tasks"].append(task.name)

        # Inbox draft (save_draft requires to+subject+html)
        subject = f"{subject_base} (msg {s['step_number']})"
        try:
            from crm.api.email import save_draft
            comm_name = save_draft(
                reference_doctype="CRM Task",
                reference_name=task.name,
                to=recipient,
                subject=subject,
                html=_text_to_html(s.get("body", "")),
            )
            created["drafts"].append(comm_name)
        except Exception as ex:  # noqa: BLE001
            created["drafts"].append({"error": str(ex), "task": task.name})

    return created


@frappe.whitelist()
def seed_engagement_plan(slug: str, option: str = "A") -> Dict[str, Any]:
    """Materialize a single engagement's sequenced outreach plan into live rows."""
    e = _engagement(slug)
    if not e:
        frappe.throw(_("Engagement not found: {0}").format(slug))
    result = _seed_one(e, option=option)
    frappe.db.commit()
    return {"slug": slug, "option": option, "created": result}


@frappe.whitelist()
def seed_all_engagements(option: str = "A") -> Dict[str, Any]:
    """Materialize all 10 engagements. Idempotent."""
    out = []
    for e in _load_industry_json():
        try:
            r = _seed_one(e, option=option)
            out.append({"slug": e.get("slug"), "ok": True,
                        "sequence": r["sequence"], "tasks": len(r["tasks"]),
                        "drafts": len(r["drafts"]), "prospect": r["prospect"]})
        except Exception as ex:  # noqa: BLE001
            out.append({"slug": e.get("slug"), "ok": False, "error": str(ex)})
    frappe.db.commit()
    return {"seeded": out}
