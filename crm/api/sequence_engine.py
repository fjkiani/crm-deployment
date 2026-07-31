"""crm.api.sequence_engine — the omnichannel cadence engine.

SUBSUMES crm/api/cadence.py (commit 0f991dc9): the same proven human-gated
advance/refuse core, plus arming, a unified channel-event entry, the 360 worklist
aggregator, and the NEW delay semantics (delay_days = offset from prior step
completion, not absolute from seed day).

Contract: see INTERFACE.md. 4-space indent. Never auto-sends / auto-calls /
auto-WhatsApps — a human confirms every touch. State lives on the Outreach
Sequence Instance, NEVER in lead.additional_data (the fake MCP pattern).
"""
import datetime
import re

import frappe
from frappe.utils import now_datetime

from crm.api.email import assert_deliverable

_STEP_TITLE_RE = re.compile(r"^\s*Step\s+(\d+)\s*:", re.IGNORECASE)
MAX_RETRIES_PER_LEAD = 5
CHANNELS = ("Email", "Call", "WhatsApp", "LinkedIn")


# ---------------------------------------------------------------------------
# Resolution helpers (from cadence.py — proven)
# ---------------------------------------------------------------------------
def _parse_step_number(task):
    m = _STEP_TITLE_RE.match(task.get("title") or "")
    return int(m.group(1)) if m else None


def _get_task(task_name):
    if not task_name or not frappe.db.exists("CRM Task", task_name):
        return None
    return frappe.get_doc("CRM Task", task_name)


def _resolve_instances(os_name):
    return frappe.get_all(
        "Outreach Sequence Instance",
        filters={"outreach_sequence": os_name},
        fields=["name", "prospect", "outreach_sequence", "status",
                "current_step", "total_steps", "next_send_date",
                "emails_sent", "last_email_sent"],
    )


def _refusal(reason, **ctx):
    out = {"advanced": False, "ok": False, "reason": reason}
    out.update(ctx)
    return out


def _resolve_instance(instance_name=None, task=None):
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
    lead = task.get("lead")
    if lead:
        for inst in instances:
            prospect = inst.get("prospect")
            if prospect and frappe.db.get_value("Lead Prospect", prospect, "promoted_to_lead") == lead:
                return frappe.get_doc("Outreach Sequence Instance", inst["name"]), None
    return None, _refusal("ambiguous_instance", sequence=os_name,
                          candidates=[i["name"] for i in instances])


def _step_communication(task_name):
    rows = frappe.get_all(
        "Communication",
        filters={"reference_doctype": "CRM Task", "reference_name": task_name},
        fields=["name", "recipients", "delivery_status", "status", "subject"],
        order_by="creation asc",
        limit=1,
    )
    return rows[0] if rows else None


def _sequence_steps(os_name):
    """Per-step rows (channel + delay) for a sequence, ordered by step_number.

    Reads the Sequence Step doctype (standalone, with `sequence` Link + `channel`).
    Falls back to deriving steps from CRM Tasks when no Step rows exist (the
    current seeded state) so the engine works before the seed writes Step rows.
    """
    try:
        rows = frappe.get_all(
            "Outreach Sequence Step",
            filters={"sequence": os_name},
            fields=["name", "step_number", "delay_days", "channel", "email_template"],
        )
        if rows:
            rows.sort(key=lambda r: int(r.get("step_number") or 0))
            return rows
    except Exception:
        pass
    # Fallback: derive from tasks (Step {N}: title) — delay from due_date ordering.
    tasks = frappe.get_all(
        "CRM Task",
        filters={"reference_doctype": "Outreach Sequence", "reference_docname": os_name},
        fields=["name", "title", "due_date", "status"],
    )
    derived = []
    for t in tasks:
        n = _parse_step_number(t)
        if n is not None:
            derived.append({"step_number": n, "delay_days": None, "channel": "Email",
                            "task": t.get("name"), "due_date": t.get("due_date")})
    derived.sort(key=lambda r: r["step_number"])
    return derived


def _step_delay(os_name, step_number):
    """delay_days for a step (offset from prior completion). None if unknown."""
    for s in _sequence_steps(os_name):
        if int(s.get("step_number") or 0) == step_number:
            d = s.get("delay_days")
            try:
                return int(d) if d is not None else None
            except (TypeError, ValueError):
                return None
    return None


def _next_step_task(os_name, next_step_number):
    rows = frappe.get_all(
        "CRM Task",
        filters={"reference_doctype": "Outreach Sequence", "reference_docname": os_name},
        fields=["name", "title", "due_date", "status"],
    )
    for r in rows:
        if _parse_step_number(r) == next_step_number:
            return r
    return None


# ---------------------------------------------------------------------------
# Core advance (shared by all channels) — from cadence.py, NEW delay semantics
# ---------------------------------------------------------------------------
def _advance_core(instance, task, step_number, comm):
    now = now_datetime()
    total = int(instance.get("total_steps") or 0)
    os_name = instance.get("outreach_sequence")

    task.db_set("status", "Done")
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
        # NEW delay semantics: next_send_date = now + delay_days(next step).
        # Fall back to the next task's existing due_date if no delay is recorded.
        delay = _step_delay(os_name, step_number + 1)
        nxt = _next_step_task(os_name, step_number + 1)
        if delay is not None:
            next_send_date = now + datetime.timedelta(days=delay)
        elif nxt and nxt.get("due_date"):
            next_send_date = nxt.get("due_date")
        if next_send_date:
            instance.db_set("next_send_date", next_send_date)
            # Re-date the next task to the completion-relative due date.
            if nxt and delay is not None:
                try:
                    nxt_doc = frappe.get_doc("CRM Task", nxt["name"])
                    nxt_doc.db_set("due_date", next_send_date)
                except Exception:
                    pass
        nxt_comm = _step_communication(nxt["name"]) if nxt else None
        next_draft = nxt_comm.get("name") if nxt_comm else None

    return {
        "advanced": True, "ok": True,
        "instance": instance.get("name"),
        "current_step": step_number,
        "total_steps": total,
        "status": "Completed" if completed else (instance.get("status") or "In Progress"),
        "next_send_date": str(next_send_date) if next_send_date else None,
        "next_draft": next_draft,
        "task": task.get("name"),
        "communication": comm.get("name") if comm else None,
    }


def _resolve_step_and_check(instance, task, step_number=None):
    """Shared ordering/idempotency checks. Returns (step_number, error)."""
    if task is not None:
        sn = _parse_step_number(task)
        if sn is None:
            return None, _refusal("unparseable_step_title", task=task.get("name"),
                                  title=task.get("title"))
        step_number = sn
    if step_number is None:
        step_number = int(instance.get("current_step") or 0) + 1
    current = int(instance.get("current_step") or 0)
    if step_number <= current:
        return None, _refusal("already_advanced", instance=instance.get("name"),
                              current_step=current, attempted_step=step_number)
    if step_number != current + 1:
        return None, _refusal("out_of_order", instance=instance.get("name"),
                              current_step=current, attempted_step=step_number)
    return step_number, None


# ---------------------------------------------------------------------------
# Email advance (human-gated) — from cadence.py
# ---------------------------------------------------------------------------
@frappe.whitelist()
def advance_sequence_instance(instance_name=None, task_name=None, communication_name=None):
    task = _get_task(task_name)
    if task_name and task is None:
        return _refusal("task_not_found", task=task_name)
    instance, err = _resolve_instance(instance_name=instance_name, task=task)
    if err:
        return err
    step_number, err = _resolve_step_and_check(instance, task)
    if err:
        return err

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
    if (comm.get("delivery_status") or "") != "Sent":
        return _refusal("email_not_sent", communication=comm.get("name"),
                        delivery_status=comm.get("delivery_status") or "", step=step_number)
    recipients = [r.strip() for r in (comm.get("recipients") or "").split(",") if r.strip()]
    try:
        assert_deliverable(recipients)
    except Exception as e:
        return _refusal("undeliverable_recipient", communication=comm.get("name"),
                        recipients=recipients, detail=str(e), step=step_number)
    return _advance_core(instance, task, step_number, comm)


# ---------------------------------------------------------------------------
# Call advance (human-gated) — from cadence.py
# ---------------------------------------------------------------------------
def _lead_for_instance(instance):
    prospect = instance.get("prospect")
    if not prospect:
        return None
    try:
        return frappe.db.get_value("Lead Prospect", prospect, "promoted_to_lead")
    except Exception:
        return None


def _completed_call_log(lead_name):
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
    task = _get_task(task_name)
    if task is None:
        return _refusal("task_not_found", task=task_name)
    instance, err = _resolve_instance(instance_name=instance_name, task=task)
    if err:
        return err
    step_number, err = _resolve_step_and_check(instance, task)
    if err:
        return err
    completed = False
    if call_outcome and str(call_outcome).lower() in ("completed", "ended", "success", "done"):
        completed = True
    if not completed:
        completed = _completed_call_log(_lead_for_instance(instance)) is not None
    if not completed:
        return _refusal("call_not_completed", task=task.get("name"), step=step_number,
                        instance=instance.get("name"))
    return _advance_core(instance, task, step_number, comm=None)


# ---------------------------------------------------------------------------
# Unified channel-event entry (webhook / WA delivered / inbound reply)
# ---------------------------------------------------------------------------
def _retry_task(task, instance):
    """No-answer / failed: re-date the task +1 day, emails_sent unchanged."""
    try:
        retries = int(task.get("retry_count") or 0)
    except Exception:
        retries = 0
    if retries >= MAX_RETRIES_PER_LEAD:
        return {"ok": True, "retried": False, "reason": "max_retries", "task": task.get("name")}
    new_due = now_datetime() + datetime.timedelta(days=1)
    task.db_set("due_date", new_due)
    try:
        task.db_set("retry_count", retries + 1)
    except Exception:
        pass
    return {"ok": True, "retried": True, "task": task.get("name"),
            "next_due": str(new_due), "retry": retries + 1}


@frappe.whitelist()
def on_channel_event(instance_name=None, task_name=None, channel="Email",
                     outcome=None, communication_name=None):
    """Route a channel completion/attempt to the right advance or retry."""
    channel = (channel or "Email").strip()
    oc = (outcome or "").strip().lower()

    # Absolute: unsubscribe.
    if oc == "unsubscribe":
        instance, err = _resolve_instance(instance_name=instance_name, task=_get_task(task_name))
        if err:
            return err
        instance.db_set("status", "Unsubscribed")
        return {"ok": True, "unsubscribed": True, "instance": instance.get("name")}

    # Negative call outcomes -> retry, do not advance.
    if channel == "Call" and oc in ("no-answer", "no_answer", "failed", "voicemail", "busy"):
        task = _get_task(task_name)
        if task is None:
            return _refusal("task_not_found", task=task_name)
        instance, err = _resolve_instance(instance_name=instance_name, task=task)
        if err:
            return err
        return _retry_task(task, instance)

    if channel == "Email":
        return advance_sequence_instance(instance_name=instance_name, task_name=task_name,
                                         communication_name=communication_name)
    if channel == "Call":
        return advance_call_step(task_name=task_name, call_outcome=outcome,
                                 instance_name=instance_name)
    if channel == "WhatsApp":
        return advance_whatsapp_step(task_name=task_name, instance_name=instance_name,
                                     delivered=(oc in ("delivered", "read", "sent", "")))
    return _refusal("unknown_channel", channel=channel)


# ---------------------------------------------------------------------------
# WhatsApp advance (same core; gates on delivered + enabled + phone)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def advance_whatsapp_step(task_name, instance_name=None, delivered=False):
    task = _get_task(task_name)
    if task is None:
        return _refusal("task_not_found", task=task_name)
    instance, err = _resolve_instance(instance_name=instance_name, task=task)
    if err:
        return err
    step_number, err = _resolve_step_and_check(instance, task)
    if err:
        return err
    # Gate: WhatsApp must be enabled/installed (honest, not silent).
    try:
        from crm.api import whatsapp as _wa
        if hasattr(_wa, "is_whatsapp_installed") and not _wa.is_whatsapp_installed():
            return _refusal("whatsapp_not_installed", task=task.get("name"))
        if hasattr(_wa, "is_whatsapp_enabled") and not _wa.is_whatsapp_enabled():
            return _refusal("whatsapp_not_enabled", task=task.get("name"))
    except ImportError:
        return _refusal("whatsapp_not_installed", task=task.get("name"))
    if not delivered:
        return _refusal("whatsapp_not_delivered", task=task.get("name"), step=step_number)
    return _advance_core(instance, task, step_number, comm=None)


# ---------------------------------------------------------------------------
# Arm a sequence (NEW delay semantics: rebuild due dates from arm time)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def arm_sequence(os_name):
    if not os_name or not frappe.db.exists("Outreach Sequence", os_name):
        return _refusal("sequence_not_found", sequence=os_name)
    seq = frappe.get_doc("Outreach Sequence", os_name)
    now = now_datetime()
    steps = _sequence_steps(os_name)
    if not steps:
        return _refusal("no_steps", sequence=os_name)

    # Rebuild each step task's due_date: step 1 = now + delay(1); step N builds off
    # the cumulative offsets (a planning baseline; each advance re-dates from actual
    # completion). When a step has no recorded delay (fallback path, no Step rows),
    # preserve its ORIGINAL relative spacing from step 1 rather than collapsing to 0.
    tasks_by_step = {}
    for s in steps:
        n = int(s.get("step_number") or 0)
        t = _next_step_task(os_name, n)
        if t:
            tasks_by_step[n] = t
    # Original step-1 due date as the anchor for relative spacing.
    orig_anchor = None
    if 1 in tasks_by_step and tasks_by_step[1].get("due_date"):
        orig_anchor = tasks_by_step[1].get("due_date")

    cumulative = 0
    rebuilt = 0
    for s in steps:
        n = int(s.get("step_number") or 0)
        d = s.get("delay_days")
        if d is not None:
            try:
                d = int(d)
            except (TypeError, ValueError):
                d = None
        if d is None:
            # Fallback: preserve original offset from step 1's due date.
            t = tasks_by_step.get(n)
            if t and orig_anchor and t.get("due_date"):
                try:
                    d = max(0, (t["due_date"] - orig_anchor).days)
                except Exception:
                    d = 0
            else:
                d = 0
        cumulative += d
        t = tasks_by_step.get(n)
        if t:
            try:
                tdoc = frappe.get_doc("CRM Task", t["name"])
                tdoc.db_set("due_date", now + datetime.timedelta(days=cumulative))
                rebuilt += 1
            except Exception:
                pass

    seq.db_set("status", "Active")
    seq.db_set("active", 1)
    return {"ok": True, "sequence": os_name, "status": "Active", "steps_rebuilt": rebuilt}


# ---------------------------------------------------------------------------
# 360 worklist aggregator
# ---------------------------------------------------------------------------
def _placeholder(addr):
    a = (addr or "").strip().lower()
    return (not a) or a.endswith("@needs-backfill.invalid") or a.endswith(".invalid")


@frappe.whitelist()
def get_today_worklist(user=None, channel=None, limit=50):
    now = now_datetime()
    today = now.date()
    out = {"ok": True, "due_email": [], "due_call": [], "due_whatsapp": [],
           "needs_approval": [], "blocked": [], "waiting": [], "needs_human": [],
           "health": _health()}

    instances = frappe.get_all(
        "Outreach Sequence Instance",
        filters={"status": ["in", ["Not Started", "In Progress"]]},
        fields=["name", "prospect", "outreach_sequence", "status", "current_step",
                "total_steps", "next_send_date"],
        limit=limit,
    )
    for inst in instances:
        os_name = inst.get("outreach_sequence")
        current = int(inst.get("current_step") or 0)
        total = int(inst.get("total_steps") or 0)
        if current >= total:
            continue
        nxt = _next_step_task(os_name, current + 1)
        if not nxt:
            continue
        comm = _step_communication(nxt["name"])
        chan = _step_channel(os_name, current + 1)
        if channel and chan != channel:
            continue
        item = {
            "instance": inst.get("name"), "sequence": os_name,
            "prospect": inst.get("prospect"), "lead": _lead_for_instance(inst),
            "step_number": current + 1, "total_steps": total, "channel": chan,
            "due_date": str(nxt.get("due_date")) if nxt.get("due_date") else None,
            "task": nxt.get("name"),
            "subject": comm.get("subject") if comm else None,
            "communication": comm.get("name") if comm else None,
        }
        # Blocked: placeholder email / no phone.
        blocked_reason = None
        if chan == "Email" and comm and _placeholder(comm.get("recipients")):
            blocked_reason = "placeholder_email"
        if chan in ("Call", "WhatsApp"):
            phone = frappe.db.get_value("Lead Prospect", inst.get("prospect"), "phone") if inst.get("prospect") else None
            if not phone:
                blocked_reason = "no_phone"
        if blocked_reason:
            item["blocked_reason"] = blocked_reason
            out["blocked"].append(item)
            continue
        # Due vs waiting by next_send_date / due_date.
        due = nxt.get("due_date")
        due_date = getattr(due, "date", lambda: None)()
        if due_date and due_date <= today:
            key = {"Email": "due_email", "Call": "due_call", "WhatsApp": "due_whatsapp"}.get(chan)
            if key:
                out[key].append(item)
            # A ready draft also surfaces in needs_approval.
            if chan == "Email" and comm and (comm.get("delivery_status") or "") != "Sent":
                out["needs_approval"].append(item)
        else:
            out["waiting"].append(item)
    return out


def _step_channel(os_name, step_number):
    for s in _sequence_steps(os_name):
        if int(s.get("step_number") or 0) == step_number:
            return s.get("channel") or "Email"
    return "Email"


def _health():
    h = {"vapi_configured": False, "twilio_configured": False,
         "whatsapp_installed": False, "whatsapp_enabled": False}
    try:
        from crm.api import whatsapp as _wa
        if hasattr(_wa, "is_whatsapp_installed"):
            h["whatsapp_installed"] = bool(_wa.is_whatsapp_installed())
        if hasattr(_wa, "is_whatsapp_enabled"):
            h["whatsapp_enabled"] = bool(_wa.is_whatsapp_enabled())
    except Exception:
        pass
    try:
        h["vapi_configured"] = bool(frappe.conf.get("vapi_api_key"))
    except Exception:
        pass
    try:
        h["twilio_configured"] = bool(frappe.db.exists("CRM Twilio Settings")) if hasattr(frappe.db, "exists") else False
    except Exception:
        pass
    return h


# ---------------------------------------------------------------------------
# Read-only state (from cadence.py) + mark_step_complete
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_sequence_state(instance_name):
    if not frappe.db.exists("Outreach Sequence Instance", instance_name):
        return {"ok": False, "reason": "instance_not_found", "instance": instance_name}
    instance = frappe.get_doc("Outreach Sequence Instance", instance_name)
    current = int(instance.get("current_step") or 0)
    total = int(instance.get("total_steps") or 0)
    os_name = instance.get("outreach_sequence")
    nxt = _next_step_task(os_name, current + 1) if current < total else None
    nxt_comm = _step_communication(nxt["name"]) if nxt else None
    state = {
        "ok": True, "instance": instance_name, "sequence": os_name,
        "prospect": instance.get("prospect"), "status": instance.get("status"),
        "current_step": current, "total_steps": total,
        "next_send_date": str(instance.get("next_send_date")) if instance.get("next_send_date") else None,
        "emails_sent": instance.get("emails_sent"),
        "last_email_sent": str(instance.get("last_email_sent")) if instance.get("last_email_sent") else None,
        "next_task": nxt.get("name") if nxt else None,
        "next_draft": nxt_comm.get("name") if nxt_comm else None,
        "next_subject": nxt_comm.get("subject") if nxt_comm else None,
        "next_channel": _step_channel(os_name, current + 1) if current < total else None,
    }
    try:
        from crm.api import intelligence
        prospect = instance.get("prospect")
        email = frappe.db.get_value("Lead Prospect", prospect, "pi_email") if prospect else None
        state["dossier"] = intelligence.get_dossier(email=email) if email else None
        state["kb"] = intelligence.search_crm_knowledge(os_name or "", limit=3) if os_name else []
    except Exception:
        state["dossier"] = None
        state["kb"] = []
    return state


@frappe.whitelist()
def mark_step_complete(task_name, outcome=None, channel="Email"):
    """Human marks a step's task done; route to advance if the channel completed."""
    task = _get_task(task_name)
    if task is None:
        return _refusal("task_not_found", task=task_name)
    res = on_channel_event(task_name=task_name, channel=channel, outcome=outcome)
    return {"ok": res.get("ok", bool(res.get("advanced"))), "task": task_name,
            "task_status": task.get("status"), "advance": res}
