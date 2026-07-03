# Copyright (c) 2026, NYX Agent and contributors
# For license information, please see license.txt
"""
NYX Tasks API
=============
Whitelisted CRUD + conversion endpoints for CRM Task, with typed lead/deal
linkage (in addition to the legacy dynamic reference_doctype/reference_docname).

Conversion is *configurable*: a task can be converted into either
  - a CRM Deal (reusing the canonical crm_lead.convert_to_deal seam), or
  - an AACR Intel Opportunity (a child row appended to the lead's AACR Intel doc).

The default conversion target is read from site config key
``nyx_task_convert_default`` (values: "deal" | "opportunity"), defaulting to
"deal". An explicit ``target`` argument always overrides the config default.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
TERMINAL_STATUSES = ("Done", "Canceled")
OPEN_STATUSES = ("Backlog", "Todo", "In Progress")


def _as_dict(v):
	"""Frappe passes JSON strings for dict/list args over HTTP."""
	if isinstance(v, str):
		try:
			return json.loads(v)
		except Exception:
			return {}
	return v or {}


def _resolve_lead(task_doc):
	"""Best-effort lead name from typed field or dynamic reference."""
	if task_doc.get("lead"):
		return task_doc.get("lead")
	if task_doc.get("reference_doctype") == "CRM Lead" and task_doc.get("reference_docname"):
		return task_doc.get("reference_docname")
	return None


def _config_target():
	target = (frappe.conf.get("nyx_task_convert_default") or "deal").lower().strip()
	return target if target in ("deal", "opportunity") else "deal"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_tasks(lead=None, deal=None, reference_doctype=None, reference_docname=None,
              status=None, assigned_to=None, limit=50):
	"""List tasks filtered by typed link OR legacy dynamic reference.

	Backward compatible: if reference_docname is given it matches the dynamic
	link exactly as the legacy get_linked_tasks did.
	"""
	filters = {}
	or_filters = None
	if lead:
		# match either the typed field OR a dynamic CRM Lead reference
		or_filters = [["lead", "=", lead], ["reference_docname", "=", lead]]
	elif deal:
		or_filters = [["deal", "=", deal], ["reference_docname", "=", deal]]
	elif reference_docname:
		filters["reference_docname"] = reference_docname
		if reference_doctype:
			filters["reference_doctype"] = reference_doctype
	if status:
		filters["status"] = status
	if assigned_to:
		filters["assigned_to"] = assigned_to

	try:
		limit = min(int(limit), 200)
	except Exception:
		limit = 50

	tasks = frappe.get_all(
		"CRM Task",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "title", "description", "assigned_to", "start_date",
			"due_date", "priority", "status", "lead", "deal",
			"reference_doctype", "reference_docname", "modified",
		],
		order_by="modified desc",
		limit_page_length=limit,
	)
	return tasks or []


@frappe.whitelist()
def create_task(title, lead=None, deal=None, priority=None, status=None,
                due_date=None, start_date=None, description=None,
                assigned_to=None, reference_doctype=None, reference_docname=None):
	"""Create a CRM Task. Sets BOTH the typed link and the dynamic reference
	so old (dynamic-link) and new (typed) consumers both see the task."""
	if not title:
		frappe.throw(_("Task title is required"))

	doc = frappe.new_doc("CRM Task")
	doc.title = title
	doc.priority = priority or "Medium"
	doc.status = status or "Todo"
	if due_date:
		doc.due_date = due_date
	if start_date:
		doc.start_date = start_date
	if description:
		doc.description = description
	if assigned_to:
		doc.assigned_to = assigned_to

	# typed links
	if lead:
		doc.lead = lead
	if deal:
		doc.deal = deal

	# keep the dynamic reference in sync for legacy consumers
	if reference_doctype and reference_docname:
		doc.reference_doctype = reference_doctype
		doc.reference_docname = reference_docname
	elif lead:
		doc.reference_doctype = "CRM Lead"
		doc.reference_docname = lead
	elif deal:
		doc.reference_doctype = "CRM Deal"
		doc.reference_docname = deal

	doc.insert()
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def update_task(name, **kwargs):
	"""Update editable fields of a task."""
	doc = frappe.get_doc("CRM Task", name)
	editable = {
		"title", "priority", "status", "due_date", "start_date",
		"description", "assigned_to", "lead", "deal",
		"reference_doctype", "reference_docname",
	}
	changed = False
	for k, v in kwargs.items():
		if k in editable:
			doc.set(k, v)
			changed = True
	if changed:
		doc.save()
		frappe.db.commit()
	return doc.name


@frappe.whitelist()
def set_status(name, status):
	"""Convenience: move a task to a new status."""
	valid = {"Backlog", "Todo", "In Progress", "Done", "Canceled"}
	if status not in valid:
		frappe.throw(_("Invalid status: {0}").format(status))
	frappe.db.set_value("CRM Task", name, "status", status)
	frappe.db.commit()
	return {"name": name, "status": status}


@frappe.whitelist()
def delete_task(name):
	frappe.delete_doc("CRM Task", name)
	frappe.db.commit()
	return {"deleted": name}


# ---------------------------------------------------------------------------
# conversion  (configurable: deal | opportunity)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def convert_task(name, target=None, opportunity=None, deal=None,
                 mark_done=1):
	"""Convert a task's lead into a Deal OR append an AACR Intel Opportunity.

	target:
	    "deal"        -> reuse crm_lead.convert_to_deal(lead); links task.deal
	    "opportunity" -> append AACR Intel Opportunity row to lead's AACR Intel
	    (None)        -> use site config key nyx_task_convert_default (def "deal")

	Returns a dict describing what was created and re-links the task.
	"""
	task = frappe.get_doc("CRM Task", name)
	lead_name = _resolve_lead(task.as_dict())
	if not lead_name:
		frappe.throw(_("Task {0} is not linked to a CRM Lead; cannot convert.").format(name))

	target = (target or _config_target()).lower().strip()

	if target == "deal":
		result = _convert_to_deal(task, lead_name, _as_dict(deal))
	elif target == "opportunity":
		result = _convert_to_opportunity(task, lead_name, _as_dict(opportunity))
	else:
		frappe.throw(_("Unknown conversion target: {0}").format(target))

	# mark the task done so it leaves the open queue
	if int(mark_done or 0):
		task.reload()
		task.status = "Done"
		task.save(ignore_permissions=True)
		frappe.db.commit()

	result["task"] = name
	return result


def _convert_to_deal(task, lead_name, deal_overrides):
	"""Reuse the canonical Lead->Deal seam, then link the task to the deal."""
	from crm.fcrm.doctype.crm_lead.crm_lead import convert_to_deal as lead_convert

	deal_name = lead_convert(lead_name, deal=deal_overrides or None)

	# link the task to the new deal (typed + dynamic)
	task.reload()
	task.deal = deal_name
	if not task.lead:
		task.lead = lead_name
	task.reference_doctype = "CRM Deal"
	task.reference_docname = deal_name
	task.save(ignore_permissions=True)
	frappe.db.commit()
	return {"target": "deal", "deal": deal_name, "lead": lead_name}


def _convert_to_opportunity(task, lead_name, opp):
	"""Append an AACR Intel Opportunity child row to the lead's AACR Intel doc,
	creating the parent AACR Intel doc if the lead has none yet."""
	intel_name = frappe.db.get_value("AACR Intel", {"crm_lead": lead_name}, "name")
	if intel_name:
		intel = frappe.get_doc("AACR Intel", intel_name)
		created_parent = False
	else:
		intel = frappe.new_doc("AACR Intel")
		intel.crm_lead = lead_name
		# intel_id is the autoname (field:intel_id) -> must be set & unique
		intel.intel_id = opp.get("intel_id") or f"INTEL-{lead_name}"
		lead_title = frappe.db.get_value("CRM Lead", lead_name, "lead_name")
		intel.talk_title = opp.get("talk_title") or (lead_title or lead_name)
		created_parent = True

	row = intel.append("opportunities", {})
	row.priority = (opp.get("priority") or "medium").lower()
	row.opportunity_type = opp.get("opportunity_type") or "Follow-up"
	row.description = opp.get("description") or task.title
	row.crispro_angle = opp.get("crispro_angle") or ""
	row.transcript_evidence = opp.get("transcript_evidence") or ""
	row.external_validation_needed = opp.get("external_validation_needed") or ""

	intel.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"target": "opportunity",
		"aacr_intel": intel.name,
		"created_parent": created_parent,
		"lead": lead_name,
		"opportunity_index": len(intel.opportunities),
	}


@frappe.whitelist()
def get_convert_default():
	"""Expose the configured default conversion target to the UI."""
	return {"default_target": _config_target()}
