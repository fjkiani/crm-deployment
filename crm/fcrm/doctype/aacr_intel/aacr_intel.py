# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AACRIntel(Document):
	pass


# Watch kinds, re-expanded from the generic AACR Intel Watch child table into the
# Schema-B string-array shape the corpus uses. Order is the canonical Schema-B order.
WATCH_KINDS = [
	"companies_to_monitor",
	"assets_to_track",
	"key_data_gaps",
	"unresolved_questions",
	"cognitive_dissonance",
	"rhetorical_signals",
	"nct_candidates",
]


def _clean(d, keys):
	"""Keep only the contract keys with non-empty values; drop empties so the
	frontend renderers fall back to '—'. Mirrors get_aacr_talk.clean()."""
	out = {}
	for k in keys:
		v = d.get(k)
		if v not in (None, ""):
			out[k] = v
	return out


def _assemble(doc):
	"""Inverse of the Schema-B loader: re-assemble an AACR Intel doctype + its six
	child tables back into the nested competitive-intel data-contract record the
	frontend expects. The component layer is storage-agnostic — it reads field
	names from the intel schema descriptor, so the shape produced here is the
	single source of truth the schema is written against."""

	# --- the 5 dict-array child tables -> contract arrays ---
	opportunities = [
		_clean(o.as_dict(), [
			"priority", "opportunity_type", "description", "crispro_angle",
			"transcript_evidence", "external_validation_needed",
		])
		for o in (doc.opportunities or [])
	]
	vulnerabilities = [
		_clean(v.as_dict(), [
			"failure_type", "evidence_strength", "failing_compound_or_target",
			"mechanistic_blindspot", "hidden_tox_signal", "ghost_responder_admission",
			"unexplained_resistance_quote",
		])
		for v in (doc.vulnerabilities or [])
	]
	moat_weaknesses = [
		_clean(m.as_dict(), [
			"vulnerable_ip_or_chemistry", "ip_vulnerability_note",
			"clinical_strategy_weakness", "scale_or_manufacturing_bottleneck",
		])
		for m in (doc.moat_weaknesses or [])
	]
	trial_risks = [
		_clean(t.as_dict(), [
			"severity", "target_biology", "missing_biomarker", "trial_name_or_nct",
			"statistical_concern", "flawed_enrollment_criteria", "static_vs_dynamic_failure",
		])
		for t in (doc.trial_risks or [])
	]
	# `name` is reserved in child rows, so the competitor name is stored as `name1`
	# -> re-key back to `name` (same pattern as get_aacr_talk models).
	competitors = []
	for c in (doc.competitors or []):
		cd = c.as_dict()
		competitors.append(_clean(
			{"name": cd.get("name1"), "context": cd.get("context"), "sentiment": cd.get("sentiment")},
			["name", "context", "sentiment"],
		))

	# --- watchlist: re-expand the generic {kind, value} child rows into the
	#     Schema-B string-array fields, keyed by kind. ---
	watch_lists = {k: [] for k in WATCH_KINDS}
	for row in (doc.watchlist or []):
		if row.kind in watch_lists and row.value not in (None, ""):
			watch_lists[row.kind].append(row.value)

	counts = {
		"opportunities": len(opportunities),
		"vulnerabilities": len(vulnerabilities),
		"moat_weaknesses": len(moat_weaknesses),
		"trial_risks": len(trial_risks),
		"competitors": len(competitors),
		"watchlist": sum(len(v) for v in watch_lists.values()),
	}

	record = {
		"intel_id": doc.intel_id,
		"canonical_talk_uid": doc.intel_id,
		"talk_title": doc.talk_title,
		"session_title": doc.session_title,
		"speaker_name": doc.speaker_name,
		"institution": doc.institution,
		"a_talk_uid": doc.a_talk_uid,
		"presentation_type": doc.presentation_type,
		"data_maturity": doc.data_maturity,
		"sample_size_adequacy": doc.sample_size_adequacy,
		"follow_up_adequacy": doc.follow_up_adequacy,
		"crm_lead": doc.crm_lead,
		# the 5 Schema-B array keys the descriptor renders as tables
		"crispro_opportunity": opportunities,
		"vulnerability_identified": vulnerabilities,
		"competitive_moat_weakness": moat_weaknesses,
		"trial_dilution_risk": trial_risks,
		"cited_competitors": competitors,
		"counts": counts,
	}
	# the 7 watch string-array fields (rendered as labelled chip rows)
	record.update(watch_lists)
	return record


@frappe.whitelist()
def get_aacr_intel(talk_id):
	"""Return the competitive-intel record for a single talk, assembled from the
	AACR Intel doctype. `talk_id` is the lead's source_ref_id (= canonical_talk_uid
	for backfilled leads, or AACR-TRK-N for the dual-key aliased speaker leads).

	Returns None if no AACR Intel exists for this id (frontend treats null as
	"no competitive intel for this lead" and hides the section)."""
	if not talk_id or not frappe.db.exists("AACR Intel", talk_id):
		return None
	doc = frappe.get_doc("AACR Intel", talk_id)
	return _assemble(doc)


@frappe.whitelist()
def list_aacr_intel(search=None, presentation_type=None, has_opportunities=None, limit=50, start=0):
	"""Browsable competitive-intel corpus index. Opportunity-first ordering so the
	most actionable talks surface first. Child counts are computed with grouped
	queries (one per child table) rather than per-doc assembly, so the list stays
	cheap even across the full ~929-doc corpus."""
	limit = min(int(limit or 50), 200)
	start = int(start or 0)

	filters = {}
	if presentation_type:
		filters["presentation_type"] = presentation_type
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {
			"talk_title": ["like", like],
			"session_title": ["like", like],
			"speaker_name": ["like", like],
			"institution": ["like", like],
		}

	rows = frappe.get_all(
		"AACR Intel",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name as intel_id", "talk_title", "session_title", "speaker_name",
			"institution", "presentation_type", "data_maturity", "crm_lead",
		],
		limit_page_length=0,  # fetch all matching ids, then sort + page after counting
		order_by="speaker_name asc",
	)
	if not rows:
		return {"total": 0, "rows": []}

	ids = [r["intel_id"] for r in rows]

	# Child-row counts per parent via grouped COUNT(*) — one query per child table.
	def counts_by_parent(child_doctype):
		res = frappe.get_all(
			child_doctype,
			filters={"parent": ["in", ids], "parenttype": "AACR Intel"},
			fields=["parent", "count(name) as n"],
			group_by="parent",
		)
		return {r["parent"]: r["n"] for r in res}

	opp = counts_by_parent("AACR Intel Opportunity")
	vul = counts_by_parent("AACR Intel Vulnerability")
	moat = counts_by_parent("AACR Intel Moat Weakness")
	risk = counts_by_parent("AACR Intel Trial Risk")
	comp = counts_by_parent("AACR Intel Competitor")
	watch = counts_by_parent("AACR Intel Watch")

	for r in rows:
		i = r["intel_id"]
		r["n_opportunities"] = opp.get(i, 0)
		r["n_vulnerabilities"] = vul.get(i, 0)
		r["n_moat_weaknesses"] = moat.get(i, 0)
		r["n_trial_risks"] = risk.get(i, 0)
		r["n_competitors"] = comp.get(i, 0)
		r["n_watchlist"] = watch.get(i, 0)
		r["n_total"] = (
			r["n_opportunities"] + r["n_vulnerabilities"] + r["n_moat_weaknesses"]
			+ r["n_trial_risks"] + r["n_competitors"] + r["n_watchlist"]
		)

	# has_opportunities filter (post-count, since it depends on the grouped count)
	if has_opportunities in (True, "true", "1", 1):
		rows = [r for r in rows if r["n_opportunities"] > 0]

	# Opportunity-first sort: most opportunities, then richest overall, then name.
	rows.sort(key=lambda r: (-r["n_opportunities"], -r["n_total"], r["speaker_name"] or ""))

	total = len(rows)
	page = rows[start:start + limit]
	return {"total": total, "rows": page}


@frappe.whitelist()
def get_company_intel(company):
	"""Aggregate every competitive-intel mention of a company across the corpus:
	where it appears as a cited competitor, and where it appears on a watchlist
	(companies_to_monitor / assets_to_track). This is the honest bridge for leads
	whose person is not an AACR speaker but whose ORG is discussed in the corpus —
	no fabricated person->talk link.

	Runs server-side via the Frappe ORM (NOT the REST `like` filter layer), so it
	is unaffected by the host's broken HTTP filter encoding."""
	if not company:
		return None
	like = f"%{company}%"

	as_competitor = frappe.get_all(
		"AACR Intel Competitor",
		filters={"name1": ["like", like], "parenttype": "AACR Intel"},
		fields=["parent as intel_id", "name1 as name", "context", "sentiment"],
	)
	on_watchlist = frappe.get_all(
		"AACR Intel Watch",
		filters={
			"value": ["like", like],
			"kind": ["in", ["companies_to_monitor", "assets_to_track"]],
			"parenttype": "AACR Intel",
		},
		fields=["parent as intel_id", "kind", "value"],
	)

	# Distinct talks touched, with their human-readable titles.
	talk_ids = sorted({r["intel_id"] for r in as_competitor} | {r["intel_id"] for r in on_watchlist})
	talks = []
	if talk_ids:
		talks = frappe.get_all(
			"AACR Intel",
			filters={"name": ["in", talk_ids]},
			fields=["name as intel_id", "talk_title", "session_title", "speaker_name", "institution", "crm_lead"],
		)

	return {
		"company": company,
		"as_competitor": as_competitor,
		"on_watchlist": on_watchlist,
		"talks": talks,
		"counts": {
			"as_competitor": len(as_competitor),
			"on_watchlist": len(on_watchlist),
			"distinct_talks": len(talk_ids),
		},
	}


@frappe.whitelist(methods=["GET"], allow_guest=True)
def get_spa_boot():
	"""Return SPA boot (incl. csrf_token) when www/crm.py boot merge is stale on host."""
	from frappe.utils import cint, get_system_timezone

	try:
		from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
	except Exception:
		def is_fc_site():
			return False

	tz = {
		"system": get_system_timezone(),
		"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
		or get_system_timezone(),
	}
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/crm",
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"is_demo_site": frappe.conf.get("is_demo_site"),
			"is_fc_site": is_fc_site(),
			"timezone": tz,
			"time_zone": tz,
		}
	)
