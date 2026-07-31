import os

import frappe
import requests


@frappe.whitelist()
def ask_nyx(message):
	"""
	Proxies a chat message to the EAIA Agent Service.
	Set EAIA_URL environment variable to point at the deployed agent.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("You must be logged in to access Intelligence.", frappe.PermissionError)

	# Read URL from environment — no hardcoded tunnel URLs
	AGENT_URL = os.environ.get("EAIA_URL", "").rstrip("/") + "/chat"

	if not os.environ.get("EAIA_URL"):
		return (
			"⚠️ **Intelligence Core not configured.** "
			"Set the `EAIA_URL` environment variable to enable Nyx."
		)

	user_context = {
		"user_id": frappe.session.user,
		"full_name": frappe.utils.get_fullname(frappe.session.user),
	}

	payload = {
		"message": message,
		"history": [],
		"user_context": user_context,
	}

	try:
		response = requests.post(AGENT_URL, json=payload, timeout=30)
		response.raise_for_status()
		data = response.json()
		return data.get("response", "Error: No response from Agent.")

	except requests.exceptions.ConnectionError:
		frappe.log_error("EAIA Service Unreachable")
		return "⚠️ **Intelligence Core offline.** Check that the EAIA service is running."

	except requests.exceptions.Timeout:
		return "⚠️ **Intelligence Core timed out.** The agent took too long to respond."

	except Exception as e:
		frappe.log_error(f"EAIA Error: {str(e)}")
		return f"⚠️ **Agent Error**: {str(e)}"


@frappe.whitelist()
def get_dossier(phone=None, email=None, lead_id=None):
	"""Resolve caller context for voice / EAIA pre-call intelligence."""
	from crm.integrations.api import get_contact_by_phone_number

	lead_name = lead_id
	data = {}

	if not lead_name and email:
		lead_name = frappe.db.get_value("CRM Lead", {"email": email}, "name")
		if not lead_name and frappe.db.exists("DocType", "Lead Prospect"):
			prospect = frappe.db.get_value(
				"Lead Prospect",
				{"pi_email": email},
				["name", "pi_name", "institution", "cancer_type", "tier", "source_ref_id", "lead_score"],
				as_dict=True,
			)
			if prospect:
				data = {"doctype": "Lead Prospect", **prospect}
				return _format_dossier_response(data)

	if not lead_name and phone:
		contact = get_contact_by_phone_number(phone)
		if contact.get("lead"):
			lead_name = contact["lead"]
		elif contact.get("name") and not contact.get("deal"):
			data = {
				"doctype": "Contact",
				"first_name": contact.get("full_name", ""),
				"company_name": "",
			}
			return _format_dossier_response(data)

		if not lead_name and frappe.db.exists("DocType", "Lead Prospect"):
			pass  # Lead Prospect has no phone field; phone match uses CRM Lead / Contact only

	if lead_name and frappe.db.exists("CRM Lead", lead_name):
		lead = frappe.get_doc("CRM Lead", lead_name)
		notes = frappe.get_all(
			"FCRM Note",
			filters={"reference_doctype": "CRM Lead", "reference_docname": lead_name},
			fields=["title", "content"],
			order_by="creation desc",
			limit=3,
		)
		intel = {}
		if lead.additional_data:
			try:
				import json

				intel = json.loads(lead.additional_data)
			except Exception:
				intel = {"raw": lead.additional_data}

		data = {
			"doctype": "CRM Lead",
			"lead_name": lead.name,
			"first_name": lead.first_name,
			"last_name": lead.last_name,
			"organization": lead.organization,
			"job_title": lead.job_title,
			"email": lead.email,
			"mobile_no": getattr(lead, "mobile_no", None),
			"status": lead.status,
			"lead_score": getattr(lead, "lead_score", None),
			"source": lead.source,
			"pain_points": getattr(lead, "pain_points", None),
			"tier": getattr(lead, "tier", None),
			"source_ref_id": getattr(lead, "source_ref_id", None),
			"intel": intel,
			"notes": notes,
		}
		return _format_dossier_response(data)

	return {"formatted": "No dossier found. Unknown caller. Treat as cold call.", "data": {}}


def _format_dossier_response(data: dict) -> dict:
	"""Return raw data + prompt-ready formatted string."""
	doctype = data.get("doctype")

	if doctype == "Lead Prospect":
		formatted = f"""
TARGET DOSSIER (Priority: {data.get('tier', 'N/A')})
---------------------------------------------
NAME: Dr. {data.get('pi_name', 'Unknown')}
INSTITUTION: {data.get('institution', 'N/A')}
RESEARCH: {data.get('cancer_type', 'N/A')}
SCORE: {data.get('lead_score', 'N/A')}
SOURCE REF: {data.get('source_ref_id', 'N/A')}
"""
	elif doctype == "CRM Lead":
		notes_text = ""
		for n in data.get("notes") or []:
			notes_text += f"- {n.get('title', 'Note')}: {(n.get('content') or '')[:200]}\n"
		formatted = f"""
CRM LEAD DOSSIER
----------------
NAME: {data.get('first_name', '')} {data.get('last_name', '')}
ORG: {data.get('organization', 'N/A')}
TITLE: {data.get('job_title', 'N/A')}
STATUS: {data.get('status', 'N/A')} | SCORE: {data.get('lead_score', 'N/A')}
TIER: {data.get('tier', 'N/A')}
PAIN POINTS: {data.get('pain_points', 'N/A')}
SOURCE REF: {data.get('source_ref_id', 'N/A')}
NOTES:
{notes_text or 'None'}
"""
	else:
		formatted = f"""
CONTACT DOSSIER
---------------
NAME: {data.get('first_name', '')} {data.get('last_name', '')}
COMPANY: {data.get('company_name', 'N/A')}
"""

	return {"formatted": formatted.strip(), "data": data}


@frappe.whitelist()
def search_crm_knowledge(query: str, limit: int = 10):
	"""Search FCRM Notes and CRM Lead fields for voice / KB context."""
	if not query or not str(query).strip():
		return {"error": "query is required", "notes": [], "leads": []}

	q = str(query).strip()
	limit = int(limit)
	notes = frappe.get_all(
		"FCRM Note",
		filters={"content": ["like", f"%{q}%"]},
		fields=["name", "title", "content", "reference_doctype", "reference_docname", "creation"],
		order_by="creation desc",
		limit=limit,
	)
	for n in notes:
		n["content"] = (n.get("content") or "")[:500]

	lead_filters = [
		["organization", "like", f"%{q}%"],
		["lead_name", "like", f"%{q}%"],
	]
	if frappe.db.has_column("CRM Lead", "pain_points"):
		lead_filters.append(["pain_points", "like", f"%{q}%"])

	leads = frappe.get_all(
		"CRM Lead",
		or_filters=lead_filters,
		fields=["name", "lead_name", "organization", "status", "lead_score", "source_ref_id"],
		order_by="modified desc",
		limit=limit,
	)

	return {"query": q, "notes": notes, "leads": leads, "total": len(notes) + len(leads)}

@frappe.whitelist()
def get_grounding_context(lead_id=None, query=None, limit=5):
	"""Shared knowledge-grounding bundle for email brain, Vapi, and WhatsApp.

	Returns the lead dossier plus top-k CRM knowledge hits so every channel grounds
	on the SAME verified claims (single source of truth, no per-channel drift).
	"""
	dossier = None
	if lead_id:
		try:
			dossier = get_dossier(lead_id=lead_id)
		except Exception:
			dossier = None
	knowledge = []
	if query:
		try:
			knowledge = search_crm_knowledge(query, limit=limit)
		except Exception:
			knowledge = []
	grounded = bool(dossier) or bool(knowledge)
	return {
		"grounded": grounded,
		"dossier": dossier,
		"knowledge": knowledge,
		"rule": ("Ground every factual claim in the dossier/knowledge above."
		         if grounded else
		         "No verified background: do NOT state specific facts, figures, or claims."),
	}
