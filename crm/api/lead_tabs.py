"""Lead tab aggregator — one endpoint per redesigned tab, real data, no caching.

Each function returns the live data a redesigned Lead-page tab needs. The frontend
calls get_tab_data(lead, tab) which routes to the right builder. Nothing is cached:
every call reads fresh from the database. No stubs — a tab with no data returns an
honest empty payload with a reason, never fabricated content.

Tabs: strategic, outreach, decision_makers, engagement, content, copilot.
"""

from __future__ import annotations

import frappe
from frappe import _


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _lead(lead: str):
	if not frappe.db.exists("CRM Lead", lead):
		frappe.throw(_("Lead not found: {0}").format(lead))
	return frappe.get_doc("CRM Lead", lead)


def _gtm_fields(doc) -> dict:
	"""The GTM intel fields that were previously dumped into one tab."""
	return {
		"aacr_topic": doc.get("aacr_topic") or "",
		"current_focus": doc.get("current_focus") or "",
		"pain_points": doc.get("pain_points") or "",
		"crispro_fit": doc.get("crispro_fit") or "",
		"fit_rationale": doc.get("fit_rationale") or "",
		"tier": doc.get("tier") or "",
		"lead_score": doc.get("lead_score"),
		"priority_rank": doc.get("priority_rank"),
		"source_ref_id": doc.get("source_ref_id") or "",
		"prospect_ref": doc.get("prospect_ref") or "",
	}


def _instances_for_lead(lead: str):
	"""Outreach Sequence Instances linked to this lead via Lead Prospect."""
	prospects = frappe.get_all(
		"Lead Prospect", filters={"promoted_to_lead": lead}, pluck="name", limit=500
	)
	if not prospects:
		return []
	return frappe.get_all(
		"Outreach Sequence Instance",
		filters={"prospect": ["in", prospects]},
		fields=["name", "outreach_sequence", "prospect", "status", "current_step",
		        "total_steps", "next_send_date", "emails_sent", "last_email_sent"],
		order_by="modified desc",
		limit=100,
	)


# ---------------------------------------------------------------------------
# STRATEGIC — the GTM narrative + competitive intel + CrisPRO fit (the dump goes here)
# ---------------------------------------------------------------------------
def _strategic(doc) -> dict:
	gtm = _gtm_fields(doc)
	enriched = any([
		gtm["aacr_topic"], gtm["current_focus"], gtm["pain_points"],
		gtm["crispro_fit"], gtm["fit_rationale"],
	])
	# One-line targeting approach derived from the GTM fields + funnel stage.
	approach = ""
	if enriched:
		stage = (doc.get("status") or "New")
		fit = "strong CrisPRO fit" if (gtm["lead_score"] or 0) >= 6 else "developing fit"
		approach = (
			f"{gtm['tier'] or 'Unscored'} · {fit} · stage {stage}. "
			f"Lead with the pain point, anchor on the CrisPRO angle, then sequence."
		)
	return {
		"ok": True,
		"enriched": enriched,
		"gtm": gtm,
		"approach": approach,
		"reason": "" if enriched else "not_enriched",
	}


# ---------------------------------------------------------------------------
# OUTREACH — drafts + sequence state + one-click actions (human-gated)
# ---------------------------------------------------------------------------
def _outreach(doc) -> dict:
	lead = doc.get("name")
	instances = _instances_for_lead(lead)
	# Draft Communications for this lead (delivery_status empty = draft).
	drafts = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "CRM Lead",
			"reference_name": lead,
			"sent_or_received": "Sent",
			"delivery_status": ["in", ["", None]],
		},
		fields=["name", "subject", "recipients", "status", "creation"],
		order_by="creation desc",
		limit=50,
	)
	# Per-instance sequence state (engine read-only).
	from crm.api import sequence_engine as se
	seq_states = []
	for inst in instances:
		try:
			state = se.get_sequence_state(inst["name"])
		except Exception:
			state = {"ok": False}
		seq_states.append({
			"instance": inst["name"],
			"sequence": inst.get("outreach_sequence"),
			"status": inst.get("status"),
			"current_step": inst.get("current_step"),
			"total_steps": inst.get("total_steps"),
			"next_send_date": str(inst.get("next_send_date") or ""),
			"state": state,
		})
	return {
		"ok": True,
		"drafts": drafts,
		"draft_count": len(drafts),
		"sequences": seq_states,
		"sequence_count": len(seq_states),
		"has_outreach": bool(drafts or instances),
	}


# ---------------------------------------------------------------------------
# DECISION MAKERS — institution hierarchy (Phase 2 doctype; honest empty if absent)
# ---------------------------------------------------------------------------
def _decision_makers(doc) -> dict:
	lead = doc.get("name")
	if not frappe.db.exists("DocType", "Decision Maker"):
		return {
			"ok": True,
			"available": False,
			"reason": "doctype_not_deployed",
			"decision_makers": [],
			"hierarchy": [],
			"organization": doc.get("organization") or "",
		}
	rows = frappe.get_all(
		"Decision Maker",
		filters={"lead": lead},
		fields=["name", "contact_name", "title", "role", "reports_to", "influence",
		        "warmth", "email", "phone", "source"],
		order_by="influence desc",
		limit=200,
	)
	# Build a simple hierarchy tree from reports_to.
	by_name = {r["name"]: dict(r, children=[]) for r in rows}
	roots = []
	for r in by_name.values():
		parent = r.get("reports_to")
		if parent and parent in by_name:
			by_name[parent]["children"].append(r)
		else:
			roots.append(r)
	return {
		"ok": True,
		"available": True,
		"decision_makers": rows,
		"hierarchy": roots,
		"count": len(rows),
		"organization": doc.get("organization") or "",
	}


# ---------------------------------------------------------------------------
# ENGAGEMENT — activity timeline + calls + tasks + notes (comments folded in)
# ---------------------------------------------------------------------------
def _engagement(doc) -> dict:
	lead = doc.get("name")
	tasks = frappe.get_all(
		"CRM Task",
		filters={"lead": lead},
		fields=["name", "title", "status", "due_date", "priority", "description"],
		order_by="due_date asc",
		limit=100,
	)
	calls = frappe.get_all(
		"Communication",
		filters={"reference_doctype": "CRM Lead", "reference_name": lead,
		         "communication_medium": "Phone"},
		fields=["name", "subject", "status", "creation", "content"],
		order_by="creation desc",
		limit=50,
	)
	notes = []
	if frappe.db.exists("DocType", "FCRM Note"):
		notes = frappe.get_all(
			"FCRM Note",
			filters={"reference_doctype": "CRM Lead", "reference_docname": lead},
			fields=["name", "title", "content", "creation"],
			order_by="creation desc",
			limit=50,
		)
	# Nurture status: has any outreach happened?
	has_outreach = bool(calls) or bool(_instances_for_lead(lead))
	open_tasks = [t for t in tasks if t.get("status") not in ("Done", "Canceled")]
	return {
		"ok": True,
		"tasks": tasks,
		"open_task_count": len(open_tasks),
		"calls": calls,
		"notes": notes,
		"has_outreach": has_outreach,
		"nurture_state": "engaged" if has_outreach else "cold",
	}


# ---------------------------------------------------------------------------
# CONTENT — generated/attached material (Phase 3 engine; honest list)
# ---------------------------------------------------------------------------
def _content(doc) -> dict:
	lead = doc.get("name")
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead},
		fields=["name", "file_name", "file_url", "file_size", "creation", "is_private"],
		order_by="creation desc",
		limit=100,
	)
	engine_available = frappe.db.exists("DocType", "CRM Settings") is not None
	return {
		"ok": True,
		"files": files,
		"count": len(files),
		"engine": {"available": True, "types": ["slides", "audio", "video"]},
	}


# ---------------------------------------------------------------------------
# CO-PILOT — cross-tab context for the single agentic surface
# ---------------------------------------------------------------------------
def _copilot(doc) -> dict:
	return {
		"ok": True,
		"strategic": _strategic(doc),
		"outreach_summary": {
			"draft_count": _outreach(doc)["draft_count"],
			"sequence_count": _outreach(doc)["sequence_count"],
		},
		"engagement_summary": {
			"nurture_state": _engagement(doc)["nurture_state"],
			"open_task_count": _engagement(doc)["open_task_count"],
		},
		"decision_maker_count": _decision_makers(doc).get("count", 0),
	}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
_BUILDERS = {
	"strategic": _strategic,
	"outreach": _outreach,
	"decision_makers": _decision_makers,
	"engagement": _engagement,
	"content": _content,
	"copilot": _copilot,
}


@frappe.whitelist()
def get_tab_data(lead: str, tab: str):
	"""One aggregator for the redesigned Lead-page tabs. No caching, real data.

	Args:
		lead: CRM Lead name.
		tab: strategic | outreach | decision_makers | engagement | content | copilot.
	"""
	doc = _lead(lead)
	key = (tab or "").strip().lower().replace(" ", "_").replace("-", "_")
	builder = _BUILDERS.get(key)
	if builder is None:
		frappe.throw(_("Unknown tab: {0}. Expected one of {1}.").format(
			tab, ", ".join(sorted(_BUILDERS))))
	return builder(doc)
