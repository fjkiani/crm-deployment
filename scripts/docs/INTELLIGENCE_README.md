# 🧠 Intelligent, Multi‑Agent Business Intelligence System (2025)

This document describes the current, production design of our intelligence system. It replaces legacy notes with a semantic‑first, provider‑backed, multi‑agent approach that reliably returns named decision‑makers, recent investments, and strategic gaps with sources and confidence.

---

## 1) High‑Level Architecture

- Orchestrator: Question‑driven workflow coordinating agents and providers
- Providers (data plane):
  - Tavily (semantic search, raw content)
  - Diffbot (Analyze API for entity extraction from URLs)
  - LinkedIn RapidAPI (company + people endpoints)
  - Gemini (optional synthesis)
  - Bright Data (planned; SERP/news/company datasets)
- Agents (control plane): specialized, composable units that combine providers with domain logic
- Guardrails: answer‑quality detection, escalation to entity extractors, source/citation enforcement
- Outputs: structured JSON (decision_makers, investments, gaps, sources, scores) + optional synthesis

Key implementation:
- `scalable_crm_intelligence/components/services/` → `tavily_client.py`, `diffbot_client.py`, `gemini_synthesizer.py` (planned: `linkedin_client.py`, `brightdata_client.py`)
- `scalable_crm_intelligence/pipelines/semantic_intelligence_pipeline.py`
- `scalable_crm_intelligence/bin/semantic_intel.py` (CLI)
- `scalable_crm_intelligence/ui/streamlit_app.py` (Streamlit UI)

---

## 2) Agents (what we run and why)

1) Decision‑Maker Agent
- Purpose: Return named executives/decision‑makers with titles and links
- Providers: LinkedIn RapidAPI (primary), Diffbot (secondary), Tavily (source discovery)
- Guardrails: If only generic definitions are returned, auto‑escalate; require ≥3 unique people or output “insufficient data” with follow‑ups
- Output: `decision_makers[] = {name, title, linkedin_url?, source_url, source_title?, confidence}`

2) Investment Intelligence Agent
- Purpose: Identify recent investments and portfolio companies relevant to a domain
- Providers: Tavily (include_raw_content), Diffbot (amount/stage extraction), Bright Data (planned filings/news)
- Output: `investments[] = {company, amount?, currency?, date?, stage?, sector?, co_investors?, source_url, confidence}`

3) Gap Analysis Agent
- Purpose: Identify strategic gaps/whitespace and support with evidence
- Providers: Tavily (topic news/analysis), optional Gemini synthesis
- Output: `gaps[] = {statement, evidence_url, rationale, confidence}`

4) Company Resolver Agent
- Purpose: Resolve company → domain → LinkedIn companyId; surface firmographics
- Providers: Tavily (domain inference), LinkedIn RapidAPI (company‑by‑domain), optional Diffbot
- Output: `{name, domain, linkedin_company_id?, employee_count?, industry?}`

5) News & Filings Agent (planned)
- Purpose: Fetch recent news/filings for targeted recall
- Providers: Bright Data (SERP/news datasets), SEC/EDGAR
- Output: curated, deduped sources with topic tags

6) Synthesis Agent (optional)
- Purpose: Convert structured results into cited executive briefings
- Provider: Gemini
- Output: `strategic_synthesis` (never replaces structured JSON)

---

## 3) Orchestration Flow (per company/question)

1) Decompose (if needed) into focuses: decision_makers, investments, gaps
2) Company Resolver → domain and LinkedIn companyId
3) For each focus:
   - Tavily top sources (`include_raw_content` preferred)
   - Guardrail: if Tavily answer is generic/definition‑like → mark low quality
   - If low quality or focus == decision_makers → LinkedIn employees + Diffbot Analyze on top URLs
   - Merge + dedupe entities; score confidence
4) Validate minimum thresholds per focus; add follow‑ups when insufficient
5) Optional: Synthesis Agent composes an executive summary citing counts and confidence

---

## 4) Output Schema

```json
{
  "company": "Abbey Capital",
  "focus_domains": ["healthcare"],
  "analysis_timestamp": "2025-08-30T20:30:02Z",
  "questions_analyzed": 3,
  "total_sources": 24,
  "decision_makers": [
    { "name": "Jane Doe", "title": "Managing Partner", "linkedin_url": "...", "source_url": "...", "confidence": 0.9 }
  ],
  "investments": [
    { "company": "HTA", "amount": 25000000, "currency": "USD", "date": "2024-11-10", "stage": "growth", "source_url": "...", "confidence": 0.8 }
  ],
  "gaps": [
    { "statement": "Underweight in supply‑chain tech", "evidence_url": "...", "rationale": "missed trend in ...", "confidence": 0.75 }
  ],
  "sources": [
    { "title": "Our People - Abbey Capital", "url": "https://www.abbeycapital.com/our-people/" }
  ],
  "strategic_synthesis": "optional text",
  "method": "semantic_pipeline_tavily_llm"
}
```

Notes
- Synthesis never substitutes for structured fields
- Confidence = extraction quality × source authority × cross‑reference

---

## 5) Providers & Usage

Tavily (required)
- Semantic search and ranking; supports `include_answer` and `include_raw_content`
- We prefer `include_raw_content: true` for explicit entity extraction; `include_answer` is never trusted alone

Diffbot (Analyze)
- Entity extraction (people, orgs) from URLs
- Upgrades generic answers, adds named people/titles with sources

LinkedIn RapidAPI
- Decision‑maker resolution via company→employees (title filter)
- Typical endpoints: `get-company-by-domain`, `get-company-employees` / `search-people`
- Title filters: ["Managing Partner","Partner","Founder","CEO","CIO","MD","Managing Director","Director","Head","VP","Investment","Portfolio","Healthcare"]

Bright Data (planned)
- SERP/news/filings data to improve recall for investments/gaps
- Added as another source provider with rate‑limit + caching

Gemini (optional)
- Synthesis only; transforms structured results into an executive briefing citing counts/confidence

---

## 6) Guardrails & Quality Controls

- Generic answer detection: flags definition‑like answers or those lacking proper nouns/company mentions
- Auto‑escalation: Diffbot on top URLs and/or LinkedIn employees endpoint
- Minimum thresholds: e.g., ≥3 decision‑makers for confidence > 0.6; else “insufficient” + follow‑ups
- Domain/source control: `exclude_domains` for low‑signal sites; allowlist for authoritative sources
- Deduplication: normalize name/title; dedupe across providers
- Caching (planned): reduce API costs/latency

---

## 7) Running the System

CLI
```bash
cd /Users/fahadkiani/Desktop/development/crm-deployment/scalable_crm_intelligence
export TAVILY_API_KEY='your_tavily_key'
# Optional
export GEMINI_API_KEY='your_gemini_key'
export DIFFBOT_TOKEN='your_diffbot_token'
export LINKEDIN_RAPIDAPI_KEY='your_rapidapi_key'

python3 bin/semantic_intel.py \
  --company "Abbey Capital" \
  --domains healthcare \
  --question "Who are the decision-makers?" \
  --question "Recent investments in healthcare?" \
  --question "What gaps exist in healthcare?" \
  --max-results 3 \
  --out abbey_semantic_cli.json
```

Streamlit
```bash
cd /Users/fahadkiani/Desktop/development/crm-deployment/scalable_crm_intelligence
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run ui/streamlit_app.py
# Open http://localhost:8501, paste keys, and toggle Diffbot/LinkedIn enrichment
```

---

## 8) Agent → Provider Mapping

- Decision‑Maker Agent → LinkedIn RapidAPI (primary), Diffbot (secondary), Tavily (discovery)
- Investment Agent → Tavily (raw content), Diffbot (amount/stage), Bright Data (planned)
- Gap Analysis Agent → Tavily (thematic) + optional Gemini
- Company Resolver → Tavily (domain), LinkedIn RapidAPI (companyId)
- News & Filings (planned) → Bright Data + SEC/EDGAR
- Synthesis (optional) → Gemini

---

## 9) Configuration

Required
- `TAVILY_API_KEY`

Optional
- `GEMINI_API_KEY` (synthesis)
- `DIFFBOT_TOKEN` (entity extraction)
- `LINKEDIN_RAPIDAPI_KEY` (decision‑maker resolution)
- `LINKEDIN_RAPIDAPI_HOST=linkedin-data-api.p.rapidapi.com`

Pipeline flags (CLI/UI)
- `--domains`, `--question` (repeatable), `--max-results`, exclude/include domain controls

---

## 10) Roadmap

- Add `LinkedInClient` service + pipeline integration (employees pagination, senior title filtering)
- Add `BrightDataClient` for SERP/news/filings; improve investment recall
- Add caching layer for provider calls (per company/domain)
- Add per‑agent confidence/latency metrics

---

## 11) Ethics & Compliance

Use only publicly available data, respect terms of service and privacy laws, and collect/store only what is necessary for the stated business purpose. Prefer official pages and filings where possible.

---

## 12) Troubleshooting

- One‑sentence/generic answers? Enable Diffbot and LinkedIn, and increase `max_results` to 5–7
- Too few decision‑makers? Ensure domain resolution is correct and fetch more employee pages
- High latency? Reduce per‑provider pages and enable caching when available

---

This design turns the system into a reliable, extensible intelligence engine that delivers named decision‑makers, investments, and gaps with sources and confidence—ready for sales, BD, and research workflows.

---

## 13) Lead Enrichment Objectives & KPIs

Primary goal: convert raw leads into meeting‑ready targets with personalized angles.

- Objectives
  - Identify all relevant decision‑makers and influencers (names, titles, LI URLs)
  - Extract recent activity, investments, and triggers tied to our offering
  - Detect explicit gaps/pains with supporting evidence (URLs)
  - Generate tailored messaging angles and call‑to‑actions
  - Prioritize leads by fit, urgency, and contactability

- KPIs
  - Decision‑makers found per account (target ≥3 with confidence ≥0.6)
  - Number of evidence‑backed gaps per account (target ≥2)
  - Outreach readiness score (0–100)
  - Meeting conversion rate (tracked downstream)

---

## 14) Meeting‑Oriented Agent Suite (Deep Dive)

1) Account Profiling Agent
   - Inputs: company name/domain, industry
   - Outputs: firmographics (domain, size, AUM if available, industry, ICP fit hints)
   - Providers: Tavily (domain + overview), LinkedIn company (RapidAPI)

2) Decision‑Maker Graph Agent
   - Inputs: domain, linkedin_company_id
   - Outputs: decision_makers[] with senior titles, LI URLs, location; influence map (basic)
   - Providers: LinkedIn RapidAPI (employees/search), Diffbot (page entities), Tavily for team pages
   - Guardrails: title filters; dedupe by name; confidence score by source authority

3) Gap/Pain Detection Agent
   - Inputs: domain, industry, strategic themes
   - Outputs: gaps[] with statements, evidence URLs, rationale, confidence
   - Providers: Tavily (include_raw_content), Diffbot (extract claims), Bright Data (planned news/filings)
   - Heuristics: look for unmet needs, negative trends, under‑investment patterns, tech debt signals

4) Investment & Signal Agent
   - Inputs: target domain/sector keywords (e.g., healthcare)
   - Outputs: investments[] and trigger signals (new fund, job postings, PR)
   - Providers: Tavily (news/PR), Bright Data (planned SERP/news), Diffbot (entity extraction)

5) Objection & Risk Agent
   - Outputs: likely objections (budget, timing, vendor lock‑in), risk factors, and evidence
   - Providers: Tavily (reviews/forums/press), Diffbot

6) Messaging & Sequencer Agent
   - Inputs: decision_makers[], gaps[], signals[], ICP profile
   - Outputs: 3–5 outreach variants (subject/body/CTA), talk tracks, follow‑up prompts
   - Provider: Gemini (synthesis over structured findings)

---

## 15) Gap Detection Framework

We classify gaps across four axes, each requiring evidence:

- Strategic: whitespace (e.g., missing subsectors), missed partnerships, market timing
- Operational: process bottlenecks (e.g., sourcing, diligence, reporting), tool fragmentation
- Technical: lack of automation/AI, data quality, integrations
- Organizational: missing roles, unclear ownership, hiring patterns

Evidence rules:
- Prefer official pages, filings, reputable trade press
- Extract sentence‑level claims with URLs (Diffbot/Tavily raw content)
- Score confidence by source authority + cross‑source agreement

---

## 16) Prioritization & Scoring

Per lead, compute a meeting‑readiness score (0–100):

- Fit (0–30): industry, size, clear ICP alignment
- Access (0–25): ≥3 decision‑makers with LI URLs, verified contact vectors
- Need (0–30): ≥2 evidence‑backed gaps, recency of signals
- Timing (0–15): recent news/funding/hiring or initiative windows

Score gates:
- <50 → research again; add missing decision‑makers or gaps
- 50–75 → light personalization; 2‑step sequence
- >75 → hyper‑personalized sequence + warm intro strategy

---

## 17) Outreach Generation (Meeting‑Ready)

For each decision‑maker:
- Subject: role‑specific + evidence‑anchored (≤7 words)
- Body: 120–180 words max; cite 1–2 gaps with URLs; show a 1‑line outcome promise; 1 CTA
- PS: second angle (investment or signal)

For the account:
- Talk track bullets (3–5) mapped to gaps
- Objection handling cheatsheet with evidence links

All copy is derived from structured findings and cites counts (e.g., “3 decision‑makers identified; 2 evidence‑backed gaps”).

---

## 18) Implementation Plan (Next Steps)

- Add `LinkedInClient` service and integrate into `SemanticIntelligencePipeline` (employees pagination, title filter)
- Add Bright Data client hooks for news/filings recall; merge with Diffbot extractions
- Implement scoring module (fit/access/need/timing) with thresholds
- Extend Streamlit to display: scores, gaps by axis, outreach variants per decision‑maker
- Add export: JSON + CSV (decision_makers and outreach)
