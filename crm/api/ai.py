import frappe
from frappe import _
from datetime import datetime, timedelta


@frappe.whitelist()
def get_counts(days: int = 7):
	"""Return simple AI/Email counts for dashboard.
	- drafts: Email Communications in Draft status
	- sent_today: Email Communications sent today
	- recent_total: total Email Communications in last N days
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

	return {
		"drafts": drafts,
		"sent_today": int(sent_today or 0),
		"recent_total": int(recent_total or 0),
		"window_days": days,
	}
