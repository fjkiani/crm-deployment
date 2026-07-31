"""crm.api.cadence — the human-gated cadence engine.

This closes the confirmed gap in GROUND_TRUTH.md (G1): seeding writes Email
Templates + an Outreach Sequence + CRM Tasks + draft Communications, but nothing
advances ``Outreach Sequence Instance.current_step`` when a step completes. The
dead ``crm/leadgen/outreach/sequence_manager.py`` tried to be this engine but
reads fields that do not exist (``instance.lead_prospect``, ``sequence.steps``,
doctype ``Email``) and is imported nowhere. This module is the live, correct one.

Design contract (see WORKER_PLAN.md):
  * HUMAN-GATED. ``advance_sequence_instance`` runs ONLY on a human-confirmed
    signal: the step's CRM Task is being marked done AND its Communication draft
    was actually sent (``delivery_status == "Sent"``). It NEVER sends email and
    NEVER places a call itself.
  * REFUSAL HONESTY. If the step's email was never sent, or the recipient is an
    undeliverable placeholder (``*@needs-backfill.invalid``), it refuses and
    changes NOTHING. No false record that a KOL was contacted.
  * IDEMPOTENT. Advancing the same step twice is a no-op.
  * MULTI-INSTANCE SAFE. Tasks reference the Sequence, not the Instance. When a
    Sequence has more than one Instance and the task carries no prospect/lead
    disambiguator, it refuses rather than advance the wrong prospect.
  * ORDERED. The step number is parsed from the task title ``Step {N}: ...`` and
    must equal ``current_step + 1``; out-of-order completion is refused.

Indentation: 4 spaces (matches crm/api/industry.py).
"""
import datetime
import re

import frappe
from frappe.utils import now_datetime

from crm.api.email import assert_deliverable

_STEP_TITLE_RE = re.compile(r"^\s*Step\s+(\d+)\s*:", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------
def _parse_step_number(task):
    """Return the integer step number from a CRM Task title, or None."""
    m = _STEP_TITLE_RE.match(task.get("title") or "")
    return int(m.group(1)) if m else None


def _get_task(task_name):
    if not task_name or not frappe.db.exists("CRM Task", task_name):
        return None
    return frappe.get_doc("CRM Task", task_name)


def _resolve_instances(os_name):
    """All Outreach Sequence Instances for a Sequence name."""
    return frappe.get_all(
        "Outreach Sequence Instance",
        filters={"outreach_sequence": os_name},
        fields=["name", "prospect", "outreach_sequence", "status",
                "current_step", "total_steps", "next_send_date",
                "emails_sent", "last_email_sent"],
    )


def _resolve_instance(instance_name=None, task=None):
    """Resolve the single Instance this advance applies to.

    Returns (instance_doc, error_dict). Exactly one of the two is non-None.
    """
    if instance_name:
        if not frappe.db.exists("Outreach Sequence Instance", instance_name):
            return None, _refusal("instance_not_found", instance=instance_name)
        return frappe.get_doc("Outreach Sequence Instance", instance_name), None

    if task is None:
        return None, _refusal("no_instance_or_task")

    os_name = task.get("reference_docname")
    if task.get("reference_doctype") != "Outreach Sequence" or not os_name:
        return None, _refusal("task_not_linked_to_sequence", task=task.get("name"))

    instances = _resolve_instances(os_name)
    if not instances:
        return None, _refusal("no_instance_for_sequence", sequence=os_name)
    if len(instances) == 1:
        return frappe.get_doc("Outreach Sequence Instance", instances[0]["name"]), None

    # Multiple instances on one Sequence: disambiguate via the task's lead/prospect.
    lead = task.get("lead")
    if lead:
        for inst in instances:
            prospect = inst.get("prospect")
            if prospect and frappe.db.get_value("Lead Prospect", prospect, "promoted_to_lead") == lead:
                return frappe.get_doc("Outreach Sequence Instance", inst["name"]), None
    return None, _refusal(
        "ambiguous_instance",
        sequence=os_name,
        candidates=[i["name"] for i in instances],
    )


def _step_communication(task_name):
    """The Communication draft linked to this task (the approval-queue join)."""
    rows = frappe.get_all(
        "Communication",
        filters={"reference_doctype": "CRM Task", "reference_name": task_name},
        fields=["name", "recipients", "delivery_status", "status", "subject"],
        order_by="creation asc",
        limit=1,
    )
    return rows[0] if rows else None


def _next_step_task(os_name, next_step_number):
    """The CRM Task for the NEXT step (to recover its due_date as next_send_date)."""
    rows = frappe.get_all(
        "CRM Task",
        filters={"reference_doctype": "Outreach Sequence", "reference_docname": os_name},
        fields=["name", "title", "due_date", "status"],
    )
    for r in rows:
        if _parse_step_number(r) == next_step_number:
            return r
    return None


def _refusal(reason, **ctx):
    out = {"advanced": False, "reason": reason}
    out.update(ctx)
    return out


# ---------------------------------------------------------------------------
# Core advance (shared by email steps and Vapi call steps)
# ---------------------------------------------------------------------------
def _advance_core(instance, task, step_number, comm):
    """Mutate + persist the advance. Caller has already passed every gate.

    Returns the result dict. This is the ONLY place state changes, so email and
    call steps share one code path (no second stack).
    """
    now = now_datetime()
    total = int(instance.get("total_steps") or 0)

    # Mark the step's task done.
    task.db_set("status", "Done")

    # Advance the instance.
    instance.db_set("current_step", step_number)
    instance.db_set("emails_sent", int(instance.get("emails_sent") or 0) + 1)
    instance.db_set("last_email_sent", now)
    if (instance.get("status") or "") in ("Not Started", ""):
        instance.db_set("status", "In Progress")

    completed = total and step_number >= total
    next_send_date = None
    next_draft = None
    if completed:
        instance.db_set("status", "Completed")
        instance.db_set("next_send_date", None)
    else:
        nxt = _next_step_task(instance.get("outreach_sequence"), step_number + 1)
        if nxt and nxt.get("due_date"):
            next_send_date = nxt.get("due_date")
            instance.db_set("next_send_date", next_send_date)
        nxt_comm = _step_communication(nxt["name"]) if nxt else None
        next_draft = nxt_comm.get("name") if nxt_comm else None

    return {
        "advanced": True,
        "instance": instance.get("name"),
        "current_step": step_number,
        "total_steps": total,
        "status": "Completed" if completed else (instance.get("status") or "In Progress"),
        "next_send_date": str(next_send_date) if next_send_date else None,
        "next_draft": next_draft,
        "task": task.get("name"),
        "communication": comm.get("name") if comm else None,
    }


# ---------------------------------------------------------------------------
# Public, whitelisted API
# ---------------------------------------------------------------------------
@frappe.whitelist()
def advance_sequence_instance(instance_name=None, task_name=None, communication_name=None):
    """Advance a sequence one step on a HUMAN-CONFIRMED email send.

    Gates (any failure -> refusal, no state change):
      1. resolve the Instance (direct, or via task -> sequence, multi-instance safe)
      2. step number from the task title must equal current_step + 1 (ordered)
      3. idempotency: this step not already advanced
      4. the step's Communication must exist with delivery_status == "Sent"
      5. the recipient must be deliverable (assert_deliverable)

    NEVER sends email. The human sends; this only records the cadence state.
    """
    task = _get_task(task_name)
    if task_name and task is None:
        return _refusal("task_not_found", task=task_name)

    instance, err = _resolve_instance(instance_name=instance_name, task=task)
    if err:
        return err

    # Which step fired?
    if task is not None:
        step_number = _parse_step_number(task)
        if step_number is None:
            return _refusal("unparseable_step_title", task=task.get("name"), title=task.get("title"))
    else:
        # Direct instance advance with no task: assume the immediate next step.
        step_number = int(instance.get("current_step") or 0) + 1

    current = int(instance.get("current_step") or 0)

    # Idempotency: already advanced past/at this step.
    if step_number <= current:
        return _refusal("already_advanced", instance=instance.get("name"),
                        current_step=current, attempted_step=step_number)

    # Ordered: must be exactly the next step.
    if step_number != current + 1:
        return _refusal("out_of_order", instance=instance.get("name"),
                        current_step=current, attempted_step=step_number)

    # Resolve the step's Communication (the send proof).
    comm = None
    if communication_name:
        if not frappe.db.exists("Communication", communication_name):
            return _refusal("communication_not_found", communication=communication_name)
        comm = frappe.get_doc("Communication", communication_name)
    elif task is not None:
        comm = _step_communication(task.get("name"))

    if comm is None:
        return _refusal("no_draft_for_step", task=task.get("name") if task else None,
                        step=step_number)

    # REFUSAL GATE: the email must actually have been sent.
    if (comm.get("delivery_status") or "") != "Sent":
        return _refusal("email_not_sent", communication=comm.get("name"),
                        delivery_status=comm.get("delivery_status") or "",
                        step=step_number)

    # REFUSAL GATE: deliverability honesty (placeholder recipients refused).
    recipients = [r.strip() for r in (comm.get("recipients") or "").split(",") if r.strip()]
    try:
        assert_deliverable(recipients)
    except Exception as e:
        return _refusal("undeliverable_recipient", communication=comm.get("name"),
                        recipients=recipients, detail=str(e), step=step_number)

    return _advance_core(instance, task, step_number, comm)


def _doctype_exists(doctype):
    try:
        return bool(frappe.get_meta(doctype))
    except Exception:
        return False


def _lead_for_instance(instance):
    """The CRM Lead key for an instance's prospect (used to join Vapi Call Log)."""
    prospect = instance.get("prospect")
    if not prospect:
        return None
    try:
        return frappe.db.get_value("Lead Prospect", prospect, "promoted_to_lead")
    except Exception:
        return None


def _completed_call_log(lead_name):
    """A completed Vapi Call Log for this lead, if one exists.

    Vapi Call Log links to the lead via ``crm_lead`` (see vapi._create_call_logs)
    and marks completion via ``status`` (Initiated/Completed) + ``outcome``. We
    attempt the query directly and treat a missing doctype as "no log" rather than
    pre-gating on get_meta (which is unreliable in some contexts).
    """
    if not lead_name:
        return None
    try:
        rows = frappe.get_all(
            "Vapi Call Log",
            filters={"crm_lead": lead_name},
            fields=["name", "status", "outcome", "vapi_call_id"],
            order_by="creation desc",
        )
    except Exception:
        return None
    for lg in rows:
        status = (lg.get("status") or "").lower()
        outcome = (lg.get("outcome") or "").lower()
        if status in ("completed", "ended", "done") or outcome in ("completed", "ended", "success"):
            return lg
    return None


@frappe.whitelist()
def advance_call_step(task_name, call_outcome=None, instance_name=None):
    """Advance a sequence on a HUMAN-CONFIRMED Vapi call completion.

    For a Call step the 'sent' signal is the Vapi webhook end-of-call report, not
    a Communication. The refusal gate therefore checks for a COMPLETED Vapi Call
    Log for the instance's lead (or an explicit human-supplied outcome) instead of
    ``delivery_status``. Instance resolution, ordering, idempotency, and the
    advance itself are the SAME core as the email path — no second stack.

    The call is placed separately by the human via vapi.initiate_outbound_call
    (which already grounds via _build_call_context -> get_dossier +
    search_crm_knowledge). This function NEVER places a call; it only records the
    cadence state after a human-confirmed completion.
    """
    task = _get_task(task_name)
    if task is None:
        return _refusal("task_not_found", task=task_name)

    instance, err = _resolve_instance(instance_name=instance_name, task=task)
    if err:
        return err

    step_number = _parse_step_number(task)
    if step_number is None:
        return _refusal("unparseable_step_title", task=task.get("name"), title=task.get("title"))

    current = int(instance.get("current_step") or 0)
    if step_number <= current:
        return _refusal("already_advanced", instance=instance.get("name"),
                        current_step=current, attempted_step=step_number)
    if step_number != current + 1:
        return _refusal("out_of_order", instance=instance.get("name"),
                        current_step=current, attempted_step=step_number)

    # REFUSAL GATE: require a completed call. Either an explicit human outcome, or
    # a completed Vapi Call Log for the instance's lead.
    completed = False
    log = None
    if call_outcome and str(call_outcome).lower() in ("completed", "ended", "success", "done"):
        completed = True
    if not completed:
        lead = _lead_for_instance(instance)
        log = _completed_call_log(lead)
        completed = log is not None
    if not completed:
        return _refusal("call_not_completed", task=task.get("name"), step=step_number,
                        instance=instance.get("name"))

    return _advance_core(instance, task, step_number, comm=None)


@frappe.whitelist()
def get_sequence_state(instance_name):
    """Read-only cadence state for the UI, with grounding for the NEXT step.

    Returns current_step/total_steps/next_send_date plus the next step's draft and
    a dossier/KB snippet so the human approves with context (reuses
    intelligence.get_dossier + search_crm_knowledge; no new KB stack).
    """
    if not frappe.db.exists("Outreach Sequence Instance", instance_name):
        return {"ok": False, "reason": "instance_not_found", "instance": instance_name}
    instance = frappe.get_doc("Outreach Sequence Instance", instance_name)
    current = int(instance.get("current_step") or 0)
    total = int(instance.get("total_steps") or 0)
    os_name = instance.get("outreach_sequence")

    nxt = _next_step_task(os_name, current + 1) if current < total else None
    nxt_comm = _step_communication(nxt["name"]) if nxt else None

    state = {
        "ok": True,
        "instance": instance_name,
        "sequence": os_name,
        "prospect": instance.get("prospect"),
        "status": instance.get("status"),
        "current_step": current,
        "total_steps": total,
        "next_send_date": str(instance.get("next_send_date")) if instance.get("next_send_date") else None,
        "emails_sent": instance.get("emails_sent"),
        "last_email_sent": str(instance.get("last_email_sent")) if instance.get("last_email_sent") else None,
        "next_task": nxt.get("name") if nxt else None,
        "next_draft": nxt_comm.get("name") if nxt_comm else None,
        "next_subject": nxt_comm.get("subject") if nxt_comm else None,
    }

    # Grounding for the next step (best-effort; never blocks the read).
    try:
        from crm.api import intelligence
        prospect = instance.get("prospect")
        email = frappe.db.get_value("Lead Prospect", prospect, "pi_email") if prospect else None
        dossier = intelligence.get_dossier(email=email) if email else None
        kb = intelligence.search_crm_knowledge(os_name or "", limit=3) if os_name else []
        state["dossier"] = dossier
        state["kb"] = kb
    except Exception:
        state["dossier"] = None
        state["kb"] = []
    return state
