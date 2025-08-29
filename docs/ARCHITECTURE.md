# Architecture Overview

## Backend (Frappe app: `crm`)
- `hooks.py`: app icon/route, website routes, doc_events, after_migrate
- `www/crm.py` + `www/crm.html`: serves `/crm` with boot context
- `api/*`: whitelisted endpoints used by the SPA
- `fcrm/doctype/*`: domain DocTypes and server logic
- `integrations/*`: Twilio/Exotel webhooks and actions
- `patches/*`: data migrations and defaults

## Frontend (Vue app)
- `frontend/src`: pages (Leads, Deals, Organizations, Contacts, Tasks, Dashboard), components, stores
- Built artifacts live in `public/frontend` and load at `/crm`

## Data model
- Core objects: Lead, Deal, Organization, Contact(s), Task, CallLog
- Config: Statuses, View Settings, Fields Layout, Settings

## Flows
- Lead → Deal (with status pipeline)
- Activities: comments, emails, WhatsApp, calls, tasks
- Telephony & messaging: Twilio/Exotel handlers

## Integrations (endpoints)
- Twilio (`crm/integrations/twilio/api.py`)
  - `is_enabled` (whitelist)
  - `generate_access_token` (whitelist)
  - `voice` (allow_guest) – webhook that returns TwiML
  - `twilio_incoming_call_handler` (allow_guest)
  - `update_recording_info` (allow_guest)
  - `update_call_status_info` (allow_guest)

- Exotel (`crm/integrations/exotel/handler.py`)
  - `handle_request` (allow_guest) – incoming webhook
  - `make_a_call` (whitelist) – outgoing call
  - Additional status/update helpers

## Background work
- Realtime: `frappe.publish_realtime` for call events
- Hooks: `doc_events` (validate/update triggers)
- Migrations: `patches/v1_0/*.py` and `after_migrate` hook
