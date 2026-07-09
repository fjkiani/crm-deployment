# Copyright (c) 2026, Brenus and contributors
# For license information, please see license.txt
"""Nyx campaign orchestration — segment-driven outreach, end-to-end.

This is the glue the CRM was missing: it turns a *segment* (e.g. "Tier 3 —
Nurture") into a concrete, human-approved outreach campaign, reusing the proven
materialization mechanics from ``crm.api.industry`` (Outreach Sequence + steps +
Instances + a kickoff CRM Task) and the in-CRM LLM path from
``crm.api.nyx_email_brain`` (OpenRouter) for the *reasoning* step.

Human-in-the-loop by design:
  1. ``plan_campaign``  — NYX proposes a plan. Writes NOTHING.
  2. (human reviews / edits in the UI)
  3. ``launch_campaign`` — materializes the reviewed plan into live rows.

Staleness-aware:
  ``list_campaigns`` reports per-sequence instance/task/draft counts and the
  last activity date so a stale campaign is visible, not silently rotting.

Everything degrades honestly: if no LLM provider has credits, ``plan_campaign``
returns a deterministic template plan and says so — it never fabricates a
"drafted by AI" result.
"""

from __future__ import annotations

import datetime
import html
import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _

# Reuse the shipped campaign-materialization helpers and LLM seam.
from crm.api.industry import (  # noqa: E402
    OUTREACH_SENDER_EMAIL,
    _rank_to_tier,
    _text_to_html,
)
from crm.api.nyx_email_brain import _resolve_llm, _active_llm_provider  # noqa: E402


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
_MANAGER_ROLES = {"System Manager", "Sales Manager"}


def _require_manager():
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required."), frappe.PermissionError)
    if not (_MANAGER_ROLES & set(frappe.get_roles())):
        frappe.throw(
            _("Only Sales Managers can plan or launch campaigns."),
            frappe.PermissionError,
        )


# ---------------------------------------------------------------------------
# Segment helpers  (a "segment" = a slice of Lead Prospect by tier / status)
# ---------------------------------------------------------------------------
# Human-friendly labels for the tiers, so the UI reads like the user's mental
# model ("Tier 3 — Nurture") without hardcoding it in the frontend.
_TIER_LABELS = {
    "Tier 1": "Tier 1 — Priority",
    "Tier 2": "Tier 2 — Active",
    "Tier 3": "Tier 3 — Nurture",
}

_ELIGIBLE_STATUS = ["Not Contacted", "Contacted", None]


def _segment_filters(tier: Optional[str], status: Optional[str]) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if tier:
        filters["tier"] = tier
    if status:
        filters["outreach_status"] = status
    return filters


def _segment_prospects(tier: Optional[str], status: Optional[str],
                       limit: int = 0) -> List[Dict[str, Any]]:
    fields = ["name", "pi_name", "institution", "cancer_type", "tier",
              "lead_score", "outreach_status", "pi_email"]
    kwargs = dict(filters=_segment_filters(tier, status), fields=fields,
                  order_by="lead_score desc")
    if limit:
        kwargs["limit"] = limit
    return frappe.get_all("Lead Prospect", **kwargs)


@frappe.whitelist()
def campaign_segments() -> Dict[str, Any]:
    """Segments the user can launch a campaign against, with LIVE counts.

    Returns tiers (with nurture-style labels) and outreach statuses, each with
    the number of prospects currently in that slice — so the UI shows
    "Tier 3 — Nurture (888)" rather than an abstract dropdown.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required."), frappe.PermissionError)

    tier_rows = frappe.db.sql(
        "SELECT tier, COUNT(*) n FROM `tabLead Prospect` "
        "WHERE tier IS NOT NULL AND tier != '' GROUP BY tier ORDER BY tier",
        as_dict=True,
    )
    status_rows = frappe.db.sql(
        "SELECT outreach_status, COUNT(*) n FROM `tabLead Prospect` "
        "WHERE outreach_status IS NOT NULL AND outreach_status != '' "
        "GROUP BY outreach_status ORDER BY outreach_status",
        as_dict=True,
    )
    tiers = [
        {"value": r["tier"], "label": _TIER_LABELS.get(r["tier"], r["tier"]),
         "count": r["n"]}
        for r in tier_rows
    ]
    statuses = [
        {"value": r["outreach_status"], "label": r["outreach_status"], "count": r["n"]}
        for r in status_rows
    ]
    return {"ok": True, "tiers": tiers, "statuses": statuses,
            "total_prospects": frappe.db.count("Lead Prospect")}


# ---------------------------------------------------------------------------
# 1. PLAN  — NYX reasons about the segment. Writes nothing.
# ---------------------------------------------------------------------------
def _default_steps(tier: Optional[str]) -> List[Dict[str, Any]]:
    """Deterministic fallback cadence (used when no LLM is available)."""
    if tier == "Tier 1":
        return [
            {"step_number": 1, "delay_days": 0, "channel": "Email",
             "angle": "Direct value — CrisPRO fit for their program"},
            {"step_number": 2, "delay_days": 3, "channel": "Email",
             "angle": "Proof point / specific data hook"},
            {"step_number": 3, "delay_days": 7, "channel": "Call",
             "angle": "Offer a 15-min call"},
            {"step_number": 4, "delay_days": 14, "channel": "Email",
             "angle": "Break-up / last touch"},
        ]
    # Nurture (Tier 3) — longer, lighter cadence.
    return [
        {"step_number": 1, "delay_days": 0, "channel": "Email",
         "angle": "Low-pressure intro + relevant insight"},
        {"step_number": 2, "delay_days": 10, "channel": "Email",
         "angle": "Educational asset / recent result"},
        {"step_number": 3, "delay_days": 21, "channel": "Email",
         "angle": "Soft check-in / opt-in to keep in touch"},
    ]


_PLAN_SYSTEM = (
    "You are Nyx, a B2B outreach strategist for Brenus Pharma's CrisPRO platform "
    "(precision-oncology target/biomarker intelligence). You are planning an email "
    "outreach campaign to a SEGMENT of prospects. Return ONLY valid JSON with keys: "
    "campaign_name (string), rationale (1-2 sentences on why this cadence fits the "
    "segment), subject (string, no placeholders), steps (array of objects with "
    "step_number:int, delay_days:int, channel:'Email'|'Call', angle:string, "
    "body:string). Keep bodies short (<120 words), specific, no fabricated data, "
    "no merge-tags other than {first_name} and {institution}. 3-4 steps."
)


@frappe.whitelist()
def plan_campaign(segment_tier: Optional[str] = None,
                  segment_status: Optional[str] = None,
                  goal: Optional[str] = None) -> Dict[str, Any]:
    """Propose a campaign plan for a segment. WRITES NOTHING.

    NYX reasons about the segment via the in-CRM LLM (OpenRouter). If no LLM
    provider is configured / has credits, returns a deterministic template plan
    and flags ``llm_used: false`` so the UI can be honest about it.
    """
    _require_manager()
    tier = (segment_tier or "").strip() or None
    status = (segment_status or "").strip() or None

    prospects = _segment_prospects(tier, status)
    seg_count = len(prospects)
    if seg_count == 0:
        return {"ok": False, "reason": "empty_segment",
                "detail": _("No prospects match this segment."),
                "segment": {"tier": tier, "status": status, "count": 0}}

    seg_label = _TIER_LABELS.get(tier, tier) if tier else (status or "All prospects")
    sample = [
        {"name": p["pi_name"], "institution": p["institution"],
         "focus": p.get("cancer_type"), "score": p.get("lead_score")}
        for p in prospects[:8]
    ]

    llm = _resolve_llm()
    llm_used = False
    plan: Dict[str, Any] = {}
    if llm:
        prompt = (
            f"{_PLAN_SYSTEM}\n\n"
            f"SEGMENT: {seg_label} ({seg_count} prospects).\n"
            f"GOAL: {goal or 'Book intro conversations with the highest-fit prospects.'}\n"
            f"SAMPLE PROSPECTS (name, institution, focus, fit score):\n"
            f"{json.dumps(sample, indent=2)}\n\n"
            f"Return the JSON plan now."
        )
        try:
            raw = llm(prompt) or ""
            # Tolerate models that wrap JSON in prose / code fences.
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                plan = json.loads(raw[start:end + 1])
                llm_used = bool(plan.get("steps"))
        except Exception as ex:  # noqa: BLE001
            frappe.log_error(f"plan_campaign LLM parse: {ex}", "nyx_campaigns")
            plan = {}

    if not llm_used:
        steps = _default_steps(tier)
        plan = {
            "campaign_name": f"{seg_label} — Outreach",
            "rationale": _(
                "Template cadence (no AI provider configured). "
                "Configure a model to get segment-tailored copy."
            ),
            "subject": f"CrisPRO — {seg_label}",
            "steps": steps,
        }

    # Normalize / guard the step list.
    steps = plan.get("steps") or _default_steps(tier)
    for i, s in enumerate(steps, start=1):
        s.setdefault("step_number", i)
        s.setdefault("delay_days", 0 if i == 1 else (i - 1) * 7)
        s.setdefault("channel", "Email")

    return {
        "ok": True,
        "llm_used": llm_used,
        "llm_provider": _active_llm_provider(),
        "segment": {"tier": tier, "status": status, "label": seg_label,
                    "count": seg_count},
        "plan": {
            "campaign_name": plan.get("campaign_name") or f"{seg_label} — Outreach",
            "rationale": plan.get("rationale") or "",
            "subject": plan.get("subject") or f"CrisPRO — {seg_label}",
            "steps": steps,
        },
        "sample_prospects": sample,
    }


# ---------------------------------------------------------------------------
# 2. LAUNCH  — materialize the (reviewed) plan into live rows. Idempotent-ish.
# ---------------------------------------------------------------------------
def _campaign_sequence_label(name: str) -> str:
    return f"Campaign — {name}"


@frappe.whitelist()
def launch_campaign(campaign_name: str,
                    subject: str,
                    steps: Any,
                    segment_tier: Optional[str] = None,
                    segment_status: Optional[str] = None,
                    enroll_limit: int = 25,
                    create_kickoff_task: int = 1) -> Dict[str, Any]:
    """Materialize a reviewed campaign plan.

    Creates: an Outreach Sequence (plan container), a kickoff CRM Task that
    references the sequence (so it shows on /tasks and deep-links to the Nyx
    hub), and — up to ``enroll_limit`` — Outreach Sequence Instances enrolling
    the segment's top-scored prospects. Returns everything created.

    Nothing is *sent*. Enrolment queues the campaign for the human to work; the
    kickoff task is the human's entry point.
    """
    _require_manager()
    if isinstance(steps, str):
        steps = json.loads(steps)
    if not campaign_name or not steps:
        frappe.throw(_("campaign_name and steps are required."))

    tier = (segment_tier or "").strip() or None
    status = (segment_status or "").strip() or None
    enroll_limit = max(0, min(int(enroll_limit or 0), 200))

    created: Dict[str, Any] = {"sequence": None, "task": None,
                               "instances": [], "skipped": [], "email_templates": []}

    # ---- 1. Email Templates (one per step) --------------------------------
    slug = frappe.scrub(campaign_name)[:40]
    for s in steps:
        n = int(s.get("step_number", 1))
        et_name = f"campaign-{slug}-step-{n}"
        html = _text_to_html(s.get("body", "") or s.get("angle", ""))
        subj = f"{subject} (msg {n})"
        if frappe.db.exists("Email Template", et_name):
            et = frappe.get_doc("Email Template", et_name)
            et.subject, et.response_html, et.response, et.use_html = subj, html, html, 1
            et.save(ignore_permissions=True)
        else:
            et = frappe.get_doc({"doctype": "Email Template", "name": et_name,
                                 "subject": subj, "use_html": 1,
                                 "response_html": html, "response": html})
            et.insert(ignore_permissions=True)
        created["email_templates"].append(et.name)

    # ---- 2. Outreach Sequence (identify by sequence_name FIELD) -----------
    seq_label = _campaign_sequence_label(campaign_name)
    existing = frappe.get_all("Outreach Sequence",
                              filters={"sequence_name": seq_label}, limit=1)
    seq = (frappe.get_doc("Outreach Sequence", existing[0]["name"])
           if existing else frappe.get_doc({"doctype": "Outreach Sequence"}))
    first_body = _text_to_html(steps[0].get("body", "") or steps[0].get("angle", ""))
    last_delay = steps[-1].get("delay_days", 0)
    seq.sequence_name = seq_label
    seq.tier = tier or "Tier 3"
    seq.subject_template = subject
    seq.body_template = first_body
    seq.follow_up_days = str(last_delay)
    seq.max_follow_ups = len(steps)
    seq.sender_email = OUTREACH_SENDER_EMAIL
    seq.unsubscribe_link = 1
    seq.status = "Draft"
    seq.active = 0
    if existing:
        seq.save(ignore_permissions=True)
    else:
        seq.insert(ignore_permissions=True)
    seq_name = seq.name
    created["sequence"] = seq_name

    # ---- 3. Enroll segment prospects as Instances -------------------------
    if enroll_limit:
        for p in _segment_prospects(tier, status, limit=enroll_limit):
            inst_exists = frappe.get_all(
                "Outreach Sequence Instance",
                filters={"prospect": p["name"], "outreach_sequence": seq_name},
                limit=1)
            if inst_exists:
                created["skipped"].append(p["name"])
                continue
            inst = frappe.get_doc({
                "doctype": "Outreach Sequence Instance",
                "prospect": p["name"], "outreach_sequence": seq_name,
                "status": "Not Started", "current_step": 0,
                "total_steps": len(steps), "owner": frappe.session.user,
            })
            inst.insert(ignore_permissions=True)
            created["instances"].append(inst.name)

    # ---- 4. Kickoff CRM Task (references the sequence) --------------------
    if int(create_kickoff_task or 0):
        seg_label = _TIER_LABELS.get(tier, tier) if tier else (status or "All prospects")
        n_enrolled = len(created["instances"])
        steps_html = "".join(
            f"<li><b>Day {s.get('delay_days', 0)} · {s.get('channel', 'Email')}:</b> "
            f"{html.escape(s.get('angle', '') or s.get('body', '')[:120])}</li>"
            for s in steps
        )
        desc = (
            f"<p><b>Campaign:</b> {html.escape(campaign_name)}</p>"
            f"<p><b>Segment:</b> {html.escape(seg_label)} — "
            f"{n_enrolled} prospect(s) enrolled.</p>"
            f"<p><b>Subject:</b> {html.escape(subject)}</p>"
            f"<p><b>Cadence:</b></p><ol>{steps_html}</ol>"
            f"<p>Review the enrolled prospects and drafts, then approve sends "
            f"from the Human Inbox.</p>"
        )
        task = frappe.get_doc({
            "doctype": "CRM Task",
            "title": f"Kick off campaign: {campaign_name}",
            "priority": "High" if (tier == "Tier 1") else "Medium",
            "status": "Todo",
            "start_date": datetime.date.today(),
            "due_date": datetime.datetime.combine(
                datetime.date.today(), datetime.time(9, 0)),
            "description": desc,
            "reference_doctype": "Outreach Sequence",
            "reference_docname": seq_name,
        })
        task.insert(ignore_permissions=True)
        created["task"] = task.name

    frappe.db.commit()
    return {"ok": True, "campaign_name": campaign_name, "sequence": seq_name,
            "created": created,
            "enrolled_count": len(created["instances"]),
            "skipped_count": len(created["skipped"])}


# ---------------------------------------------------------------------------
# 3. LIST  — surface campaigns for the hub + staleness signal
# ---------------------------------------------------------------------------
@frappe.whitelist()
def list_campaigns(limit: int = 50) -> Dict[str, Any]:
    """All Outreach Sequences with live enrolment / task / activity counts.

    Powers the Nyx hub campaign panel and the ``?sequence=`` deep-link focus.
    ``last_activity`` surfaces stale campaigns.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required."), frappe.PermissionError)
    limit = max(1, min(int(limit or 50), 200))

    seqs = frappe.get_all(
        "Outreach Sequence",
        fields=["name", "sequence_name", "tier", "status", "active",
                "max_follow_ups", "sender_email", "modified"],
        order_by="modified desc", limit=limit)

    out = []
    for s in seqs:
        n_inst = frappe.db.count("Outreach Sequence Instance",
                                 {"outreach_sequence": s["name"]})
        n_active = frappe.db.count(
            "Outreach Sequence Instance",
            {"outreach_sequence": s["name"], "status": ["in", ["In Progress", "Not Started"]]})
        n_tasks = frappe.db.count("CRM Task",
                                  {"reference_doctype": "Outreach Sequence",
                                   "reference_docname": s["name"]})
        last_inst = frappe.get_all(
            "Outreach Sequence Instance",
            filters={"outreach_sequence": s["name"]},
            fields=["modified"], order_by="modified desc", limit=1)
        last_activity = last_inst[0]["modified"] if last_inst else s["modified"]
        # staleness: no instance activity in 14 days while still active
        stale = False
        if last_activity:
            age = (frappe.utils.now_datetime()
                   - frappe.utils.get_datetime(last_activity)).days
            stale = age >= 14 and n_active > 0
        out.append({
            "name": s["name"], "sequence_name": s["sequence_name"],
            "tier": s["tier"], "status": s["status"], "active": s["active"],
            "steps": s["max_follow_ups"], "sender_email": s["sender_email"],
            "enrolled": n_inst, "active_instances": n_active, "tasks": n_tasks,
            "last_activity": str(last_activity) if last_activity else None,
            "stale": stale,
        })
    return {"ok": True, "campaigns": out, "total": len(out)}


# ---------------------------------------------------------------------------
# 4. SUGGEST TASKS  — NYX proposes next-best actions from pipeline state
# ---------------------------------------------------------------------------
@frappe.whitelist()
def suggest_tasks(mood: Optional[str] = None, limit: int = 6) -> Dict[str, Any]:
    """Propose next-best tasks from LIVE pipeline state. WRITES NOTHING.

    Deterministic signals (uncontacted high-tier prospects, drafts awaiting
    approval, stale active campaigns). ``mood`` optionally biases the ordering
    ("aggressive" -> prioritize new high-tier outreach; "cleanup" -> prioritize
    stale campaigns + pending drafts). The frontend creates the chosen tasks via
    ``crm.api.tasks.create_task`` — this endpoint only *recommends*.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required."), frappe.PermissionError)
    limit = max(1, min(int(limit or 6), 20))
    mood = (mood or "").strip().lower()

    suggestions: List[Dict[str, Any]] = []

    # Signal 1: high-tier prospects not yet contacted.
    for tier in ("Tier 1", "Tier 2"):
        rows = frappe.get_all(
            "Lead Prospect",
            filters={"tier": tier, "outreach_status": ["in", ["Not Contacted", None, ""]]},
            fields=["name", "pi_name", "institution"], limit=5,
            order_by="lead_score desc")
        if rows:
            names = ", ".join(r["pi_name"] for r in rows[:3])
            suggestions.append({
                "kind": "outreach_hightier",
                "priority": "High" if tier == "Tier 1" else "Medium",
                "title": f"Start outreach to {len(rows)} un-contacted {tier} prospect(s)",
                "detail": f"e.g. {names}. Launch a {tier} campaign from the hub.",
                "action": "plan_campaign",
                "action_params": {"segment_tier": tier, "segment_status": "Not Contacted"},
                "weight": 100 if tier == "Tier 1" else 70,
            })

    # Signal 2: drafts awaiting human approval (Communication in Draft).
    n_drafts = frappe.db.count("Communication", {
        "communication_type": "Communication", "communication_medium": "Email",
        "sent_or_received": "Sent", "status": ["in", ["Draft", "Open"]]})
    if n_drafts:
        suggestions.append({
            "kind": "approve_drafts", "priority": "High",
            "title": f"Review & approve {n_drafts} outreach draft(s)",
            "detail": "Drafts are queued in the Human Inbox awaiting your approval.",
            "action": "open_inbox", "action_params": {},
            "weight": 90,
        })

    # Signal 3: stale active campaigns.
    stale_campaigns = [c for c in list_campaigns(limit=100)["campaigns"] if c["stale"]]
    for c in stale_campaigns[:3]:
        suggestions.append({
            "kind": "revive_campaign", "priority": "Medium",
            "title": f"Campaign '{c['sequence_name']}' has stalled",
            "detail": f"{c['active_instances']} prospect(s) mid-sequence, "
                      f"no activity since {(c['last_activity'] or '')[:10]}.",
            "action": "open_campaign", "action_params": {"sequence": c["name"]},
            "weight": 60,
        })

    # Mood biasing.
    if mood in ("aggressive", "hunt", "growth"):
        for s in suggestions:
            if s["kind"] == "outreach_hightier":
                s["weight"] += 40
    elif mood in ("cleanup", "tidy", "maintenance"):
        for s in suggestions:
            if s["kind"] in ("revive_campaign", "approve_drafts"):
                s["weight"] += 40

    suggestions.sort(key=lambda x: x["weight"], reverse=True)
    return {"ok": True, "mood": mood or None,
            "suggestions": suggestions[:limit], "total": len(suggestions)}


# ---------------------------------------------------------------------------
# 5. GTM OUTREACH REASONING  — per-lead "best move right now" for the GTM tab
# ---------------------------------------------------------------------------
_GTM_STALE_DAYS = 14

_GTM_SYSTEM = (
    "You are Nyx, an outreach strategist for Brenus Pharma's CrisPRO platform "
    "(precision-oncology target/biomarker intelligence). Given ONE lead's GTM + "
    "competitive intel, recommend the single best outreach move RIGHT NOW. Return "
    "ONLY valid JSON with keys: recommended_action (one of "
    "'send_first_touch','follow_up','re_engage','nurture','hold'), urgency (one of "
    "'now','this_week','this_month','low'), angle (1 sentence — the hook to lead "
    "with, grounded ONLY in the provided intel), subject (email subject, no "
    "placeholders), talking_points (array of 2-4 short strings), rationale (1-2 "
    "sentences on why this move and timing). No fabricated data. No merge-tags "
    "other than {first_name} and {institution}."
)


def _gtm_intel_synced_at(additional_data: Optional[str]):
    """Pull the intel_synced_at timestamp written by synthesize_gtm_from_intel."""
    if not additional_data:
        return None
    try:
        ad = json.loads(additional_data)
    except Exception:  # noqa: BLE001
        return None
    return ((ad or {}).get("nyx_gtm") or {}).get("intel_synced_at")


def _default_gtm_reasoning(tier: str, has_focus: bool, stale: bool) -> Dict[str, Any]:
    """Deterministic recommendation when no LLM is configured. Tier-driven."""
    if tier == "Tier 1":
        action, urgency = "send_first_touch", "now"
    elif tier == "Tier 2":
        action, urgency = "send_first_touch", "this_week"
    else:
        action, urgency = "nurture", "this_month"
    if stale:
        action = "re_engage"
    angle = (
        "Lead with the CrisPRO fit noted in this lead's synthesized GTM intel."
        if has_focus else
        "Intel is thin — open with a discovery angle and enrich before a hard pitch."
    )
    return {
        "recommended_action": action,
        "urgency": urgency,
        "angle": angle,
        "subject": "CrisPRO — precision target intelligence",
        "talking_points": [
            "Reference their most recent disclosed program / result.",
            "Tie CrisPRO's target/biomarker angle to their stated focus.",
            "Propose a short intro call.",
        ],
        "rationale": _(
            "Template recommendation (no AI provider configured). Configure a "
            "model in Nyx settings for lead-specific reasoning."
        ),
    }


@frappe.whitelist()
def gtm_outreach_reasoning(lead_name: str) -> Dict[str, Any]:
    """NYX's best-outreach-move reasoning for ONE lead. WRITES NOTHING.

    Reads the lead's synthesized GTM narrative + score/tier + intel freshness,
    then reasons (via the in-CRM LLM seam) about the best outreach action and
    timing *right now*. Falls back to a deterministic, tier-driven suggestion
    when no model is configured, flagging ``llm_used: false`` so the UI stays
    honest. The human reviews and decides — this endpoint only advises.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required."), frappe.PermissionError)
    if not lead_name or not frappe.db.exists("CRM Lead", lead_name):
        return {"ok": False, "reason": "not_found",
                "detail": _("Lead {0} not found.").format(lead_name)}

    lead = frappe.db.get_value(
        "CRM Lead", lead_name,
        ["lead_name", "organization", "tier", "lead_score", "source_ref_id",
         "current_focus", "pain_points", "crispro_fit", "fit_rationale",
         "aacr_topic", "status", "additional_data"],
        as_dict=True,
    ) or {}

    tier = lead.get("tier") or ""
    synced_at = _gtm_intel_synced_at(lead.get("additional_data"))
    stale = False
    stale_days = None
    if synced_at:
        try:
            dt = frappe.utils.get_datetime(synced_at)
            stale_days = (frappe.utils.now_datetime() - dt).days
            stale = stale_days >= _GTM_STALE_DAYS
        except Exception:  # noqa: BLE001
            pass
    else:
        # never synced from intel -> treat as stale IFF the lead has a resolvable ref
        stale = bool(lead.get("source_ref_id"))

    has_focus = bool((lead.get("current_focus") or lead.get("crispro_fit") or "").strip())

    llm = _resolve_llm()
    llm_used = False
    reasoning: Dict[str, Any] = {}
    if llm:
        intel_blob = {
            "tier": tier,
            "fit_score_0_10": lead.get("lead_score"),
            "current_focus": lead.get("current_focus"),
            "pain_points": lead.get("pain_points"),
            "crispro_fit": lead.get("crispro_fit"),
            "fit_rationale": lead.get("fit_rationale"),
            "aacr_topic": lead.get("aacr_topic"),
            "intel_age_days": stale_days,
        }
        prompt = (
            f"{_GTM_SYSTEM}\n\n"
            f"LEAD: {lead.get('lead_name') or lead_name}"
            f" @ {lead.get('organization') or 'unknown org'}.\n"
            f"GTM + COMPETITIVE INTEL (synthesized):\n"
            f"{json.dumps(intel_blob, indent=2, default=str)}\n\n"
            f"Return the JSON recommendation now."
        )
        try:
            raw = llm(prompt) or ""
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                reasoning = json.loads(raw[start:end + 1])
                llm_used = bool(reasoning.get("recommended_action"))
        except Exception as ex:  # noqa: BLE001
            frappe.log_error(f"gtm_outreach_reasoning LLM: {ex}", "nyx_campaigns")
            reasoning = {}

    if not llm_used:
        reasoning = _default_gtm_reasoning(tier, has_focus, stale)

    # Guard / normalize the talking-points list.
    tps = reasoning.get("talking_points") or []
    if isinstance(tps, str):
        tps = [tps]
    reasoning["talking_points"] = [str(t) for t in tps][:6]

    return {
        "ok": True,
        "llm_used": llm_used,
        "llm_provider": _active_llm_provider(),
        "lead": {
            "name": lead_name,
            "display": lead.get("lead_name") or lead_name,
            "organization": lead.get("organization"),
            "tier": tier,
            "lead_score": lead.get("lead_score"),
            "has_intel": bool(lead.get("source_ref_id")),
        },
        "staleness": {
            "intel_synced_at": synced_at,
            "intel_age_days": stale_days,
            "stale": stale,
            "threshold_days": _GTM_STALE_DAYS,
        },
        "reasoning": {
            "recommended_action": reasoning.get("recommended_action") or "nurture",
            "urgency": reasoning.get("urgency") or "low",
            "angle": reasoning.get("angle") or "",
            "subject": reasoning.get("subject") or "CrisPRO — precision target intelligence",
            "talking_points": reasoning["talking_points"],
            "rationale": reasoning.get("rationale") or "",
        },
    }
