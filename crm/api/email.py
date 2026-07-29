import frappe
from frappe import _
from frappe.utils import cstr
from frappe import publish_realtime


def _safe_get_email_settings() -> dict:
	"""Return resolver settings with safe defaults if the Single DocType is missing."""
	settings = {
		"prefer_open_deal": False,
		"auto_create_lead_for_unknown": False,
		"domain_matching_enabled": True,
	}
	try:
		if frappe.db.exists("CRM Email Settings"):
			doc = frappe.get_single("CRM Email Settings")
			settings["prefer_open_deal"] = bool(doc.get("prefer_open_deal"))
			settings["auto_create_lead_for_unknown"] = bool(doc.get("auto_create_lead_for_unknown"))
			settings["domain_matching_enabled"] = bool(doc.get("domain_matching_enabled", True))
	except Exception:
		# ignore if settings not present
		pass
	return settings


def _match_contact_by_email(email: str) -> str | None:
	"""Return Contact name matching the given email (primary or child emails)."""
	if not email:
		return None
	# Primary field on Contact
	name = frappe.db.get_value("Contact", {"email_id": email}, "name")
	if name:
		return name
	# Child table Contact Email
	parent = frappe.db.get_value("Contact Email", {"email_id": email}, "parent")
	return parent


def _prefer_open_deal_for_contact(contact: str) -> str | None:
	"""Return an open CRM Deal linked to Contact if present."""
	if not contact:
		return None
	deal = frappe.db.get_value(
		"CRM Deal",
		{"contact": contact, "status": ["in", ["Open", "Qualifying", "Negotiating"]]},
		"name",
	)
	return deal


def _match_lead_by_email(email: str) -> str | None:
	"""Return CRM Lead name by common email fields."""
	if not email:
		return None
	name = frappe.db.get_value("CRM Lead", {"email_id": email}, "name")
	if name:
		return name
	name = frappe.db.get_value("CRM Lead", {"email": email}, "name")
	return name


def _match_org_by_domain(domain: str) -> str | None:
	"""Heuristic: try matching Organization by website containing domain."""
	if not domain:
		return None
	org = frappe.db.get_value("CRM Organization", {"website": ["like", f"%{domain}%"]}, "name")
	return org


@frappe.whitelist()
def resolve_reference(emails: list[str] | None = None, in_reply_to: str | None = None) -> dict | None:
	"""Smart resolver for linking Communications.

	Priority: thread inheritance → Contact (optionally prefer open Deal) → Lead → Organization (by domain) → optional auto-create Lead.
	"""
	emails = emails or []
	settings = _safe_get_email_settings()

	# 1) Thread inheritance via in_reply_to → parent Communication
	try:
		if in_reply_to:
			parent = frappe.db.get_value(
				"Communication",
				{"message_id": in_reply_to},
				["reference_doctype", "reference_name"],
				as_dict=True,
			)
			if parent and parent.reference_doctype and parent.reference_name:
				return {"doctype": parent.reference_doctype, "name": parent.reference_name}
	except Exception:
		pass

	# Normalize email list
	flat_emails: list[str] = []
	for e in emails:
		if not e:
			continue
		for part in cstr(e).split(","):
			addr = part.strip()
			if addr and addr not in flat_emails:
				flat_emails.append(addr)

	# 2) Contact by email → optionally prefer open Deal
	for em in flat_emails:
		contact = _match_contact_by_email(em)
		if contact:
			if settings.get("prefer_open_deal"):
				deal = _prefer_open_deal_for_contact(contact)
				if deal:
					return {"doctype": "CRM Deal", "name": deal}
			return {"doctype": "Contact", "name": contact}

	# 3) Lead by email
	for em in flat_emails:
		lead = _match_lead_by_email(em)
		if lead:
			return {"doctype": "CRM Lead", "name": lead}

	# 4) Organization by domain
	if settings.get("domain_matching_enabled"):
		for em in flat_emails:
			if "@" in em:
				domain = em.split("@", 1)[1]
				org = _match_org_by_domain(domain)
				if org:
					return {"doctype": "CRM Organization", "name": org}

	# 5) Optional auto-create Lead from first email
	if settings.get("auto_create_lead_for_unknown") and flat_emails:
		try:
			lead = frappe.get_doc(
				{
					"doctype": "CRM Lead",
					"email_id": flat_emails[0],
					"lead_name": cstr(flat_emails[0]).split("@")[0].title(),
				}
			)
			lead.insert(ignore_permissions=True)
			return {"doctype": "CRM Lead", "name": lead.name}
		except Exception:
			pass

	return None


def _collect_comm_emails(doc) -> list[str]:
	"""Collect sender/recipients/cc/bcc from Communication doc into a flat list."""
	emails: list[str] = []
	for field in ("sender", "recipients", "cc", "bcc"):
		val = doc.get(field)
		if not val:
			continue
		for part in cstr(val).split(","):
			addr = part.strip()
			if addr and addr not in emails:
				emails.append(addr)
	return emails


def auto_link_communication(doc, method: str | None = None):
	"""Hook: auto-link newly created Communications lacking a reference."""
	try:
		# Only if not already linked
		if doc.get("reference_doctype") and doc.get("reference_name"):
			return
		emails = _collect_comm_emails(doc)
		result = resolve_reference(emails=emails, in_reply_to=doc.get("in_reply_to"))
		if result and result.get("doctype") and result.get("name"):
			# Persist reference
			doc.db_set({
				"reference_doctype": result["doctype"],
				"reference_name": result["name"],
			})
	except Exception:
		# Best-effort; don't interrupt inbound processing
		pass
def _notify_on_draft(reference_doctype: str, reference_name: str, communication_name: str, subject: str):
	"""Notify the referenced doc owner and assignees about the new draft (best-effort)."""
	try:
		# Collect recipients: owner + assignees (ToDo allocated_to)
		recipients: set[str] = set()
		owner = frappe.db.get_value(reference_doctype, reference_name, "owner")
		if owner and owner != "Guest":
			recipients.add(owner)
		for row in frappe.get_all(
			"ToDo",
			filters={
				"reference_type": reference_doctype,
				"reference_name": reference_name,
				"status": ["in", ["Open", "Pending"]],
			},
			fields=["allocated_to"],
		):
			user = row.get("allocated_to")
			if user and user != "Guest":
				recipients.add(user)
		if not recipients:
			return
		# Use Notification Log if available; fallback to realtime per user
		for user in recipients:
			try:
				from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
				enqueue_create_notification(
					{
						"type": "Alert",
						"document_type": "Communication",
						"document_name": communication_name,
						"subject": _(f"AI Draft Ready: {subject}"),
						"for_user": user,
					}
				)
			except Exception:
				publish_realtime(
					"crm_email_draft_created_notify",
					{"communication_name": communication_name, "subject": subject},
					user=user,
				)
	except Exception:
		# best-effort; ignore errors
		pass


@frappe.whitelist()
def get_inbox(doctype: str | None = None, docname: str | None = None, status: str | None = None, direction: str | None = None, limit: int = 20):
	"""Return recent Communications linked to a doc or globally for CRM entities.

	Args:
		doctype: Optional filter for linked doctype
		docname: Optional filter for linked docname
		status: Optional Communication status filter (e.g. "Draft", "Sent")
		direction: Optional inbound/outbound filter -> maps to sent_or_received
			("inbound"/"received" -> Received, "outbound"/"sent" -> Sent)
		limit: Max records to return
	"""
	filters = {"communication_type": ["in", ["Communication", "Comment"]]}
	if doctype and docname:
		filters.update({"reference_doctype": doctype, "reference_name": docname})
	else:
		filters.update({"reference_doctype": ["in", ["CRM Lead", "Contact", "CRM Organization"]]})
	if status:
		# The Communication `status` Select cannot hold "Draft"/"Sent" (only
		# Open/Replied/Closed/Linked; reference-linked comms become "Linked").
		# Map the UI's draft/sent intent onto the doctype-legal `delivery_status`
		# field (its Select includes "Sent"; drafts have it empty). Other status
		# values fall through to a literal match for backward compatibility.
		s = str(status).strip().lower()
		if s == "draft":
			# outbound + not yet dispatched
			filters["sent_or_received"] = "Sent"
			filters["delivery_status"] = ["in", ["", None]]
		elif s == "sent":
			filters["delivery_status"] = "Sent"
		else:
			filters["status"] = status
	if direction:
		d = str(direction).strip().lower()
		if d in ("inbound", "received", "in"):
			filters["sent_or_received"] = "Received"
		elif d in ("outbound", "sent", "out"):
			filters["sent_or_received"] = "Sent"

	rows = frappe.get_all(
		"Communication",
		filters=filters,
		fields=[
			"name",
			"subject",
			"sender",
			"recipients",
			"sent_or_received",
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
			"sent_or_received",
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
def save_draft(reference_doctype: str, reference_name: str, to: str, subject: str, html: str, cc: str | None = None, bcc: str | None = None, provider_thread_id: str | None = None, communication_name: str | None = None):
	"""Create or update a draft Communication linked to a CRM entity.

	Upsert semantics: when ``communication_name`` is supplied and that
	Communication still exists and has NOT been sent, its editable fields
	(recipients/subject/content/cc/bcc) are updated in place. This is what makes
	"edit an AI/saved draft then send it" faithful — the persisted draft always
	reflects the latest editor contents instead of being replaced by a new doc
	or, worse, sent as its original version. Otherwise a new draft is inserted.

	Returns the Communication name.
	"""
	if not to or not subject or not html:
		raise_frappe("to, subject and html are required")

	# --- Update path: persist edits onto an existing, not-yet-sent draft ------
	if communication_name and frappe.db.exists("Communication", communication_name):
		comm = frappe.get_doc("Communication", communication_name)
		if (comm.status or "") == "Sent" or (comm.delivery_status or "") == "Sent":
			# Never mutate something already sent; fall through to insert a new draft.
			pass
		else:
			updates = {
				"recipients": to,
				"subject": subject,
				"content": html,
				"cc": cc,
				"bcc": bcc,
			}
			meta = frappe.get_meta("Communication")
			if provider_thread_id and meta.has_field("provider_thread_id"):
				updates["provider_thread_id"] = provider_thread_id
			comm.db_set(updates)
			return comm.name

	fields = {
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "Email",
		"sent_or_received": "Sent",
		"subject": subject,
		"sender": frappe.session.user,
		"recipients": to,
		"cc": cc,
		"bcc": bcc,
		"content": html,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"status": "Draft",
	}
	if provider_thread_id and frappe.get_meta("Communication").has_field("provider_thread_id"):
		fields["provider_thread_id"] = provider_thread_id

	comm = frappe.get_doc(fields)
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

	# Notify referenced doc owner (best-effort)
	_notify_on_draft(reference_doctype, reference_name, comm.name, subject)

	return comm.name


@frappe.whitelist()
def save_draft_with_provider(reference_doctype: str, reference_name: str, to: str, subject: str, html: str, provider: str | None = None, provider_message_id: str | None = None, provider_thread_id: str | None = None, cc: str | None = None, bcc: str | None = None):
	"""Create a draft and link provider IDs in one call (EAIA convenience).

	Returns: { "communication_name": str }
	"""
	name = save_draft(
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		to=to,
		subject=subject,
		html=html,
		cc=cc,
		bcc=bcc,
		provider_thread_id=provider_thread_id,
	)
	# Link provider IDs if provided
	if provider or provider_message_id or provider_thread_id:
		link_provider_ids(
			communication_name=name,
			provider=provider,
			provider_message_id=provider_message_id,
			provider_thread_id=provider_thread_id,
		)
	return {"communication_name": name}


# RFC 2606 reserves .invalid for addresses that can never resolve. industry._seed_one
# uses `<name>@needs-backfill.invalid` when a contact has no verified email, so a
# seeded draft is deliberately un-sendable until a human backfills the address.
_UNDELIVERABLE_TLDS = (".invalid", ".example", ".test", ".localhost")
_PLACEHOLDER_DOMAINS = ("needs-backfill.invalid", "example.com", "example.org", "example.net")


def _undeliverable(addr: str) -> bool:
	a = (addr or "").strip().lower()
	if not a or "@" not in a:
		return True
	dom = a.rsplit("@", 1)[-1]
	return dom.endswith(_UNDELIVERABLE_TLDS) or dom in _PLACEHOLDER_DOMAINS


def assert_deliverable(recipients: list, cc: list = None, bcc: list = None):
	"""Block a send to a placeholder address.

	Without this, a seeded draft addressed to `<name>@needs-backfill.invalid` would
	be queued and then stamped delivery_status="Sent", and Nyx Action Log would
	record `executed` -- a false record that a KOL was contacted. Fail loudly and
	name the offending address so the operator knows exactly what to backfill.
	"""
	bad = [a for a in list(recipients or []) + list(cc or []) + list(bcc or [])
	       if _undeliverable(a)]
	if bad:
		raise_frappe(
			"Refusing to send: {0} placeholder/undeliverable address(es) — {1}. "
			"Backfill a verified email on the contact first.".format(len(bad), ", ".join(bad[:5]))
		)


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

	# Never let a placeholder recipient be recorded as a real send (see W5-1).
	assert_deliverable(recipients, cc_list, bcc_list)

	frappe.sendmail(
		recipients=recipients,
		subject=comm.subject,
		message=comm.content,
		cc=cc_list,
		bcc=bcc_list,
		reference_doctype=comm.reference_doctype,
		reference_name=comm.reference_name,
	)

	# The Communication doctype's `status` Select does NOT allow "Draft"/"Sent"
	# (only Open/Replied/Closed/Linked), and reference-linked comms are auto-set to
	# "Linked". The reliable, doctype-legal send marker is `delivery_status`, whose
	# Select DOES include "Sent". Set both: status for legacy readers, delivery_status
	# as the authoritative sent/draft discriminator used by get_inbox().
	comm.db_set("status", "Sent")
	comm.db_set("delivery_status", "Sent")
	return {"ok": True}


@frappe.whitelist()
def link_provider_ids(communication_name: str, provider: str | None = None, provider_message_id: str | None = None, provider_thread_id: str | None = None):
	"""Attach external provider IDs to an existing Communication."""
	comm = frappe.get_doc("Communication", communication_name)
	meta = frappe.get_meta("Communication")
	updates: dict[str, object] = {}
	if provider and meta.has_field("provider"):
		updates["provider"] = provider
	if provider_message_id and meta.has_field("provider_message_id"):
		updates["provider_message_id"] = provider_message_id
	if provider_thread_id and meta.has_field("provider_thread_id"):
		updates["provider_thread_id"] = provider_thread_id
	if updates:
		comm.db_set(updates)
	return {"ok": True}


@frappe.whitelist()
def find_communication_by_provider_id(provider_message_id: str | None = None, provider_thread_id: str | None = None):
	"""Durable idempotency lookup for the EAIA bridge.

	Returns the existing Communication (name + reference) for a given provider
	message/thread id, or None. Because the CRM is the source of truth, this
	survives EAIA-service restarts (unlike a local processed_ids.json file).
	"""
	if provider_message_id:
		name = frappe.db.get_value(
			"Communication",
			{"provider_message_id": provider_message_id},
			["name", "reference_doctype", "reference_name", "status"],
			as_dict=True,
		)
		if name:
			return name
	if provider_thread_id:
		name = frappe.db.get_value(
			"Communication",
			{"provider_thread_id": provider_thread_id},
			["name", "reference_doctype", "reference_name", "status"],
			as_dict=True,
			order_by="creation desc",
		)
		if name:
			return name
	return None


def _lead_for_communication(comm) -> str | None:
	ref_dt = comm.reference_doctype
	ref_dn = comm.reference_name
	if not (ref_dt and ref_dn):
		return None
	if ref_dt == "CRM Lead":
		return ref_dn
	if ref_dt == "CRM Deal":
		return frappe.db.get_value("CRM Deal", ref_dn, "lead")
	return None


def _map_triage_action(action: str) -> str:
	normalized = (action or "NOTIFY").upper()
	if normalized == "RESPOND":
		return "respond"
	if normalized == "IGNORE":
		return "ignore"
	return "notify"


@frappe.whitelist()
def triage_communication(communication_name: str) -> dict:
	"""AI triage for Human Inbox. Returns action/reason/priority/suggested_response."""
	if not communication_name:
		raise_frappe("communication_name is required")

	comm = frappe.get_doc("Communication", communication_name)
	lead_name = _lead_for_communication(comm)

	try:
		from crm.api.nyx_email_brain import TRIAGE_SYSTEM, _lead_context, _resolve_llm, _safe_json

		complete = _resolve_llm()
		if complete and lead_name:
			lead = frappe.get_doc("CRM Lead", lead_name)
			ctx = _lead_context(lead, comm.content)
			triage_raw = complete(f"{TRIAGE_SYSTEM}\n\nLEAD CONTEXT:\n{ctx}")
			triage = _safe_json(triage_raw, {"action": "NOTIFY", "reason": "unparseable triage"})
			action = _map_triage_action(triage.get("action"))
			return {
				"action": action,
				"reason": triage.get("reason") or "",
				"priority": "high" if action == "respond" else "medium",
				"suggested_response": "Draft a personalized reply" if action == "respond" else "",
			}
	except Exception:
		frappe.log_error(title="triage_communication failed", message=frappe.get_traceback())

	return {
		"action": "notify",
		"reason": "Manual review recommended",
		"priority": "medium",
		"suggested_response": "Review this email and draft a reply if needed",
	}


@frappe.whitelist()
def draft_ai_response(
	communication_name: str,
	tone: str = "professional",
	include_context: bool = True,
) -> dict:
	"""Draft a reply for Human Inbox. Creates a Draft Communication when possible."""
	if not communication_name:
		raise_frappe("communication_name is required")

	comm = frappe.get_doc("Communication", communication_name)
	lead_name = _lead_for_communication(comm)

	if lead_name:
		result = frappe.call(
			"crm.api.nyx_email_brain.triage_and_draft",
			lead_name=lead_name,
			incoming=comm.content,
			force=True,
		)
		draft_name = result.get("communication")
		if draft_name:
			draft = frappe.get_doc("Communication", draft_name)
			return {
				"subject": draft.subject,
				"content": draft.content,
				"summary": f"NYX draft ({result.get('triage') or result.get('decision') or 'ready'})",
				"communication_name": draft.name,
			}

	try:
		from crm.api.nyx_email_brain import DRAFT_SYSTEM, _resolve_llm, _safe_json

		complete = _resolve_llm()
		if complete and comm.reference_doctype and comm.reference_name:
			context = f"Linked to {comm.reference_doctype} {comm.reference_name}"
			if include_context:
				context += f"\nInbound from: {comm.sender}\nSubject: {comm.subject}\n{comm.content[:2000]}"
			draft_raw = complete(f"{DRAFT_SYSTEM}\n\n{context}\nTone: {tone}")
			draft = _safe_json(draft_raw, {})
			subject = (draft.get("subject") or f"Re: {comm.subject}").strip()
			html = (draft.get("html") or "").strip()
			if html:
				to = (comm.sender or comm.recipients or "").split(",")[0].strip()
				draft_name = save_draft(
					reference_doctype=comm.reference_doctype,
					reference_name=comm.reference_name,
					to=to,
					subject=subject,
					html=html,
				)
				return {
					"subject": subject,
					"content": html,
					"summary": "AI draft ready for review",
					"communication_name": draft_name,
				}
	except Exception:
		frappe.log_error(title="draft_ai_response failed", message=frappe.get_traceback())

	return {
		"subject": f"Re: {comm.subject}",
		"content": "<p>Thank you for your email. I will review this and follow up shortly.</p>",
		"summary": "Fallback draft — edit before sending",
	}


def raise_frappe(message: str):
	frappe.throw(_(message))
