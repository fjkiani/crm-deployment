from typing import Any, Dict, List, Optional
from .client import CrmClient


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
