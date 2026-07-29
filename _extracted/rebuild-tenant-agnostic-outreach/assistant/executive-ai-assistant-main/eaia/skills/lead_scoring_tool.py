import re
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from eaia.main.config import get_config
from eaia.tenant import TenantPack, get_active_pack

# ------------------------------------------------------------------------------
# SCORING CRITERIA (Harvested from lead_qualification_agent.py)
# Weights are tenant-agnostic method; ICP / rubric / persona come from the pack.
# ------------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "company_size": 0.25,
    "job_title": 0.25,
    "industry": 0.20,
    "engagement": 0.15,
    "budget_signals": 0.15
}

# Tenant-agnostic scaffold. Tenant tokens injected from the pack:
#   {scoring_persona} {what_we_sell} {icp_block} {scoring_rubric} {lead_data}
SCORING_PROMPT_SCAFFOLD = """
{scoring_persona}
WHAT WE SELL: {what_we_sell}

IDEAL CUSTOMER PROFILE (ICP):
{icp_block}

Lead Data:
{lead_data}

Scoring Rules:
{scoring_rubric}

Return ONLY valid JSON with these keys: "score" (integer 0-100), "reasoning" (string citing exact signals), "angle" (best sales angle).
"""


def _build_scoring_prompt(pack: TenantPack, lead_data: str) -> str:
    """Render the scoring prompt for a tenant from the pack."""
    return SCORING_PROMPT_SCAFFOLD.format(
        scoring_persona=pack.scoring_persona_line(),
        what_we_sell=pack.what_we_sell,
        icp_block=pack.icp_block(),
        scoring_rubric=pack.scoring_rubric or (
            f"- {pack.score_hot}-100 (HOT): strong ICP match\n"
            f"- {pack.score_warm}-{pack.score_hot - 1} (WARM): partial ICP match\n"
            f"- 0-{pack.score_warm - 1} (COLD): no ICP relevance"
        ),
        lead_data=lead_data,
    )

# ------------------------------------------------------------------------------
# TOOL DEFINITION
# ------------------------------------------------------------------------------

def _score_lead_impl(lead_data_str: str, pack: Optional[TenantPack] = None) -> str:
    """
    Score a lead from 0-100 and determine routing, using the tenant pack for
    persona/ICP/rubric/angle and routing thresholds. Falls back to keyword
    heuristic if the LLM is unavailable.

    `pack` defaults to the active tenant pack so existing callers work unchanged.
    """
    pack = pack or get_active_pack()
    score = 50  # default fallback

    # ── Attempt real LLM scoring ────────────────────────────────────────────
    reasoning = "Fallback keyword heuristic applied."
    angle = pack.default_angle
    try:
        from langchain_openai import ChatOpenAI
        from eaia.main.config import get_config

        config = get_config()
        # Prefer Cohere; fall back to OpenAI. Both consume the pack-rendered prompt.
        llm_key = getattr(config, "openai_api_key", None)
        import os
        cohere_key = os.getenv("COHERE_API_KEY")
        prompt = _build_scoring_prompt(pack, lead_data_str)

        if cohere_key:
            import requests, json
            r = requests.post('https://api.cohere.com/v2/chat',
                headers={'Authorization': f'Bearer {cohere_key}'},
                json={'model': 'command-r-plus-08-2024',
                      'messages': [{'role': 'user', 'content': prompt}],
                      'response_format': {'type': 'json_object'}},
                timeout=30)
            res = json.loads(r.json()['message']['content'][0]['text'])
            score = int(res.get("score", 50))
            reasoning = res.get("reasoning", "No reasoning provided.")
            angle = res.get("angle", angle)
        elif llm_key:
            from langchain_core.messages import HumanMessage
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=llm_key, model_kwargs={"response_format": {"type": "json_object"}})
            response = llm.invoke([HumanMessage(content=prompt)])
            import json
            res = json.loads(response.content.strip())
            score = int(res.get("score", 50))
            reasoning = res.get("reasoning", "No reasoning provided.")
            angle = res.get("angle", angle)

    except Exception as e:
        # Fallback heuristic (tenant-agnostic keyword signals)
        data = lead_data_str.lower()
        if any(x in data for x in ["cto", "ceo", "vp", "founder", "partner", "portfolio manager", "pm"]):
            score += 20
        elif "director" in data:
            score += 10
        if any(x in data for x in ["fintech", "biotech", "tech", "finance", "health", "asset management", "etf", "quant"]):
            score += 15
        if any(x in data for x in ["pricing", "cost", "demo", "urgent", "budget"]):
            score += 15
        score = min(100, score)

    # ── Routing (pack-overridable thresholds; defaults preserve 80/60) ───────
    if score >= pack.routing_enterprise:
        team = "Enterprise Sales"
        priority = "High"
    elif score >= pack.routing_mid_market:
        team = "Mid-Market Sales"
        priority = "Medium"
    else:
        team = "Marketing Nurture"
        priority = "Low"

    return f"Lead Score: {score}/100\nRouted To: {team}\nPriority: {priority}\nAnalysis: {reasoning}\nRecommended Angle: {angle}"


@tool
def score_lead(lead_data_str: str):
    """
    Score a lead from 0-100 and determine routing.
    Uses real LLM scoring via the tenant pack's ICP/rubric; falls back to a
    keyword heuristic if the LLM is unavailable.
    Args:
        lead_data_str: Analysis string or JSON containing lead details.
    Returns:
        String with Score, Routing Decision, and Rationale.
    """
    return _score_lead_impl(lead_data_str)


