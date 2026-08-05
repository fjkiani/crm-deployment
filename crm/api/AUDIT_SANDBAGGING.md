# CRM Sandbagging Audit + Tab Iteration — Master Report

**Scope:** Deep audit of the 6 lead-page tabs, the content/NotebookLM engine, and
the outreach flywheel, plus a broad shallow sandbagging scan across all ~40 API
modules. Tab frontends built/deepened. All work was **read + code-edit only** — no
endpoint that sends/calls/emails/WhatsApps a real contact was invoked, and the
audit never fired a live outbound endpoint.

**Headline:** The codebase is **largely honest**. Across **51 modules / 621
functions**, the analyzer flagged **37 non-LIVE functions**. On adjudication (every
one traced against real source): **34 benign** (correct-by-design), **2 fixed**,
**1 reported** (no code change needed), **0 requiring quarantine**. The two fixes
close the one real fake-live issue (`_content` claimed the content engine was live
unconditionally) and one misleading docstring.

---

## 1. Method

A stdlib-only AST analyzer classified every whitelisted endpoint / helper in scope.
For each function it records real DB work (`frappe.db`/`get_doc`/`get_all`/`insert`/
`save`), real external work (`requests`/SDK/subprocess), fail-loud behavior
(`raise`/`frappe.throw`), delegation, literal-only returns, hardcoded capability
constants (`live`/`available`/`ok`/`sent`), computed-but-unused availability vars,
and silent except-handler fallbacks. Verdicts:

| Verdict | Meaning |
|---|---|
| **LIVE** | Backed by real DB/external/delegated work, or honest fail-loud |
| **STUB** | Literal-only return, or self-declared placeholder text |
| **HARDCODED_CLAIM** | A capability flag (`live`/`available`) set as a constant — must verify it matches a real check |
| **SILENT_FALLBACK** | An `except` handler returns data instead of raising |
| **REVIEW** | No clear signal — manual read required |

Run in parallel across 5 workers over disjoint module sets (tabs, content,
outreach, comms/nyx, data plane), then merged and adjudicated on worker-0.

**Verdict counts (post-fix, broad re-scan of the edited tree):**

| Verdict | Count |
|---|---|
| LIVE | 580 |
| SILENT_FALLBACK | 23 |
| STUB | 8 |
| HARDCODED_CLAIM | 5 |
| REVIEW | 2 |

(The canonical de-duplicated figure across the in-scope subsystems is **37 non-LIVE
findings**; the broad re-scan counts a few functions twice where subsystems overlap.)

---

## 2. Fixes applied (2) — verified

### FIX 1 — `_content` claimed the content engine was live unconditionally (the anchor finding)
`crm/api/lead_tabs.py::_content` computed `engine_available` and then **ignored it**,
returning `engine.available = True` no matter what. The Content tab therefore
reported the content engine as live even when **no provider was authenticated** —
the exact fake-live pattern this audit targets.

**Now:** availability is derived from `notebooklm_engine.available_providers()`
(presence-only; never returns secret values). Payload:
`engine = {available: any_live, providers, live_kinds, supported_kinds, reason}`.
An import/derivation failure is surfaced as `available: False` with an
`engine_unavailable: …` reason — it is **never** faked-live.

- Re-audit: `_content` verdict is now **LIVE** (tab HARDCODED_CLAIM 2→1).
- Regression test added — `crm/api/tests/test_lead_tabs_content.py` (**15/15 pass**):
  no-credential → `available: False`, reason `no_provider_authenticated`, every
  provider `live: False`; credential present → `available: True`, reason cleared;
  engine failure → `available: False`, providers not fabricated.

### FIX 2 — misleading "returns stub" docstring on real working code
`crm/api/etl.py::import_rows` carried a docstring reading *"Placeholder import
endpoint … returns stub"*, but the body is real (creates a CRM Import Job, inserts
rows, runs/enqueues `process_job`). The analyzer correctly flagged the self-declared
stub text. Docstring rewritten to describe the real behavior; **no behavior change**.
Verdict is **LIVE**.

---

## 3. Reported (1) — no code change, flagged for your call

**`crm/api/plan_generator.py::_steps_from_plan`** — when `draft_outreach_body` cannot
be imported, it falls back to a **local email-draft template**. This is **draft-only**
(never auto-sent), is logged, and is labeled in-code as a fallback. It is not a live
sandbag. **Recommendation:** surface an explicit "fallback template" flag on the plan
card so a reviewer always knows when the local template (vs. the model drafter) was
used. Left unchanged pending your preference.

---

## 4. Full finding enumeration (37) with disposition

Legend: **FIX** applied · **REPORT** flagged, no change · **BENIGN** correct-by-design.

### STUB (8)
| # | Location | Sev | Disposition | Rationale |
|---|---|---|---|---|
| 1 | `etl.py::import_rows` L251 | high | **FIX** | Real Import-Job logic; only the "returns stub" docstring was wrong — rewritten. |
| 2 | `leadgen.py::run_leadgen_job` L67 | high | BENIGN | Honest-empty: when the collector module is absent, returns `status=Unavailable`, `job_name=None`, "No job was queued." Does not fabricate a queued job. |
| 3 | `email.py::_map_triage_action` L571 | med | BENIGN | Pure deterministic map (triage action → literal). |
| 4 | `etl.py::_infer_type` L10 | med | BENIGN | Pure column type-inference helper. |
| 5 | `industry.py::_rank_to_tier` L68 | med | BENIGN | Pure rank→tier lookup. |
| 6 | `nyx_agent.py::_reg` L64 | med | BENIGN | Static tool-registry/config builder. |
| 7 | `nyx_campaigns.py::_default_steps` L132 | med | BENIGN | Default cadence configuration. |
| 8 | `vapi.py::map_outcome_to_status_priority` L79 | med | BENIGN | Deterministic call-outcome → (status, priority) map. |

### HARDCODED_CLAIM (6)
| # | Location | Sev | Disposition | Rationale |
|---|---|---|---|---|
| 9 | `lead_tabs.py::_decision_makers` L135 | med | BENIGN | `available: True` set **only after** confirming the "Decision Maker" doctype exists; honest-empty (`available: False, reason: doctype_not_deployed`) otherwise. Still flags by design — a correct capability signal. |
| 10 | `lead_tabs.py::_content` L219 | med | **FIX** | See Fix 1 — now LIVE, availability derived from a real check. |
| 11 | `notebooklm_engine.py::GeminiProvider.generate` L327 | med | BENIGN | `live: True` set only after a real google-genai SDK call; `check()` raises without a key. |
| 12 | `notebooklm_engine.py::EnterpriseProvider.generate` L397 | med | BENIGN | `live: True` only after a real HTTP call to the enterprise endpoint; `check()` raises without token+project. |
| 13 | `notebooklm_engine.py::UnofficialProvider.generate` L455 | med | BENIGN | `live: True` only after a real CLI run yields an on-disk artifact; raises `NotebookLMError` if none. |
| 14 | `notebooklm_mint.py::mint_from_bundle` L192 | med | BENIGN | `live: True` only after a real CLI+session mint; raises `NotebookLMCredentialError` without a session. |

### SILENT_FALLBACK (21) — every handler returns a safe default / honest error; **none fabricate success** (returns verified individually)
| # | Location | Sev | Disposition | Fallback return |
|---|---|---|---|---|
| 15 | `call_orchestration.py::_grounding` L20 | med | BENIGN | `""` |
| 16 | `enrichment_diag.py::_table_exists` L153 | med | BENIGN | `False` |
| 17 | `enrichment_sources.py::_pm_count` L508 | med | BENIGN | `-1` |
| 18 | `enrichment_sources.py::_pm_efetch_authors` L539 | med | BENIGN | `{}` → PubMed ordering degrades |
| 19 | `etl.py::_missing_required_fields` L781 | med | BENIGN | `[]` |
| 20 | `etl.py::get_spa_boot` L1033 (whitelisted) | med | BENIGN | `False`, then real boot dict |
| 21 | `etl_json.py::_default_llm_complete` L520 | med | BENIGN | `None` → caller degrades to "review" |
| 22 | `intelligence.py::ask_nyx` L8 | med | BENIGN | honest warning string (no fake answer) |
| 23 | `mcp_server.py::update_lead_context` L68 | med | BENIGN | honest JSON-error string |
| 24 | `notebooklm_mint.py::main` L280 | med | BENIGN | CLI exit codes `1`/`2` |
| 25 | `nyx_campaigns.py::_gtm_intel_synced_at` L544 | med | BENIGN | `None` |
| 26 | `nyx_email_brain.py::_nyx_brain_settings_value` L44 | med | BENIGN | `None` |
| 27 | `nyx_email_brain.py::_aacr_talk_for_lead` L451 | med | BENIGN | `None` (or a real doc) |
| 28 | `nyx_email_brain.py::_resolve_llm` L591 | med | BENIGN | `None` |
| 29 | `nyx_inbound.py::_lead_for_reference` L150 | med | BENIGN | `None` |
| 30 | `plan_generator.py::_n_signals_hint` L231 | med | BENIGN | `0` |
| 31 | `plan_generator.py::_signal_floor` L376 | med | BENIGN | `0.0` |
| 32 | `plan_generator.py::_steps_from_plan` L475 | med | **REPORT** | `{}` — but see §3: local email-draft template fallback, draft-only. |
| 33 | `sequence_engine.py::_step_delay` L125 | med | BENIGN | `None` |
| 34 | `sequence_engine.py::_lead_for_instance` L264 | med | BENIGN | `None` |
| 35 | `sequence_engine.py::_completed_call_log` L274 | med | BENIGN | `None` |

### REVIEW (2)
| # | Location | Sev | Disposition | Rationale |
|---|---|---|---|---|
| 36 | `notebooklm_engine.py::_Provider.check` L292 | low | BENIGN | Abstract base — `raise NotImplementedError`. |
| 37 | `notebooklm_engine.py::_Provider.generate` L302 | low | BENIGN | Abstract base — `raise NotImplementedError`. |

**Disposition totals: 2 FIX · 1 REPORT · 34 BENIGN · 0 QUARANTINE. Zero confirmed
sandbags left un-dispositioned.**

---

## 5. Live-write safety (confirmed)

The real send/call paths — `nyx_email_brain.approve_and_send`,
`nyx_email_brain.batch_triage_and_draft`, `email.send` — are all human-gated and
require an explicit, named draft; telemetry failures are logged, not swallowed. The
audit invoked **none** of them. NotebookLM produces no artifact without a real Google
session (proven by the fail-loud tests). Nothing generated is cached. Draft-only is
preserved end to end.

---

## 6. Tab build / iteration

All six lead-page tabs now have consistent **loading / empty / error** states.

| Tab | Change |
|---|---|
| **Engagement** | **New frontend.** Renders tasks / calls / notes / nurture state from the verified real backend builder. Read-only; no writes. |
| **CoPilot** | **New frontend.** Cross-tab cockpit with drill-in cards (emit tab-change) + navigational next-actions (drafts only), embeds the existing Nyx panel. |
| **Content** | Rewritten to honest availability: an amber "not authenticated" banner listing the exact unblock steps (notebooklm login / `GEMINI_API_KEY` / `NOTEBOOKLM_OAUTH_TOKEN`+`GCP_PROJECT`); Generate is disabled until a provider is live. No fabricated artifacts. |
| **Strategic** | Added error banner + Retry; `load()` now catches (previously an unhandled rejection). |
| **Outreach** | Added error banner + Retry; `load()` now catches. |
| **DecisionMakers** | Added error banner + Retry; a load **failure** is now distinct from an **empty** committee (previously both showed "no decision makers"). |

---

## 7. Verification (in-sandbox)

| Check | Result |
|---|---|
| Vue SFC compile (parse + compileScript + compileTemplate), 7 changed files | **7/7 clean** |
| `py_compile` changed Python (`lead_tabs.py`, `etl.py`, new test) | **OK** |
| Broad re-audit of edited tree | `_content` now **LIVE**; no new findings in edited files |
| NotebookLM engine tests (frappe-free) | **31/31 pass** |
| NotebookLM mint tests (frappe-free) | **8/8 pass** |
| `_content` availability regression (new) | **15/15 pass** |

No full production frontend build was run (per plan — that is part of your FC deploy).

---

## 8. Deployment gap — what remains unverified until your redeploy

The new app code is **not yet on the live instance**. Verified live (read-only) today:

- `GET /api/method/crm.api.content_engine.content_providers` → **HTTP 417**, "No module named 'crm.api.content_engine'".
- `GET /api/method/crm.api.lead_tabs.get_tab_data` → **HTTP 417**, "No module named 'crm.api.lead_tabs'".
- Baseline `GET /api/method/frappe.auth.get_logged_user` → **HTTP 200** — the instance is up and serving; the new modules simply are not deployed.

Therefore the fixes and tabs are verified by AST/lint/pytest/static-trace in-sandbox,
but **end-to-end serving requires your Frappe Cloud redeploy/build** — which I cannot
trigger. The frontend `.vue` changes additionally require the FC build step to
compile the SPA source into the served bundle.

---

## 9. Repository topology note (commit target)

`crm-deployment` carries two branches used here:
- **`fc-app-only`** — the app-only deploy artifact (backend `crm/api/` + pre-built
  SPA bundle; tracks **no** `.vue` source). The audit fixes + the new test land here.
- **`feat/wp0-8-engagement-e2e`** — the full SPA source (`frontend/src/`). The `.vue`
  tab changes are tracked here; `fc-app-only` structurally cannot hold `.vue` source
  and no prod build was run.

All pushes target `origin` (crm-deployment) only — never the Brenus remote.
