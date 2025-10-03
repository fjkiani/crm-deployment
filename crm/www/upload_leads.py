import frappe


def get_context(context=None):
	return {
		"csrf_token": frappe.sessions.get_csrf_token(),
	}


