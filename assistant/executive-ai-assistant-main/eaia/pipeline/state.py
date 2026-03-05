"""
pipeline/state.py — Single source of truth for OutreachState.

All pipeline nodes read/write this TypedDict. Adding a new field here
is the only change needed to expose it across the entire pipeline.

Field groups:
  INPUT       — prospect_name, company_name
  ENRICHMENT  — raw_research, apollo_data, enrichment{}
  SIGNALS     — distilled_signals{}, signal_gate
  SCORING     — score, score_reasoning, score_angle, score_why, framework
  EMAIL       — email_draft{}, ab_subjects
  REVIEW      — review_result, review_feedback, attempt
  CRM         — crm_synced, crm_prospect_id
  SEND        — email_sent, email_error
"""
from typing import TypedDict, Optional, List, Dict, Any


class OutreachState(TypedDict, total=False):
    # ── INPUT ─────────────────────────────────────────────────────────────
    prospect_name: str
    company_name: str

    # ── ENRICHMENT ────────────────────────────────────────────────────────
    raw_research: str          # combined blob fed to signal_distiller
    apollo_data: dict          # raw Apollo /people/match response
    enrichment: dict           # structured: {apollo_title, aum_signal,
                               #   linkedin_profile_headline, linkedin_recent_activity,
                               #   company_strategy, competitor_pressure, ...}

    # ── SIGNALS ───────────────────────────────────────────────────────────
    distilled_signals: dict    # {specific_number, recent_event, strategic_detail,
                               #   blind_spot, recommended_framework}
    signal_gate: str           # "pass:..." | "quarantine:..."

    # ── SCORING ───────────────────────────────────────────────────────────
    score: int                 # 0–100 kill score
    score_reasoning: str       # LLM explanation
    score_angle: str           # specific sales angle
    score_why: str             # rubric breakdown with ✅/❌ per criterion
    framework: str             # "challenger" | "pas" | "aida"

    # ── EMAIL ─────────────────────────────────────────────────────────────
    email_draft: dict          # {email: {subject, body, ps}, quarantined, reason}
    ab_subjects: list          # A/B subject line variants

    # ── REVIEW ────────────────────────────────────────────────────────────
    review_result: str         # "pass" | "fail"
    review_feedback: str       # human-readable failures list
    attempt: int               # write retry counter (max 2)

    # ── CRM ───────────────────────────────────────────────────────────────
    crm_synced: bool
    crm_prospect_id: str       # Frappe CRM Lead name (doc ID)

    # ── SEND ──────────────────────────────────────────────────────────────
    email_sent: bool
    email_error: str
    error: str                 # pipeline-level error message

    # ── AGENTIC ENRICHMENT (Phase 2+) ────────────────────────────────────
    detected_context: List[str]   # ["core", "financial", "clinical", ...]
    clinical_enrichment: Dict[str, Any]  # {pubmed_articles, clinical_trials, ...}
    enrichment_sources_used: List[str]   # ["tavily", "apollo", "brightdata_sec", "pubmed"]
    email_status: str             # "Draft Ready" | "Approved" | "Sent" | "Quarantined"
