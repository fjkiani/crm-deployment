### CRM Architecture Overview

### Backend (Frappe app: `crm`)
- `hooks.py`: app icon/route, website routes, doc_events, after_migrate
- `www/crm.py` + `www/crm.html`: serves `/crm` with boot context
- `api/*`: whitelisted endpoints used by the SPA
- `fcrm/doctype/*`: domain DocTypes and server logic
- `integrations/*`: Twilio/Exotel webhooks and actions
- `patches/*`: data migrations and defaults

### Frontend (Vue app)
- `frontend/src`: pages (Leads, Deals, Organizations, Contacts, Tasks, Dashboard), components, stores
- Built artifacts live in `public/frontend` and load at `/crm`

### Data model
- Core: `CRM Lead`, `CRM Deal`, `CRM Organization`, Contact(s), Task, Call Log
- Config: Statuses, View Settings, Fields Layout, Settings

### Flows
- Lead → Deal (with status pipeline)
- Activities: comments, emails, WhatsApp, calls, tasks
- Telephony & messaging: Twilio/Exotel handlers

### Hooks (from `crm/hooks.py`)
- App selector permission: `crm.api.check_app_permission`
- Doc events:
  - `Contact.validate`: `crm.api.contact.validate`
  - `ToDo.after_insert|on_update`: `crm.api.todo.*`
  - `Comment.on_update`: `crm.api.comment.on_update`
  - `WhatsApp Message.validate|on_update`: `crm.api.whatsapp.*`
  - `CRM Deal.on_update`: ERPNext Customer creation hook (if configured)
- Overrides: `Contact`, `Email Template`
- Website routes: `/crm/<path:app_path>` → `crm`
- After migrate: `fcrm_settings.after_migrate`

### Integrations (endpoints)
- Twilio (`crm/integrations/twilio/api.py`)
  - `is_enabled` (whitelist), `generate_access_token` (whitelist)
  - `voice` (allow_guest), `twilio_incoming_call_handler` (allow_guest)
  - `update_recording_info` (allow_guest), `update_call_status_info` (allow_guest)

- Exotel (`crm/integrations/exotel/handler.py`)
  - `handle_request` (allow_guest), `make_a_call` (whitelist), others

### Background work
- Realtime: `frappe.publish_realtime` for call events
- Enqueue: e.g., bulk delete in `crm/api/doc.py`
- Migrations: `patches/v1_0/*.py` and `after_migrate`

### LLM integration plan (phase 1)
Goal: agent can “read + act” via existing whitelisted APIs with context.

1) Context graph
- New describe endpoints to expose: DocType meta, API catalog, hooks

2) Tooling endpoints (new)
- `crm.api.tools.list_endpoints` → list callable endpoints with params
- `crm.api.tools.describe_doctype` → meta + relationships
- `crm.api.tools.search` → cross-entity search

3) Guarded action layer
- `crm.api.agent.run` with structured commands (create_lead, add_note, outreach), permissions, idempotency, audit

4) Prompt/context
- Provide user role, installed modules, API catalog, DocType meta, examples

5) Testing scaffold
- Golden-path: create lead, add note, convert to deal, assign, send WhatsApp (if enabled)
- Negative: permission denied, invalid fields, dedup
- Smoke: ping each `crm.api.*` for 200/403/422
