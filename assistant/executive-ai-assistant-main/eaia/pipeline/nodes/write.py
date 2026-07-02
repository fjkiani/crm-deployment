"""
pipeline/nodes/write.py — Node 4: Two-Pass Email Writer.

Pipeline position: AFTER score_node.
Purpose: Generate a personalized email using the full 10-field dossier.

Two passes:
  Pass 1 (THINK): Extract talking points — tease, insight, proof — from dossier.
  Pass 2 (WRITE): Write email body using talking points + framework rules.

Framework rules:
  challenger (HOT):  Teach something. Challenge the status quo. Cite specific proof.
  pas (WARM):        Name the Problem. Cost the pain. Present the fix.
  aida (COLD):       Hook stat. Amplify. Intent proof (peer). CTA.

10 fields injected into prospect_info (the dossier the writer receives):
  1. Name + address rule ("first name only")
  2. Title
  3. Company
  4. AUM Signal
  5. Company Investment Strategy
  6. LinkedIn Headline
  7. LinkedIn Recent Posts
  8. Competitor Pressure
  9. Specific Number (from distiller)
  10. Recent Event + Strategic Detail + Blind Spot (from distiller)
  +  Sales Angle (from scorer)

To improve this node:
  - Add a "PRIOR RESPONSES" section to dossier — if they replied before, reference it
  - Add industry-specific vocabulary injection (hedge fund vs PE vs VC terminology)
  - Add a "what not to say" list per prospect based on communication history
  - Test 3 angles per email (Challenger / PAS / AIDA) and score each for personalization
  - Run Pass 2 twice with temperature=0.7/0.3 and let review_node pick the better draft
  - Add a "personalization score" field — count how many dossier fields were used
"""
import os
import logging
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.llm import llm_json
from eaia.config import NyxConfig
from eaia.skills.challenger_email_writer import _two_pass_generate, _generate_ab_subjects

logger = logging.getLogger(__name__)


def _build_dossier(state: OutreachState) -> str:
    """
    Build the 10-field prospect dossier injected into the email writer.
    This is the single most important input — garbage in = generic email out.

    To improve:
      - Add "prior email subjects sent" so writer doesn't repeat angles
      - Add "company quarterly results" if available (earnings signal)
      - Add "trigger event" field: what happened THIS WEEK that makes now the right time
    """
    signals    = state.get("distilled_signals", {})
    enrichment = state.get("enrichment", {})
    apollo     = state.get("apollo_data", {})
    name       = state["prospect_name"]
    company    = state["company_name"]
    first_name = name.split()[0] if name else name

    linkedin_posts = enrichment.get("linkedin_recent_activity", [])
    posts_str = (
        " | ".join(linkedin_posts[:2]) if linkedin_posts
        else "None found — do not reference LinkedIn activity"
    )

    return f"""PROSPECT DOSSIER — USE THESE SIGNALS. BE SPECIFIC. EVERY SENTENCE MUST REFERENCE SOMETHING BELOW.

Name: {name} (address as "{first_name}" only — never full name)
Title: {enrichment.get('apollo_title') or apollo.get('title', 'Unknown')}
Company: {company}
AUM Signal: {enrichment.get('aum_signal') or 'Unknown — do not mention AUM if unconfirmed'}
Company Investment Strategy: {enrichment.get('company_strategy') or 'Unknown'}
LinkedIn Headline: {enrichment.get('linkedin_profile_headline') or apollo.get('headline', 'Unknown')}
LinkedIn Recent Posts: {posts_str}
Competitor Pressure: {enrichment.get('competitor_pressure') or signals.get('competitor_name', 'Unknown')}
Specific Number: {signals.get('specific_number', 'UNKNOWN')}
Recent Event: {signals.get('recent_event', 'UNKNOWN')}
Strategic Detail: {signals.get('strategic_detail', 'UNKNOWN')}
Blind Spot: {signals.get('blind_spot', 'UNKNOWN')}
Sales Angle: {state.get('score_angle', 'Challenge their current data stack')}

RULES:
- DO NOT use placeholder language ("I noticed..." "I saw that..." "I came across...")
- Every sentence must reference something above. No sentence should apply to any other prospect.
- If a field is UNKNOWN/None, do NOT reference that topic.
- Be so specific they think we've been watching their fund for months."""


async def write_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 4 — Two-pass email generation with full 10-field dossier injection.

    Input:  state["distilled_signals"] + state["enrichment"] + state["score_angle"]
    Output: state["email_draft"] + state["ab_subjects"]

    Quarantine check: If distill_node quarantined the lead, write is skipped.
    """
    cb = config.get("configurable", {}).get("callback")

    # ── Quarantine check ──────────────────────────────────────────────────
    if state.get("signal_gate", "").startswith("quarantine"):
        logger.warning("⛔ WRITE SKIPPED — lead quarantined")
        state["email_draft"] = {"quarantined": True, "reason": state.get("signal_gate", "")}
        return state

    fw = state.get("framework", NyxConfig.DEFAULT_FRAMEWORK)
    attempt = state.get("attempt", 1)
    logger.info(f"✍️ WRITE: {fw.upper()} framework, attempt {attempt}")

    if cb:
        await cb("write", "thought", {
            "message": f"Pass 1: Extract talking points from dossier. Pass 2: Write {fw.upper()} email..."
        })

    # Accept any configured LLM provider. If Cohere is absent but another provider
    # (OpenRouter/Gemma, OpenAI, Anthropic) is set, pass a sentinel so the writer's
    # _call_cohere delegates to the shared llm_json fallback chain.
    cohere_key = os.getenv("COHERE_API_KEY")
    has_fallback = any(
        os.getenv(k) for k in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    )
    if not cohere_key:
        if has_fallback:
            cohere_key = "none"  # sentinel → _call_cohere routes to llm_json
        else:
            state["email_draft"] = {"error": "No LLM provider configured"}
            return state

    signals = state.get("distilled_signals", {})
    name    = state["prospect_name"]
    company = state["company_name"]

    # Build the 10-field dossier
    prospect_info = _build_dossier(state)

    # Inject review feedback on retry
    if state.get("review_feedback") and attempt > 1:
        signals = {**signals, "_review_feedback": state["review_feedback"]}

    try:
        result = _two_pass_generate(fw, signals, prospect_info, name, company, cohere_key)
        state["email_draft"] = result
        # Persist the recipient email for /send-email
        state["email_draft"]["prospect_email"] = (
            state.get("enrichment", {}).get("apollo_email")
            or state.get("apollo_data", {}).get("email")
        )

        body = result.get("email", {}).get("body", "")
        state["ab_subjects"] = _generate_ab_subjects(body, name, company, cohere_key)

        if cb:
            subj = result.get("email", {}).get("subject", "?")
            await cb("write", "result", {
                "message": f"Email drafted ({fw.upper()}) | {subj} | {len(body.split())} words"
            })

    except Exception as e:
        logger.error(f"Write node failed: {e}")
        state["email_draft"] = {"error": str(e)}
        state["ab_subjects"] = []

    return state
