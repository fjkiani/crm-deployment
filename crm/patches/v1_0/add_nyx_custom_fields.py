"""Post-migrate: CRM Lead Nyx custom fields (nyx_score, nyx_enriched, etc.)."""


def execute():
	from crm.scripts.add_nyx_custom_fields import execute as add_fields

	return add_fields()
