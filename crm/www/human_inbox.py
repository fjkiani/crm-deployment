import frappe
from frappe import _


def _inbox_scope():
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

	user_email = frappe.session.user
	allowed_accounts = []
	try:
		allowed_accounts = frappe.get_all(
			"Email Account",
			filters={"owner": user_email},
			pluck="name",
		)
		more_accounts = frappe.get_all(
			"Email Account",
			filters={"email_id": user_email},
			pluck="name",
		)
		for account in more_accounts:
			if account not in allowed_accounts:
				allowed_accounts.append(account)
	except Exception:
		pass

	or_filters = []
	if not (doctype and docname):
		or_filters = [
			{"sender": user_email},
			{"recipients": ["like", f"%{user_email}%"]},
		]
		if allowed_accounts:
			filters["email_account"] = ["in", allowed_accounts]

	fields = [
		"name",
		"subject",
		"sender",
		"recipients",
		"content",
		"status",
		"sent_or_received",
		"reference_doctype",
		"reference_name",
		"creation",
	]

	return doctype, docname, only_drafts, limit, filters, or_filters, fields


def get_context(context):
	context.title = _("Human Inbox - AI Drafts")
	context.no_cache = 1

	doctype, docname, only_drafts, limit, filters, or_filters, fields = _inbox_scope()

	triage_items = []
	if not only_drafts:
		triage_filters = dict(filters)
		triage_filters.update(
			{
				"sent_or_received": "Received",
				"status": ["not in", ["Draft", "Sent"]],
			}
		)
		triage_items = frappe.get_all(
			"Communication",
			filters=triage_filters,
			or_filters=or_filters,
			fields=fields,
			order_by="creation desc",
			limit=limit,
		)

	draft_filters = dict(filters)
	draft_filters["status"] = "Draft"
	ai_drafts = frappe.get_all(
		"Communication",
		filters=draft_filters,
		or_filters=or_filters,
		fields=fields,
		order_by="creation desc",
		limit=limit,
	)

	context.drafts = triage_items
	context.ai_drafts = ai_drafts
	context.total_drafts = len(triage_items) + len(ai_drafts)
	context.filter_doctype = doctype
	context.filter_docname = docname
	context.filter_only_drafts = only_drafts
	context.filter_limit = limit
