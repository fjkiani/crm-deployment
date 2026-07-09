# Copyright (c) 2026, Brenus and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NyxBrainSettings(Document):
	"""Single doctype holding the Nyx outreach brain's LLM provider configuration.

	Values here take precedence over site_config / env when resolved by
	crm.api.nyx_email_brain._get_conf, so the provider/model/key can be changed
	from the CRM UI (via crm.api.nyx_email_brain.set_brain_settings) and persist
	in the database across Frappe Cloud redeploys — unlike site_config edits,
	which are wiped when the bench image is rebuilt.

	The read/write API lives in crm.api.nyx_email_brain; this controller is
	intentionally thin.
	"""

	pass
