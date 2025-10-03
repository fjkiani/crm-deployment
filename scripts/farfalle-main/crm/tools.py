from typing import Any, Dict, List, Optional
from .client import CrmClient


# ============================================================================
# VOICE OPERATIONS (NEW)
# ============================================================================

def initiate_voice_call(phone: str, contact_id: Optional[str] = None, 
                       topic: Optional[str] = None, context: Optional[str] = None) -> Dict[str, Any]:
	"""Initiate outbound call via CRM Twilio integration."""
	client = CrmClient()
	payload = {
		'to_number': phone,
		'contact_id': contact_id,
		'topic': topic,
		'context': context
	}
	return client.post('crm.integrations.twilio.api.initiate_outbound_call', json=payload)


def get_call_status(call_sid: str) -> Dict[str, Any]:
	"""Get status of a call from CRM Call Log."""
	client = CrmClient()
	filters = {'provider_call_id': call_sid}
	calls = list_docs('CRM Call Log', filters=filters, limit=1)
	if calls.get('data'):
		return calls['data'][0]
	return {'error': 'Call not found', 'call_sid': call_sid}


def get_voice_dashboard_data() -> Dict[str, Any]:
	"""Get aggregated call analytics for Voice Dashboard."""
	client = CrmClient()
	
	# Get recent calls
	recent_calls = list_docs('CRM Call Log', order_by='creation desc', limit=50)
	
	# Calculate stats
	total_calls = recent_calls.get('total', 0)
	calls_data = recent_calls.get('data', [])
	
	completed = len([c for c in calls_data if c.get('status') == 'completed'])
	failed = len([c for c in calls_data if c.get('status') in ['failed', 'no-answer', 'busy']])
	in_progress = len([c for c in calls_data if c.get('status') in ['initiated', 'ringing', 'in-progress']])
	
	# Calculate total duration (in minutes)
	total_duration = sum(int(c.get('duration', 0)) for c in calls_data) / 60
	
	return {
		'total_calls': total_calls,
		'completed': completed,
		'failed': failed,
		'in_progress': in_progress,
		'average_duration': total_duration / max(completed, 1),
		'recent_calls': calls_data[:10]  # Last 10 for dashboard
	}


def call_with_context(phone: str, company: str, contact_name: Optional[str] = None,
					 contact_id: Optional[str] = None, include_intel: bool = True) -> Dict[str, Any]:
	"""Initiate call with pre-call intelligence context."""
	context_parts = [f"Calling about: {company}"]
	
	if contact_name:
		context_parts.append(f"Contact: {contact_name}")
	
	# TODO: If include_intel, fetch company intelligence
	# For now, just make the call with basic context
	context = " | ".join(context_parts)
	
	return initiate_voice_call(
		phone=phone,
		contact_id=contact_id,
		topic=f"Outreach to {company}",
		context=context
	)


# ============================================================================
# EXISTING CRM OPERATIONS
# ============================================================================

def list_docs(doctype: str, filters: Optional[Dict[str, Any]] = None,
			 fields: Optional[List[str]] = None, order_by: str = 'modified desc', limit: int = 20) -> Dict[str, Any]:
	"""List docs via crm.api.doc.get_data.
	Returns dict with 'data' list.
	"""
	client = CrmClient()
	payload = {
		'doctype': doctype,
		'filters': filters or {},
		'order_by': order_by,
		'page_length': limit,
	}
	# The API returns many fields; requesting columns isn't required but we can post-process if needed
	resp = client.post('crm.api.doc.get_data', json=payload)
	return {
		'data': resp.get('data', []),
		'total': resp.get('total_count', 0),
	}
