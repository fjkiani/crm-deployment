"""
pipeline/nodes/score.py — Node 3: Informed Lead Scoring.

Pipeline position: AFTER distill_node.
Purpose: Score 0-100 using the full enrichment package — not a blind Tavily blob.

The rubric is additive and explicit:
  AUM > $1B    : +40 pts
  AUM $500M-1B : +30 pts
  PM/CIO title : +25 pts
  Analyst title: +15 pts
  Biotech focus: +20 pts
  Quant mandate: +10 pts
  Recent hire  : +15 pts
  LinkedIn alt-data posts: +10 pts
  Competitor confirmed  : +10 pts

Score thresholds:
  80-100: HOT → Challenger email → Enterprise team
  50-79:  WARM → PAS email → Mid-Market team
  0-49:   COLD → AIDA → Marketing nurture

To improve this node:
  - Add AUM confirmation flag: only give +40 if AUM is literally cited in SEC filing
  - Weight signals by recency (recent_event from 3 months ago > 18 months ago)
  - Add ICP fit dimensions beyond AUM: fund type (long-only vs long/short vs QMF)
  - Add competitor gap scoring: if competitor confirmed + competitor uses similar data = -20 urgency gap
  - Run scoring twice and average to reduce LLM variance
  - Add a confidence score: if score stdev across 2 runs > 15, flag as uncertain
"""
import json
import logging
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.llm import llm_json
from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

# ── Score Prompt ──────────────────────────────────────────────────────────────
SCORE_PROMPT = f"""You are a B2B sales intelligence analyst for {NyxConfig.COMPANY_NAME}, {NyxConfig.COMPANY_DESCRIPTION}.
WHAT {NyxConfig.COMPANY_NAME.upper()} SELLS: {NyxConfig.VALUE_PROP}.

ICP: Quantitative/systematic investment firms, AUM > $500M, biotech/healthcare equities.
Decision-makers: Portfolio Managers, CIOs, Research Directors, Heads of Alt Data.

PROSPECT:
Name: __NAME__
Company: __COMPANY__
Title: __TITLE__
AUM Signal: __AUM__
Company Strategy: __STRATEGY__
LinkedIn Activity: __LINKEDIN_ACTIVITY__
Enrichment Signals: __SIGNALS__
Research Context: __RESEARCH__

SCORING RUBRIC (additive):
- AUM > $1B confirmed: +40
- AUM $500M-$1B confirmed: +30
- AUM unknown or < $500M: +0
- Title = PM / CIO / Portfolio Manager / Research Director / Head of Alt Data: +25
- Title = Analyst / Associate / VP: +15
- Active biotech/healthcare focus confirmed: +20
- Quant/systematic mandate confirmed: +10
- Recent hiring signal (Head of Bio/Pharma/Genomics): +15
- LinkedIn activity about alt data / genomics / FDA / biomarkers: +10
- Competitor firm confirmed using similar/better data: +10

Score ranges:
- 80-100 (HOT): Enterprise — Challenger email
- 50-79 (WARM): Mid-Market — PAS email
- 0-49 (COLD): Marketing — AIDA email or skip

Return ONLY JSON:
{{
  "score": <integer 0-100>,
  "reasoning": "<cite actual signals: title/AUM/strategy — no generic descriptions>",
  "angle": "<one specific sales angle referencing their actual situation>",
  "why_hot_or_cold": "<bullet points with ✅/❌ for each rubric criterion>"
}}"""


async def score_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 3 — Informed lead scoring using full enrichment package.

    Input:  state["distilled_signals"] + state["enrichment"]
    Output: state["score"], state["framework"], state["score_why"]

    Quarantine check: If distill_node quarantined the lead, scoring is skipped.
    """
    cb = config.get("configurable", {}).get("callback")

    # ── Quarantine check ──────────────────────────────────────────────────
    if state.get("signal_gate", "").startswith("quarantine"):
        logger.warning("⛔ SCORE SKIPPED — lead quarantined by signal gate")
        state["score"] = 0
        state["score_reasoning"] = state.get("signal_gate", "")
        state["score_angle"] = "Quarantined — insufficient signals"
        state["framework"] = "aida"
        return state

    logger.info("📊 SCORE: Informed scoring with full enrichment")
    if cb:
        await cb("score", "thought", {
            "message": "Scoring: AUM + title + LinkedIn activity + strategy + competitors..."
        })

    signals   = state.get("distilled_signals", {})
    enrichment = state.get("enrichment", {})
    apollo    = state.get("apollo_data", {})

    try:
        _subs = {
            "__NAME__":              state["prospect_name"],
            "__COMPANY__":           state["company_name"],
            "__TITLE__":             enrichment.get("apollo_title") or apollo.get("title", "Unknown"),
            "__AUM__":               enrichment.get("aum_signal") or "Unknown — 13F not found",
            "__STRATEGY__":          enrichment.get("company_strategy") or "Unknown",
            "__LINKEDIN_ACTIVITY__": " | ".join(enrichment.get("linkedin_recent_activity", [])) or "None found",
            "__SIGNALS__":           json.dumps(signals, indent=2),
            "__RESEARCH__":          state.get("raw_research", "")[:2000],
        }
        prompt = SCORE_PROMPT
        for _k, _v in _subs.items():
            prompt = prompt.replace(_k, str(_v))
        result = llm_json(prompt)
        score = max(0, min(100, int(result.get("score", 50))))

        state["score"]           = score
        state["score_reasoning"] = result.get("reasoning", "")
        state["score_angle"]     = result.get("angle", "")
        state["score_why"]       = result.get("why_hot_or_cold", "")

        # ── Framework selection ───────────────────────────────────────────
        if "recommended_framework" not in signals or signals["recommended_framework"] == "UNKNOWN":
            if score >= NyxConfig.SCORE_HOT:
                state["framework"] = NyxConfig.FRAMEWORK_HOT
            elif score >= NyxConfig.SCORE_WARM:
                state["framework"] = NyxConfig.FRAMEWORK_WARM
            else:
                state["framework"] = NyxConfig.FRAMEWORK_COLD

        # Distiller recommendation overrides in ambiguous zone
        rec = signals.get("recommended_framework", "")
        if 45 <= score <= 75 and rec in ("challenger", "pas", "aida"):
            state["framework"] = rec

        logger.info(
            f"📊 SCORE: {score}/100 → {state['framework'].upper()} | "
            f"{state['score_reasoning'][:80]}"
        )
        if cb:
            await cb("score", "result", {
                "message": (
                    f"Score: {score}/100 | Framework: {state['framework'].upper()} | "
                    f"{result.get('angle', '')[:80]}"
                )
            })

    except Exception as e:
        logger.error(f"Score node failed: {e}")
        state["score"]           = 50
        state["score_reasoning"] = f"Scoring error: {e}"
        state["score_angle"]     = "Check enrichment and retry"
        state["framework"]       = signals.get("recommended_framework", NyxConfig.DEFAULT_FRAMEWORK)

    return state
