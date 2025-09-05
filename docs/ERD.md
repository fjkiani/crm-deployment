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

## Core link fields (concrete)

- CRM Deal (`crm/fcrm/doctype/crm_deal/crm_deal.json`)
  - `organization` → Link "CRM Organization"
  - `lead` → Link "CRM Lead"
  - `status` → Link "CRM Deal Status"
  - `contacts` → Table "CRM Contacts"
  - `sla` → Link "CRM Service Level Agreement"

- CRM Contacts (child table) (`crm/fcrm/doctype/crm_contacts/crm_contacts.json`)
  - `contact` → Link "Contact"
  - Derived fields from Contact: `full_name`, `email`, `mobile_no`, `phone`, `gender`

- CRM Lead (`crm/fcrm/doctype/crm_lead/crm_lead.json`)
  - `status` → Link "CRM Lead Status"
  - `source` → Link "CRM Lead Source"
  - `industry` → Link "CRM Industry"
  - `lead_owner` → Link "User"

- CRM Organization (`crm/fcrm/doctype/crm_organization/crm_organization.json`)
  - `industry` → Link "CRM Industry"
  - `territory` → Link "CRM Territory"
  - `currency` → Link "Currency"
  - `address` → Link "Address"
