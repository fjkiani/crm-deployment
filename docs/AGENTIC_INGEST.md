### Agentic Dataset Ingest (arbitrary structured dataset → Lead Prospect)

A dataset-agnostic ingest path: drop in an arbitrary structured dataset (nested JSON
or a File) and the app maps → normalizes → stages → imports it through Frappe's native
Data Import primitives — **without hand-authoring per-dataset code**. The first validated
test case is the AACR-2026 talk corpus (862 records). The hard core is the **field-mapping
kernel** (arbitrary source schema → target DocType field metadata).

This complements the existing `crm/api/etl.py` import pipeline (which is tabular/CSV-only and
never targeted `Lead Prospect`). It does not replace it — it reuses `import_rows`/`process_job`
downstream.

---

#### 1) What it does — the three closed gaps

1. **JSON projection** (`crm/api/etl_json.py`). Flattens arbitrary nested records to dot-paths
   (e.g. `speaker.name`) with array reduction policies (`first` / `join` / `last` / `count`,
   default `join`), emitting the same `{headers, rows}` shape the kernel already consumes.
2. **Agentic mapping proposer** (`crm/api/etl_json.py::propose_mapping_agentic`). Doctype-meta
   driven (`frappe.get_meta(target).fields`), parameterized by target DocType.
   - **Tier 1 — deterministic:** exact / alias / fuzzy match on field name + label.
   - **Tier 2 — LLM fallback** (only for fields Tier 1 can't confidently map; gated by `use_llm`).
   - Output is persisted as a reviewable **CRM Import Column Map** with per-column
     `confidence`/`basis`, a `status` (`Draft` / `Needs Review` / `Approved`), and a
     `source_signature` for auto-reuse.
3. **Agentic orchestrator** (`crm/api/leadgen.py::run_dataset_ingest`, whitelisted). Chains
   propose-mapping → CSV materialization → `etl.import_rows` (dry-run first). Emits a
   `LeadGen Job` (`job_type="dataset_ingest"`) for observability, mirroring `run_leadgen_job`.

Lead Prospect upsert (`crm/api/etl.py::_upsert_lead_prospect`) is idempotent on `source_ref_id`.

---

#### 2) Behavior — propose-and-pause, then auto-reuse

On **first sight** of a new source schema the orchestrator returns `stage="mapping_review"` with
the profile left as `Needs Review` — it does **not** silently import. A human reviews/approves the
`CRM Import Column Map` in the Frappe UI. On the **next** run, a matching `source_signature` with an
`Approved` status is auto-reused and the import proceeds (`stage="imported"`).

Required-field gaps (target fields with `reqd=1` that nothing mapped to — e.g. `tier`, `source` for
`Lead Prospect`) are surfaced in `unmapped_required` so the reviewer fills them before approval.

---

#### 3) How to trigger

**A. Server-side (`bench execute`)**
```bash
bench --site alpha-crm.frappe.cloud execute crm.api.leadgen.run_dataset_ingest \
  --kwargs '{"target_doctype": "Lead Prospect", "file_url": "/files/aacr2026.json", "dry_run": 1, "use_llm": 1}'
```

**B. HTTP (whitelisted method)**
```bash
POST /api/method/crm.api.leadgen.run_dataset_ingest
Authorization: token <api_key>:<api_secret>
Content-Type: application/json

{"target_doctype": "Lead Prospect", "file_url": "/files/aacr2026.json", "dry_run": 1, "use_llm": 1}
```

**C. eaia agent (LangGraph)**
`assistant/executive-ai-assistant-main/eaia/agents/ingest.py` provides `zi_ingest_agent` and a
standalone `ingest_army` graph (`build_ingest_graph()`, single node `ingestor`). It calls the
whitelisted method over REST with `use_llm=1`. Invoke with state fields: `ingest_file_url` (or
`ingest_records_json`), `ingest_target_doctype` (default `Lead Prospect`), `ingest_dry_run`
(default `1`), optional `ingest_profile_name`. It is a **separate** graph, not wired into the
GTM `army` pipeline.

---

#### 4) `run_dataset_ingest` parameters

| Param | Default | Meaning |
|---|---|---|
| `target_doctype` | `"Lead Prospect"` | Destination staging DocType. |
| `records_json` / `file_url` | — | Provide one. Inline JSON array/envelope, or a File URL. |
| `profile_name` | `ingest::<doctype>::<now>` | CRM Import Column Map name. |
| `array_policy` | `"join"` | Array reduction: `first`/`join`/`last`/`count`. |
| `dry_run` | `1` | Count rows that would upsert without writing. |
| `auto_approve_deterministic` | `0` | If set, auto-approve a clean Tier-1-only mapping with no LLM fills and no required gaps. |
| `use_llm` | `0` | Enable the server-side Tier-2 Gemini mapping pass. |
| `_llm_complete` | `None` | In-process callable; takes precedence over `use_llm` (same-process callers only). |

**The `use_llm` flag** lets a REST/agent trigger enable the LLM tier without shipping a Python
callable across the process boundary: when truthy, the proposer builds its own server-side Gemini
callable (`_default_llm_complete`, lazy `langchain_google_genai`). It degrades gracefully to no
Tier-2 mappings if the dependency or API key is absent — Tier-1 deterministic mapping still runs.

---

#### 5) Target: `Lead Prospect` (staging), not `CRM Lead`

`Lead Prospect` is the staging target for source-driven scientific/clinical data; `CRM Lead` is a
separate, deliberate promotion target (`promoted_to_lead` link). Landing academic PIs (≈73% of the
AACR corpus, no company/AUM) directly as `CRM Lead` would feed the finance-shaped scoring engine
garbage — staging keeps them quarantined until a non-finance scoring path exists.

The 6 confident Tier-1 maps for AACR → Lead Prospect: `talk_id`→`source_ref_id`,
`speaker.name`→`pi_name`, `speaker.affiliation`→`institution`, `tumor_types`→`cancer_type`,
`clinical_stage`→`trial_phase`, `MOA_summary`→`notes`.

---

#### 6) Validation

`validate_ingest_gate.py` (repo root) runs the **real** orchestrator on the **real** AACR-862
dataset with `frappe` stubbed (sandbox cannot execute `@frappe.whitelist()` functions against a
live DB). All 7 assertions pass: pauses at `mapping_review` (no silent import); ≥6 Tier-1 maps;
flags required-field gaps; auto-reuses the approved profile; dry-run counts all 862 rows; 0 errors;
emits a LeadGen Job. The actual Frappe Cloud DB write is the one step still pending a live run.

```bash
python3 validate_ingest_gate.py
```

---

#### 7) Doctype changes (additive)

- **CRM Import Column Map:** `+target_doctype`, `+status`, `+source_signature`
- **CRM Import Column Map Item:** `+confidence`, `+basis`
- **LeadGen Job:** `job_type` options `+dataset_ingest`
