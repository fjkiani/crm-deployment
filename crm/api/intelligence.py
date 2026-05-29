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
