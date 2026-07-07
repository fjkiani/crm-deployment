# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt
"""
AACR session navigation.

Talks are keyed `<session_slug>::<speaker_key>::<n>` and AACR Talk.session_title
already stores the slug. These APIs let the frontend browse the conference by
session:

  list_sessions()                     -> every session slug + its talk/lead counts
  list_talks_by_session(session_slug) -> talks in one session + linked-lead info

Malformed talk_ids (no `::`) are grouped under session_slug = the whole id and
still returned, so nothing is silently dropped.
"""

import frappe


def _slug_expr():
	# session_title stores the slug; fall back to substring of talk_id when blank.
	return "COALESCE(NULLIF(t.session_title, ''), SUBSTRING_INDEX(t.name, '::', 1))"


@frappe.whitelist()
def list_sessions(search: str = None, limit: int = 0, start: int = 0) -> dict:
	"""All sessions with talk counts + linked-lead counts, most-populated first."""
	slug = _slug_expr()
	where, values = "", {}
	if search:
		where = f"WHERE {slug} LIKE %(s)s OR t.session_title LIKE %(s)s"
		values["s"] = f"%{search}%"

	lim = ""
	if int(limit or 0):
		lim = "LIMIT %(pl)s OFFSET %(st)s"
		values["pl"] = int(limit)
		values["st"] = int(start or 0)

	rows = frappe.db.sql(
		f"""
		SELECT {slug} AS session_slug,
		       COUNT(DISTINCT t.name) AS n_talks,
		       COUNT(DISTINCT l.name) AS n_leads,
		       MAX(t.session_title) AS session_title
		FROM `tabAACR Talk` t
		LEFT JOIN `tabCRM Lead` l ON l.source_ref_id = t.name
		{where}
		GROUP BY session_slug
		ORDER BY n_talks DESC, session_slug ASC
		{lim}
		""",
		values, as_dict=True,
	)
	total = frappe.db.sql(
		f"SELECT COUNT(*) FROM (SELECT {slug} AS s FROM `tabAACR Talk` t "
		f"{where} GROUP BY s) x", values,
	)[0][0]
	return {"total": total, "sessions": rows}


@frappe.whitelist()
def list_talks_by_session(session_slug: str) -> dict:
	"""All talks in one session, each with its linked CRM Lead (if any).

	Slug is matched against session_title first, then against the
	leading `::`-delimited segment of the talk id (covers malformed ids)."""
	if not session_slug:
		return {"session_slug": session_slug, "n_talks": 0, "talks": []}

	slug = _slug_expr()
	rows = frappe.db.sql(
		f"""
		SELECT t.name AS talk_id, t.talk_title, t.session_title,
		       t.speaker_name, t.clinical_stage, t.novelty_flag,
		       l.name AS lead_name, l.lead_name AS lead_person, l.organization,
		       l.email, l.tier, l.lead_score, l.priority_rank,
		       (i.name IS NOT NULL) AS has_competitive_intel
		FROM `tabAACR Talk` t
		LEFT JOIN `tabCRM Lead` l ON l.source_ref_id = t.name
		LEFT JOIN `tabAACR Intel` i ON i.a_talk_uid = t.name
		WHERE {slug} = %(slug)s
		ORDER BY t.name ASC
		""",
		{"slug": session_slug}, as_dict=True,
	)
	return {
		"session_slug": session_slug,
		"session_title": rows[0]["session_title"] if rows else session_slug,
		"n_talks": len(rows),
		"n_leads": sum(1 for r in rows if r.get("lead_name")),
		"talks": rows,
	}


# ---------------------------------------------------------------------------
# AACR 2026 intelligence layer (abstract enrichment + axis dashboard)
# Static intelligence corpus bundled at crm/aacr_data/*.json, loaded once and
# cached in-process. No live-DB migration; deploys atomically with the app.
# ---------------------------------------------------------------------------

import json
import os
from functools import lru_cache


def _aacr_data_dir():
	return os.path.join(frappe.get_app_path("crm"), "aacr_data")


@lru_cache(maxsize=8)
def _load_aacr_json(filename: str):
	"""Load and cache a bundled AACR data file. Returns {} on any failure."""
	path = os.path.join(_aacr_data_dir(), filename)
	try:
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		frappe.log_error(f"AACR data load failed: {filename}", "session_nav")
		return {}


@frappe.whitelist()
def talk_detail(talk_name: str) -> dict:
	"""Full talk record + abstract enrichment + linked lead + competitive intel.

	Powers the abstract detail panel. Joins the live AACR Talk doc with the
	bundled schema_a enrichment (key_findings, open_questions, readouts, etc.),
	the linked CRM Lead, and AACR Intel."""
	if not talk_name or not frappe.db.exists("AACR Talk", talk_name):
		return {"talk_name": talk_name, "found": False}

	talk = frappe.get_doc("AACR Talk", talk_name).as_dict()

	# targets child: gene_or_protein (+ modality/alteration context)
	def _targets(rows):
		out = []
		for r in rows or []:
			g = (r.get("gene_or_protein") or "").strip()
			if g:
				extra = " / ".join(x for x in [r.get("alteration"), r.get("modality")] if x)
				out.append(f"{g} ({extra})" if extra else g)
		return out

	# biomarkers child: name (+ type)
	def _biomarkers(rows):
		out = []
		for r in rows or []:
			n = (r.get("name") or "").strip()
			if n:
				out.append(f"{n} [{r.get('type')}]" if r.get("type") else n)
		return out

	lead = frappe.db.get_value(
		"CRM Lead", {"source_ref_id": talk_name},
		["name", "lead_name", "organization", "email", "tier",
		 "lead_score", "priority_rank", "status"], as_dict=True,
	)

	# AACR Intel header fields (competitive-intel child tables live separately)
	intel = None
	if frappe.db.exists("DocType", "AACR Intel"):
		intel = frappe.db.get_value(
			"AACR Intel", {"a_talk_uid": talk_name},
			["name", "presentation_type", "data_maturity",
			 "sample_size_adequacy", "follow_up_adequacy"],
			as_dict=True,
		)

	enrichment = _load_aacr_json("talk_enrichment.json").get(talk_name, {})
	axes = _load_aacr_json("talk_axis_map.json").get(talk_name, [])

	return {
		"talk_name": talk_name,
		"found": True,
		"talk_title": talk.get("talk_title"),
		"session_title": talk.get("session_title"),
		"speaker_name": talk.get("speaker_name"),
		"speaker_affiliation": talk.get("speaker_affiliation"),
		"speaker_role": talk.get("speaker_role"),
		"clinical_stage": talk.get("clinical_stage"),
		"novelty_flag": talk.get("novelty_flag"),
		"moa_summary": talk.get("moa_summary"),
		"targets": _targets(talk.get("targets")),
		"biomarkers": _biomarkers(talk.get("biomarkers")),
		"crispro_axes": axes,
		"enrichment": enrichment,
		"lead": lead,
		"intel": intel,
	}


@frappe.whitelist()
def axis_dashboard() -> dict:
	"""Aggregate AACR 2026 intelligence for the dashboard.

	Returns the 10-axis intelligence, competitive landscape, and track-B
	summary. Static corpus-level analytics (not per-lead)."""
	axis = _load_aacr_json("axis_intelligence.json")
	landscape = _load_aacr_json("competitive_landscape.json")
	track_b = _load_aacr_json("track_b_intelligence.json")

	axes = axis.get("axes", {})
	gap = axis.get("gap_analysis", [])

	# session-talks per axis from the bundled talk->axis map, then how many of
	# those talks have a linked live CRM Lead, so dashboard cards can link out.
	talk_axis = _load_aacr_json("talk_axis_map.json")  # {talk_id: [axis, ...]}
	axis_talk_ids = {}
	for tid, axs in talk_axis.items():
		for a in axs:
			axis_talk_ids.setdefault(a, []).append(tid)

	axis_lead_counts, axis_talk_counts = {}, {}
	linked = set()
	try:
		rows = frappe.db.sql(
			"SELECT source_ref_id FROM `tabCRM Lead` WHERE source_ref_id IS NOT NULL",
			as_dict=True,
		)
		linked = {r["source_ref_id"] for r in rows}
	except Exception:
		linked = set()
	for a, tids in axis_talk_ids.items():
		axis_talk_counts[a] = len(tids)
		axis_lead_counts[a] = sum(1 for t in tids if t in linked)

	return {
		"generated": axis.get("generated"),
		"corpus_size": axis.get("corpus_size"),
		"llm_enriched": axis.get("llm_enriched"),
		"axes": axes,
		"gap_analysis": gap,
		"axis_lead_counts": axis_lead_counts,
		"axis_talk_counts": axis_talk_counts,
		"companies": landscape.get("companies", []),
		"companies_identified": landscape.get("companies_identified"),
		"top_opportunities": (track_b or {}).get("top_opportunities", []),
		"cancer_type_gaps": (track_b or {}).get("cancer_type_gaps", {}),
		"white_space": (track_b or {}).get("white_space_deep_dive", {}),
	}


@frappe.whitelist()
def talks_by_axis(axis: str, limit: int = 50) -> dict:
	"""Session-talks + linked leads for a CrisPRO axis (dashboard drill-down).

	Enables slug navigation: axis card -> the talks/leads on that axis ->
	individual Lead. Matched via AACR Intel.crispro_axis."""
	if not axis:
		return {"axis": axis, "n": 0, "talks": []}

	# talk_ids on this axis from the bundled map
	talk_axis = _load_aacr_json("talk_axis_map.json")
	tids = [t for t, axs in talk_axis.items() if axis in (axs or [])]
	if not tids:
		return {"axis": axis, "n": 0, "n_leads": 0, "talks": []}
	tids = tids[: int(limit) * 3]  # cap the IN-list; final slice after sort

	rows = frappe.db.sql(
		"""
		SELECT t.name AS talk_id, t.talk_title, t.speaker_name,
		       t.session_title, t.clinical_stage, t.novelty_flag,
		       l.name AS lead_name, l.lead_name AS lead_person,
		       l.organization, l.email, l.tier, l.lead_score
		FROM `tabAACR Talk` t
		LEFT JOIN `tabCRM Lead` l ON l.source_ref_id = t.name
		WHERE t.name IN %(tids)s
		ORDER BY (l.name IS NULL) ASC, l.lead_score DESC, t.name ASC
		LIMIT %(lim)s
		""",
		{"tids": tids, "lim": int(limit)}, as_dict=True,
	)
	return {
		"axis": axis,
		"n": len(rows),
		"n_leads": sum(1 for r in rows if r.get("lead_name")),
		"talks": rows,
	}
