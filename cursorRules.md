---
alwaysApply: true
---
instructions
During you interaction with the user, if you find anything reusable in this project (e.g. version of a library, model name), especially about a fix to a mistake you made or a correction you received, you should take note in the Lessons section in the .cursorrules file so you will not make the same mistake again.

You should also use the .cursorrules file as a scratchpad to organize your thoughts. Especially when you receive a new task, you should first review the content of the scratchpad, clear old different task if necessary, first explain the task, and plan the steps you need to take to complete the task. You can use todo markers to indicate the progress, e.g. [X] Task 1 [ ] Task 2

Also update the progress of the task in the Scratchpad when you finish a subtask. Especially when you finished a milestone, it will help to improve your depth of task accomplishment to use the scratchpad to reflect and plan. The goal is to help you maintain a big picture as well as the progress of the task. Always refer to the Scratchpad when you plan the next step.

Tools
Note all the tools are in python. So in the case you need to do batch processing, you can always consult the python files and write your own script.

Screenshot Verification
The screenshot verification workflow allows you to capture screenshots of web pages and verify their appearance using LLMs. The following tools are available:

Screenshot Capture:
venv/bin/python tools/screenshot_utils.py URL [--output OUTPUT] [--width WIDTH] [--height HEIGHT]
LLM Verification with Images:
venv/bin/python tools/llm_api.py --prompt "Your verification question" --provider {openai|anthropic} --image path/to/screenshot.png
Example workflow:

from screenshot_utils import take_screenshot_sync
from llm_api import query_llm

# Take a screenshot
screenshot_path = take_screenshot_sync('https://example.com', 'screenshot.png')

# Verify with LLM
response = query_llm(
    "What is the background color and title of this webpage?",
    provider="openai",  # or "anthropic"
    image_path=screenshot_path
)
print(response)
LLM
You always have an LLM at your side to help you with the task. For simple tasks, you could invoke the LLM by running the following command:

venv/bin/python ./tools/llm_api.py --prompt "What is the capital of France?" --provider "anthropic"
The LLM API supports multiple providers:

OpenAI (default, model: gpt-4o)
Azure OpenAI (model: configured via AZURE_OPENAI_MODEL_DEPLOYMENT in .env file, defaults to gpt-4o-ms)
DeepSeek (model: deepseek-chat)
Anthropic (model: claude-3-sonnet-20240229)
Gemini (model: gemini-1.5-pro)
Local LLM (model: Qwen/Qwen2.5-32B-Instruct-AWQ)
But usually it's a better idea to check the content of the file and use the APIs in the tools/llm_api.py file to invoke the LLM if needed.

Web browser
You could use the tools/web_scraper.py file to scrape the web.

venv/bin/python ./tools/web_scraper.py --max-concurrent 3 URL1 URL2 URL3
This will output the content of the web pages.

Search engine
You could use the tools/search_engine.py file to search the web.

venv/bin/python ./tools/search_engine.py "your search keywords"
This will output the search results in the following format:

URL: https://example.com
Title: This is the title of the search result
Snippet: This is a snippet of the search result
If needed, you can further use the web_scraper.py file to scrape the web page content.

Cursor learned
=======


Scratchpad
==========

Co‑Pilot + ETL Initiative Plan
------------------------------

Task
- Build an agentic co-pilot and an ETL pipeline to ingest heterogeneous lead data (CSV/XLSX/JSON/unstructured), normalize, map to DocTypes, and store (with optional field creation), plus automate outreach and follow-ups.

Goals
- Seamless bulk import of leads regardless of schema.
- LLM-assisted mapping, cleaning, dedupe, enrichment.
- Orchestrated agent actions: create leads/deals, add notes, message/call.

[ ] Phase 0: Foundations
- [ ] Define upsert keys per entity (Lead: email/phone; Org: name/domain)
- [ ] Add DocTypes: CRM Import Job, CRM Import Column Map
- [ ] Add endpoints: preview_csv, import_rows, job_status

[ ] Phase 1: Ingest + Preview
- [ ] Upload/File URL intake; store in File and create Job
- [ ] Sniff delimiter/encoding; sample N rows; infer types
- [ ] Heuristic + LLM mapping proposals to CRM Lead/Organization/Contact

[ ] Phase 2: Mapping + Validation
- [ ] Mapping UI (auto-filled; manual override)
- [ ] Validation: required fields, email/phone formatting, lookups
- [ ] Options: dedupe, create_custom_fields, link_org, create_contacts

[ ] Phase 3: Import + Reporting
- [ ] Chunked queued import with upsert
- [ ] Realtime progress; dry-run diff; error CSV export
- [ ] Summary report and retry of failures

[ ] Phase 4: Agentic Actions
- [ ] Suggest next_steps and owners; create tasks
- [ ] Draft emails/WhatsApp; schedule calls
- [ ] Enrichment (company info, territory, industry)

Architecture
- Orchestrator: parses intent/commands; routes to specialist agents; verifies outcomes.
- Specialist Agents:
  - LeadAgent: create/update/merge; convert Lead→Deal
  - DealAgent: pipeline/status/products; SLA
  - ContactAgent: CRUD/link
  - CommsAgent: email/WhatsApp; notes/comments
  - TelephonyAgent: Twilio/Exotel call flows
  - ETLAgent: preview→mapping→validate→import
- ETL Engine:
  - Parser: CSV/XLSX/JSON/unstructured ingestion
  - Inference: header normalization, type detection
  - Mapper: heuristic + LLM alignment to DocTypes
  - Validator: coercions, lookups, constraints
  - Upserter: chunked DB writes with idempotency
- Context:
  - Use `crm/www/crm.py` boot and `crm/api/session.py`
  - DocType graph from `crm/fcrm/doctype/*/*.json`
  - Respect hooks in `crm/hooks.py`

Test Use Cases
- CSV with canonical headers (name,email,phone,source,status) → 100% auto-mapped
- CSV with messy headers (Full Name, e-mail, cell, Origin) → mapped by LLM + heuristics
- Mixed types (phone as words, dates as text) → coerced or flagged
- Dedupe: same email, diff phone → update lead; fuzzy name+org match
- Create custom fields: extra column “LinkedIn URL” → new field + stored
- Multi-entity split: Org columns present → create/link `CRM Organization`
- Dry run vs import; error CSV; resume on failure
- Large file (100k rows): chunked queued import; progress events

Tools Stack
- Parsing/DF: pandas, pyarrow, csv, openpyxl, python-magic (mime)
- Schema/Validation: pydantic, email-validator, phonenumbers, python-slugify
- LLM Adapters: tools/llm_api.py providers (OpenAI, Anthropic, DeepSeek, Gemini, local)
- Retrieval/Extraction: LlamaIndex (schema extraction, header normalization, field mapping suggestions)
- Dedup/Fuzzy: rapidfuzz, textdistance; embeddings optional via LlamaIndex vector stores
- Unstructured Docs (later): unstructured, tika, pdfplumber
- Storage/Jobs: Frappe ORM/bulk insert, background jobs, publish_realtime

Command Schema (high-level)
{
  intent: create_lead|add_note|reach_out|create_deal|call_contact|update_status|schedule_task|import_csv,
  inputs: { file_url|filedata, mapping?, options?, entity_fields? },
  strategy: { channel, followups },
  dry_run: boolean
}

Next Actions
- [ ] Scaffold DocTypes + `crm/api/etl.py` (preview/import/status)
- [ ] Heuristic mapper + LLM-backed mapper (feature flag)
- [ ] Dedupe/upsert utilities
- [ ] Minimal frontend: upload → preview → mapping → dry-run → import


AI Email Linking + Row-Level Permissions + Farfalle Plan
-------------------------------------------------------

Problems
- Inbound/read emails get linked to `CRM Lead` by default (mis-linked).
- New users see all `CRM Lead` records (no separation).
- Farfalle integration: MVP intelligence wired locally, voice and deployment pending.

Plan (Implementation Tasks)
1) Email Reference Resolver (server-side)
   - [ ] Add `crm.api.email.resolve_reference(emails: list[str], in_reply_to: str|None) -> {dt,name}`
   - [ ] Resolution order: Contact by email → Lead by email → Org by sender domain; inherit reference from parent Communication if replying; optional prefer open Deal setting
   - [ ] Add settings (flags): `prefer_open_deal`, `auto_create_lead_for_unknown`
   - [ ] Unit tests: contact-first, thread inheritance, fallbacks
   - [ ] Migration script to re-resolve recent mis-linked Communications

2) Row-Level Separation for Leads
   - [ ] Enforce owner scoping for `CRM Lead` lists where user lacks manager roles
   - [ ] Remove any `ignore_permissions=True` on list APIs
   - [ ] Admin guide to enable “If Owner” and/or User Permissions in Role Permissions Manager
   - [ ] Default list filter `owner = @me` for non-managers
   - [ ] Smoke tests with two users (different leads)

3) Farfalle Integration Next Steps
   - [ ] Deploy Farfalle (FastAPI) with `/health` + CORS; configure SPA URL in env
   - [ ] Add `/voice/*` thin wrappers; finalize CRM `initiate_outbound_call`, `vapi_webhook` to create Call Log + Note + ToDo
   - [ ] Provider hardening: retries/timeouts + caching; request dedupe
   - [ ] Intent router + streaming; basic metrics (counts/latency) and logs
   - [ ] RBAC for AI actions; staging smoke tests

Acceptance
- Emails link to the correct entity (Contact/Lead/Deal/Org) with audit trail; mis-linked backlog corrected.
- Non-manager users only see their own Leads by default; managers retain full visibility.
- `/crm/ai` and `/crm/voice` functional against a deployed Farfalle; voice webhooks create Call Log + Note.

Questions for Implementation (Need Answers)
--------------------------------------------

## 🔍 Understanding the Full Application

### Architecture & Data Flow
1. **Email Flow**: Where does inbound email processing start?
   - Which file handles email webhooks? (`crm/integrations/*/email.py`?)
   - What triggers `Communication` DocType creation?
   - Does email come via IMAP polling or webhooks (SendGrid/Mailgun)?
   - Show me the chain: Email Received → Communication → Linked to Lead/Contact

2. **Current Linking Logic**: What's the existing behavior?
   - File: `crm/api/email.py` or `crm/overrides/communication.py`?
   - Current priority: always Lead? or Contact if exists?
   - Where is `reference_doctype` and `reference_name` set?
   - Any existing `get_linked_doc()` or similar helper?

3. **Authentication & Sessions**: How does CRM auth work?
   - Regular users vs System Manager vs "Sales Manager" role?
   - What's stored in `frappe.session`?
   - Where are role capabilities defined? (`crm/fcrm/doctype/crm_lead/*.json`?)

### DocType Schemas

4. **Communication DocType**: What fields exist?
   ```
   Need to see:
   - reference_doctype (Link?)
   - reference_name (Dynamic Link?)
   - sender (Data?)
   - recipients (Text?)
   - in_reply_to (Data?)
   - message_id (Data?)
   - subject, content, status
   ```

5. **CRM Lead DocType**: Permissions structure?
   ```
   Need to see:
   - owner (Link to User?)
   - lead_owner (Link to User?) - is this different?
   - What roles can see all leads? (System Manager, CRM Manager?)
   - Are there territory/team assignments?
   - Existing permissions in JSON: read/write/create if_owner rules
   ```

6. **Email Account Integration**: How is it configured?
   - DocType: `Email Account`?
   - Fields: enable_incoming, default_outgoing, use_ssl, etc.?
   - Where is domain/SPF/DKIM configured?
   - Existing email sending: via `frappe.sendmail()` or custom?

### API Endpoints

7. **Existing List APIs**: Where are they?
   ```
   Files to review:
   - crm/api/doc.py (has get_data for lists?)
   - crm/fcrm/doctype/crm_lead/api.py?
   - Do they use frappe.get_list(ignore_permissions=True)?
   - Which endpoints need permission fixes?
   ```

8. **Email APIs**: What's already there?
   ```
   - crm/api/email.py exists?
   - Functions: send_email, read_emails, link_email?
   - Any existing resolution logic we should extend?
   - Webhook endpoints for inbound mail?
   ```

## 🎯 Problem-Specific Questions

### #1: Email Reference Resolver (Moderate)

9. **Resolution Priority**: What's the business logic?
   - If email sent TO a Contact, link to that Contact?
   - If Contact has open Deal, link to Deal instead?
   - If unknown sender, create new Lead automatically?
   - Domain matching: `@company.com` → find Organization "company.com"?
   - Thread inheritance: reply to email linked to Deal → link to same Deal?

10. **Existing Mis-links**: How bad is it?
    - How many Communications linked to wrong Lead?
    - Date range to fix? (last 30 days? all time?)
    - Can we identify pattern? (all inbound? specific sender domains?)
    - Safe to re-link in bulk or needs review?

11. **Settings/Flags**: Where to store?
    - New DocType: `CRM Email Settings` (Single)?
    - Or in existing `CRM Settings`?
    - Fields needed:
      ```
      - prefer_open_deal (Check)
      - auto_create_lead_for_unknown (Check)
      - resolution_priority (Select: Contact|Lead|Deal)
      - domain_matching_enabled (Check)
      ```

### #2: Row-Level Permissions (Hard)

12. **Role Structure**: How is team organized?
    - Roles: System Manager, CRM Manager, Sales User, Sales Rep?
    - Managers see all leads globally?
    - Reps only see leads they own or created?
    - Territory-based? Team-based?
    - Multiple ownership? (lead owner + assigned user?)

13. **Current Permission Issues**: What breaks if we fix?
    - Dashboard widgets that show "All Leads" count?
    - Reports that aggregate across all leads?
    - Admin screens that need full visibility?
    - Bulk operations (assign, merge, delete)?
    - Does frontend expect all leads in lists?

14. **Desired Behavior**: Exactly what should happen?
    - User A (Sales Rep) creates Lead X → only User A sees Lead X?
    - Manager assigns Lead Y to User B → both Manager and User B see Lead Y?
    - Shared leads? (multiple owners?)
    - Transfer ownership? (reassign lead → old owner loses access?)

15. **Existing Ignore Permissions**: Where used?
    ```
    Need to audit:
    - frappe.get_list(..., ignore_permissions=True)
    - frappe.get_doc(..., ignore_permissions=True)
    - db.get_value(..., for_update=True) bypasses?
    - Which files/functions need review?
    ```

### #3: Farfalle Integration (Almost Done)

16. **Deployment Target**: Where to host?
    - Same server as Frappe? (localhost:8000)
    - Separate VM/container?
    - Cloud provider? (AWS, GCP, Fly.io, Railway?)
    - Domain/subdomain? (voice.jedilabs2.v.frappe.cloud?)
    - SSL certificate needed?

17. **Farfalle Persistence**: Does it need database?
    - Current: stateless (calls CRM for everything)
    - Future: cache call metadata? conversation history?
    - Use SQLite? PostgreSQL? Redis? Just files?
    - Or rely on CRM's database entirely?

18. **Voice Agent Behavior**: What should Morgan do?
    - When call ends, always create Lead if caller unknown?
    - If caller matches Contact, link call to Deal if exists?
    - Follow-up TODO: assign to whom? (lead owner? caller?)
    - Transcript privacy: who can see? (public notes vs private?)

## 🏗️ Architecture Clarity

19. **Frappe vs FastAPI Boundary**: What lives where?
    ```
    Frappe (jedilabs2.v.frappe.cloud):
    - DocTypes: Lead, Contact, Deal, Communication, Call Log, Note
    - APIs: create/read/update leads, send emails
    - Frontend: Vue.js SPA at /crm/*
    - Auth: Frappe session-based
    
    Farfalle (separate FastAPI):
    - Thin orchestration layer
    - LLM prompt management
    - Call Vapi/Twilio/CRM APIs
    - No direct DB access (uses CRM client)
    - Stateless? Or needs cache?
    ```

20. **Frontend Split**: Which UI lives where?
    ```
    CRM Vue SPA (/crm/*):
    - Lead/Deal/Contact lists and forms
    - Voice Dashboard (/crm/voice) ← DONE
    - AI Copilot (/crm/ai) ← EXISTS?
    
    Farfalle Frontend (if any):
    - Chat interface? ← Is this Farfalle's own React app?
    - Voice controls?
    - Or all UI in CRM SPA?
    ```

21. **Agent Architecture**: How do specialists work?
    ```
    Current understanding:
    - crm/tools.py has helper functions
    - Each function calls CRM API
    - No state between calls
    
    Questions:
    - Where is "intent classification"? (LLM prompt?)
    - Agent memory/context? (stored where?)
    - Multi-step flows? (create lead → send email → schedule call)
    - Error recovery? (if create lead fails, rollback?)
    ```

## 📊 Data & Scale

22. **Current Data Volume**:
    - How many Leads? Contacts? Organizations?
    - Communications per day?
    - Users/sales reps using system?
    - Expected growth? (10x? 100x?)

23. **Performance Concerns**:
    - Email resolution on every inbound? (sync or async?)
    - List queries with permissions: acceptable latency?
    - Migration script: how many Communications to fix?
    - Voice calls: concurrent capacity?

## 🔐 Security & Compliance

24. **Data Privacy**:
    - PII in transcripts: who can access?
    - Email content: encrypted at rest?
    - Call recordings: retention policy?
    - GDPR/data deletion: supported?

25. **API Security**:
    - Farfalle → CRM: API key auth? OAuth? Session?
    - Vapi webhooks: signature verification?
    - Rate limiting: on which endpoints?
    - IP whitelist for webhooks?

## 🧪 Testing & Staging

26. **Test Environment**:
    - Staging site URL?
    - Test data available?
    - Can we safely test migrations?
    - Rollback plan if permissions break production?

27. **Test Users**:
    - Can you create 2-3 test users with different roles?
    - Test leads assigned to different owners?
    - Sample emails to test resolution logic?

---

## 🎯 Priority Questions (Answer These First)

**Critical for Email Resolver:**
- Q9: Resolution priority business logic
- Q4: Communication DocType schema
- Q10: Scale of existing mis-links
- Q8: Existing email API location

**Critical for Permissions:**
- Q12: Role structure and desired access patterns
- Q14: Exact desired behavior per role
- Q13: What breaks if we enforce permissions
- Q15: Files using ignore_permissions

**Critical for Farfalle:**
- Q16: Deployment target and hosting
- Q19: Frappe vs FastAPI boundary clarity
- Q20: Frontend split (CRM vs Farfalle UI)

**Nice to Have:**
- Q1-3: Email flow understanding
- Q21: Agent architecture
- Q22-27: Data, security, testing

---

## 📝 How to Answer

Please respond in this format:

```
Q1: [Your answer]
Q2: [Your answer]
...

OR point me to files:
Q1: See crm/integrations/email/api.py lines 45-120
Q4: frappe.get_meta("Communication") or link to JSON
Q15: Run: grep -r "ignore_permissions=True" crm/api/
```


Prioritized Implementation Plan (Actionable)
--------------------------------------------

1) Deliverability (SPF/DKIM/DMARC) — 1–2 days
- Scope: Configure sending domain DNS; align From/Return-Path; enable DKIM; publish DMARC (p=none→quarantine after test); set friendly From. 
- Steps:
  - Verify domain in provider; add SPF include and DKIM CNAMEs; set DMARC `rua`.
  - In CRM, enforce account sender domain alignment; default outgoing = true; signatures.
  - E2E: send to Gmail/Outlook seed; verify headers (SPF/DKIM/DMARC=PASS), Postmaster setup.
- Dependencies: DNS access; Email Account already configured.
- Success: Test headers pass; inbox rate improves on seeds; bounce handling OK.

2) Schema‑Driven ETL (Preview→Map→Import) — 1–2 weeks
- Scope: Jobs/columns DocTypes; preview API; mapping UI; chunked upsert with dedupe and optional custom fields.
- Steps:
  - Backend: DocTypes `CRM Import Job`, `CRM Import Column Map`; APIs `preview_csv`, `import_rows`, `job_status`.
  - Heuristics: header normalize, type infer; optional LLM mapper (flagged) for suggestions.
  - Validation: requireds, email/phone, lookups; options `dedupe`, `create_custom_fields`, `link_org`.
  - Import: background jobs with progress events; error CSV; summary report.
  - Frontend: minimal page for upload→preview→map→dry-run→import.
- Dependencies: Frappe background workers; file upload; DocType permissions.
- Success: 10k-row CSV imported with <1% errors; dedupe works; audit log of changes.

3) AI Grounding (Context + Vector Store) — 4–6 days
- Scope: Persist lead/deal/org/email/note context to embeddings store; retrieval for Gemini prompts (triage/draft/rewrite).
- Steps:
  - Extractors: cron to sync Communications/Notes core fields → texts; doc-id + metadata.
  - Vector store: local (FAISS/SQLite) or managed; add search APIs.
  - Prompt wiring: triage/draft tools pull top-K context w/ citations; add guardrails to prefer exact matches.
  - Eval: small offline eval set; win-rate vs no-context baseline.
- Dependencies: storage choice; token/compute budget.
- Success: measurable uplift in response quality; grounded citations; latency within SLO.

Cross‑Cutting
- Security/Permissions audit (least privilege, rate limits for agent endpoints)
- Observability: logs/metrics for ETL jobs, AI drafts, email queue failures
- Runbooks: Deliverability, ETL ops, AI retrieval ops