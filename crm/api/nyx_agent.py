"""
crm/api/nyx_agent.py — NYX agentic orchestrator (tool-using, human-gated).

Turns NYX from a summary generator into a tool-using agent that:
  1. plan_workflow()  — proposes an ORDERED list of tool-calls (writes nothing)
  2. execute_step()   — runs ONE proposed step, with dry-run, gating, audit + undo
  3. undo_action()    — reverses a reversible executed action

Safety scaffolding (all four requested):
  - Dry-run preview: execute_step(dry_run=True) returns "would do X" without mutating.
  - Audit trail: every proposed/dry_run/executed/blocked/undone action -> Nyx Action Log.
  - Undo: reversible actions capture pre-state (undo_data_json) and can be reversed.
  - Kill switch: nyx_execution_enabled flag; when off, all writes=True are refused.

NYX never auto-executes writes. The frontend drives step-by-step on user click; every
irreversible action requires confirm=True. Read/reversible steps still run only on click.

The orchestrator calls the UNDERLYING whitelisted functions directly (same pattern as
crm.api.agent.run), not the MCP-protocol wrappers.
"""

from __future__ import annotations

import json
import logging

import frappe
from frappe import _
from frappe.utils import now_datetime

from crm.api.nyx_email_brain import _resolve_llm, _active_llm_provider, _get_conf

logger = logging.getLogger(__name__)

_LOG_DT = "Nyx Action Log"


# ---------------------------------------------------------------------------
# guards + kill switch
# ---------------------------------------------------------------------------
def _guard():
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _execution_enabled() -> bool:
	"""Kill switch. Priority: runtime default (UI toggle) -> site_config -> default ON.

	The UI toggle writes a DefaultValue via set_nyx_execution(); that takes precedence so
	freezing/unfreezing works instantly without a config edit. site_config can hard-set it
	(e.g. ship disabled). Absent both -> enabled.
	"""
	runtime = frappe.db.get_default("nyx_execution_enabled")
	if runtime not in (None, ""):
		return str(runtime) not in ("0", "false", "False", "no", "off")
	val = _get_conf("nyx_execution_enabled", default=1)
	return str(val) not in ("0", "false", "False", "no", "off")


# ---------------------------------------------------------------------------
# TOOL REGISTRY — curated, safe subset. Each: writes / reversible / dry_run_supported
# handler is a callable(params:dict) -> (result:dict, undo_data:dict|None)
# ---------------------------------------------------------------------------
def _reg():
	return {
		"enrich_engagement": {
			"label": "Enrich engagement (company + contacts)",
			"writes": False, "reversible": True, "dry_run_supported": False,
			"params": ["slug", "force"],
		},
		"enrich_contact": {
			"label": "Enrich contact (person)",
			"writes": False, "reversible": True, "dry_run_supported": False,
			"params": ["lead_name", "force"],
		},
		"gtm_outreach_reasoning": {
			"label": "Assess best outreach move (NYX reasoning)",
			"writes": False, "reversible": True, "dry_run_supported": False,
			"params": ["lead_name"],
		},
		"synthesize_gtm_from_intel": {
			"label": "Sync GTM narrative from intel",
			"writes": True, "reversible": True, "dry_run_supported": True,
			"params": ["lead_name", "commit"],
		},
		"seed_engagement_plan": {
			"label": "Seed outreach plan (sequence + tasks + drafts)",
			"writes": True, "reversible": False, "dry_run_supported": False,
			"params": ["slug", "option"],
		},
		"create_task": {
			"label": "Create a CRM task",
			"writes": True, "reversible": True, "dry_run_supported": True,
			"params": ["title", "lead", "priority", "description", "reference_doctype", "reference_docname"],
		},
		"create_note": {
			"label": "Add a note to the lead timeline",
			"writes": True, "reversible": True, "dry_run_supported": True,
			"params": ["lead_name", "title", "content"],
		},
		"update_lead_score": {
			"label": "Update lead score",
			"writes": True, "reversible": True, "dry_run_supported": True,
			"params": ["lead_name", "score", "reasoning"],
		},
		"save_draft": {
			"label": "Draft outreach email to inbox",
			"writes": True, "reversible": True, "dry_run_supported": True,
			"params": ["reference_doctype", "reference_name", "to", "subject", "html"],
		},
		"approve_and_send": {
			"label": "Send email (IRREVERSIBLE)",
			"writes": True, "reversible": False, "dry_run_supported": True,
			"params": ["communication_name"],
		},
	}


# ---------------------------------------------------------------------------
# handlers — call underlying whitelisted fns; return (result, undo_data)
# ---------------------------------------------------------------------------
def _h_enrich_engagement(p):
	from crm.api.enrichment_api import enrich_engagement
	return enrich_engagement(p["slug"], force=int(p.get("force", 0))), None


def _h_enrich_contact(p):
	from crm.api.enrichment_api import enrich_contact
	return enrich_contact(p["lead_name"], force=int(p.get("force", 0))), None


def _h_gtm_reasoning(p):
	from crm.api.nyx_campaigns import gtm_outreach_reasoning
	return gtm_outreach_reasoning(p["lead_name"]), None


def _h_synth_gtm(p):
	from crm.api.intel_bridge import synthesize_gtm_from_intel
	lead = p["lead_name"]
	# capture pre-state for undo (score/tier + gtm fields)
	pre = frappe.db.get_value("CRM Lead", lead,
	                          ["lead_score", "tier", "additional_data"], as_dict=True) or {}
	res = synthesize_gtm_from_intel(lead, commit=bool(int(p.get("commit", 1))))
	undo = {"lead": lead, "lead_score": pre.get("lead_score"), "tier": pre.get("tier")}
	return res, undo


def _h_seed_plan(p):
	from crm.api.industry import seed_engagement_plan
	return seed_engagement_plan(p["slug"], option=p.get("option", "A")), None


def _h_create_task(p):
	from crm.api.tasks import create_task
	name = create_task(
		title=p["title"], lead=p.get("lead"), priority=p.get("priority"),
		description=p.get("description"),
		reference_doctype=p.get("reference_doctype"), reference_docname=p.get("reference_docname"),
	)
	return {"task": name}, {"task": name}


def _h_create_note(p):
	note = frappe.get_doc({
		"doctype": "FCRM Note", "title": p["title"], "content": p.get("content", ""),
		"reference_doctype": "CRM Lead", "reference_docname": p["lead_name"],
	})
	note.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"note": note.name}, {"note": note.name}


def _h_update_score(p):
	lead = p["lead_name"]
	pre = frappe.db.get_value("CRM Lead", lead, "lead_score")
	frappe.db.set_value("CRM Lead", lead, "lead_score", int(p["score"]))
	frappe.db.commit()
	return {"lead": lead, "score": int(p["score"])}, {"lead": lead, "prev_score": pre}


def _h_save_draft(p):
	from crm.api.email import save_draft
	res = save_draft(
		reference_doctype=p["reference_doctype"], reference_name=p["reference_name"],
		to=p["to"], subject=p["subject"], html=p["html"],
	)
	comm = res if isinstance(res, str) else (res.get("name") if isinstance(res, dict) else None)
	return {"communication": comm}, {"communication": comm}


def _h_approve_send(p):
	from crm.api.email import send
	return send(communication_name=p["communication_name"]), None


_HANDLERS = {
	"enrich_engagement": _h_enrich_engagement,
	"enrich_contact": _h_enrich_contact,
	"gtm_outreach_reasoning": _h_gtm_reasoning,
	"synthesize_gtm_from_intel": _h_synth_gtm,
	"seed_engagement_plan": _h_seed_plan,
	"create_task": _h_create_task,
	"create_note": _h_create_note,
	"update_lead_score": _h_update_score,
	"save_draft": _h_save_draft,
	"approve_and_send": _h_approve_send,
}


# ---------------------------------------------------------------------------
# audit log
# ---------------------------------------------------------------------------
def _log(subject_type, subject_key, tool, params, status, result=None,
         undo_data=None, dry_run=False, rationale=""):
	meta = _reg().get(tool, {})
	doc = frappe.get_doc({
		"doctype": _LOG_DT,
		"actor": frappe.session.user,
		"subject_type": subject_type or "",
		"subject_key": subject_key or "",
		"tool": tool,
		"status": status,
		"dry_run": 1 if dry_run else 0,
		"writes": 1 if meta.get("writes") else 0,
		"reversible": 1 if meta.get("reversible") else 0,
		"timestamp": now_datetime(),
		"rationale": rationale or "",
		"params_json": json.dumps(params or {})[:100000],
		"result_json": json.dumps(result or {}, default=str)[:100000],
		"undo_data_json": json.dumps(undo_data or {}, default=str)[:100000],
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


# ---------------------------------------------------------------------------
# ENDPOINT: plan_workflow — proposes ordered steps, writes nothing
# ---------------------------------------------------------------------------
_PLAN_SYS = """You are NYX, the agentic outreach orchestrator for CrisPRO (Brenus Pharma).
Given a target (an industry engagement or a lead) and a goal, propose an ORDERED workflow
of concrete tool-calls that moves the outreach forward. Only use tools from the ALLOWED list.
Order matters: enrich/assess before drafting; draft before sending. Never propose sending
without a preceding draft + assessment.

Return ONLY valid JSON:
{"steps": [
  {"tool": "<one of allowed>", "params": {..}, "rationale": "why this step, now"}
]}"""


@frappe.whitelist()
def plan_workflow(subject_type: str, subject_key: str, goal: str = "") -> dict:
	"""Propose an ordered agentic workflow. WRITES NOTHING (except a 'proposed' audit row)."""
	_guard()
	reg = _reg()
	ctx = _plan_context(subject_type, subject_key)
	llm = _resolve_llm()
	steps = []
	method = "deterministic"
	if llm:
		try:
			allowed = ", ".join(reg.keys())
			prompt = (f"{_PLAN_SYS}\n\nALLOWED TOOLS: {allowed}\n\n"
			          f"TARGET: {subject_type} = {subject_key}\n"
			          f"CONTEXT: {json.dumps(ctx)[:2000]}\n"
			          f"GOAL: {goal or 'advance outreach to next best action'}")
			out = _strip_fence(llm(prompt))
			data = json.loads(out)
			steps = [s for s in data.get("steps", []) if s.get("tool") in reg]
			method = f"llm:{_active_llm_provider()}"
		except Exception as e:
			logger.warning(f"plan_workflow llm failed, deterministic fallback: {e}")
			steps = []
	if not steps:
		steps = _default_plan(subject_type, subject_key, ctx)
		method = method if method.startswith("llm") else "deterministic"
	# annotate each step with registry metadata
	enriched = []
	for s in steps:
		meta = reg.get(s["tool"], {})
		enriched.append({
			"tool": s["tool"],
			"label": meta.get("label", s["tool"]),
			"params": s.get("params", {}),
			"rationale": s.get("rationale", ""),
			"writes": bool(meta.get("writes")),
			"reversible": bool(meta.get("reversible")),
			"dry_run_supported": bool(meta.get("dry_run_supported")),
			"requires_confirm": bool(meta.get("writes") and not meta.get("reversible")),
		})
	_log(subject_type, subject_key, "plan_workflow", {"goal": goal},
	     "proposed", result={"n_steps": len(enriched), "method": method})
	return {"subject_type": subject_type, "subject_key": subject_key,
	        "goal": goal, "method": method, "steps": enriched,
	        "execution_enabled": _execution_enabled()}


def _plan_context(subject_type, subject_key):
	if subject_type == "Company":
		from crm.api.industry import _engagement
		eng = _engagement(subject_key) or {}
		fm = eng.get("front_matter", {})
		return {"company": fm.get("company"), "trial": fm.get("trial"),
		        "lead_drug": fm.get("lead_drug"), "priority_rank": fm.get("outreach_priority_rank"),
		        "primary_contact": fm.get("primary_contact")}
	if frappe.db.exists("CRM Lead", subject_key):
		return frappe.db.get_value("CRM Lead", subject_key,
		                           ["lead_name", "organization", "tier", "lead_score"], as_dict=True)
	return {}


def _default_plan(subject_type, subject_key, ctx):
	"""Deterministic, safe default workflow when no LLM is available."""
	if subject_type == "Company":
		slug = subject_key
		return [
			{"tool": "enrich_engagement", "params": {"slug": slug},
			 "rationale": "Pull live company + KOL intel (news, trials, publications, firmographics) before acting."},
			{"tool": "seed_engagement_plan", "params": {"slug": slug, "option": "A"},
			 "rationale": "Materialize the sequenced outreach plan into tasks + inbox drafts."},
		]
	lead = subject_key
	return [
		{"tool": "enrich_contact", "params": {"lead_name": lead},
		 "rationale": "Pull live person intel (publications, trials, firmographics)."},
		{"tool": "gtm_outreach_reasoning", "params": {"lead_name": lead},
		 "rationale": "Assess the best outreach move and timing right now."},
		{"tool": "synthesize_gtm_from_intel", "params": {"lead_name": lead, "commit": 0},
		 "rationale": "Preview a GTM narrative synced from intel (dry, no write)."},
	]


# ---------------------------------------------------------------------------
# ENDPOINT: execute_step — run ONE step with gating + audit + undo capture
# ---------------------------------------------------------------------------
@frappe.whitelist()
def execute_step(subject_type: str, subject_key: str, tool: str,
                 params=None, dry_run: int = 0, confirm: int = 0,
                 rationale: str = "") -> dict:
	_guard()
	reg = _reg()
	if tool not in reg:
		frappe.throw(_("Unknown tool: {0}").format(tool))
	if isinstance(params, str):
		params = frappe.parse_json(params) if params.strip().startswith("{") else {}
	params = params or {}
	dry_run = int(dry_run or 0)
	confirm = int(confirm or 0)
	meta = reg[tool]

	# kill switch: refuse writes when disabled
	if meta.get("writes") and not dry_run and not _execution_enabled():
		log = _log(subject_type, subject_key, tool, params, "blocked",
		           result={"reason": "nyx_execution_disabled"}, rationale=rationale)
		return {"status": "blocked", "reason": "NYX execution is disabled (kill switch on).",
		        "action_log": log}

	# irreversible gate: require confirm
	if meta.get("writes") and not meta.get("reversible") and not dry_run and not confirm:
		log = _log(subject_type, subject_key, tool, params, "blocked",
		           result={"reason": "confirm_required"}, rationale=rationale)
		return {"status": "blocked", "reason": "This action is irreversible. Pass confirm=1 to proceed.",
		        "action_log": log, "requires_confirm": True}

	# dry-run: describe, do not mutate
	if dry_run:
		if not meta.get("dry_run_supported"):
			return {"status": "error",
			        "reason": f"{tool} does not support dry-run (it is a read/idempotent action)."}
		preview = _dry_preview(tool, params)
		log = _log(subject_type, subject_key, tool, params, "dry_run",
		           result=preview, dry_run=True, rationale=rationale)
		return {"status": "dry_run", "would_do": preview, "action_log": log}

	# execute for real
	try:
		result, undo_data = _HANDLERS[tool](params)
		log = _log(subject_type, subject_key, tool, params, "executed",
		           result=result, undo_data=undo_data, rationale=rationale)
		return {"status": "executed", "result": result, "action_log": log,
		        "undoable": bool(meta.get("reversible") and undo_data)}
	except frappe.PermissionError:
		raise
	except Exception as e:
		logger.exception(f"execute_step {tool} failed")
		log = _log(subject_type, subject_key, tool, params, "error",
		           result={"error": str(e)}, rationale=rationale)
		return {"status": "error", "reason": str(e), "action_log": log}


def _dry_preview(tool, params):
	"""Human-readable 'what would happen' without mutating."""
	if tool == "create_task":
		return {"action": "Would create CRM Task",
		        "title": params.get("title"), "lead": params.get("lead"),
		        "priority": params.get("priority", "Medium")}
	if tool == "create_note":
		return {"action": "Would add note to lead timeline",
		        "lead": params.get("lead_name"), "title": params.get("title")}
	if tool == "update_lead_score":
		cur = frappe.db.get_value("CRM Lead", params.get("lead_name"), "lead_score")
		return {"action": "Would update lead score", "lead": params.get("lead_name"),
		        "from": cur, "to": params.get("score")}
	if tool == "save_draft":
		return {"action": "Would draft email to inbox", "to": params.get("to"),
		        "subject": params.get("subject")}
	if tool == "synthesize_gtm_from_intel":
		return {"action": "Would sync GTM narrative from intel (score/tier may change)",
		        "lead": params.get("lead_name")}
	if tool == "approve_and_send":
		return {"action": "Would SEND email (irreversible)",
		        "communication": params.get("communication_name")}
	return {"action": f"Would run {tool}", "params": params}


# ---------------------------------------------------------------------------
# ENDPOINT: undo_action
# ---------------------------------------------------------------------------
@frappe.whitelist()
def undo_action(action_log_name: str) -> dict:
	_guard()
	if not frappe.db.exists(_LOG_DT, action_log_name):
		frappe.throw(_("Action log not found."))
	log = frappe.get_doc(_LOG_DT, action_log_name)
	if log.status != "executed":
		return {"status": "noop", "reason": f"Action is '{log.status}', not undoable."}
	if not log.reversible:
		return {"status": "noop", "reason": "Action is irreversible (e.g. a send)."}
	undo = json.loads(log.undo_data_json or "{}")
	tool = log.tool
	try:
		if tool == "create_task" and undo.get("task"):
			frappe.delete_doc("CRM Task", undo["task"], ignore_permissions=True, force=True)
		elif tool == "create_note" and undo.get("note"):
			frappe.delete_doc("FCRM Note", undo["note"], ignore_permissions=True, force=True)
		elif tool == "save_draft" and undo.get("communication"):
			frappe.delete_doc("Communication", undo["communication"], ignore_permissions=True, force=True)
		elif tool == "update_lead_score" and undo.get("lead"):
			frappe.db.set_value("CRM Lead", undo["lead"], "lead_score", undo.get("prev_score"))
		elif tool == "synthesize_gtm_from_intel" and undo.get("lead"):
			frappe.db.set_value("CRM Lead", undo["lead"],
			                    {"lead_score": undo.get("lead_score"), "tier": undo.get("tier")})
		else:
			return {"status": "noop", "reason": f"No undo path for {tool}."}
		frappe.db.commit()
		log.status = "undone"
		log.save(ignore_permissions=True)
		frappe.db.commit()
		return {"status": "undone", "tool": tool}
	except Exception as e:
		logger.exception("undo failed")
		return {"status": "error", "reason": str(e)}


# ---------------------------------------------------------------------------
# ENDPOINT: action trail (audit) for a subject
# ---------------------------------------------------------------------------
@frappe.whitelist()
def action_trail(subject_type: str = "", subject_key: str = "", limit: int = 30) -> dict:
	_guard()
	filters = {}
	if subject_type:
		filters["subject_type"] = subject_type
	if subject_key:
		filters["subject_key"] = subject_key
	rows = frappe.get_all(
		_LOG_DT, filters=filters,
		fields=["name", "actor", "tool", "status", "dry_run", "writes", "reversible",
		        "timestamp", "rationale", "result_json"],
		order_by="timestamp desc", limit_page_length=int(limit or 30),
	)
	for r in rows:
		try:
			r["result"] = json.loads(r.pop("result_json") or "{}")
		except Exception:
			r["result"] = {}
	return {"actions": rows, "execution_enabled": _execution_enabled()}


# ---------------------------------------------------------------------------
# ENDPOINT: kill switch state (read) — set is admin-only via site_config
# ---------------------------------------------------------------------------
@frappe.whitelist()
def nyx_execution_status() -> dict:
	_guard()
	return {"enabled": _execution_enabled()}


@frappe.whitelist()
def set_nyx_execution(enabled: int) -> dict:
	"""Toggle the kill switch. System Manager only (writes site-level runtime flag)."""
	_guard()
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw(_("Only System Manager can toggle NYX execution."), frappe.PermissionError)
	# Store on a cache-backed runtime flag so it survives without a config edit.
	frappe.db.set_default("nyx_execution_enabled", "1" if int(enabled) else "0")
	return {"enabled": bool(int(enabled))}


def _strip_fence(txt: str) -> str:
	import re
	txt = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
	txt = re.sub(r"\s*```$", "", txt)
	return txt.strip()
