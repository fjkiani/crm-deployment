import frappe
from frappe import _


SUPPORTED = {
	"email.triage",
	"email.draft_ai",
	"email.draft",
	"email.draft_with_provider",
	"email.send",
	"email.link_provider_ids",
	"email.resolve_reference",
	"email.find_by_provider_id",
}


@frappe.whitelist()
def run(command: str, params: dict | None = None):
	"""Agent action router. Supported commands:

	- email.triage: { communication_name }
	- email.draft_ai: { communication_name, tone?, include_context? }
	- email.draft: { reference_doctype, reference_name, to, subject, html, cc?, bcc?, provider_thread_id? }
	- email.draft_with_provider: { reference_doctype, reference_name, to, subject, html, provider?, provider_message_id?, provider_thread_id?, cc?, bcc? }
	- email.send: { communication_name }
	- email.link_provider_ids: { communication_name, provider?, provider_message_id?, provider_thread_id? }
	"""
	if command not in SUPPORTED:
		frappe.throw(_(f"Unsupported command: {command}"))
	params = params or {}
	if command == "email.triage":
		return frappe.call(
			"crm.api.email.triage_communication",
			communication_name=params.get("communication_name"),
		)
	if command == "email.draft_ai":
		return frappe.call(
			"crm.api.email.draft_ai_response",
			communication_name=params.get("communication_name"),
			tone=params.get("tone", "professional"),
			include_context=params.get("include_context", True),
		)
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
	if command == "email.resolve_reference":
		return frappe.call(
			"crm.api.email.resolve_reference",
			emails=params.get("emails"),
			in_reply_to=params.get("in_reply_to"),
		)
	if command == "email.find_by_provider_id":
		return frappe.call(
			"crm.api.email.find_communication_by_provider_id",
			provider_message_id=params.get("provider_message_id"),
			provider_thread_id=params.get("provider_thread_id"),
		)
