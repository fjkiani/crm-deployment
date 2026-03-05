"""
Zeta Protocols: Competitive Intelligence Tools
==============================================
LangChain @tool wrappers for Phase 9 Vulture & Dark Enrichment.
Provides capabilities to monitor competitor failures and find negative signals.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_core.tools import tool

@tool
async def monitor_competitor_news(competitor_name: str) -> str:
    """Search for recent negative news or failures regarding a specific competitor.
    
    Use this for the Vulture Protocol to find trigger events (clinical trial failures,
    layoffs, data breaches, missed earnings) that can be used to re-engage leads.
    
    Args:
        competitor_name: Name of the competitor to monitor (e.g. "Acme Corp")
    """
    try:
        from eaia.pipeline.enrichment.tavily import tavily_search
        
        # Craft a targeted query for negative events
        query = f'"{competitor_name}" (failure OR layoff OR lawsuit OR breach OR "missed earnings" OR "clinical trial fails" OR "FDA warning")'
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            results = await loop.run_in_executor(ex, tavily_search, query)

        if not results:
            return f"No recent negative events found for: {competitor_name}"

        formatted = []
        for r in results[:3]: # Top 3 most relevant negative events
            url = r.get("url", "")
            content = r.get("content", "")[:500]
            formatted.append(f"[{url}]\n{content}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Competitor monitoring error: {e}"


@tool
async def dark_signal_search(company_name: str) -> str:
    """Deep search for negative signals (dark enrichment) about a specific company.
    
    Use this to find vulnerabilities, lawsuits, FDA warnings, or compliance failures
    that can be used as a targeted sales angle (e.g. "While you deal with X...").
    
    Args:
        company_name: Name of the company to search (e.g. "GlobalPharma")
    """
    try:
        from eaia.pipeline.enrichment.tavily import tavily_search
        
        query = f'"{company_name}" ("lawsuit" OR "SEC investigation" OR "FDA warning letter" OR "scandal" OR "compliance failure" OR "data breach")'
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            results = await loop.run_in_executor(ex, tavily_search, query)

        if not results:
            return f"No dark signals found for: {company_name}"

        formatted = []
        for r in results[:3]:
            url = r.get("url", "")
            title = r.get("title", "")
            content = r.get("content", "")[:500]
            formatted.append(f"[{title}]({url})\n{content}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Dark signal search error: {e}"


ALL_COMPETITIVE_TOOLS = [
    monitor_competitor_news,
    dark_signal_search
]
