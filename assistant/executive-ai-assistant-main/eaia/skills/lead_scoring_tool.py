import re
from typing import Dict, Any, List
from langchain_core.tools import tool
from eaia.main.config import get_config

# ------------------------------------------------------------------------------
# SCORING CRITERIA (Harvested from lead_qualification_agent.py)
# ------------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "company_size": 0.25,
    "job_title": 0.25,
    "industry": 0.20,
    "engagement": 0.15,
    "budget_signals": 0.15
}

SCORING_PROMPT_TEMPLATE = """
You are a B2B sales intelligence analyst for Zeta, a genomic data analytics platform.
WHAT ZETA SELLS: Proprietary genomic datasets that quantify biological drug response signals. Buyers are quantitative fund managers who use alternative data.

IDEAL CUSTOMER PROFILE (ICP):
- Quantitative or systematic investment firms
- AUM > $500M
- Active in biotech/healthcare equities or alternative data
- Decision-makers: PMs, CIOs, Research Directors

Lead Data:
{lead_data}

Scoring Rules:
- 80-100 (HOT): Quant/systematic fund + biotech exposure + decision-maker title + AUM > 500M
- 50-79 (WARM): Matches 2-3 ICP criteria but missing a key signal
- 0-49 (COLD): No quant mandate, no biotech relevance

Return ONLY valid JSON with these keys: "score" (integer 0-100), "reasoning" (string citing exact signals), "angle" (best sales angle).
"""

ROUTING_THRESHOLDS = {
    "enterprise": 80,
    "mid_market": 60,
    "smb": 40
}

# ------------------------------------------------------------------------------
# TOOL DEFINITION
# ------------------------------------------------------------------------------

@tool
def score_lead(lead_data_str: str):
    """
    Score a lead from 0-100 and determine routing.
    FIX F12: Uses real LLM scoring via the SCORING_PROMPT_TEMPLATE.
    Falls back to keyword heuristic if LLM is unavailable.
    Args:
        lead_data_str: Analysis string or JSON containing lead details.
    Returns:
        String with Score, Routing Decision, and Rationale.
    """
    score = 50  # default fallback

    # ── Attempt real LLM scoring ────────────────────────────────────────────
    reasoning = "Fallback keyword heuristic applied."
    angle = "Pitch Zeta genomic data as an alternative data source."
    try:
        from langchain_openai import ChatOpenAI
        from eaia.main.config import get_config

        config = get_config()
        # FIX: We now use cohere key but in generic OpenAI format if proxying, or just Cohere directly.
        # But wait, earlier we used OpenAI. Let's keep it robust and try to load JSON.
        llm_key = getattr(config, "openai_api_key", None)
        import os
        cohere_key = os.getenv("COHERE_API_KEY")

        if cohere_key:
            import requests, json
            r = requests.post('https://api.cohere.com/v2/chat',
                headers={'Authorization': f'Bearer {cohere_key}'},
                json={'model': 'command-r-plus-08-2024',
                      'messages': [{'role': 'user', 'content': SCORING_PROMPT_TEMPLATE.format(lead_data=lead_data_str)}],
                      'response_format': {'type': 'json_object'}},
                timeout=30)
            res = json.loads(r.json()['message']['content'][0]['text'])
            score = int(res.get("score", 50))
            reasoning = res.get("reasoning", "No reasoning provided.")
            angle = res.get("angle", "No angle generated.")
        elif llm_key:
            from langchain_core.messages import HumanMessage
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=llm_key, model_kwargs={"response_format": {"type": "json_object"}})
            prompt = SCORING_PROMPT_TEMPLATE.format(lead_data=lead_data_str)
            response = llm.invoke([HumanMessage(content=prompt)])
            import json
            res = json.loads(response.content.strip())
            score = int(res.get("score", 50))
            reasoning = res.get("reasoning", "No reasoning provided.")
            angle = res.get("angle", "No angle generated.")

    except Exception as e:
        # Fallback heuristic
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

    # ── Routing ─────────────────────────────────────────────────────────────
    if score >= ROUTING_THRESHOLDS["enterprise"]:
        team = "Enterprise Sales"
        priority = "High"
    elif score >= ROUTING_THRESHOLDS["mid_market"]:
        team = "Mid-Market Sales"
        priority = "Medium"
    else:
        team = "Marketing Nurture"
        priority = "Low"

    return f"Lead Score: {score}/100\nRouted To: {team}\nPriority: {priority}\nAnalysis: {reasoning}\nRecommended Angle: {angle}"


