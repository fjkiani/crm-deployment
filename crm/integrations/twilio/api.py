import json

import frappe
from frappe import _
from werkzeug.wrappers import Response

from crm.integrations.api import get_contact_by_phone_number

from .twilio_handler import IncomingCall, Twilio, TwilioCallDetails


@frappe.whitelist()
def is_enabled():
	return frappe.db.get_single_value("CRM Twilio Settings", "enabled")


@frappe.whitelist()
def generate_access_token():
	"""Returns access token that is required to authenticate Twilio Client SDK."""
	twilio = Twilio.connect()
	if not twilio:
		return {}

	from_number = frappe.db.get_value("CRM Telephony Agent", frappe.session.user, "twilio_number")
	if not from_number:
		return {
			"ok": False,
			"error": "caller_phone_identity_missing",
			"detail": "Phone number is not mapped to the caller",
		}

	token = twilio.generate_voice_access_token(identity=frappe.session.user)
	return {"token": frappe.safe_decode(token)}


@frappe.whitelist(allow_guest=True)
def voice(**kwargs):
	"""This is a webhook called by twilio to get instructions when the voice call request comes to twilio server."""

	def _get_caller_number(caller):
		identity = caller.replace("client:", "").strip()
		user = Twilio.emailid_from_identity(identity)
		return frappe.db.get_value("CRM Telephony Agent", user, "twilio_number")

	args = frappe._dict(kwargs)
	twilio = Twilio.connect()
	if not twilio:
		return

	assert args.AccountSid == twilio.account_sid
	assert args.ApplicationSid == twilio.application_sid

	# Generate TwiML instructions to make a call
	from_number = _get_caller_number(args.Caller)
	resp = twilio.generate_twilio_dial_response(from_number, args.To)

	call_details = TwilioCallDetails(args, call_from=from_number)
	create_call_log(call_details)
	return Response(resp.to_xml(), mimetype="text/xml")


@frappe.whitelist(allow_guest=True)
def twilio_incoming_call_handler(**kwargs):
	args = frappe._dict(kwargs)
	call_details = TwilioCallDetails(args)
	create_call_log(call_details)

	resp = IncomingCall(args.From, args.To).process()
	return Response(resp.to_xml(), mimetype="text/xml")


def create_call_log(call_details: TwilioCallDetails):
	details = call_details.to_dict()

	call_log = frappe.get_doc({**details, "doctype": "CRM Call Log", "telephony_medium": "Twilio"})

	# link call log with lead/deal
	contact_number = details.get("from") if details.get("type") == "Incoming" else details.get("to")
	link(contact_number, call_log)

	call_log.save(ignore_permissions=True)
	frappe.db.commit()
	return call_log


def link(contact_number, call_log):
	contact = get_contact_by_phone_number(contact_number)
	if contact.get("name"):
		doctype = "Contact"
		docname = contact.get("name")
		if contact.get("lead"):
			doctype = "CRM Lead"
			docname = contact.get("lead")
		elif contact.get("deal"):
			doctype = "CRM Deal"
			docname = contact.get("deal")
		call_log.link_with_reference_doc(doctype, docname)


def update_call_log(call_sid, status=None):
	"""Update call log status."""
	twilio = Twilio.connect()
	if not (twilio and frappe.db.exists("CRM Call Log", call_sid)):
		return

	try:
		call_details = twilio.get_call_info(call_sid)
		call_log = frappe.get_doc("CRM Call Log", call_sid)
		call_log.status = TwilioCallDetails.get_call_status(status or call_details.status)
		call_log.duration = call_details.duration
		call_log.start_time = get_datetime_from_timestamp(call_details.start_time)
		call_log.end_time = get_datetime_from_timestamp(call_details.end_time)
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		return call_log
	except Exception:
		frappe.log_error(title="Error while updating call record")
		frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def update_recording_info(**kwargs):
	try:
		args = frappe._dict(kwargs)
		recording_url = args.RecordingUrl
		call_sid = args.CallSid
		update_call_log(call_sid)
		frappe.db.set_value("CRM Call Log", call_sid, "recording_url", recording_url)
	except Exception:
		frappe.log_error(title=_("Failed to capture Twilio recording"))


@frappe.whitelist(allow_guest=True)
def update_call_status_info(**kwargs):
	try:
		args = frappe._dict(kwargs)
		parent_call_sid = args.ParentCallSid
		update_call_log(parent_call_sid, status=args.CallStatus)

		call_info = {
			"ParentCallSid": args.ParentCallSid,
			"CallSid": args.CallSid,
			"CallStatus": args.CallStatus,
			"CallDuration": args.CallDuration,
			"From": args.From,
			"To": args.To,
		}

		client = Twilio.get_twilio_client()
		client.calls(args.ParentCallSid).user_defined_messages.create(content=json.dumps(call_info))
	except Exception:
		frappe.log_error(title=_("Failed to update Twilio call status"))


def get_datetime_from_timestamp(timestamp):
	from datetime import datetime
	from zoneinfo import ZoneInfo

	if not timestamp:
		return None

	datetime_utc_tz_str = timestamp.strftime("%Y-%m-%d %H:%M:%S%z")
	datetime_utc_tz = datetime.strptime(datetime_utc_tz_str, "%Y-%m-%d %H:%M:%S%z")
	system_timezone = frappe.utils.get_system_timezone()
	converted_datetime = datetime_utc_tz.astimezone(ZoneInfo(system_timezone))
	return frappe.utils.format_datetime(converted_datetime, "yyyy-MM-dd HH:mm:ss")


# ============================================================================
# VOICE MVP - VAPI INTEGRATION (NEW)
# ============================================================================

@frappe.whitelist()
def initiate_outbound_call(to_number, contact_id=None, topic=None, context=None):
	"""
	Initiate outbound call via Vapi AI agent.
	Called by Farfalle voice orchestration layer.
	
	Args:
		to_number: Phone number to call (E.164 format)
		contact_id: Optional CRM Contact ID to link
		topic: Call topic/purpose
		context: Additional context for AI agent
		
	Returns:
		dict: {success: bool, call_sid: str, call_log_id: str, message: str}
	"""
	import requests
	from datetime import datetime
	
	try:
		# Get Vapi credentials from site config or env
		vapi_api_key = frappe.conf.get('vapi_api_key') or frappe.get_site_config().get('vapi_api_key')
		vapi_agent_id = frappe.conf.get('vapi_agent_id') or frappe.get_site_config().get('vapi_agent_id')
		
		if not vapi_api_key or not vapi_agent_id:
			frappe.throw(_("Vapi configuration missing. Set vapi_api_key and vapi_agent_id in site_config.json"))
		
		# Create CRM Call Log first
		call_log = frappe.get_doc({
			"doctype": "CRM Call Log",
			"type": "Outgoing",
			"to": to_number,
			"from": frappe.db.get_single_value("CRM Twilio Settings", "twilio_number"),
			"status": "initiated",
			"medium": "Vapi AI",
			"started_at": datetime.now(),
		})
		
		# Link to contact if provided
		if contact_id:
			call_log.contact = contact_id
		
		# Add context as note
		if topic or context:
			note_content = []
			if topic:
				note_content.append(f"Topic: {topic}")
			if context:
				note_content.append(f"Context: {context}")
			call_log.note = "\n".join(note_content)
		
		call_log.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Initiate Vapi call
		vapi_url = "https://api.vapi.ai/call/phone"
		headers = {
			"Authorization": f"Bearer {vapi_api_key}",
			"Content-Type": "application/json"
		}
		
		payload = {
			"phoneNumberId": vapi_agent_id,  # Vapi phone number/agent ID
			"customer": {
				"number": to_number,
			},
			"assistant": {
				"firstMessage": f"Hello! {topic or 'I am calling from your CRM system.'}"
			}
		}
		
		# Add custom context if provided
		if context:
			payload["assistant"]["context"] = context
		
		response = requests.post(vapi_url, json=payload, headers=headers, timeout=10)
		response.raise_for_status()
		
		vapi_data = response.json()
		call_sid = vapi_data.get('id')  # Vapi call ID
		
		# Update call log with Vapi call ID
		call_log.provider_call_id = call_sid
		call_log.status = "in-progress"
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		
		return {
			"success": True,
			"call_sid": call_sid,
			"call_log_id": call_log.name,
			"message": "Call initiated successfully"
		}
		
	except requests.exceptions.RequestException as e:
		frappe.log_error(f"Vapi API Error: {str(e)}", "Vapi Call Initiation Failed")
		return {
			"success": False,
			"error": str(e),
			"message": "Failed to initiate call with Vapi"
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Voice Call Initiation Error")
		return {
			"success": False,
			"error": str(e),
			"message": "Internal error initiating call"
		}


@frappe.whitelist(allow_guest=True)
def vapi_webhook(**kwargs):
	"""
	Webhook endpoint for Vapi call events.
	Receives real-time events: call started, ended, transcript updates.
	
	Expected events:
		- call.started: Call connected
		- call.ended: Call completed
		- transcript.update: Live transcript chunk
		- assistant.request: AI processing
	"""
	try:
		args = frappe._dict(kwargs)
		event_type = args.get('type') or args.get('event')
		call_id = args.get('call', {}).get('id') if isinstance(args.get('call'), dict) else args.get('call_id')
		
		if not call_id:
			frappe.log_error("No call ID in Vapi webhook", "Vapi Webhook Error")
			return {"status": "error", "message": "Missing call ID"}
		
		# Find corresponding CRM Call Log
		call_logs = frappe.get_all(
			"CRM Call Log",
			filters={"provider_call_id": call_id},
			fields=["name"],
			limit=1
		)
		
		if not call_logs:
			# Call log might not exist yet, create placeholder
			frappe.log_error(f"Call log not found for Vapi call: {call_id}", "Vapi Webhook")
			return {"status": "ok", "message": "Call log not found"}
		
		call_log = frappe.get_doc("CRM Call Log", call_logs[0].name)
		
		# Handle different event types
		if event_type in ['call.started', 'call-started']:
			call_log.status = "in-progress"
			call_log.started_at = frappe.utils.now_datetime()
			
		elif event_type in ['call.ended', 'call-ended', 'call.completed']:
			call_log.status = "completed"
			call_log.ended_at = frappe.utils.now_datetime()
			
			# Calculate duration
			if call_log.started_at and call_log.ended_at:
				from frappe.utils import time_diff_in_seconds
				call_log.duration = time_diff_in_seconds(call_log.ended_at, call_log.started_at)
			
			# Extract transcript and summary
			call_data = args.get('call', {})
			transcript = call_data.get('transcript') or call_data.get('messages', [])
			summary = call_data.get('summary') or args.get('summary')
			
			# Create FCRM Note with call summary/transcript
			if transcript or summary:
				note_content = []
				
				if summary:
					note_content.append(f"**Call Summary:**\n{summary}")
				
				if transcript:
					note_content.append("\n**Transcript:**")
					if isinstance(transcript, list):
						for msg in transcript:
							role = msg.get('role', 'unknown')
							content = msg.get('content', '')
							note_content.append(f"- **{role.title()}**: {content}")
					else:
						note_content.append(str(transcript))
				
				# Create note linked to call log
				note = frappe.get_doc({
					"doctype": "FCRM Note",
					"title": f"Call Summary - {call_log.to}",
					"content": "\n".join(note_content),
					"reference_doctype": "CRM Call Log",
					"reference_docname": call_log.name,
				})
				note.insert(ignore_permissions=True)
				
				# Create follow-up ToDo if needed
				if summary and any(keyword in summary.lower() for keyword in ['follow up', 'callback', 'next step']):
					todo = frappe.get_doc({
						"doctype": "ToDo",
						"description": f"Follow up on call with {call_log.to}: {summary[:200]}",
						"reference_type": "CRM Call Log",
						"reference_name": call_log.name,
						"allocated_to": frappe.session.user,
						"status": "Open",
					})
					todo.insert(ignore_permissions=True)
		
		elif event_type in ['transcript.update', 'transcript-update']:
			# Real-time transcript update (optional handling)
			pass
		
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		
		return {"status": "ok", "message": "Event processed"}
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Vapi Webhook Processing Error")
		return {"status": "error", "message": str(e)}
