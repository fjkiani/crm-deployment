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
