"""Directory read APIs for the repurposed Contacts + Organizations views.

Both stock doctypes (CRM Organization / core Contact) are empty or disconnected
from the Brenus data model. The real people/companies live in Lead Prospect
(916 rows) and the 10 curated industry engagements. These read-only aggregations
surface that real data without touching schema or the empty stock doctypes.
"""

import json
import os
import re
from collections import OrderedDict

import frappe

# ---------------------------------------------------------------------------
# engagement KB (bundled) — companies + trial/target metadata
# ---------------------------------------------------------------------------

_ENGAGEMENTS_CACHE = None


def _load_engagements():
	global _ENGAGEMENTS_CACHE
	if _ENGAGEMENTS_CACHE is not None:
		return _ENGAGEMENTS_CACHE
	path = os.path.join(
		os.path.dirname(os.path.dirname(__file__)), "industry_data", "engagements.json"
	)
	try:
		with open(path, "r", encoding="utf-8") as fh:
			_ENGAGEMENTS_CACHE = json.load(fh)
	except Exception:
		_ENGAGEMENTS_CACHE = []
	return _ENGAGEMENTS_CACHE


def _norm(s):
	"""Normalize an institution/company string for loose matching."""
	if not s:
		return ""
	s = s.lower()
	s = re.sub(r"[^a-z0-9]+", " ", s).strip()
	return s


# ---------------------------------------------------------------------------
# Contacts: derived from Lead Prospect (pi_name / pi_email / institution)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def list_contacts(search=None, tier=None, outreach_status=None, start=0, page_length=50):
	"""Real KOL / industry contacts, sourced from Lead Prospect.

	Returns paginated rows with prospect linkage + a needs_backfill flag for
	placeholder (.invalid) or missing emails. Rows with unknown pi_name are
	skipped so the directory stays meaningful.
	"""
	start = int(start or 0)
	page_length = min(int(page_length or 50), 200)

	filters = [["pi_name", "not in", ["unknown", "Unknown", ""]]]
	if tier:
		filters.append(["tier", "=", tier])
	if outreach_status:
		filters.append(["outreach_status", "=", outreach_status])

	or_filters = None
	if search:
		s = f"%{search}%"
		or_filters = [
			["pi_name", "like", s],
			["institution", "like", s],
			["pi_email", "like", s],
		]

	total = frappe.db.count("Lead Prospect", filters=filters)

	rows = frappe.get_all(
		"Lead Prospect",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"pi_name",
			"pi_email",
			"institution",
			"cancer_type",
			"tier",
			"lead_score",
			"outreach_status",
			"source",
		],
		order_by="lead_score desc, pi_name asc",
		start=start,
		page_length=page_length,
	)

	# map engagement companies to slugs for deep-linking contacts to an engagement
	eng_by_norm = {
		_norm(e.get("front_matter", {}).get("company")): e.get("slug")
		for e in _load_engagements()
	}

	out = []
	for r in rows:
		email = (r.get("pi_email") or "").strip()
		needs_backfill = (not email) or email.endswith(".invalid")
		inst_norm = _norm(r.get("institution"))
		eng_slug = eng_by_norm.get(inst_norm)
		out.append(
			{
				"prospect": r["name"],
				"name": r.get("pi_name"),
				"email": email or None,
				"institution": r.get("institution"),
				"cancer_type": r.get("cancer_type") or None,
				"tier": r.get("tier"),
				"lead_score": r.get("lead_score"),
				"outreach_status": r.get("outreach_status"),
				"source": r.get("source"),
				"needs_backfill": needs_backfill,
				"engagement_slug": eng_slug,
			}
		)

	return {
		"rows": out,
		"total": total,
		"start": start,
		"page_length": page_length,
		"returned": len(out),
	}


@frappe.whitelist()
def contact_facets():
	"""Distinct tier + outreach_status values for filter dropdowns."""
	tiers = frappe.db.sql(
		"SELECT DISTINCT tier FROM `tabLead Prospect` WHERE tier IS NOT NULL ORDER BY tier",
		as_dict=False,
	)
	statuses = frappe.db.sql(
		"SELECT DISTINCT outreach_status FROM `tabLead Prospect` "
		"WHERE outreach_status IS NOT NULL ORDER BY outreach_status",
		as_dict=False,
	)
	return {
		"tiers": [t[0] for t in tiers if t[0]],
		"outreach_statuses": [s[0] for s in statuses if s[0]],
	}


# ---------------------------------------------------------------------------
# Organizations: engagement companies (curated) + top prospect institutions
# ---------------------------------------------------------------------------


@frappe.whitelist()
def list_organizations(search=None, limit_institutions=40):
	"""Real organizations for the Brenus workflow.

	Two groups, both derived from live data:
	  1. engagements  — the 10 curated industry target companies, with
	     trial / target / posture / rank metadata + a deep link to /industry/:slug.
	  2. institutions — distinct Lead Prospect institutions ranked by prospect
	     count (top N), so the view is a useful directory, not a 700-row dump.
	Engagement companies are de-duplicated out of the institutions list.
	"""
	limit_institutions = min(int(limit_institutions or 40), 200)

	# --- group 1: engagement companies ---
	engagements = []
	eng_norms = set()
	for e in _load_engagements():
		fm = e.get("front_matter", {})
		company = fm.get("company")
		if not company:
			continue
		eng_norms.add(_norm(company))
		try:
			rank = int(fm.get("outreach_priority_rank"))
		except (TypeError, ValueError):
			rank = 999
		engagements.append(
			{
				"slug": e.get("slug"),
				"company": company,
				"lead_drug": fm.get("lead_drug"),
				"target": fm.get("target"),
				"trial": fm.get("trial"),
				"phase": fm.get("phase"),
				"rank": rank,
				"claim_posture": fm.get("claim_posture"),
				"primary_contact": fm.get("primary_contact"),
			}
		)
	engagements.sort(key=lambda x: x["rank"])

	# --- group 2: prospect institutions by count ---
	inst_rows = frappe.db.sql(
		"""
		SELECT institution, COUNT(*) AS n
		FROM `tabLead Prospect`
		WHERE institution IS NOT NULL
		  AND institution NOT IN ('unknown', 'Unknown', '')
		GROUP BY institution
		ORDER BY n DESC
		""",
		as_dict=True,
	)

	institutions = []
	for row in inst_rows:
		inst = row["institution"]
		if _norm(inst) in eng_norms:
			continue  # already represented as a curated engagement company
		if search and search.lower() not in inst.lower():
			continue
		institutions.append({"institution": inst, "prospect_count": row["n"]})

	total_institutions = len(institutions)
	institutions = institutions[:limit_institutions]

	if search:
		engagements = [e for e in engagements if search.lower() in (e["company"] or "").lower()]

	return {
		"engagements": engagements,
		"institutions": institutions,
		"engagement_count": len(engagements),
		"institution_count_total": total_institutions,
		"institution_count_shown": len(institutions),
	}
