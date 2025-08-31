import frappe
from frappe import _


SUPPORTED = {
	"email.draft",
	"email.draft_with_provider",
	"email.send",
	"email.link_provider_ids",
}


@frappe.whitelist()
def run(command: str, params: dict | None = None):
	"""Agent action router. Supported commands:

	- email.draft: { reference_doctype, reference_name, to, subject, html, cc?, bcc?, provider_thread_id? }
	- email.draft_with_provider: { reference_doctype, reference_name, to, subject, html, provider?, provider_message_id?, provider_thread_id?, cc?, bcc? }
	- email.send: { communication_name }
	- email.link_provider_ids: { communication_name, provider?, provider_message_id?, provider_thread_id? }
	"""
	if command not in SUPPORTED:
		frappe.throw(_(f"Unsupported command: {command}"))
	params = params or {}
	if command == "email.draft":
		return frappe.call(
			"crm.api.email.save_draft",
			reference_doctype=params.get("reference_doctype"),
			reference_name=params.get("reference_name"),
			to=params.get("to"),
			subject=params.get("subject"),
			html=params.get("html"),
			cc=params.get("cc"),
			bcc=params.get("bcc"),
			provider_thread_id=params.get("provider_thread_id"),
		)
	if command == "email.draft_with_provider":
		return frappe.call(
			"crm.api.email.save_draft_with_provider",
			reference_doctype=params.get("reference_doctype"),
			reference_name=params.get("reference_name"),
			to=params.get("to"),
			subject=params.get("subject"),
			html=params.get("html"),
			provider=params.get("provider"),
			provider_message_id=params.get("provider_message_id"),
			provider_thread_id=params.get("provider_thread_id"),
			cc=params.get("cc"),
			bcc=params.get("bcc"),
		)
	if command == "email.send":
		return frappe.call("crm.api.email.send", communication_name=params.get("communication_name"))
	if command == "email.link_provider_ids":
		return frappe.call(
			"crm.api.email.link_provider_ids",
			communication_name=params.get("communication_name"),
			provider=params.get("provider"),
			provider_message_id=params.get("provider_message_id"),
			provider_thread_id=params.get("provider_thread_id"),
		)
