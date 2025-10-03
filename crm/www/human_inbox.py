import frappe
from frappe import _


def get_context(context):
	context.title = _("Human Inbox - AI Drafts")
	context.no_cache = 1

	# Filters from query params
	doctype = (frappe.form_dict.get("doctype") or "").strip()
	docname = (frappe.form_dict.get("docname") or "").strip()
	only_drafts = frappe.form_dict.get("only_drafts") in (1, "1", True, "true", "on")
	limit = frappe.utils.cint(frappe.form_dict.get("limit") or 50)
	if limit <= 0 or limit > 200:
		limit = 50

	filters = {
		"communication_type": "Communication",
		"communication_medium": "Email",
	}
	if doctype and docname:
		filters.update(reference_doctype=doctype, reference_name=docname)
	if only_drafts:
		filters.update(status="Draft")

	drafts = frappe.get_all(
		"Communication",
		filters=filters,
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
		limit=limit,
	)

	context.ai_drafts = drafts
	context.total_drafts = len(drafts)
	context.filter_doctype = doctype
	context.filter_docname = docname
	context.filter_only_drafts = only_drafts
	context.filter_limit = limit
