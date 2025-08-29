# CRM ERD (high-level)

Key relationships:
- CRM Lead → CRM Deal (qualification)
- CRM Deal → CRM Organization (belongs to)
- CRM Deal ↔ CRM Contacts (table)
- CRM Deal → CRM Deal Status (status)
- CRM Deal → CRM Service Level Agreement
- CRM Call Log → CRM Deal (for)
- CRM Task → CRM Deal (for)
- CRM Product ↔ CRM Deal (quoted items)
- Settings: CRM Global/Fields Layout/View Settings, etc.

See DocType JSON under `crm/fcrm/doctype/*/*.json` for fields and link options.
