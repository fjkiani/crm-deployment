import frappe
from frappe import _
from frappe.utils import cstr
from frappe import publish_realtime
import json
import requests
from typing import Dict, Any, Optional


def get_openai_client():
	"""Get OpenAI client for AI operations."""
	api_key = frappe.conf.get("openai_api_key") or frappe.get_site_config().get("openai_api_key")
	if not api_key:
		frappe.throw(_("OpenAI API key not configured. Set openai_api_key in site config."))
	
	# For now, using requests directly. In production, use OpenAI SDK
	return {"api_key": api_key}


def call_openai(messages: list, model: str = "gpt-4o-mini", temperature: float = 0.0) -> str:
	"""Make OpenAI API call."""
	client = get_openai_client()
	
	headers = {
		"Authorization": f"Bearer {client['api_key']}",
		"Content-Type": "application/json"
	}
	
	data = {
		"model": model,
		"messages": messages,
		"temperature": temperature
	}
	
	try:
		response = requests.post(
			"https://api.openai.com/v1/chat/completions",
			headers=headers,
			json=data,
			timeout=30
		)
		response.raise_for_status()
		return response.json()["choices"][0]["message"]["content"]
	except Exception as e:
		frappe.log_error(f"OpenAI API call failed: {str(e)}")
		frappe.throw(_("AI service temporarily unavailable"))


@frappe.whitelist()
def triage_email(communication_name: str) -> Dict[str, Any]:
	"""AI-powered email triage to determine action needed.
	
	Returns: {
		"action": "respond|notify|ignore",
		"reason": "explanation",
		"priority": "high|medium|low",
		"suggested_response": "brief suggestion"
	}
	"""
	comm = frappe.get_doc("Communication", communication_name)
	
	# Get context about the CRM entity
	context = ""
	if comm.reference_doctype and comm.reference_name:
		ref_doc = frappe.get_doc(comm.reference_doctype, comm.reference_name)
		if comm.reference_doctype == "CRM Lead":
			context = f"Lead: {ref_doc.lead_name} ({ref_doc.status})"
		elif comm.reference_doctype == "Contact":
			context = f"Contact: {ref_doc.first_name} {ref_doc.last_name}"
		elif comm.reference_doctype == "CRM Organization":
			context = f"Organization: {ref_doc.organization_name}"
	
	# Build triage prompt
	prompt = f"""You are an AI assistant helping to triage emails in a CRM system.

Email Context:
- From: {comm.sender}
- To: {comm.recipients}
- Subject: {comm.subject}
- CRM Context: {context}
- Content: {comm.content[:1000]}...

Triage Rules:
- RESPOND: Direct questions, meeting requests, urgent matters, follow-ups
- NOTIFY: Important updates, documents shared, but no immediate action needed
- IGNORE: Spam, automated notifications, irrelevant content

Analyze this email and respond with JSON:
{{
	"action": "respond|notify|ignore",
	"reason": "brief explanation",
	"priority": "high|medium|low", 
	"suggested_response": "brief suggestion for response"
}}"""

	messages = [{"role": "user", "content": prompt}]
	
	try:
		response = call_openai(messages)
		result = json.loads(response)
		
		# Validate response structure
		required_fields = ["action", "reason", "priority", "suggested_response"]
		if not all(field in result for field in required_fields):
			raise ValueError("Invalid response structure")
		
		# Update communication with triage result
		comm.db_set("status", f"Triage: {result['action'].title()}")
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Email triage failed: {str(e)}")
		return {
			"action": "notify",
			"reason": "AI triage failed, manual review needed",
			"priority": "medium",
			"suggested_response": "Please review this email manually"
		}


@frappe.whitelist()
def draft_ai_response(communication_name: str, tone: str = "professional", include_context: bool = True) -> Dict[str, Any]:
	"""AI-powered email response drafting.
	
	Args:
		communication_name: Communication to respond to
		tone: professional|casual|friendly|formal
		include_context: Whether to include CRM context
	"""
	comm = frappe.get_doc("Communication", communication_name)
	
	# Get thread context
	thread_emails = thread_context(communication=communication_name, limit=5)
	
	# Get CRM context
	context = ""
	if comm.reference_doctype and comm.reference_name:
		ref_doc = frappe.get_doc(comm.reference_doctype, comm.reference_name)
		if comm.reference_doctype == "CRM Lead":
			context = f"Lead: {ref_doc.lead_name} (Status: {ref_doc.status})"
		elif comm.reference_doctype == "Contact":
			context = f"Contact: {ref_doc.first_name} {ref_doc.last_name}"
		elif comm.reference_doctype == "CRM Organization":
			context = f"Organization: {ref_doc.organization_name}"
	
	# Build drafting prompt
	prompt = f"""You are drafting an email response in a CRM system.

CRM Context: {context if include_context else "None"}

Email Thread:
{chr(10).join([f"- {email['sender']}: {email['subject']} ({email['content'][:200]}...)" for email in thread_emails])}

Original Email:
From: {comm.sender}
Subject: {comm.subject}
Content: {comm.content}

Instructions:
- Write a {tone} response
- Be concise but helpful
- Reference the CRM context if relevant
- Include a clear call-to-action if appropriate
- Keep it under 200 words

Respond with JSON:
{{
	"subject": "Re: {comm.subject}",
	"content": "email body in HTML format",
	"summary": "brief summary of what this response does"
}}"""

	messages = [{"role": "user", "content": prompt}]
	
	try:
		response = call_openai(messages)
		result = json.loads(response)
		
		# Validate response
		if not all(field in result for field in ["subject", "content", "summary"]):
			raise ValueError("Invalid response structure")
		
		return result
		
	except Exception as e:
		frappe.log_error(f"AI drafting failed: {str(e)}")
		return {
			"subject": f"Re: {comm.subject}",
			"content": "<p>Thank you for your email. I'll review this and get back to you shortly.</p>",
			"summary": "Generic response due to AI error"
		}


@frappe.whitelist()
def get_inbox(doctype: str | None = None, docname: str | None = None, status: str | None = None, limit: int = 20):
	"""Return recent Communications linked to a doc or globally for CRM Lead/Contact/Organization.

	Args:
		doctype: Optional filter for linked doctype
		docname: Optional filter for linked docname
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
	"""Return thread context: list of Communications for a doc or by thread provider ID.

	Either pass a Communication name, or doctype+docname.
	"""
	filters = {}
	if communication:
		comm = frappe.get_doc("Communication", communication)
		if comm.get("provider_thread_id"):
			filters["provider_thread_id"] = comm.provider_thread_id
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
	
	# Publish realtime event for draft creation
	publish_realtime("crm_email_draft_created", {
		"communication_name": comm.name,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"subject": subject,
		"sender": frappe.session.user,
	}, user=frappe.session.user)
	
	return comm.name


@frappe.whitelist()
def send(communication_name: str):
	"""Send a Communication via email."""
	comm = frappe.get_doc("Communication", communication_name)
	
	# Send the email
	comm.send_email()
	
	# Update status and save
	comm.status = "Sent"
	comm.save()
	
	return {"ok": True}


@frappe.whitelist()
def link_provider_ids(communication_name: str, provider: str | None = None, provider_message_id: str | None = None, provider_thread_id: str | None = None):
	"""Link external provider IDs to a Communication."""
	comm = frappe.get_doc("Communication", communication_name)
	
	if provider:
		comm.provider = provider
	if provider_message_id:
		comm.provider_message_id = provider_message_id
	if provider_thread_id:
		comm.provider_thread_id = provider_thread_id
	
	comm.save()
	return {"ok": True}


def raise_frappe(message: str):
	"""Helper to raise frappe exceptions."""
	frappe.throw(_(message))

