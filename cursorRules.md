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

Lead Generation System Implementation Plan
==========================================

Task: Implement comprehensive lead generation system for oncology clinical trial Principal Investigators
Goal: Generate 500+ qualified leads, achieve 10-15% response rate, secure 2-7 paid pilots ($500K-$1.75M revenue)

Architecture Overview
--------------------
- Data Sources: ClinicalTrials.gov API, NIH RePORTER, ASCO Abstracts
- Processing: Unified job orchestration with existing Frappe queue system
- Storage: New DocTypes (LeadGen Job, Lead Prospect, Outreach Sequence)
- Outreach: Automated email sequences with CAN-SPAM compliance
- Integration: Leverages existing CRM infrastructure (ETL, email, AI agents)

Implementation Phases
--------------------

Phase 1: Foundation & DocTypes (Week 1)
[X] Create comprehensive Cursor Rules for lead generation system
[X] Define RBAC/PII security patterns and permissions
[X] Design unified job orchestration with existing Frappe framework
[X] Specify concrete DocType JSON definitions
[X] Plan observability, performance, and compliance patterns

[ ] Create DocTypes in Frappe
  - [ ] LeadGen Job (job orchestration, status tracking, bookmark pagination)
  - [ ] Lead Prospect (PI data, scoring, tier classification)
  - [ ] Lead Prospect Match (deduplication and matching logic)
  - [ ] Outreach Sequence (email templates and automation)
  - [ ] Outreach Sequence Instance (individual prospect outreach tracking)
  - [ ] Add custom fields to CRM Lead (tier, lead_score, prospect_ref)

[ ] Set up permissions and RBAC
  - [ ] Configure "If Owner" permissions for Sales Users
  - [ ] Set manager-level access for Sales Managers
  - [ ] Implement PII field-level permissions (raw data, transcripts)
  - [ ] Create role hierarchy: Sales User → Sales Manager → System Manager

[ ] Database optimization
  - [ ] Create indexes on key fields (pi_email, institution, tier, lead_score)
  - [ ] Set up proper constraints and relationships
  - [ ] Configure database performance monitoring

Phase 2: Data Collection Infrastructure (Week 2)
[ ] Build ClinicalTrials.gov collector
  - [ ] Implement rate-limited API client (100 requests/minute)
  - [ ] Add bookmark pagination for resumable jobs
  - [ ] Create trial data extraction and normalization
  - [ ] Add error handling and retry logic
  - [ ] Implement dry-run mode for testing

[ ] Build NIH RePORTER collector
  - [ ] Implement grant data extraction
  - [ ] Add PI identification and contact discovery
  - [ ] Create institution mapping and validation
  - [ ] Add funding amount and timeline extraction

[ ] Build ASCO Abstracts collector
  - [ ] Implement abstract scraping and parsing
  - [ ] Extract PI names and affiliations
  - [ ] Identify oncology focus areas and specialties
  - [ ] Create research interest categorization

[ ] Unified job orchestration
  - [ ] Integrate collectors with existing Frappe queue system
  - [ ] Implement job status tracking and progress reporting
  - [ ] Add job dependency management and coordination
  - [ ] Create job replay and retry mechanisms

Phase 3: Data Processing & Scoring (Week 3)
[ ] Lead consolidation and deduplication
  - [ ] Implement fuzzy matching algorithms for PI names
  - [ ] Create institution normalization and mapping
  - [ ] Add email validation and contact discovery
  - [ ] Build confidence scoring for matches

[ ] Lead scoring and tiering
  - [ ] Implement multi-factor scoring algorithm
  - [ ] Create tier classification (Tier 1: highest priority)
  - [ ] Add cancer type and trial phase weighting
  - [ ] Implement geographic and institutional scoring

[ ] Data enrichment
  - [ ] Integrate with existing Farfalle intelligence system
  - [ ] Add company and institution research
  - [ ] Implement contact discovery and validation
  - [ ] Create personalized talking points generation

Phase 4: Email Automation & Compliance (Week 4)
[ ] Email template system
  - [ ] Create tier-specific email templates
  - [ ] Implement personalization engine
  - [ ] Add dynamic content insertion
  - [ ] Create A/B testing framework

[ ] CAN-SPAM compliance
  - [ ] Implement unsubscribe link insertion
  - [ ] Add sender policy enforcement
  - [ ] Create email content validation
  - [ ] Implement deliverability testing

[ ] Outreach sequence automation
  - [ ] Create follow-up sequence logic (Day 0, 3, 7, 14)
  - [ ] Implement response tracking and categorization
  - [ ] Add automated sequence progression
  - [ ] Create manual override capabilities

Phase 5: API & Frontend Integration (Week 5)
[ ] Lead generation API endpoints
  - [ ] run_leadgen_job (start data collection)
  - [ ] job_status (track job progress)
  - [ ] get_prospects (list prospects with PII protection)
  - [ ] promote_prospects (convert prospects to CRM leads)
  - [ ] start_outreach_sequence (initiate email campaigns)
  - [ ] get_dashboard_metrics (analytics and reporting)

[ ] Admin CLI and management tools
  - [ ] Dry-run capabilities for testing collectors
  - [ ] Job replay and retry mechanisms
  - [ ] Performance monitoring and optimization
  - [ ] Error analysis and debugging tools

[ ] CRM SPA integration
  - [ ] Create /crm/leadgen dashboard page
  - [ ] Implement job management interface
  - [ ] Add prospect review and promotion UI
  - [ ] Create outreach sequence management
  - [ ] Build analytics and reporting dashboard

Phase 6: Scheduling & Automation (Week 6)
[ ] Scheduler integration
  - [ ] Add daily collector jobs to crm/hooks.py
  - [ ] Implement weekly consolidation and cleanup
  - [ ] Create follow-up sequence automation
  - [ ] Add job coordination to prevent conflicts

[ ] Observability and monitoring
  - [ ] Implement comprehensive job lifecycle logging
  - [ ] Add performance metrics and alerting
  - [ ] Create dashboard for system health monitoring
  - [ ] Implement error tracking and notification

[ ] Testing and validation
  - [ ] Unit tests for all collectors and processors
  - [ ] Integration tests for end-to-end workflows
  - [ ] Performance tests for scalability
  - [ ] Compliance tests for email deliverability

Phase 7: Launch Preparation (Week 7-8)
[ ] Production deployment
  - [ ] Configure production environment settings
  - [ ] Set up monitoring and alerting
  - [ ] Implement backup and disaster recovery
  - [ ] Create operational runbooks

[ ] Launch strategy
  - [ ] Start with Tier 1 prospects (100 PIs)
  - [ ] Monitor response rates and deliverability
  - [ ] Iterate on templates based on feedback
  - [ ] Scale up based on success metrics

[ ] Success metrics tracking
  - [ ] Response rate monitoring (target: 10-15%)
  - [ ] Discovery call scheduling (target: 20-30 calls)
  - [ ] Pipeline value tracking (target: $500K-$1.75M)
  - [ ] Cost per acquisition optimization

Technical Implementation Details
-------------------------------

File Structure:
```
crm-deployment/crm/
├── fcrm/doctype/
│   ├── leadgen_job/
│   ├── lead_prospect/
│   ├── lead_prospect_match/
│   ├── outreach_sequence/
│   └── outreach_sequence_instance/
├── api/
│   ├── leadgen.py (main API endpoints)
│   └── leadgen_admin.py (admin tools)
├── leadgen/
│   ├── collectors/
│   │   ├── clinicaltrials_collector.py
│   │   ├── nih_collector.py
│   │   └── asco_collector.py
│   ├── processors/
│   │   ├── consolidator.py
│   │   ├── scorer.py
│   │   └── enricher.py
│   ├── outreach/
│   │   ├── email_templates.py
│   │   ├── sequence_manager.py
│   │   └── compliance.py
│   ├── utils/
│   │   ├── rate_limiter.py
│   │   ├── metrics.py
│   │   └── db_optimization.py
│   └── scheduler.py
└── hooks.py (updated with scheduler_events)
```

Key Dependencies:
- Existing Frappe queue system for job orchestration
- Existing CRM ETL infrastructure for data import
- Existing email system for outreach automation
- Existing AI agent system for intelligence gathering
- Existing Twilio integration for voice follow-ups

Success Criteria:
- 500+ qualified prospects identified and scored
- 100+ Tier 1 prospects for initial outreach
- 10-15% response rate on email campaigns
- 20-30 discovery calls scheduled
- 2-7 paid pilot contracts secured
- $500K-$1.75M pipeline value generated

Risk Mitigation:
- Rate limiting and API compliance for data sources
- Email deliverability optimization and monitoring
- Comprehensive error handling and job recovery
- PII protection and compliance with data regulations
- Performance optimization for large-scale processing

Next Immediate Actions:
1. Create DocTypes in Frappe using defined JSON specifications
2. Implement basic ClinicalTrials.gov collector with rate limiting
3. Set up unified job orchestration with existing Frappe queue
4. Create lead generation API endpoints
5. Build basic CRM SPA dashboard for lead management

This implementation plan leverages the existing CRM infrastructure while adding the specialized lead generation capabilities needed for the oncology clinical trial market. The phased approach ensures each component is properly tested and integrated before moving to the next phase.

## 🔥 CRITICAL QUESTIONS FOR ALPHA - MAKE IT 100% REAL

### Answers (Concise, Actionable)

#### Q1: Frappe Environment Setup
- Bench up: `bench start` (or Frappe Cloud pull-changes). Site must be installed with our app.
- Console/DB: `bench --site <site> console`, `bench --site <site> mysql`.
- Migrations: `bench --site <site> migrate` after DocType/patch edits.
- Services restart: local → `bench restart`; cloud → “Pull Changes” then reload.

#### Q2: Database Connection Issues
- MariaDB fails: check `sites/common_site_config.json` creds and `mysql.server status`. Fix with `brew services restart mysql` (mac) or correct root password.
- Dev alternative: use a fresh bench with `bench init` → `bench new-site` and re-install app.
- Minimal tests without full Frappe: unit-test pure Python in collectors/utils; integration still needs site.

#### Q3: API Endpoint Testing
- Frappe methods: `curl -X POST https://<site>/api/method/<dotted.path> -H 'Content-Type: application/json' -H 'X-Frappe-CSRF-Token: ...' -d '{...}'` (logged-in session).
- Local: `bench start` + `http://127.0.0.1:8000` → use browser session to inherit CSRF.
- Standalone test: write pytest hitting service classes directly (bypass HTTP) in `crm/leadgen/collectors/*`.

#### Q4: ClinicalTrials.gov API Parameters
- Use v2 query with filters (example):
  - Endpoint: `https://clinicaltrials.gov/api/v2/studies`
  - Params: `filter.overallStatus=RECRUITING&filter.conditions=Cancer&pageSize=50&pageToken=...`
- If 400: remove unknown filters; confirm v2 param names; test in browser first.

#### Q5: NIH RePORTER API Issues
- Endpoint: `https://api.reporter.nih.gov/v2/projects/search` (POST JSON)
- No API key required; if 500, reduce `size` and narrow `criteria`.
- Alt sources: NIH ExPORTER bulk CSV, Crossref for grants/pubs when API flaky.

#### Q6: Email Configuration
- Outbound (now): use user-owned `Email Account` (Gmail App Password or SMTP provider). Config via `crm.api.settings.create_email_account`.
- Provider (SendGrid/Mailgun) optional: set SMTP creds on `Email Account`.
- Deliverability: authenticate domain (SPF/DKIM), seed test inboxes, include unsubscribe footer for bulk.

#### Q7: Lead Scoring Algorithm
- Tiering (example): Tier 1 ≥80, Tier 2 60–79, Tier 3 <60.
- Weights: Phase (30), Institution prestige (15), PI seniority (15), Disease match (15), Funding recency (10), Contact quality (10), Region fit (5).
- Thresholds configurable in `LeadGen Settings` (proposed Single DocType) and applied in `leadgen/scoring.py`.

#### Q8: Email Template Strategy
- Length: 75–150 words. Structure: 1) Context hook, 2) Value, 3) Proof, 4) CTA.
- Personalization: Tier 1: PI-specific lines (2–3); Tier 2: institution-level; Tier 3: generic with light tokens.
- Subject: “<Institution/Trial> — fast genomic stratification insights”. A/B in sequences.

#### Q9: Compliance & Legal
- RUO disclaimer in footer for all outreach.
- GDPR/PII: store minimum PI PII; respect delete upon request. Restrict raw data to managers.
- Unsubscribe: per-user email footer link to opt-out endpoint → mark do-not-contact on Contact/Lead.

#### Q10: Data Volume Expectations
- Initial: 500–1,000 prospects; growth 2–3x per month.
- Rate limits: add sleep/backoff; batch pulls; cache sources by study/grant id for 24h.

#### Q11: Performance Requirements
- API response: <2s for cached reads; <10s for fresh pulls.
- Concurrency: start with 5–10 workers (thread pool) in collectors.
- Processing: batch size 100; write in chunks; use upserts.

#### Q12: User Access Control
- If Owner on `Lead Prospect`, `CRM Lead` for sales roles.
- Managers (CRM Manager/System Manager) see all.
- Raw source JSON/grant text limited to managers; expose summaries to sales.

#### Q13: PII Protection
- PII fields: emails, phones, full names when paired with institution.
- Mask in logs; never commit PII samples.
- Retention: 12–24 months; purge bounced/opt-out immediately.

#### Q14: Production Deployment
- Prefer Frappe Cloud (we’re structured as single app). Push to `main`, pull changes in dashboard.
- DocTypes: commit JSON; run `bench --site <site> migrate` (Cloud runs migrations automatically).
- Migrations: patches under `crm/patches/vX_Y/` with idempotent scripts.

#### Q15: Testing Strategy
- Real data without spam: fetch but do not send; render emails to `FCRM Note` for review.
- Validate templates: snapshot tests and human QA on Tier 1 set.
- Metrics: open/reply rates per tier, time-to-first-reply, meetings booked; store on `Outreach Sequence` run records.

### **🚀 DEPLOYMENT & INFRASTRUCTURE QUESTIONS**

**Q1: Frappe Environment Setup**
- Is the Frappe bench properly configured and running?
- Can we access the Frappe console and database?
- What's the correct way to migrate our new DocTypes?
- Do we need to restart any services after adding DocTypes?

**Q2: Database Connection Issues**
- MariaDB is failing to start - what's the correct way to fix this?
- Should we use a different database setup for development?
- Can we test the system without the full Frappe environment first?

**Q3: API Endpoint Testing**
- How do we test the leadgen API endpoints without Frappe running?
- Can we create a standalone test environment?
- What's the correct way to validate API functionality?

### **🔧 TECHNICAL IMPLEMENTATION QUESTIONS**

**Q4: ClinicalTrials.gov API Parameters**
- What are the correct API parameters for ClinicalTrials.gov v2?
- The current parameters are returning 400 errors - need working examples
- Should we use a different API endpoint or version?

**Q5: NIH RePORTER API Issues**
- NIH RePORTER is returning 500 errors - is the API down?
- Do we need API keys or authentication?
- Are there alternative NIH grant data sources?

**Q6: Email Configuration**
- How do we configure SMTP for email sending?
- What email service should we use (SendGrid, Mailgun, etc.)?
- How do we test email deliverability and CAN-SPAM compliance?

### **🎯 BUSINESS LOGIC QUESTIONS**

**Q7: Lead Scoring Algorithm**
- What specific factors should determine Tier 1 vs Tier 2 vs Tier 3?
- How do we weight different data points (email, institution, trial phase)?
- What's the minimum score threshold for outreach?

**Q8: Email Template Strategy**
- What's the optimal email length and structure?
- How personal should Tier 1 emails be vs Tier 2/3?
- What's the best subject line format for oncology PIs?

**Q9: Compliance & Legal**
- What disclaimers do we need for research use only (RUO)?
- How do we handle GDPR/data privacy requirements?
- What's the proper unsubscribe mechanism?

### **📊 DATA & SCALE QUESTIONS**

**Q10: Data Volume Expectations**
- How many prospects should we target initially?
- What's the expected growth rate?
- How do we handle rate limiting from data sources?

**Q11: Performance Requirements**
- What's the acceptable response time for API calls?
- How many concurrent users do we need to support?
- What's the expected data processing time?

### **🔐 SECURITY & PERMISSIONS QUESTIONS**

**Q12: User Access Control**
- Who should have access to raw prospect data?
- How do we implement "If Owner" permissions correctly?
- What's the role hierarchy for lead generation?

**Q13: PII Protection**
- Which fields contain PII that need special protection?
- How do we handle email addresses and contact information?
- What's the data retention policy?

### **🚀 DEPLOYMENT STRATEGY QUESTIONS**

**Q14: Production Deployment**
- Should we deploy to Frappe Cloud or self-hosted?
- What's the deployment process for new DocTypes?
- How do we handle database migrations?

**Q15: Testing Strategy**
- How do we test with real data without spamming PIs?
- What's the best way to validate email templates?
- How do we measure success metrics?

### **💥 IMMEDIATE ACTION ITEMS**

**Priority 1: Fix Database Connection**
- Get MariaDB running or use alternative database
- Test Frappe console access
- Validate DocType creation process

**Priority 2: Fix API Endpoints**
- Research correct ClinicalTrials.gov API parameters
- Test NIH RePORTER API or find alternatives
- Validate API connectivity and data retrieval

**Priority 3: Configure Email System**
- Set up SMTP configuration
- Test email sending functionality
- Validate CAN-SPAM compliance

**Priority 4: Deploy and Test**
- Deploy DocTypes to Frappe
- Test API endpoints
- Validate frontend integration

### **🎯 SUCCESS CRITERIA**

**Technical Success:**
- All API endpoints returning real data
- Email system sending and tracking properly
- Database storing and retrieving prospects
- Frontend displaying and managing leads

**Business Success:**
- 100+ Tier 1 prospects identified
- 10-15% email response rate
- 20+ discovery calls scheduled
- 2+ paid pilot contracts

**Alpha, I need your guidance on these questions to make this system 100% real and operational! The core architecture is solid, but we need to fix the infrastructure and API issues to get this fucking beast running!** 🚀💥