import frappe


def execute():
	"""Add provider mapping fields to Communication for external email threads."""
	add_custom_field(
		dt="Communication",
		fieldname="provider",
		label="Provider",
		fieldtype="Data",
		help="Email provider key, e.g., gmail",
	)
	add_custom_field(
		dt="Communication",
		fieldname="provider_message_id",
		label="Provider Message ID",
		fieldtype="Data",
		help="External message ID from provider",
	)
	add_custom_field(
		dt="Communication",
		fieldname="provider_thread_id",
		label="Provider Thread ID",
		fieldtype="Data",
		help="External thread/conversation ID from provider",
	)


def add_custom_field(dt: str, fieldname: str, label: str, fieldtype: str, help: str = ""):
	if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
		return
	cf = frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": dt,
			"fieldname": fieldname,
			"label": label,
			"fieldtype": fieldtype,
			"insert_after": "subject",
			"description": help,
		}
	)
	cf.insert(ignore_permissions=True)
	frappe.clear_cache(doctype=dt)


