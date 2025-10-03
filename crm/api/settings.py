import frappe


@frappe.whitelist()
def create_email_account(data):
	service = data.get("service")
	service_config = email_service_config.get(service)
	if not service_config:
		return "Service not supported"

	try:
		email_doc = frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_id": data.get("email_id"),
				"email_account_name": data.get("email_account_name"),
				"service": service,
				"enable_incoming": data.get("enable_incoming"),
				"enable_outgoing": data.get("enable_outgoing"),
				"default_incoming": data.get("default_incoming"),
				"default_outgoing": data.get("default_outgoing"),
				"email_sync_option": "ALL",
				"initial_sync_count": 100,
				"create_contact": 1,
				"track_email_status": 1,
				"use_tls": 1,
				"use_imap": 1,
				"smtp_port": 587,
				**service_config,
			}
		)
		if service == "Frappe Mail":
			email_doc.api_key = data.get("api_key")
			email_doc.api_secret = data.get("api_secret")
			email_doc.frappe_mail_site = data.get("frappe_mail_site")
			email_doc.append_to = "CRM Lead"
		else:
			email_doc.append("imap_folder", {"append_to": "CRM Lead", "folder_name": "INBOX"})
			email_doc.password = data.get("password")
			# validate whether the credentials are correct
			email_doc.get_incoming_server()

		# if correct credentials, save the email account
		email_doc.save()
	except Exception as e:
		frappe.throw(str(e))


email_service_config = {
	"Frappe Mail": {
		"domain": None,
		"password": None,
		"awaiting_password": 0,
		"ascii_encode_password": 0,
		"login_id_is_different": 0,
		"login_id": None,
		"use_imap": 0,
		"use_ssl": 0,
		"validate_ssl_certificate": 0,
		"use_starttls": 0,
		"email_server": None,
		"incoming_port": 0,
		"always_use_account_email_id_as_sender": 1,
		"use_tls": 0,
		"use_ssl_for_outgoing": 0,
		"smtp_server": None,
		"smtp_port": None,
		"no_smtp_authentication": 0,
	},
	"GMail": {
		"email_server": "imap.gmail.com",
		"use_ssl": 1,
		"smtp_server": "smtp.gmail.com",
	},
	"Outlook": {
		"email_server": "imap-mail.outlook.com",
		"use_ssl": 1,
		"smtp_server": "smtp-mail.outlook.com",
	},
	"Sendgrid": {
		"smtp_server": "smtp.sendgrid.net",
		"smtp_port": 587,
	},
	"SparkPost": {
		"smtp_server": "smtp.sparkpostmail.com",
	},
	"Yahoo": {
		"email_server": "imap.mail.yahoo.com",
		"use_ssl": 1,
		"smtp_server": "smtp.mail.yahoo.com",
		"smtp_port": 587,
	},
	"Yandex": {
		"email_server": "imap.yandex.com",
		"use_ssl": 1,
		"smtp_server": "smtp.yandex.com",
		"smtp_port": 587,
	},
}


@frappe.whitelist()
def seed_default_layouts() -> dict:
    """Seed default quick-entry and sidebar field layouts for CRM doctypes.

    Run via: POST /api/method/crm.api.settings.seed_default_layouts
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw("Authentication required")
    try:
        from crm.patches.v1_0.create_default_fields_layout import execute as seed_fields
        from crm.patches.v1_0.create_default_sidebar_fields_layout import (
            execute as seed_sidebar,
        )
        seed_fields()
        seed_sidebar()
        frappe.clear_cache()
        return {"ok": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), title="Seed Default Layouts Failed")
        frappe.throw(f"Seeding failed: {type(e).__name__}: {e}")


@frappe.whitelist()
def seed_all_crm_defaults(force: int = 0) -> dict:
    """Seed all core CRM defaults (statuses, sources, industries, layouts, etc.).

    Run via: POST /api/method/crm.api.settings.seed_all_crm_defaults
    Args:
        force: 1 to overwrite existing layouts
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw("Authentication required")

    try:
        from crm import install as crm_install
        from crm.patches.v1_0.create_default_sidebar_fields_layout import (
            execute as seed_sidebar,
        )

        # Master data
        crm_install.add_default_lead_statuses()
        crm_install.add_default_deal_statuses()
        crm_install.add_default_communication_statuses()
        crm_install.add_default_industries()
        crm_install.add_default_lead_sources()
        crm_install.add_default_lost_reasons()

        # Layouts (quick entry, side panel, data fields)
        crm_install.add_default_fields_layout(force=bool(force))
        seed_sidebar()

        # Property setters, dropdowns, scripts, dashboards
        crm_install.add_property_setter()
        crm_install.add_standard_dropdown_items()
        crm_install.add_default_scripts()
        crm_install.create_default_manager_dashboard(force=bool(force))

        frappe.clear_cache()
        return {"ok": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), title="Seed All CRM Defaults Failed")
        frappe.throw(f"Seeding failed: {type(e).__name__}: {e}")


@frappe.whitelist()
def ensure_import_masters() -> dict:
    """Ensure common import master values exist.

    - CRM Lead Status: Open
    - CRM Lead Source: Research
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw("Authentication required")

    created = []

    # Lead Status: Open
    if not frappe.db.exists("CRM Lead Status", "Open"):
        doc = frappe.new_doc("CRM Lead Status")
        doc.lead_status = "Open"
        doc.color = "gray"
        # place it before New if needed
        doc.position = 0
        doc.insert(ignore_permissions=True)
        created.append("CRM Lead Status: Open")

    # Lead Source: Research
    if not frappe.db.exists("CRM Lead Source", "Research"):
        doc = frappe.new_doc("CRM Lead Source")
        doc.source_name = "Research"
        doc.insert(ignore_permissions=True)
        created.append("CRM Lead Source: Research")

    frappe.clear_cache()
    return {"ok": True, "created": created}
