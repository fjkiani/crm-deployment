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
