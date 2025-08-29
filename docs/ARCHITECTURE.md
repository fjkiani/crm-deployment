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
