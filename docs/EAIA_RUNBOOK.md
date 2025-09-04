# EAIA Runbook

## Prereqs
- CRM: API key/secret user with Communication write access
- Email Account configured in CRM
- EAIA: Python venv, `langchain-google-genai` installed
- Secrets placed at `assistant/executive-ai-assistant-main/eaia/.secrets/.env`

Example `.env`:
```
GEMINI_API_KEY=... 
GOOGLE_API_KEY=... 
CRM_SITE=https://<site>
CRM_KEY=...
CRM_SECRET=...
```

## Gmail OAuth
1) Put Google OAuth desktop `secrets.json` in `eaia/.secrets`
2) Run: `.venv/bin/python scripts/setup_gmail_direct.py`

## Run ingest once
```
cd assistant/executive-ai-assistant-main
CRM_SITE=... CRM_KEY=... CRM_SECRET=... \
.venv/bin/python scripts/run_ingest.py --minutes-since 60
```

## Scheduler
```
EAIA_INTERVAL_SEC=300 EAIA_WINDOW_MIN=15 \
.venv/bin/python scripts/scheduler_loop.py
```

## E2E (Draft and optional send)
```
EAIA_TEST_FROM=foo@bar.com EAIA_TEST_TO=me@bar.com \
EAIA_TEST_MESSAGE_ID=test-mid-123 EAIA_TEST_THREAD_ID=test-tid-abc \
EAIA_TEST_SEND=0 \
.venv/bin/python scripts/e2e_crm_send.py
```

## Expected flow
- EAIA ingests Gmail → triage → draft
- On accept, EAIA posts a Draft Communication to CRM
- Human Inbox (/human_inbox or /crm/human_inbox) shows draft → review → send

## Troubleshooting
- 417 on CRM ping: ignore or switch to a token-auth POST endpoint
- No drafts showing: check `eaia/.secrets/processed_ids.json` for idempotency
- Gmail auth errors: ensure Desktop OAuth client and Test User access



