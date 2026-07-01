# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt

import frappe
try:
    from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
except Exception:  # pragma: no cover
    def is_fc_site():
        return False
from frappe.utils import cint, get_system_timezone
from frappe.utils.telemetry import capture

no_cache = 1


def get_context(context):
	"""Merge CRM SPA boot into the website context.

	Frappe's ``get_website_settings()`` already sets ``context.boot`` to the
	minimal ``get_boot_data()`` payload (``sysdefaults`` + ``time_zone`` only).
	TemplatePage calls ``get_context(self.context)`` when the function accepts
	an argument — we must merge here, not replace the whole context object.
	"""
	merge_boot(context)
	if frappe.session.user != "Guest":
		capture("active_site", "crm")
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw("This method is only meant for developer mode")
	return get_boot()


@frappe.whitelist(methods=["GET"], allow_guest=True)
def get_spa_boot():
	"""Return SPA boot payload (incl. csrf_token) for clients missing HTML boot."""
	return get_boot()


def merge_boot(context):
	"""Layer CRM boot keys onto any existing website boot dict."""
	boot = frappe._dict(context.get("boot") or {})
	boot.update(get_boot())
	context.boot = boot


def get_boot():
	tz = {
		"system": get_system_timezone(),
		"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
		or get_system_timezone(),
	}
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": get_default_route(),
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"sysdefaults": frappe.defaults.get_defaults(),
			"is_demo_site": frappe.conf.get("is_demo_site"),
			"is_fc_site": is_fc_site(),
			"timezone": tz,
			"time_zone": tz,
		}
	)


def get_default_route():
	return "/crm"
