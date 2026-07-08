import json

import frappe
from frappe import _
from datetime import datetime, timedelta


@frappe.whitelist()
def get_counts(days: int = 7):
	"""Return simple AI/Email counts for dashboard.
	- drafts: Email Communications in Draft status
	- sent_today: Email Communications sent today
	- recent_total: total Email Communications in last N days
	- last_eaia_run: last EAIA ping timestamp if recorded
	"""
	# HTTP passes params as strings; coerce so timedelta doesn't raise TypeError
	try:
		days = int(days)
	except (TypeError, ValueError):
		days = 7
	now = frappe.utils.now_datetime()
	start_day = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
	today = now.strftime("%Y-%m-%d")

	def _count(filters):
		return frappe.db.count("Communication", filters=filters)

	# Drafts (comm type=Communication, medium=Email)
	drafts = _count({
		"communication_type": "Communication",
		"communication_medium": "Email",
		"status": "Draft",
	})

	# Sent today
	sent_today = frappe.db.sql(
		"""
		select count(*) from `tabCommunication`
		where communication_type='Communication'
		and communication_medium='Email'
		and status='Sent'
		and date(creation)=%s
		""",
		(today,), as_dict=False
	)[0][0]

	# Recent total (last N days)
	recent_total = frappe.db.sql(
		"""
		select count(*) from `tabCommunication`
		where communication_type='Communication'
		and communication_medium='Email'
		and creation >= %s
		""",
		(start_day,), as_dict=False
	)[0][0]

	last_run = frappe.cache().get_value("eaia:last_run") or frappe.conf.get("eaia_last_run")

	return {
		"drafts": drafts,
		"sent_today": int(sent_today or 0),
		"recent_total": int(recent_total or 0),
		"window_days": days,
		"last_eaia_run": last_run,
	}


@frappe.whitelist()
def ping_eaia():
	"""Record EAIA last-run timestamp for display on the dashboard widget."""
	ts = frappe.utils.now()
	frappe.cache().set_value("eaia:last_run", ts)
	return {"ok": True, "ts": ts}


@frappe.whitelist()
def get_pipeline_analytics():
	"""Whitelisted, frontend-callable pipeline analytics.

	Self-contained (queries live CRM data only). Returns a dict of:
	  - funnel: CRM Lead status -> count
	  - frameworks: outreach framework A/B counts
	  - metrics: totals + enrichment coverage

	NOTE: mcp_server.get_pipeline_analytics exists but is an @mcp.tool()
	(MCP protocol only, not @frappe.whitelist), so the frontend cannot call
	it. This wrapper exposes the same computation over REST as a dict.
	"""
	try:
		status_counts = frappe.db.sql(
			"""
			SELECT status, count(*) as count
			FROM `tabCRM Lead`
			GROUP BY status
			""",
			as_dict=True,
		)
		funnel = {row["status"] or "Unknown": row["count"] for row in status_counts}

		leads = frappe.get_all("CRM Lead", fields=["name", "additional_data"])
		frameworks = {"challenger": 0, "pas": 0, "aida": 0, "unknown": 0}
		total_enriched = 0
		total_entangled = 0
		total_vulture = 0

		for l in leads:
			if not l.additional_data:
				continue
			try:
				data = json.loads(l.additional_data)
			except Exception:
				continue
			if "score" in data or "signals" in data:
				total_enriched += 1
			fw = data.get("framework") or data.get("sequence_framework")
			if fw:
				fw = str(fw).lower()
				frameworks[fw if fw in frameworks else "unknown"] += 1
			if data.get("entangled"):
				total_entangled += 1
			if data.get("vulture_event_detected"):
				total_vulture += 1

		total = len(leads)
		metrics = {
			"total_leads": total,
			"total_enriched": total_enriched,
			"enrichment_coverage": round((total_enriched / total * 100), 1) if total else 0,
			"total_entangled": total_entangled,
			"total_vulture_events": total_vulture,
		}
		return {"funnel": funnel, "frameworks": frameworks, "metrics": metrics}
	except Exception as e:
		frappe.log_error(f"get_pipeline_analytics error: {e}")
		return {"funnel": {}, "frameworks": {}, "metrics": {}, "error": str(e)}
