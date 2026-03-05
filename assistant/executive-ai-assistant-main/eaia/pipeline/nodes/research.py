"""
pipeline/nodes/research.py — Node 1: 5-Source Parallel Enrichment.

Pipeline position: FIRST (feeds all downstream nodes)
Architecture: Enrich BEFORE Score — informed scoring changes framework selection.

5 parallel sources:
  Source 1: Tavily        → recent news, strategy mentions, AUM articles
  Source 2: Apollo        → email, title, LinkedIn URL, phone (contact data)
  Source 3: BrightData    → LinkedIn profile extract (headline, summary, posts)
  Source 4: BrightData    → SEC 13F filing → AUM dollar amount
  Source 5: BrightData    → company website strategy + competitor intel

Output (written to state):
  state["raw_research"]  → combined text blob fed to distill_node
  state["apollo_data"]   → raw Apollo response dict
  state["enrichment"]    → structured enrichment dict fed to score/write nodes

How to improve this node:
  - Add Hunter.io as email fallback if Apollo returns no email
  - Add Proxycurl for LinkedIn (more structured than BrightData regex crawl)
  - Add Crunchbase API for fund AUM + sector focus (cleaner than SEC)
  - Add Glassdoor/LinkedIn jobs scraping for open roles (hiring intent signal)
  - Cache enrichment results by (name, company) with 7-day TTL
  - Switch from ThreadPoolExecutor to asyncio.gather for true async parallelism
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.enrichment.apollo import apollo_match
from eaia.pipeline.enrichment.tavily import tavily_search
from eaia.pipeline.enrichment.brightdata import (
    linkedin_profile,
    aum_from_sec,
    company_strategy,
    competitor_intel,
)

logger = logging.getLogger(__name__)


async def research_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 1 — 5-source parallel enrichment.
    Always runs first. Everything downstream depends on what this finds.
    """
    cb = config.get("configurable", {}).get("callback")
    name = state["prospect_name"]
    company = state["company_name"]
    logger.info(f"🔍 RESEARCH (5-source): {name} @ {company}")

    if cb:
        await cb("research", "thought", {
            "message": f"5-source enrichment: Tavily + Apollo + LinkedIn + SEC 13F + Strategy..."
        })

    loop = asyncio.get_event_loop()

    # ── Phase 1: Apollo + Tavily in parallel ──────────────────────────────
    with ThreadPoolExecutor(max_workers=2) as ex:
        t_fut = loop.run_in_executor(
            ex, tavily_search,
            f"{company} {name} investment strategy AUM portfolio news 2024 2025"
        )
        a_fut = loop.run_in_executor(ex, apollo_match, name, company)
        tavily_results, apollo = await asyncio.gather(t_fut, a_fut)

    apollo = apollo or {}
    linkedin_url = apollo.get("linkedin_url", "")

    if cb:
        email_found = "✅ " + apollo.get("email", "?") if apollo.get("email") else "❌ no email"
        await cb("research", "thought", {
            "message": f"Apollo: {email_found} | LinkedIn URL: {'✅' if linkedin_url else '❌'} | Now running BrightData..."
        })

    # ── Phase 2: BrightData 4-way parallel (needs linkedin_url from Apollo) ──
    with ThreadPoolExecutor(max_workers=4) as ex:
        li_fut  = loop.run_in_executor(ex, linkedin_profile, linkedin_url)
        aum_fut = loop.run_in_executor(ex, aum_from_sec, company)
        st_fut  = loop.run_in_executor(ex, company_strategy, company, "")
        co_fut  = loop.run_in_executor(ex, competitor_intel, company)
        li_profile, aum_signal, strategy_signal, competitor_signal = await asyncio.gather(
            li_fut, aum_fut, st_fut, co_fut
        )

    # ── Compose structured enrichment dict ────────────────────────────────
    enrichment = {
        "apollo_email":               apollo.get("email"),
        "apollo_title":               apollo.get("title"),
        "apollo_linkedin_url":        apollo.get("linkedin_url"),
        "apollo_headline":            apollo.get("headline"),
        "apollo_seniority":           apollo.get("seniority"),
        "apollo_departments":         apollo.get("departments"),
        "linkedin_profile_headline":  li_profile.get("headline", ""),
        "linkedin_profile_summary":   li_profile.get("summary", ""),
        "linkedin_recent_activity":   li_profile.get("recent_activity", []),
        "aum_signal":                 aum_signal,
        "company_strategy":           strategy_signal,
        "competitor_pressure":        competitor_signal,
    }
    enrichment = {k: v for k, v in enrichment.items() if v}  # strip empty

    # ── Compose raw research blob for distill_node ─────────────────────────
    raw_parts = [f"[{r['url']}]\n{r['content'][:600]}" for r in tavily_results]

    if apollo:
        raw_parts.append(
            f"[APOLLO CONTACT]\nEmail: {apollo.get('email', 'N/A')}\n"
            f"Title: {apollo.get('title', 'N/A')}\n"
            f"Headline: {apollo.get('headline', 'N/A')}\n"
            f"Seniority: {apollo.get('seniority', 'N/A')}\n"
            f"Departments: {apollo.get('departments', [])}"
        )
    if li_profile:
        raw_parts.append(
            f"[LINKEDIN PROFILE]\nHeadline: {li_profile.get('headline', '')}\n"
            f"Summary: {li_profile.get('summary', '')}\n"
            f"Recent Posts: {' | '.join(li_profile.get('recent_activity', [])[:2])}"
        )
    if aum_signal:
        raw_parts.append(f"[SEC 13F AUM]\n{aum_signal}")
    if strategy_signal:
        raw_parts.append(f"[COMPANY STRATEGY]\n{strategy_signal}")
    if competitor_signal:
        raw_parts.append(f"[COMPETITOR INTEL]\n{competitor_signal}")

    state["raw_research"] = "\n\n".join(raw_parts)
    state["apollo_data"]  = apollo
    state["enrichment"]   = enrichment

    loaded = len([k for k, v in enrichment.items() if v])
    logger.info(f"✅ RESEARCH COMPLETE — {loaded} enrichment signals loaded")

    if cb:
        await cb("research", "result", {
            "message": (
                f"Enrichment: title={enrichment.get('apollo_title','?')} | "
                f"AUM={'✅' if aum_signal else '❌'} | "
                f"LinkedIn={'✅' if li_profile else '❌'} | "
                f"Strategy={'✅' if strategy_signal else '❌'}"
            )
        })

    return state
