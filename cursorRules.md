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