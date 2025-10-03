import os
import requests
from typing import Any, Dict, Optional


class CrmClient:
	"""Minimal CRM HTTP client with session cookies and CSRF token.
	Env:
	- CRM_BASE_URL, CRM_USER, CRM_PASSWORD (or CRM_API_KEY if available)
	"""

	def __init__(self, base_url: Optional[str] = None):
		self.base_url = (base_url or os.getenv('CRM_BASE_URL', '')).rstrip('/')
		self.s = requests.Session()
		self.csrf = None

	def login(self) -> None:
		user = os.getenv('CRM_USER')
		pwd = os.getenv('CRM_PASSWORD')
		if not (self.base_url and user and pwd):
			raise RuntimeError('Missing CRM_BASE_URL/CRM_USER/CRM_PASSWORD')
		res = self.s.post(f"{self.base_url}/api/method/login", data={
			'usr': user,
			'pwd': pwd,
		})
		res.raise_for_status()
		# CSRF cookie
		for c in self.s.cookies:
			if c.name == 'csrf_token':
				self.csrf = c.value
				break

	def post(self, method: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		if not self.csrf:
			self.login()
		h = {'X-Frappe-CSRF-Token': self.csrf, 'Content-Type': 'application/json'}
		url = f"{self.base_url}/api/method/{method}"
		res = self.s.post(url, headers=h, json=json or {})
		if res.status_code == 403 and 'CSRF' in res.text:
			# refresh CSRF and retry once
			self.csrf = None
			self.login()
			h['X-Frappe-CSRF-Token'] = self.csrf
			res = self.s.post(url, headers=h, json=json or {})
		res.raise_for_status()
		data = res.json()
		return data.get('message') if isinstance(data, dict) else data
