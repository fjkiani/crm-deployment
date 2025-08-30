### EAIA (Executive AI Assistant) ↔ CRM Email Integration

This guide wires the external EAIA service to CRM for email triage, drafting, and sending.

#### 1) Provision credentials
- Create a limited user in CRM (role: can call email + agent endpoints).
- Generate API Key/Secret: User → API Access.
- Optional: IP allowlist on your ingress.

#### 2) Deploy EAIA
- Repo: `assistant/executive-ai-assistant-main` (LangGraph)
- Configure `.env`/`config.yaml` with Gmail OAuth (or service account where appropriate).
- Ensure scripts: `scripts/setup_gmail.py`, `scripts/run_single.py`, `scripts/run_ingest.py` work locally.

#### 3) Required CRM endpoints
- Inbox/context: `crm.api.email.get_inbox`, `crm.api.email.thread_context`
- Draft/send: `crm.api.email.save_draft`, `crm.api.email.send`
- Provider mapping: `crm.api.email.link_provider_ids`
- Agent router: `crm.api.agent.run` (email.* commands)

#### 4) ID mapping
- Patch adds `provider`, `provider_message_id`, `provider_thread_id` to `Communication`.
- EAIA should set these via `link_provider_ids` for reconciliation.

#### 5) EAIA → CRM calls (examples)
- Draft response:
  - Call `crm.api.agent.run` with `email.draft` and params {reference_doctype, reference_name, to, subject, html, provider_thread_id}
- Link IDs:
  - Call `crm.api.agent.run` with `email.link_provider_ids` {communication_name, provider, provider_message_id, provider_thread_id}
- Send approved draft:
  - Call `crm.api.agent.run` with `email.send` {communication_name}

Use HTTP: `POST /api/method/<path>` with `Authorization: token <api_key>:<api_secret>`.

#### 6) Human Inbox (UI)
- A realtime event `crm_email_draft_created` is published on draft save.
- Build a list view subscribing to this channel to surface drafts for approval.

#### 7) Testing flow
1) Inbound Gmail → EAIA triage → EAIA posts thread summary to CRM notes (optional)
2) EAIA drafts reply → `save_draft` (agent.run email.draft)
3) User approves in CRM → `send`
4) EAIA links provider IDs for sent message → `link_provider_ids`

#### 8) Ops
- Monitor scheduler/email queue and EAIA logs.
- Add rate limits on EAIA → CRM if needed.


