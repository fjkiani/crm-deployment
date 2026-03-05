"""
Research Tools — LangChain @tool wrappers for enrichment data sources
=====================================================================
Wraps the existing research functions (Tavily, Apollo, BrightData)
as LangChain tools so the enrichment agent can bind and call them.
"""

import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def web_search(query: str) -> str:
    """Search the web for recent news, strategy mentions, and intelligence about a prospect or company.

    Use this as the FIRST research tool to understand who the prospect is and what
    their company does. The results will help you decide which specialized tools
    to use next (e.g., clinical trials if healthcare, SEC filings if finance).

    Args:
        query: Search query (e.g., "John Smith RA Capital investment strategy AUM")
    """
    try:
        from eaia.pipeline.enrichment.tavily import tavily_search
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            results = await loop.run_in_executor(ex, tavily_search, query)

        if not results:
            return f"No web results found for: {query}"

        formatted = []
        for r in results[:5]:
            url = r.get("url", "")
            content = r.get("content", "")[:600]
            formatted.append(f"[{url}]\n{content}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Web search error: {e}"


@tool
async def apollo_enrich(prospect_name: str, company_name: str) -> str:
    """Enrich a prospect via Apollo.io — returns email, title, LinkedIn URL, seniority.

    Call this to get contact data. Always call this alongside web_search as
    the foundation of any enrichment.

    Args:
        prospect_name: Full name (e.g., "John Smith")
        company_name: Company name (e.g., "RA Capital Management")
    """
    try:
        from eaia.pipeline.enrichment.apollo import apollo_match
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            result = await loop.run_in_executor(ex, apollo_match, prospect_name, company_name)

        if not result:
            return f"No Apollo data found for {prospect_name} at {company_name}"

        parts = [
            f"Email: {result.get('email', 'N/A')}",
            f"Title: {result.get('title', 'N/A')}",
            f"LinkedIn: {result.get('linkedin_url', 'N/A')}",
            f"Headline: {result.get('headline', 'N/A')}",
            f"Seniority: {result.get('seniority', 'N/A')}",
            f"Departments: {result.get('departments', [])}",
        ]
        return "\n".join(parts)
    except Exception as e:
        return f"Apollo enrichment error: {e}"


@tool
async def brightdata_search(company_name: str, search_type: str = "strategy") -> str:
    """Deep web research via BrightData — scrapes LinkedIn, SEC filings, company websites.

    Use this for deeper intelligence after web_search reveals interesting signals.
    Search types:
    - "strategy": company website analysis for investment strategy
    - "sec": SEC 13F filing for AUM dollar amounts
    - "competitor": competitor intelligence
    - "linkedin": LinkedIn profile scraping (requires prospect's LinkedIn URL)

    Args:
        company_name: Company to research
        search_type: One of "strategy", "sec", "competitor", "linkedin"
    """
    try:
        from eaia.pipeline.enrichment.brightdata import (
            aum_from_sec, company_strategy, competitor_intel,
        )
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=1) as ex:
            if search_type == "sec":
                result = await loop.run_in_executor(ex, aum_from_sec, company_name)
            elif search_type == "competitor":
                result = await loop.run_in_executor(ex, competitor_intel, company_name)
            else:
                result = await loop.run_in_executor(ex, company_strategy, company_name, "")

        return str(result) if result else f"No {search_type} data found for {company_name}"
    except Exception as e:
        return f"BrightData {search_type} error: {e}"


@tool
async def distill_signals(raw_intel: str, prospect_name: str, company_name: str) -> str:
    """Distill raw research text into structured intelligence signals.

    Call this after gathering sufficient raw research from web_search, apollo,
    brightdata, pubmed, etc. It extracts: specific_number, recent_event,
    strategic_detail, blind_spot, and recommended_framework.

    Args:
        raw_intel: Combined raw research text to distill
        prospect_name: Prospect's full name
        company_name: Company name
    """
    try:
        from eaia.pipeline.llm import llm_json
        prompt = f"""Analyze this research about {prospect_name} at {company_name} and extract:

RESEARCH:
{raw_intel[:6000]}

Return JSON with these exact fields:
{{
  "specific_number": "A concrete number (AUM, revenue, funding amount, trial size). If none found, 'UNKNOWN'.",
  "recent_event": "Most recent newsworthy event about this person/company. If none, 'UNKNOWN'.",
  "strategic_detail": "Their specific strategy or focus area. If unclear, 'UNKNOWN'.",
  "blind_spot": "A gap or risk they may not see. If none obvious, 'UNKNOWN'.",
  "competitor_name": "A named competitor or peer. If none, 'UNKNOWN'.",
  "recommended_framework": "challenger if score >= 70, pas if 40-69, aida if < 40",
  "detected_context": ["list of contexts: 'core', 'financial', 'clinical', 'biotech', 'pharma'"],
  "signal_strength": "strong/moderate/weak — based on how many fields are non-UNKNOWN"
}}"""
        result = llm_json(prompt)
        import json
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Distillation error: {e}"


@tool
async def score_lead(
    prospect_name: str,
    company_name: str,
    signals_json: str,
    detected_context: str = "core",
) -> str:
    """Score a lead 0-100 based on distilled signals. Adapts rubric to detected context.

    Call this AFTER distill_signals. The score determines:
    - 70+: HOT → challenger framework, prioritize
    - 40-69: WARM → PAS framework
    - <40: COLD → AIDA framework, lower priority

    Args:
        prospect_name: Prospect name
        company_name: Company name
        signals_json: JSON string of distilled signals from distill_signals tool
        detected_context: Comma-separated contexts (e.g., "core,financial,clinical")
    """
    try:
        import json
        from eaia.pipeline.llm import llm_json
        signals = json.loads(signals_json) if isinstance(signals_json, str) else signals_json
        contexts = [c.strip() for c in detected_context.split(",")]

        rubric_parts = [
            "Score 0-100 based on:",
            "- Specific number found (+20): " + signals.get("specific_number", "UNKNOWN"),
            "- Recent event found (+20): " + signals.get("recent_event", "UNKNOWN"),
            "- Strategic detail found (+15): " + signals.get("strategic_detail", "UNKNOWN"),
            "- Blind spot identified (+15): " + signals.get("blind_spot", "UNKNOWN"),
            "- Competitor pressure (+10): " + signals.get("competitor_name", "UNKNOWN"),
        ]

        if "financial" in contexts:
            rubric_parts.append("- AUM > $1B (+10), AUM > $500M (+5)")
        if "clinical" in contexts:
            rubric_parts.append("- Active Phase 2/3 trials (+10), Published papers (+5)")
        if "biotech" in contexts:
            rubric_parts.append("- Recent funding round (+10), Pipeline compound (+5)")

        prompt = f"""Score this lead for sales outreach potential.

PROSPECT: {prospect_name} at {company_name}
CONTEXT: {', '.join(contexts)}

{chr(10).join(rubric_parts)}

Return JSON:
{{
  "score": <0-100>,
  "framework": "challenger" if score >= 70, "pas" if 40-69, "aida" if < 40,
  "reasoning": "2-3 sentences explaining the score",
  "angle": "Specific sales angle to use in outreach",
  "why": "Rubric breakdown with ✅/❌ per criterion"
}}"""
        result = llm_json(prompt)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Scoring error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# ALL RESEARCH TOOLS — for agent.bind_tools()
# ══════════════════════════════════════════════════════════════════════════════

# Farfalle deep research (graceful fallback if not running)
try:
    from eaia.tools.farfalle_tools import farfalle_deep_research
    _farfalle_tools = [farfalle_deep_research]
except ImportError:
    _farfalle_tools = []

ALL_RESEARCH_TOOLS = [
    web_search,
    apollo_enrich,
    brightdata_search,
    distill_signals,
    score_lead,
    *_farfalle_tools,
]

