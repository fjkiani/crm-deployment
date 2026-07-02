"""
Vapi voice integration — single source of truth for outbound calls and webhooks.

Endpoints (whitelisted):
  crm.api.vapi.initiate_outbound_call
  crm.api.vapi.handle_webhook  (also exposed as vapi_webhook)
  crm.api.vapi.get_health
  crm.api.vapi.get_dashboard
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

VAPI_API_BASE = "https://api.vapi.ai"
MAX_RETRIES_PER_LEAD = 5


# ── Config helpers ────────────────────────────────────────────────────────────


def _vapi_api_key() -> str:
	key = frappe.conf.get("vapi_api_key") or os.environ.get("VAPI_API_KEY")
	if not key and frappe.db.exists("DocType", "CRM Twilio Settings"):
		key = frappe.db.get_single_value("CRM Twilio Settings", "vapi_api_key")
	if not key:
		frappe.throw(_("Vapi API key not configured (site config vapi_api_key or VAPI_API_KEY)"))
	return key


def _vapi_phone_number_id() -> str:
	pid = frappe.conf.get("vapi_phone_number_id") or os.environ.get("VAPI_PHONE_NUMBER_ID")
	if not pid and frappe.db.exists("DocType", "CRM Twilio Settings"):
		pid = frappe.db.get_single_value("CRM Twilio Settings", "vapi_phone_number_id")
	if not pid:
		frappe.throw(_("Vapi phone number ID not configured (vapi_phone_number_id or VAPI_PHONE_NUMBER_ID)"))
	return pid


def _webhook_base_url() -> str:
	return (
		frappe.conf.get("vapi_webhook_base_url")
		or os.environ.get("VAPI_WEBHOOK_BASE_URL")
		or frappe.utils.get_url()
	).rstrip("/")


# ── Outcome mapping (mirrors test_zeta_pipeline_az.test_i_vapi_webhook) ───────


def map_outcome_to_status_priority(outcome: str) -> tuple[str, str]:
	outcome_lower = (outcome or "").lower()
	negative = ["not interested", "dnc", "refused", "do not contact"]
	if any(outcome_lower in [x, f"{x}."] or outcome_lower.startswith(x) for x in negative):
		return "Junk", "Low"
	if "voicemail" in outcome_lower or "no answer" in outcome_lower or "left message" in outcome_lower:
		return "Contacted", "Medium"
	if any(x in outcome_lower for x in ["appointment", "interested", "set", "booked", "demo"]):
		return "Opportunity", "High"
	if outcome_lower in ("no", "refused", "hang up", "hung up"):
		return "Junk", "Low"
	return "Contacted", "Medium"


# ── Governor / dedup ──────────────────────────────────────────────────────────


def _already_called_today(lead_name: str) -> bool:
	today = str(date.today())
	return bool(
		frappe.db.exists(
			"Vapi Call Log",
			{"crm_lead": lead_name, "call_date": today, "status": ["!=", "Failed"]},
		)
	)


def _total_call_count(lead_name: str) -> int:
	return frappe.db.count("Vapi Call Log", {"crm_lead": lead_name})


def should_call_lead(lead_name: str) -> tuple[bool, str]:
	if not lead_name:
		return True, "OK"
	if _already_called_today(lead_name):
		return False, "Already called today"
	if _total_call_count(lead_name) >= MAX_RETRIES_PER_LEAD:
		return False, f"Governor: max retries ({MAX_RETRIES_PER_LEAD}) reached"
	return True, "OK"


# ── Dossier for system prompt ───────────────────────────────────────────────


def _build_call_context(lead_name: str | None, context: str | None) -> str:
	parts = []
	if lead_name:
		try:
			from crm.api.intelligence import get_dossier

			dossier = get_dossier(lead_id=lead_name)
			if isinstance(dossier, dict) and dossier.get("formatted"):
				parts.append(dossier["formatted"])
		except Exception as e:
			frappe.log_error(f"Vapi dossier fetch failed: {e}", "Vapi Call")
	if context:
		parts.append(context)
	return "\n\n".join(parts) if parts else "No pre-call intelligence available."


# ── Outbound call ─────────────────────────────────────────────────────────────


@frappe.whitelist()
def initiate_outbound_call(
	to_number: str | None = None,
	phone: str | None = None,
	contact_id: str | None = None,
	lead_name: str | None = None,
	crm_prospect_id: str | None = None,
	topic: str | None = None,
	context: str | None = None,
	objective: str | None = None,
):
	"""Place an outbound Vapi AI call and create Vapi Call Log + CRM Call Log."""
	phone_number = (to_number or phone or "").strip()
	if not phone_number:
		frappe.throw(_("Phone number is required"))

	lead_name = lead_name or crm_prospect_id or contact_id
	call_objective = objective or topic or "Follow up on our research outreach"

	ok, reason = should_call_lead(lead_name)
	if not ok:
		frappe.throw(_(reason))

	dossier_text = _build_call_context(lead_name, context)
	system_message = f"""You are Nyx, an AI executive assistant for CrisPRO / Zeta Intelligence.
Objective: {call_objective}

{dossier_text}

RULES:
- Professional, concise, confident
- If voicemail: 20-second message referencing the objective
- Never claim to be a human
"""

	first_message = f"Hi, I'm calling on behalf of our research team regarding {call_objective}. Do you have a minute?"

	payload = {
		"phoneNumberId": _vapi_phone_number_id(),
		"customer": {"number": phone_number},
		"assistant": {
			"firstMessage": first_message,
			"model": {
				"provider": "openai",
				"model": "gpt-4o-mini",
				"messages": [{"role": "system", "content": system_message}],
				"temperature": 0.7,
				"maxTokens": 250,
			},
			"voice": {"provider": "11labs", "voiceId": "burt"},
			"endCallFunctionEnabled": True,
			"recordingEnabled": True,
			"maxDurationSeconds": 300,
			"silenceTimeoutSeconds": 30,
		},
		"metadata": {
			"crm_lead": lead_name or "",
			"topic": call_objective,
		},
	}

	headers = {"Authorization": f"Bearer {_vapi_api_key()}", "Content-Type": "application/json"}
	resp = requests.post(f"{VAPI_API_BASE}/call", headers=headers, json=payload, timeout=30)
	if resp.status_code not in (200, 201):
		frappe.log_error(resp.text, "Vapi initiate_outbound_call")
		frappe.throw(_("Vapi API error: {0}").format(resp.text[:500]))

	vapi_data = resp.json()
	call_id = vapi_data.get("id", "")

	_create_call_logs(
		vapi_call_id=call_id,
		from_number=_vapi_phone_number_id(),
		to_number=phone_number,
		lead_name=lead_name,
		status="Initiated",
		topic=call_objective,
	)

	return {
		"status": "call_initiated",
		"call_id": call_id,
		"vapi_call_id": call_id,
		"to": phone_number,
		"lead_name": lead_name,
	}


def _create_call_logs(
	vapi_call_id: str,
	from_number: str,
	to_number: str,
	lead_name: str | None,
	status: str,
	topic: str | None = None,
	outcome: str | None = None,
	duration: int = 0,
	transcript: str | None = None,
	summary: str | None = None,
	recording_url: str | None = None,
):
	"""Upsert Vapi Call Log and mirror to CRM Call Log."""
	vapi_log = None
	if vapi_call_id and frappe.db.exists("DocType", "Vapi Call Log"):
		existing_name = frappe.db.get_value("Vapi Call Log", {"vapi_call_id": vapi_call_id}, "name")
		if existing_name:
			vapi_log = frappe.get_doc("Vapi Call Log", existing_name)
		else:
			vapi_log = frappe.get_doc(
				{
					"doctype": "Vapi Call Log",
					"vapi_call_id": vapi_call_id,
					"from_number": from_number,
					"to_number": to_number,
					"crm_lead": lead_name,
					"status": status,
					"call_date": str(date.today()),
					"topic": topic,
				}
			)
			vapi_log.insert(ignore_permissions=True)

		if outcome:
			vapi_log.outcome = outcome
			crm_status, priority = map_outcome_to_status_priority(outcome)
			vapi_log.crm_lead_status = crm_status
			vapi_log.priority = priority
		if duration:
			vapi_log.duration_seconds = duration
		if transcript:
			vapi_log.transcript = transcript
		if summary:
			vapi_log.summary = summary
		if recording_url:
			vapi_log.recording_url = recording_url
		vapi_log.status = status
		vapi_log.save(ignore_permissions=True)

	# CRM Call Log (unified telephony view)
	if vapi_call_id:
		call_log_fields = {
			"doctype": "CRM Call Log",
			"id": vapi_call_id,
			"from": from_number,
			"to": to_number,
			"status": status,
			"type": "Outgoing",
			"telephony_medium": "Vapi",
			"duration": duration or 0,
			"recording_url": recording_url,
			"note": summary or topic,
		}
		if frappe.db.exists("CRM Call Log", vapi_call_id):
			doc = frappe.get_doc("CRM Call Log", vapi_call_id)
			doc.update({k: v for k, v in call_log_fields.items() if k != "doctype"})
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc(call_log_fields)
			if lead_name:
				doc.reference_doctype = "CRM Lead"
				doc.reference_docname = lead_name
			doc.insert(ignore_permissions=True)

	frappe.db.commit()


# ── Webhook ───────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True)
def handle_webhook(**kwargs):
	"""Vapi server webhook — end-of-call reports and status updates."""
	try:
		payload = frappe.request.get_json(silent=True) or kwargs
	except Exception:
		payload = kwargs

	message = payload.get("message") or payload
	msg_type = message.get("type") or payload.get("type")

	if msg_type == "end-of-call-report":
		return _process_end_of_call_report(message)
	if msg_type in ("status-update", "hang"):
		return _process_status_update(message)

	return {"status": "ignored", "type": msg_type}


@frappe.whitelist(allow_guest=True)
def vapi_webhook(**kwargs):
	"""Backward-compatible alias for docs / Vapi dashboard URL."""
	return handle_webhook(**kwargs)


def _process_end_of_call_report(report: dict):
	call_info = report.get("call") or {}
	call_id = call_info.get("id") or report.get("callId", "")
	duration = int(report.get("durationSeconds") or report.get("duration") or 0)
	recording_url = report.get("recordingUrl") or report.get("recording_url")
	transcript = report.get("transcript") or ""
	analysis = report.get("analysis") or {}
	summary = analysis.get("summary") or ""
	structured = analysis.get("structuredData") or {}
	outcome = structured.get("outcome") or report.get("endedReason") or "completed"

	metadata = call_info.get("metadata") or report.get("metadata") or {}
	lead_name = metadata.get("crm_lead") or metadata.get("crm_prospect_id")

	customer = call_info.get("customer") or report.get("customer") or {}
	to_number = customer.get("number") or report.get("customer", {}).get("number", "")

	_create_call_logs(
		vapi_call_id=call_id,
		from_number="vapi",
		to_number=to_number,
		lead_name=lead_name or None,
		status="Completed",
		outcome=outcome,
		duration=duration,
		transcript=transcript,
		summary=summary,
		recording_url=recording_url,
	)

	if lead_name and transcript:
		_create_follow_up_note(lead_name, call_id, outcome, transcript, summary, duration)

	if lead_name and outcome:
		crm_status, _priority = map_outcome_to_status_priority(outcome)
		if crm_status in ("Opportunity", "Junk", "Contacted"):
			try:
				frappe.db.set_value("CRM Lead", lead_name, "status", crm_status)
			except Exception:
				pass

	return {"status": "processed", "call_id": call_id, "outcome": outcome}


def _process_status_update(message: dict):
	call_info = message.get("call") or {}
	call_id = call_info.get("id", "")
	status = message.get("status") or call_info.get("status") or "In Progress"
	if call_id and frappe.db.exists("DocType", "Vapi Call Log"):
		existing_name = frappe.db.get_value("Vapi Call Log", {"vapi_call_id": call_id}, "name")
		if existing_name:
			frappe.db.set_value("Vapi Call Log", existing_name, "status", status)
			frappe.db.commit()
	return {"status": "updated", "call_id": call_id}


def _create_follow_up_note(lead_name: str, call_id: str, outcome: str, transcript: str, summary: str, duration: int):
	note_content = (
		f"**Vapi Call** `{call_id}`\n"
		f"**Outcome:** {outcome}\n"
		f"**Duration:** {duration}s\n\n"
		f"**Summary:** {summary}\n\n"
		f"**Transcript:**\n{transcript[:4000]}"
	)
	frappe.get_doc(
		{
			"doctype": "FCRM Note",
			"title": f"📞 Vapi: {outcome}",
			"content": note_content,
			"reference_doctype": "CRM Lead",
			"reference_docname": lead_name,
		}
	).insert(ignore_permissions=True)

	keywords = ["follow up", "call back", "schedule", "demo", "meeting"]
	if any(k in (transcript + summary).lower() for k in keywords):
		frappe.get_doc(
			{
				"doctype": "CRM Task",
				"title": f"Follow up call: {lead_name}",
				"description": summary or transcript[:500],
				"reference_doctype": "CRM Lead",
				"reference_docname": lead_name,
				"due_date": date.today(),
				"status": "Todo",
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()


# ── Dashboard / health ────────────────────────────────────────────────────────


@frappe.whitelist()
def get_health():
	"""Health check for Voice Dashboard — probes Vapi API with configured key."""
	ok = False
	detail = ""
	configured = bool(
		frappe.conf.get("vapi_api_key")
		or os.environ.get("VAPI_API_KEY")
	)
	try:
		headers = {"Authorization": f"Bearer {_vapi_api_key()}"}
		resp = requests.get(f"{VAPI_API_BASE}/phone-number", headers=headers, timeout=10)
		ok = resp.status_code == 200
		detail = "connected" if ok else resp.text[:200]
		configured = True
	except Exception as e:
		detail = str(e)
	return {
		"vapi": ok,
		"configured": configured,
		"detail": detail,
		"webhook_url": f"{_webhook_base_url()}/api/method/crm.api.vapi.handle_webhook",
	}


@frappe.whitelist()
def get_dashboard():
	"""Aggregated voice analytics for Voice Dashboard."""
	vapi_logs = []
	if frappe.db.exists("DocType", "Vapi Call Log"):
		vapi_logs = frappe.get_all(
			"Vapi Call Log",
			fields=[
				"name",
				"vapi_call_id",
				"from_number",
				"to_number",
				"status",
				"outcome",
				"duration_seconds",
				"recording_url",
				"crm_lead",
				"creation",
				"modified",
			],
			order_by="creation desc",
			limit=50,
		)

	active_statuses = {"Initiated", "Ringing", "In Progress", "queued", "ringing"}
	active = [l for l in vapi_logs if (l.get("status") or "") in active_statuses]
	completed = [l for l in vapi_logs if (l.get("status") or "") == "Completed"]
	durations = [l.get("duration_seconds") or 0 for l in completed if l.get("duration_seconds")]

	return {
		"total_calls": len(vapi_logs),
		"active_calls": len(active),
		"recent_calls": vapi_logs,
		"active_call_details": active,
		"analytics": {
			"success_rate": round(len(completed) / max(len(vapi_logs), 1) * 100, 1),
			"average_duration": round(sum(durations) / max(len(durations), 1), 1),
			"total_duration": sum(durations),
		},
		"vapi_health": get_health(),
	}
