# Copyright (c) 2026, Brenus Pharma / CrisPRO. MIT License.
"""WP1.5 -- backfill lead linkage on already-seeded engagement drafts.

Seeded engagement inbox drafts are Communications linked to their CRM Task
(reference_doctype="CRM Task"). The approval queue surfaces them via the WP1
get_inbox contract (delivery_status empty + reference_doctype includes CRM Task).
What older seeds are MISSING is the back-link to the originating CRM Lead, so the
Lead #emails tab can't find them. This script stamps that link idempotently.

It resolves the lead through the deterministic seed chain -- it never guesses:

    Communication.reference_name  -> CRM Task
    CRM Task.reference_docname    -> Outreach Sequence (OS-...)
    Outreach Sequence Instance    -> Lead Prospect (via outreach_sequence)
    Lead Prospect.source_ref_id   -> "generated::Lead::CRM-LEAD-..."  -> lead key

Fields are written ONLY when they exist on the Communication doctype (crm_lead,
engagement_draft) -- no assumption that a migration has run.

Usage (build-only; run on alpha with a real key):
    bench --site alpha-crm.v.frappe.cloud execute \
        crm.api._backfill_engagement_drafts.run --kwargs "{'dry_run': True}"
    # then, to apply:
    ... --kwargs "{'dry_run': False}"

    # optional explicit fallback for fixtures whose prospect chain predates
    # source_ref_id provenance (e.g. the alpha RAS/Kopetz drafts):
    ... --kwargs "{'dry_run': False, 'explicit_lead': 'CRM-LEAD-2026-00793', \
                   'match_terms': ['RAS', 'Kopetz', 'RAF']}"
"""
from __future__ import annotations

import frappe


def _has_field(doctype: str, field: str) -> bool:
    try:
        return bool(frappe.get_meta(doctype).has_field(field))
    except Exception:
        return False


def _lead_for_task(task_name: str) -> str | None:
    """Walk Task -> Sequence -> Instance -> Prospect -> source_ref_id -> lead."""
    if not task_name:
        return None
    task = frappe.db.get_value(
        "CRM Task", task_name, ["reference_doctype", "reference_docname"], as_dict=True
    )
    if not task or task.get("reference_doctype") != "Outreach Sequence":
        return None
    seq = task.get("reference_docname")
    if not seq:
        return None
    insts = frappe.get_all(
        "Outreach Sequence Instance",
        filters={"outreach_sequence": seq},
        fields=["prospect"],
        limit=1,
    )
    if not insts or not insts[0].get("prospect"):
        return None
    ref = frappe.db.get_value("Lead Prospect", insts[0]["prospect"], "source_ref_id") or ""
    parts = str(ref).split("::")  # generated::Lead::CRM-LEAD-...
    if len(parts) >= 3 and parts[1] == "Lead" and parts[2]:
        if frappe.db.exists("CRM Lead", parts[2]):
            return parts[2]
    return None


def run(dry_run: bool = True, explicit_lead: str | None = None,
        match_terms: list | None = None) -> dict:
    """Backfill crm_lead / engagement_draft on seeded engagement drafts.

    Returns a report with the ACTUAL comm names and the lead each would link to
    (dry-run) or was linked to (applied). Idempotent: a comm already linked to
    its resolved lead is reported as `already` and not rewritten.
    """
    has_crm_lead = _has_field("Communication", "crm_lead")
    has_marker = _has_field("Communication", "engagement_draft")

    # candidate drafts: outbound, not yet dispatched, linked to a CRM Task
    drafts = frappe.get_all(
        "Communication",
        filters={
            "communication_type": "Communication",
            "reference_doctype": "CRM Task",
            "sent_or_received": "Sent",
            "delivery_status": ["in", ["", None]],
        },
        fields=["name", "reference_name", "subject", "crm_lead"] if has_crm_lead
        else ["name", "reference_name", "subject"],
        limit=1000,
    )

    report = {
        "dry_run": bool(dry_run),
        "has_crm_lead_field": has_crm_lead,
        "has_engagement_draft_field": has_marker,
        "candidates": len(drafts),
        "linked": [],      # newly linked this run
        "already": [],     # already linked to the resolved lead
        "unresolved": [],  # no lead could be resolved (chain missing)
        "marked": [],      # engagement_draft marker set
    }

    terms = [str(t).lower() for t in (match_terms or [])]

    for d in drafts:
        comm = d["name"]
        lead = _lead_for_task(d.get("reference_name"))
        # explicit fallback ONLY when the deterministic chain failed and the
        # operator supplied both a lead and matching terms (never fabricated).
        if not lead and explicit_lead and terms:
            subj = (d.get("subject") or "").lower()
            if any(t in subj for t in terms) and frappe.db.exists("CRM Lead", explicit_lead):
                lead = explicit_lead

        if has_marker:
            report["marked"].append(comm)
            if not dry_run:
                frappe.db.set_value("Communication", comm, "engagement_draft", 1)

        if not lead:
            report["unresolved"].append({"comm": comm, "task": d.get("reference_name")})
            continue

        if has_crm_lead and d.get("crm_lead") == lead:
            report["already"].append({"comm": comm, "lead": lead})
            continue

        report["linked"].append({"comm": comm, "lead": lead, "subject": d.get("subject")})
        if not dry_run and has_crm_lead:
            frappe.db.set_value("Communication", comm, "crm_lead", lead)

    if not dry_run:
        frappe.db.commit()

    report["summary"] = (
        f"candidates={report['candidates']} "
        f"linked={len(report['linked'])} already={len(report['already'])} "
        f"unresolved={len(report['unresolved'])} marked={len(report['marked'])} "
        f"(dry_run={dry_run})"
    )
    return report
