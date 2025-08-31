import frappe
from frappe import _


def get_context(context):
	context.title = _("Human Inbox")
	context.no_cache = 1
	# passthrough filters
	context.query_string = frappe.request.query_string.decode() if getattr(frappe, 'request', None) else ""
