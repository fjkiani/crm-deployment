"""
pipeline/nodes/distill.py — Node 2: Signal Extraction + UNKNOWN Gate.

Pipeline position: AFTER research_node (reads raw_research blob).
Purpose: Extract exactly 3-5 citable signals. Kill the email if we can't find 2+.

THE GATE:
  This is the most important function in the pipeline.
  If signal_gate = "quarantine", write_node and review_node are skipped.
  No email is generated. No generic sends. Ever.

Signal quality rubric:
  REAL signal: has actual text, not "UNKNOWN", length > 10 chars
  FAKE signal: "UNKNOWN", "", None — or a generic placeholder

To improve this node:
  - Increase raw_intel limit beyond 6000 chars (use token counting)
  - Add a "confidence score" per signal (0-1) — reject low-confidence ones
  - Add entity extraction: names of people, companies, dollar amounts as structured fields
  - Run distillation twice on different chunks and merge (reduces hallucination)
  - Add a "freshness check": reject recent_event if it's > 18 months old
  - Use GPT-4o instead of Cohere for more reliable JSON adherence
"""
import logging
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.llm import llm_json
from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

# ── Distill Prompt ────────────────────────────────────────────────────────────
DISTILL_PROMPT = f"""You are an intelligence analyst for {NyxConfig.COMPANY_NAME}, {NyxConfig.COMPANY_DESCRIPTION}.

Raw research intel on a prospect is below. Extract EXACTLY 3-5 citable signals.
Only include facts with specific numbers, names, or dates — no generic descriptions.

RAW INTEL:
{raw_intel}

Return ONLY valid JSON:
{{
    "specific_number": "One hard number — AUM, fund size, headcount, revenue, or return %.",
    "recent_event": "One event from the last 18 months — fund launch, hire, acquisition, regulatory filing.",
    "strategic_detail": "One specific strategic detail — investment thesis, strategy name, sector focus.",
    "blind_spot": "One structural gap {NyxConfig.COMPANY_NAME}'s {NyxConfig.DATA_TYPE} could address. Be specific about WHY they are vulnerable.",
    "competitor_name": "One competitor or peer firm using similar/better data.",
    "recommended_framework": "One of: challenger, pas, aida"
}}

Rules:
- NEVER fabricate. If unknown, write exactly: "UNKNOWN"
- blind_spot must connect to {NyxConfig.DATA_TYPE} predicting clinical outcomes or stock moves
- specific_number must be a real number with a unit ($, %, count, date)"""


def _signal_gate(signals: dict) -> tuple:
    """
    Hard gate: Block any lead with fewer than 2 real signals.
    A signal is real if it's not UNKNOWN/empty and has > 10 chars of content.

    Returns: (should_proceed: bool, reason: str)

    To improve:
      - Add per-signal confidence scores from LLM
      - Add a "freshness" check on recent_event (reject if > 18 months)
      - Raise threshold to 3 signals for HOT leads (stricter personalization)
    """
    signal_keys = ["specific_number", "recent_event", "strategic_detail", "competitor_name"]
    real = [
        k for k in signal_keys
        if signals.get(k)
        and signals.get(k) not in ("UNKNOWN", "", None)
        and "UNKNOWN" not in str(signals.get(k, ""))
        and len(str(signals.get(k, ""))) > 10
    ]
    if len(real) < NyxConfig.SIGNAL_GATE_MIN:
        reason = (
            f"QUARANTINED: {len(real)} real signal(s) found (need {NyxConfig.SIGNAL_GATE_MIN}+). "
            f"Real: {real or 'none'}. "
            f"Lead needs deep research before email."
        )
        return False, reason
    return True, f"Gate passed: {len(real)} real signals ({', '.join(real)})"


async def distill_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 2 — Extract signals from raw research blob, then gate on quality.

    Input:  state["raw_research"]
    Output: state["distilled_signals"] + state["signal_gate"]

    If gate fails → signal_gate = "quarantine:..." → write_node skipped entirely.
    """
    cb = config.get("configurable", {}).get("callback")
    logger.info("🔬 DISTILL: Extracting signals from enrichment dossier")

    if cb:
        await cb("distill", "thought", {"message": "Citation combiner extracting signals..."})

    prompt = DISTILL_PROMPT.format(raw_intel=state["raw_research"][:6000])

    try:
        signals = llm_json(prompt)
        required = ["specific_number", "recent_event", "strategic_detail",
                    "blind_spot", "recommended_framework"]
        for k in required:
            if k not in signals:
                signals[k] = "UNKNOWN"

        fw = signals.get("recommended_framework", NyxConfig.DEFAULT_FRAMEWORK).lower().strip()
        if fw not in NyxConfig.FRAMEWORKS:
            fw = NyxConfig.DEFAULT_FRAMEWORK
        signals["recommended_framework"] = fw

    except Exception as e:
        logger.error(f"Distill LLM failed: {e}")
        signals = {
            "specific_number": "UNKNOWN", "recent_event": "UNKNOWN",
            "strategic_detail": "UNKNOWN", "blind_spot": "UNKNOWN",
            "recommended_framework": "challenger",
        }

    # ── HARD SIGNAL GATE ─────────────────────────────────────────────────
    gate_ok, gate_reason = _signal_gate(signals)

    state["distilled_signals"] = signals

    if not gate_ok:
        logger.warning(f"🚫 SIGNAL GATE BLOCKED: {gate_reason}")
        state["signal_gate"] = f"quarantine:{gate_reason}"
        if cb:
            await cb("distill", "result", {"message": f"⛔ {gate_reason}"})
        return state

    state["signal_gate"] = f"pass:{gate_reason}"
    logger.info(f"✅ DISTILL GATE PASSED: {gate_reason}")

    if cb:
        await cb("distill", "result", {
            "message": f"✅ {gate_reason} | Framework: {signals['recommended_framework'].upper()}"
        })

    return state
