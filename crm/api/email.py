import frappe
from frappe import _
from frappe.utils import cstr
from frappe import publish_realtime


@frappe.whitelist()
def get_inbox(doctype: str | None = None, docname: str | None = None, status: str | None = None, limit: int = 20):
	"""Return recent Communications linked to a doc or globally for CRM entities.

	Args:
		doctype: Optional filter for linked doctype
		docname: Optional filter for linked docname
		status: Optional Communication status filter
		limit: Max records to return
	"""
	filters = {"communication_type": ["in", ["Communication", "Comment"]]}
	if doctype and docname:
		filters.update({"reference_doctype": doctype, "reference_name": docname})
	else:
		filters.update({"reference_doctype": ["in", ["CRM Lead", "Contact", "CRM Organization"]]})
	if status:
		filters["status"] = status

	rows = frappe.get_all(
		"Communication",
		filters=filters,
		fields=[
			"name",
			"subject",
			"sender",
			"recipients",
			"communication_medium",
			"communication_type",
			"status",
			"reference_doctype",
			"reference_name",
			"provider",
			"provider_message_id",
			"provider_thread_id",
			"creation",
		],
		order_by="creation desc",
		limit=limit,
	)
	return rows


@frappe.whitelist()
def thread_context(communication: str | None = None, doctype: str | None = None, docname: str | None = None, limit: int = 50):
	"""Return thread context: list of Communications for a doc or by provider thread ID.

	Either pass a Communication name, or doctype+docname.
	"""
	filters: dict[str, object] = {}
	if communication:
		comm = frappe.get_doc("Communication", communication)
		provider_thread_id = comm.get("provider_thread_id")
		if provider_thread_id:
			filters["provider_thread_id"] = provider_thread_id
		else:
			filters.update(reference_doctype=comm.reference_doctype, reference_name=comm.reference_name)
	elif doctype and docname:
		filters.update(reference_doctype=doctype, reference_name=docname)
	else:
		raise_frappe("Pass communication or doctype+docname")

	rows = frappe.get_all(
		"Communication",
		filters=filters,
		fields=[
			"name",
			"content",
			"subject",
			"sender",
			"recipients",
			"communication_medium",
			"communication_type",
			"status",
			"reference_doctype",
			"reference_name",
			"provider",
			"provider_message_id",
			"provider_thread_id",
			"creation",
		],
		order_by="creation asc",
		limit=limit,
	)
	return rows


@frappe.whitelist()
def save_draft(reference_doctype: str, reference_name: str, to: str, subject: str, html: str, cc: str | None = None, bcc: str | None = None, provider_thread_id: str | None = None):
	"""Create a draft Communication linked to a CRM entity.

	Returns the Communication name.
	"""
	if not to or not subject or not html:
		raise_frappe("to, subject and html are required")

	comm = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"subject": subject,
			"sender": frappe.session.user,
			"recipients": to,
			"cc": cc,
			"bcc": bcc,
			"content": html,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"provider_thread_id": provider_thread_id,
			"status": "Draft",
		}
	)
	comm.insert()

	# Realtime notify for Human Inbox
	publish_realtime(
		"crm_email_draft_created",
		{
			"communication_name": comm.name,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"subject": subject,
			"sender": frappe.session.user,
		},
		user=frappe.session.user,
	)

	return comm.name


@frappe.whitelist()
def send(communication_name: str):
	"""Send a Communication via email using configured Email Account."""
	comm = frappe.get_doc("Communication", communication_name)
	if not comm.recipients:
		raise_frappe("Recipients are required")

	# Use frappe.sendmail for compatibility across versions
	recipients = [r.strip() for r in cstr(comm.recipients).split(",") if r.strip()]
	cc_list = [r.strip() for r in cstr(comm.cc or "").split(",") if r.strip()]
	bcc_list = [r.strip() for r in cstr(comm.bcc or "").split(",") if r.strip()]

	frappe.sendmail(
		recipients=recipients,
		subject=comm.subject,
		message=comm.content,
		cc=cc_list,
		bcc=bcc_list,
		reference_doctype=comm.reference_doctype,
		reference_name=comm.reference_name,
	)

	comm.db_set("status", "Sent")
	return {"ok": True}


@frappe.whitelist()
def link_provider_ids(communication_name: str, provider: str | None = None, provider_message_id: str | None = None, provider_thread_id: str | None = None):
	"""Attach external provider IDs to an existing Communication."""
	comm = frappe.get_doc("Communication", communication_name)
	updates: dict[str, object] = {}
	if provider:
		updates["provider"] = provider
	if provider_message_id:
		updates["provider_message_id"] = provider_message_id
	if provider_thread_id:
		updates["provider_thread_id"] = provider_thread_id
	if updates:
		comm.db_set(updates)
	return {"ok": True}


def raise_frappe(message: str):
	frappe.throw(_(message))
