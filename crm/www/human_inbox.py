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

	# Restrict visibility per user unless a specific doc context is provided
	# Show only communications tied to the current user's identity or mailbox
	user_email = frappe.session.user
	allowed_accounts = []
	try:
		# Email Accounts created by this user
		allowed_accounts = frappe.get_all(
			"Email Account",
			filters={"owner": user_email},
			pluck="name",
		)
		# Also include accounts whose login/email match the user (best effort)
		more_accounts = frappe.get_all(
			"Email Account",
			filters={"email_id": user_email},
			pluck="name",
		)
		for a in more_accounts:
			if a not in allowed_accounts:
				allowed_accounts.append(a)
	except Exception:
		pass

	or_filters = []
	if not (doctype and docname):
		# Sender is current user (outbound/drafts) OR recipients include current user's address (inbound)
		or_filters = [
			{"sender": user_email},
			{"recipients": ["like", f"%{user_email}%"]},
		]
		# If we know the user's Email Accounts, restrict to those mailboxes as well
		if allowed_accounts:
			filters["email_account"] = ["in", allowed_accounts]

	drafts = frappe.get_all(
		"Communication",
		filters=filters,
		or_filters=or_filters,
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
