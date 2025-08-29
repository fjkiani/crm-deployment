# CRM API Index

Entry points are available via `frappe.call({ method: "<path>", ... })` or REST `POST /api/method/<path>`.

## Core APIs (crm/api)
- crm.api.__init__
  - get_translations (allow_guest)
  - get_user_signature
  - get_posthog_settings
  - accept_invitation (allow_guest)
  - invite_by_email
  - get_file_uploader_defaults
- crm.api.auth: authentication helpers (allow_guest)
- crm.api.session: session and boot APIs
- crm.api.doc: list/filter/group/linked docs/property setters
- crm.api.dashboard: dashboard data and widgets
- crm.api.contact: contact helpers
- crm.api.notifications: notifications
- crm.api.onboarding: onboarding data
- crm.api.user: user info and prefs
- crm.api.views: saved views
- crm.api.whatsapp: WhatsApp actions
- crm.api.activities, comment, settings, demo (some allow_guest)

## Integrations
- crm.integrations.twilio.api (some allow_guest webhooks)
- crm.integrations.exotel.handler (allow_guest webhook)
- crm.integrations.api (helpers)

## DocType-bound (@frappe.whitelist)
- crm.fcrm.doctype.crm_deal.crm_deal: multiple actions (create/update/status)
- crm.fcrm.doctype.crm_lead.crm_lead: conversion helpers
- crm.fcrm.doctype.crm_call_log.crm_call_log: call log creation
- crm.fcrm.doctype.crm_fields_layout.crm_fields_layout: layout CRUD
- crm.fcrm.doctype.crm_view_settings.crm_view_settings: view config
- crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings: ERPNext linkage
- crm.fcrm.doctype.fcrm_settings.fcrm_settings: settings

## Web controller
- crm.www.crm.get_context_for_dev (POST, allow_guest) – dev-only
  Route `/crm` is served by `crm/www/crm.py` using boot context.
