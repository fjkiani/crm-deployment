"""
pipeline/nodes/score.py — Node 3: Informed Lead Scoring.

Pipeline position: AFTER distill_node.
Purpose: Score 0-100 using the full enrichment package — not a blind Tavily blob.

The rubric is additive and explicit, and is supplied by the active tenant pack
(`pack.scoring_rubric`) — NOT hardcoded here. Example (CrisPRO/finance tenant):
  primary money signal (e.g. AUM tier) : up to +40 pts
  decision-maker title                 : +25 pts
  industry/domain fit                  : +20 pts
  recent hiring/intent signal          : +15 pts
  public activity on the topic         : +10 pts
  competitor confirmed                 : +10 pts
A non-finance tenant supplies its own rubric and its own primary-signal label.

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
from eaia.tenant import TenantPack, get_active_pack

logger = logging.getLogger(__name__)

# ── Score Prompt SCAFFOLD (tenant-agnostic; ICP + rubric injected from pack) ──
# Tenant tokens: {scoring_persona} {what_we_sell} {icp_block} {scoring_rubric}
# {score_hot} {score_warm}. Prospect tokens filled per-call by score_node.
SCORE_PROMPT_SCAFFOLD = """{scoring_persona}
WHAT WE SELL: {what_we_sell}

IDEAL CUSTOMER PROFILE (ICP):
{icp_block}

PROSPECT:
Name: {name}
Company: {company}
Title: {title}
{primary_signal_label}: {aum}
Company Strategy: {strategy}
LinkedIn Activity: {linkedin_activity}
Enrichment Signals: {signals}
Research Context: {research}

SCORING RUBRIC:
{scoring_rubric}

Score ranges:
- {score_hot}-100 (HOT): Enterprise — Challenger email
- {score_warm}-{score_hot_minus_1} (WARM): Mid-Market — PAS email
- 0-{score_warm_minus_1} (COLD): Marketing — AIDA email or skip

Return ONLY JSON:
{{
  "score": <integer 0-100>,
  "reasoning": "<cite actual signals: title/primary-signal/strategy — no generic descriptions>",
  "angle": "<one specific sales angle referencing their actual situation>",
  "why_hot_or_cold": "<bullet points with check/x for each rubric criterion>"
}}"""


def _build_score_prompt(pack: TenantPack, **prospect_fields) -> str:
    """Render the scoring prompt from the tenant pack + prospect fields."""
    return SCORE_PROMPT_SCAFFOLD.format(
        scoring_persona=pack.scoring_persona_line(),
        what_we_sell=pack.what_we_sell,
        icp_block=pack.icp_block(),
        primary_signal_label=pack.primary_signal_label,
        scoring_rubric=pack.scoring_rubric or "- Strong ICP match scores higher.",
        score_hot=pack.score_hot,
        score_warm=pack.score_warm,
        score_hot_minus_1=pack.score_hot - 1,
        score_warm_minus_1=pack.score_warm - 1,
        **prospect_fields,
    )


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

    # Resolve the active tenant pack (per-request tenant_id supported via config).
    # Resolved BEFORE the callback so the progress message can use pack labels.
    tenant_id = config.get("configurable", {}).get("tenant_id")
    pack = get_active_pack(tenant_id)

    if cb:
        await cb("score", "thought", {
            "message": f"Scoring: {pack.primary_signal_label} + title + LinkedIn activity + strategy + competitors..."
        })

    signals   = state.get("distilled_signals", {})
    enrichment = state.get("enrichment", {})
    apollo    = state.get("apollo_data", {})

    try:
        prompt = _build_score_prompt(
            pack,
            name=state["prospect_name"],
            company=state["company_name"],
            title=enrichment.get("apollo_title") or apollo.get("title", "Unknown"),
            aum=enrichment.get("aum_signal") or "Unknown — 13F not found",
            strategy=enrichment.get("company_strategy") or "Unknown",
            linkedin_activity=(
                " | ".join(enrichment.get("linkedin_recent_activity", []))
                or "None found"
            ),
            signals=json.dumps(signals, indent=2),
            research=state.get("raw_research", "")[:2000],
        )
        result = llm_json(prompt)
        score = max(0, min(100, int(result.get("score", 50))))

        state["score"]           = score
        state["score_reasoning"] = result.get("reasoning", "")
        state["score_angle"]     = result.get("angle", "")
        state["score_why"]       = result.get("why_hot_or_cold", "")

        # ── Framework selection (pack-driven; HOT→challenger/WARM→pas/COLD→aida) ─
        # NOTE: fixes a pre-existing latent bug — score.py previously referenced
        # NyxConfig.FRAMEWORK_HOT/WARM/COLD which were never defined (AttributeError).
        if "recommended_framework" not in signals or signals["recommended_framework"] == "UNKNOWN":
            if score >= pack.score_hot:
                state["framework"] = "challenger"
            elif score >= pack.score_warm:
                state["framework"] = "pas"
            else:
                state["framework"] = "aida"

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
