import frappe
from frappe import _

def get_context(context):
	context.title = _("Nyx Command Center")
	context.no_cache = 1
	# We can inject agent URL or status here
	context.agent_status = "Active"
