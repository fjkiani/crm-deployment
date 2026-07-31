import json

import frappe
from frappe import _

from crm.api.doc import get_assigned_users
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user


def validate(doc, method):
	if doc.type == "Incoming" and doc.get("from"):
		name, doctype = get_lead_or_deal_from_number(doc.get("from"))
		doc.reference_doctype = doctype
		doc.reference_name = name


def on_update(doc, method):
	frappe.publish_realtime(
		"whatsapp_message",
		{
			"reference_doctype": doc.reference_doctype,
			"reference_name": doc.reference_name,
		},
	)

	notify_agent(doc)


def notify_agent(doc):
	if doc.type == "Incoming":
		doctype = doc.reference_doctype
		if doctype.startswith("CRM "):
			doctype = doctype[4:].lower()
		notification_text = f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{ _('You') }</span>
                <span>{ _('received a whatsapp message in {0}').format(doctype) }</span>
                <span class="font-medium text-ink-gray-9">{ doc.reference_name }</span>
            </div>
        """
		assigned_users = get_assigned_users(doc.reference_doctype, doc.reference_name)
		for user in assigned_users:
			notify_user(
				{
					"owner": doc.owner,
					"assigned_to": user,
					"notification_type": "WhatsApp",
					"message": doc.message,
					"notification_text": notification_text,
					"reference_doctype": "WhatsApp Message",
					"reference_docname": doc.name,
					"redirect_to_doctype": doc.reference_doctype,
					"redirect_to_docname": doc.reference_name,
				}
			)


def get_lead_or_deal_from_number(number):
	"""Get lead/deal from the given number."""

	def find_record(doctype, mobile_no, where=""):
		mobile_no = parse_mobile_no(mobile_no)

		query = f"""
            SELECT name, mobile_no
            FROM `tab{doctype}`
            WHERE CONCAT('+', REGEXP_REPLACE(mobile_no, '[^0-9]', '')) = {mobile_no}
        """

		data = frappe.db.sql(query + where, as_dict=True)
		return data[0].name if data else None

	doctype = "CRM Deal"

	doc = find_record(doctype, number) or None
	if not doc:
		doctype = "CRM Lead"
		doc = find_record(doctype, number, "AND converted is not True")
		if not doc:
			doc = find_record(doctype, number)

	return doc, doctype


def parse_mobile_no(mobile_no: str):
	"""Parse mobile number to remove spaces, brackets, etc.
	>>> parse_mobile_no("+91 (766) 667 6666")
	... "+917666676666"
	"""
	return "".join([c for c in mobile_no if c.isdigit() or c == "+"])


@frappe.whitelist()
def is_whatsapp_enabled():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	return frappe.get_cached_value("WhatsApp Settings", "WhatsApp Settings", "enabled")


@frappe.whitelist()
def is_whatsapp_installed():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	return True


@frappe.whitelist()
def get_whatsapp_messages(reference_doctype, reference_name):
	# twilio integration app is not compatible with crm app
	# crm has its own twilio integration in built
	if "twilio_integration" in frappe.get_installed_apps():
		return []
	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []
	messages = []

	if reference_doctype == "CRM Deal":
		lead = frappe.db.get_value(reference_doctype, reference_name, "lead")
		if lead:
			messages = frappe.get_all(
				"WhatsApp Message",
				filters={
					"reference_doctype": "CRM Lead",
					"reference_name": lead,
				},
				fields=[
					"name",
					"type",
					"to",
					"from",
					"content_type",
					"message_type",
					"attach",
					"template",
					"use_template",
					"message_id",
					"is_reply",
					"reply_to_message_id",
					"creation",
					"message",
					"status",
					"reference_doctype",
					"reference_name",
					"template_parameters",
					"template_header_parameters",
				],
			)

	messages += frappe.get_all(
		"WhatsApp Message",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		fields=[
			"name",
			"type",
			"to",
			"from",
			"content_type",
			"message_type",
			"attach",
			"template",
			"use_template",
			"message_id",
			"is_reply",
			"reply_to_message_id",
			"creation",
			"message",
			"status",
			"reference_doctype",
			"reference_name",
			"template_parameters",
			"template_header_parameters",
		],
	)

	# Filter messages to get only Template messages
	template_messages = [message for message in messages if message["message_type"] == "Template"]

	# Iterate through template messages
	for template_message in template_messages:
		# Find the template that this message is using
		template = frappe.get_doc("WhatsApp Templates", template_message["template"])

		# If the template is found, add the template details to the template message
		if template:
			template_message["template_name"] = template.template_name
			if template_message["template_parameters"]:
				parameters = json.loads(template_message["template_parameters"])
				template.template = parse_template_parameters(template.template, parameters)

			template_message["template"] = template.template
			if template_message["template_header_parameters"]:
				header_parameters = json.loads(template_message["template_header_parameters"])
				template.header = parse_template_parameters(template.header, header_parameters)
			template_message["header"] = template.header
			template_message["footer"] = template.footer

	# Filter messages to get only reaction messages
	reaction_messages = [message for message in messages if message["content_type"] == "reaction"]

	# Iterate through reaction messages
	for reaction_message in reaction_messages:
		# Find the message that this reaction is reacting to
		reacted_message = next(
			(m for m in messages if m["message_id"] == reaction_message["reply_to_message_id"]),
			None,
		)

		# If the reacted message is found, add the reaction to it
		if reacted_message:
			reacted_message["reaction"] = reaction_message["message"]

	for message in messages:
		from_name = get_from_name(message) if message["from"] else _("You")
		message["from_name"] = from_name
	# Filter messages to get only replies
	reply_messages = [message for message in messages if message["is_reply"]]

	# Iterate through reply messages
	for reply_message in reply_messages:
		# Find the message that this message is replying to
		replied_message = next(
			(m for m in messages if m["message_id"] == reply_message["reply_to_message_id"]),
			None,
		)

		# If the replied message is found, add the reply details to the reply message
		from_name = get_from_name(reply_message) if replied_message["from"] else _("You")
		if replied_message:
			message = replied_message["message"]
			if replied_message["message_type"] == "Template":
				message = replied_message["template"]
			reply_message["reply_message"] = message
			reply_message["header"] = replied_message.get("header") or ""
			reply_message["footer"] = replied_message.get("footer") or ""
			reply_message["reply_to"] = replied_message["name"]
			reply_message["reply_to_type"] = replied_message["type"]
			reply_message["reply_to_from"] = from_name

	return [message for message in messages if message["content_type"] != "reaction"]


@frappe.whitelist()
def create_whatsapp_message(
	reference_doctype,
	reference_name,
	message,
	to,
	attach,
	reply_to,
	content_type="text",
):
	doc = frappe.new_doc("WhatsApp Message")

	if reply_to:
		reply_doc = frappe.get_doc("WhatsApp Message", reply_to)
		doc.update(
			{
				"is_reply": True,
				"reply_to_message_id": reply_doc.message_id,
			}
		)

	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message": message or attach,
			"to": to,
			"attach": attach,
			"content_type": content_type,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def send_whatsapp_template(reference_doctype, reference_name, template, to):
	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message_type": "Template",
			"message": "Template message",
			"content_type": "text",
			"use_template": True,
			"template": template,
			"to": to,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def react_on_whatsapp_message(emoji, reply_to_name):
	reply_to_doc = frappe.get_doc("WhatsApp Message", reply_to_name)
	to = reply_to_doc.type == "Incoming" and reply_to_doc.get("from") or reply_to_doc.to
	doc = frappe.new_doc("WhatsApp Message")
	doc.update(
		{
			"reference_doctype": reply_to_doc.reference_doctype,
			"reference_name": reply_to_doc.reference_name,
			"message": emoji,
			"to": to,
			"reply_to_message_id": reply_to_doc.message_id,
			"content_type": "reaction",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def parse_template_parameters(string, parameters):
	for i, parameter in enumerate(parameters, start=1):
		placeholder = "{{" + str(i) + "}}"
		string = string.replace(placeholder, parameter)

	return string


def get_from_name(message):
	doc = frappe.get_doc(message["reference_doctype"], message["reference_name"])
	from_name = ""
	if message["reference_doctype"] == "CRM Deal":
		if doc.get("contacts"):
			for c in doc.get("contacts"):
				if c.is_primary:
					from_name = c.full_name or c.mobile_no
					break
		else:
			from_name = doc.get("lead_name")
	else:
		from_name = " ".join(filter(None, [doc.get("first_name"), doc.get("last_name")]))
	return from_name

@frappe.whitelist()
def whatsapp_health():
	"""Honest WhatsApp health card for the 360 dashboard.

	Never silent-fails: reports installed/enabled explicitly so the UI and agents
	show 'disabled' rather than a hidden no-op. Live truth: the WhatsApp app is
	NOT installed on alpha-crm, so this returns installed=False, enabled=False.
	"""
	installed = bool(is_whatsapp_installed())
	enabled = bool(is_whatsapp_enabled()) if installed else False
	template_count = 0
	if installed and frappe.db.exists("DocType", "WhatsApp Message Template"):
		try:
			template_count = frappe.db.count("WhatsApp Message Template")
		except Exception:
			template_count = 0
	return {
		"installed": installed,
		"enabled": enabled,
		"template_count": template_count,
		"status": "ready" if (installed and enabled) else ("installed_disabled" if installed else "not_installed"),
	}


_PLACEHOLDER_PHONES = ("", "+10000000000", "+15555555555", "0000000000")


def assert_deliverable_phone(phone):
	"""Block a WhatsApp/Call send to a missing or placeholder phone number.

	Parallels email.assert_deliverable: a seeded prospect with no verified phone
	must never be stamped as contacted. Fail loudly so the operator backfills.
	"""
	p = (phone or "").strip()
	digits = "".join(ch for ch in p if ch.isdigit())
	if not p or p in _PLACEHOLDER_PHONES or len(digits) < 7:
		frappe.throw(
			_("Refusing to send WhatsApp: missing/placeholder phone number '{0}'. "
			  "Backfill a verified phone on the contact first.").format(phone or "(empty)")
		)
	return True


@frappe.whitelist()
def draft_sequence_whatsapp(task_name, instance_name=None, body=None):
	"""Draft (NOT send) a WhatsApp message for a sequence step.

	Gated on WhatsApp enabled AND a deliverable phone. Returns an honest refusal
	when disabled/not-installed so the 360 board shows the step as blocked rather
	than silently dropping it. DRAFT ONLY — a human sends every touch.

	Args:
		task_name: CRM Task name for the WhatsApp step.
		instance_name: Optional Outreach Sequence Instance name.
		body: Optional message body override.
	"""
	health = whatsapp_health()
	if not health["installed"]:
		return {"ok": False, "reason": "whatsapp_not_installed", "health": health}
	if not health["enabled"]:
		return {"ok": False, "reason": "whatsapp_not_enabled", "health": health}

	if not frappe.db.exists("CRM Task", task_name):
		return {"ok": False, "reason": "task_not_found", "task": task_name}
	task = frappe.get_doc("CRM Task", task_name)
	lead_name = task.get("lead") or None
	if not lead_name:
		return {"ok": False, "reason": "no_lead_for_task", "task": task_name}

	phone = frappe.db.get_value("CRM Lead", lead_name, "phone") or \
		frappe.db.get_value("CRM Lead", lead_name, "mobile_no") or ""
	try:
		assert_deliverable_phone(phone)
	except Exception:
		return {"ok": False, "reason": "undeliverable_phone", "lead": lead_name}

	message_body = body or task.get("description") or task.get("title") or ""
	return {
		"ok": True,
		"draft": True,
		"task": task_name,
		"instance": instance_name,
		"lead": lead_name,
		"to": phone,
		"body": message_body,
		"note": "Draft only. Human sends via WhatsApp; advance on delivered.",
	}
