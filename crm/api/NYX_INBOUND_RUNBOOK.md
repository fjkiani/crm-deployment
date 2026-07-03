# NYX Inbound Email — Operator Runbook (reusable / multi-tenant)

Inbound email runs **inside the managed Frappe runtime**. There is **no standalone
Railway/Render EAIA service**. Frappe's built-in `Email Account` (IMAP) pulls mail
and creates a `Communication` per message; `crm.api.nyx_inbound` reacts to those.

## Architecture

```
Gmail (per-tenant app password)
  -> Frappe "Email Account" (IMAP poll, built-in scheduler)      [one per tenant]
  -> Communication (sent_or_received = "Received")
  -> Communication.after_insert hook:
        1) crm.api.email.auto_link_communication      (resolve -> Lead/Deal/Contact)
        2) crm.api.nyx_inbound.route_inbound_communication
  -> if autopilot ON + linked + no pending draft:
        enqueue crm.api.nyx_email_brain.triage_and_draft   (swappable brain)
  -> draft parked in Human Inbox  ->  approve_and_send
```

Everything is best-effort: a failure in routing never interrupts mail ingestion.

## Per-tenant setup (2 steps)

### 1. Provision the mailbox (SMTP send + IMAP poll)

Each tenant supplies **its own** mailbox + Gmail app password. Nothing is hardcoded.

Option A — API (whitelisted):
```
POST /api/method/crm.api.nyx_inbound.provision_gmail_email_account
  email_id=<tenant mailbox>       app_password=<gmail app password>
```

Option B — seed per-tenant config, then call with no args (creds pulled from config):
```
# site_config.json (per site/tenant) OR environment
gmail_user           = <tenant mailbox>          # or env GMAIL_USER
gmail_app_password   = <gmail app password>      # or env GMAIL_APP_PASSWORD
```
```
POST /api/method/crm.api.nyx_inbound.provision_gmail_email_account
```

Creates/updates a Frappe `Email Account`:
`smtp.gmail.com:587` (STARTTLS) for send, `imap.gmail.com:993` (SSL) for poll,
`append_to = CRM Lead`, `default_incoming = 1`. Frappe's scheduler polls IMAP
automatically once `enable_incoming = 1`.

### 2. Turn on auto-triage (opt-in)

Off by default — an unconfigured tenant is a safe no-op (stub). Enable per tenant:
```
nyx_inbound_autopilot = 1     # site_config, env NYX_INBOUND_AUTOPILOT=1
```

Optional per-tenant scoping:
```
nyx_inbound_reference_doctypes = CRM Lead,CRM Deal   # default
nyx_inbound_email_accounts     = <Email Account name(s)>  # default: all incoming
```

## Status check (truthful UI)
```
GET /api/method/crm.api.nyx_inbound.get_inbound_status
-> { autopilot, backend, reference_doctypes, email_accounts[], incoming_configured }
```

## Secrets

Gmail app passwords are secrets. They live on the `Email Account` (encrypted by
Frappe) or in per-tenant `site_config` — **never** in the git repo. For the
current tenant (fahad@crispro.ai) the app password is provided out-of-band and
must be seeded on the live site's config / Email Account by the operator; it is
intentionally not committed here.

## Brain backend

Routing calls `crm.api.nyx_email_brain.triage_and_draft`, which is backend-agnostic:
`frappe` (default, in-runtime) or `eaia` (proxy to an external LangGraph service if
one is ever stood up). Inbound routing does not care which is active.
