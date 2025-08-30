import os
import requests


BASE = os.environ.get("CRM_BASE", "http://localhost:8000")
KEY = os.environ["CRM_API_KEY"]
SECRET = os.environ["CRM_API_SECRET"]


def call(method: str, params: dict):
	url = f"{BASE}/api/method/{method}"
	resp = requests.post(url, headers={"Authorization": f"token {KEY}:{SECRET}"}, json=params, timeout=30)
	resp.raise_for_status()
	return resp.json().get("message")


def draft_email(ref_dt, ref_name, to, subject, html, provider_thread_id=None):
	return call(
		"crm.api.agent.run",
		{
			"command": "email.draft",
			"params": {
				"reference_doctype": ref_dt,
				"reference_name": ref_name,
				"to": to,
				"subject": subject,
				"html": html,
				"provider_thread_id": provider_thread_id,
			},
		},
	)


def send_email(comm):
	return call("crm.api.agent.run", {"command": "email.send", "params": {"communication_name": comm}})


if __name__ == "__main__":
	name = draft_email("CRM Lead", "LEAD-0001", "test@example.com", "Hello", "<p>Sample draft</p>")
	print("Draft:", name)
	print("Send:", send_email(name))


