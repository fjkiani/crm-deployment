import frappe
from frappe import _


def get_context(context):
	context.title = _("Human Inbox - AI Drafts")
	context.no_cache = 1

	# Show recent email communications for review (regardless of status)
	drafts = frappe.get_all(
		"Communication",
		filters={
			"communication_type": "Communication",
			"communication_medium": "Email",
		},
		fields=[
			"name",
			"subject",
			"sender",
			"recipients",
			"content",
			"status",
			"reference_doctype",
			"reference_name",
			"creation",
		],
		order_by="creation desc",
		limit=50,
	)

	context.ai_drafts = drafts
	context.total_drafts = len(drafts)
