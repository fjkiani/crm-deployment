# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt
"""
Lead Intel Facets — materialized 1:1 index over CRM Lead for list-time filtering.

Do NOT join AACR Intel child tables on every list request. Materialize scalar
facets in the `Lead Intel Facets` doctype and query that.

APIs:
  rebuild_lead_facets(lead_name)          -> materialize facets for one lead
  get_filter_manifest("CRM Lead")         -> filter + preset descriptor for the UI
  get_faceted_list(doctype, ...)          -> paginated list joining lead + facets
"""

import json

import frappe
from crm.fcrm.doctype.aacr_intel.aacr_intel import get_aacr_intel

try:
	from crm.fcrm.doctype.aacr_talk.aacr_talk import get_aacr_talk
except Exception:
	get_aacr_talk = None


def _slug(source_ref_id: str):
	if not source_ref_id or "::" not in source_ref_id:
		return None
	return source_ref_id.split("::", 1)[0] or None


@frappe.whitelist()
def rebuild_lead_facets(lead_name: str) -> dict:
	"""Materialize scalar facets for one lead (no child-table copies)."""
	lead = frappe.get_doc("CRM Lead", lead_name)
	srid = lead.source_ref_id
	intel = get_aacr_intel(srid) if srid else None
	talk = get_aacr_talk(srid) if (srid and get_aacr_talk) else None

	counts = (intel or {}).get("counts", {}) or {}
	opps = (intel or {}).get("crispro_opportunity", []) or []
	top_pri = ""
	for pri in ("high", "medium", "low"):  # highest priority present
		if any((o.get("priority") or "") == pri for o in opps):
			top_pri = pri
			break

	layers = ["gtm"]
	if intel:
		layers.append("aacr_intel")
	if talk:
		layers.append("aacr_talk")

	has_gtm = bool(lead.pain_points or lead.crispro_fit or lead.aacr_topic)

	facet = {
		"doctype": "Lead Intel Facets",
		"crm_lead": lead_name,
		"source_ref_id": srid,
		"session_slug": _slug(srid),
		"intel_layers": json.dumps(layers),
		"tier": lead.tier,
		"lead_score": lead.lead_score,
		"has_gtm_narrative": 1 if has_gtm else 0,
		"has_competitive_intel": 1 if intel else 0,
		"has_aacr_talk": 1 if talk else 0,
		"n_opportunities": counts.get("opportunities", 0),
		"n_vulnerabilities": counts.get("vulnerabilities", 0),
		"n_moat_weaknesses": counts.get("moat_weaknesses", 0),
		"n_trial_risks": counts.get("trial_risks", 0),
		"top_opportunity_priority": top_pri,
		"presentation_type": (intel or {}).get("presentation_type"),
		"data_maturity": (intel or {}).get("data_maturity"),
		"intel_synced_at": frappe.utils.now(),
	}

	if frappe.db.exists("Lead Intel Facets", lead_name):
		doc = frappe.get_doc("Lead Intel Facets", lead_name)
		doc.update(facet)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc(facet).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"lead": lead_name, "facets": {k: v for k, v in facet.items() if k != "doctype"}}


@frappe.whitelist()
def get_filter_manifest(doctype: str = "CRM Lead") -> dict:
	"""Filter + preset descriptor. Frontend renders filters by `type`; backend
	routes each filter to lead-table vs facet-table by `source`."""
	return {
		"doctype": doctype,
		"filters": [
			{"key": "tier", "label": "Tier", "type": "select", "source": "facet",
			 "fieldname": "tier", "options": ["Tier 1", "Tier 2", "Tier 3"]},
			{"key": "has_opportunities", "label": "Has CrisPRO opportunities", "type": "boolean",
			 "source": "facet", "fieldname": "n_opportunities", "operator": ">", "value": 0},
			{"key": "has_competitive_intel", "label": "Has competitive intel", "type": "boolean",
			 "source": "facet", "fieldname": "has_competitive_intel", "operator": "=", "value": 1},
			{"key": "has_gtm_narrative", "label": "GTM narrative present", "type": "boolean",
			 "source": "facet", "fieldname": "has_gtm_narrative", "operator": "=", "value": 1},
			{"key": "presentation_type", "label": "Presentation type", "type": "select",
			 "source": "facet", "fieldname": "presentation_type", "options_from": "distinct"},
			{"key": "session_slug", "label": "AACR session", "type": "select",
			 "source": "facet", "fieldname": "session_slug", "options_from": "distinct"},
		],
		"presets": [
			{"label": "Actionable — Tier 1 + opportunities",
			 "filters": {"converted": 0}, "facet_filters": {"tier": "Tier 1", "n_opportunities": [">", 0]}},
			{"label": "Has Schema B intel", "facet_filters": {"has_competitive_intel": 1}},
			{"label": "GTM narrative missing",
			 "facet_filters": {"has_gtm_narrative": 0, "has_competitive_intel": 1}},
			{"label": "Bulk nurture", "facet_filters": {"tier": "Tier 3", "has_gtm_narrative": 0}},
		],
	}


def _distinct_facet_values(fieldname: str):
	rows = frappe.get_all("Lead Intel Facets", fields=[fieldname], group_by=fieldname,
	                      order_by=f"{fieldname} asc", limit_page_length=0)
	return [r[fieldname] for r in rows if r.get(fieldname)]


@frappe.whitelist()
def get_faceted_list(doctype: str = "CRM Lead", filters=None, facet_filters=None,
                     order_by: str = "modified desc", page_length: int = 20, start: int = 0):
	"""Paginated list joining CRM Lead + Lead Intel Facets. Same response shape as
	stock get_data: {columns, rows, total_count}. facet_filters route to the facet
	table; filters route to the lead table."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	facet_filters = frappe.parse_json(facet_filters) if isinstance(facet_filters, str) else (facet_filters or {})
	page_length = min(int(page_length or 20), 100)
	start = int(start or 0)

	conds, values = ["1=1"], {}
	# lead-table filters
	for k, v in (filters or {}).items():
		conds.append(f"l.`{frappe.db.escape(k, percent=False)[1:-1]}` = %({k})s")
		values[k] = v
	# facet-table filters (support [op, val] or scalar)
	fj = []
	for k, v in (facet_filters or {}).items():
		col = frappe.db.escape(k, percent=False)[1:-1]
		if isinstance(v, (list, tuple)) and len(v) == 2:
			op, val = v
			fj.append(f"f.`{col}` {op} %(f_{k})s")
			values[f"f_{k}"] = val
		else:
			fj.append(f"f.`{col}` = %(f_{k})s")
			values[f"f_{k}"] = v
	facet_where = (" AND " + " AND ".join(fj)) if fj else ""

	# safe order_by (fieldname [asc|desc])
	ob = "l.modified desc"
	parts = str(order_by or "").split()
	if parts:
		fld = parts[0].split(".")[-1]
		direction = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ("asc", "desc") else "desc"
		ob = f"l.`{frappe.db.escape(fld, percent=False)[1:-1]}` {direction}"

	base = f"""
		FROM `tabCRM Lead` l
		LEFT JOIN `tabLead Intel Facets` f ON f.crm_lead = l.name
		WHERE {' AND '.join(conds)}{facet_where}
	"""
	total = frappe.db.sql(f"SELECT COUNT(*) {base}", values)[0][0]
	rows = frappe.db.sql(
		f"""SELECT l.name, l.lead_name, l.organization, l.email, l.status,
		           l.tier, l.lead_score, l.priority_rank, l.source_ref_id,
		           f.n_opportunities, f.n_vulnerabilities, f.session_slug,
		           f.presentation_type, f.has_gtm_narrative, f.has_competitive_intel
		    {base} ORDER BY {ob} LIMIT %(pl)s OFFSET %(st)s""",
		{**values, "pl": page_length, "st": start}, as_dict=True,
	)
	columns = [
		{"label": "Name", "key": "lead_name"}, {"label": "Organization", "key": "organization"},
		{"label": "Tier", "key": "tier"}, {"label": "Score", "key": "lead_score"},
		{"label": "Opps", "key": "n_opportunities"}, {"label": "Email", "key": "email"},
		{"label": "Status", "key": "status"},
	]
	return {"columns": columns, "rows": rows, "total_count": total}


@frappe.whitelist()
def rebuild_all_facets(only_resolvable: bool = True, limit: int = 0) -> dict:
	filters = [["source_ref_id", "like", "%::%"]] if only_resolvable else [["source_ref_id", "is", "set"]]
	names = frappe.get_all("CRM Lead", filters=filters, pluck="name", limit_page_length=limit or 0)
	out = {"rebuilt": 0, "errors": 0}
	for n in names:
		try:
			rebuild_lead_facets(n)
			out["rebuilt"] += 1
		except Exception as e:
			out["errors"] += 1
			frappe.log_error(f"rebuild_lead_facets {n}: {e}")
	return out
