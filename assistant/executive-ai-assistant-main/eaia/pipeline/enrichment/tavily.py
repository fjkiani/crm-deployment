"""
pipeline/enrichment/tavily.py — Tavily real-time web search.

What it does:
  Execute web searches against Tavily's index (real-time, not cached).
  Returns structured results with URL + content snippets + an AI answer.

Current limitations:
  - No date filtering — results may be 1-2 years old
  - Results limited to ~600 chars per source (snippets only, not full page)
  - No deduplication (same story from 5 sites = 5 results)
  - Search is broad — no domain exclusion (no paywalled sites filter)

How to improve:
  - Add `search_depth: "advanced"` + `max_results: 8` for richer context
  - Add `exclude_domains: ["reddit.com", "quora.com"]` to filter noise
  - Add date filtering with `date_range: "1y"` for freshness
  - Parallelize multiple targeted queries instead of one broad search:
      Query 1: "{name} {company} recent news 2025"
      Query 2: "{company} AUM fund size 2024 2025"
      Query 3: "{company} investment thesis biotech healthcare"
      Query 4: "{name} keynote published paper conference 2024 2025"
"""
import os
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)


def tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search the web via Tavily API.

    Args:
        query:       Search query string
        max_results: Number of results to return (max 10)

    Returns:
        List of dicts: [{url, content}, ...] including an AI answer if available.

    Signals this provides:
        - Recent news (fund launches, hires, acquisitions, regulatory events)
        - Company strategy mentions (investment thesis, sector focus)
        - Publication/keynote mentions (thought leadership signals)
    """
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        logger.warning("TAVILY_API_KEY not set — skipping Tavily search")
        return [{"url": "#", "content": "TAVILY_API_KEY not set"}]

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": True,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        if data.get("answer"):
            results.append({"url": "tavily_answer", "content": data["answer"]})
        for res in data.get("results", []):
            results.append({
                "url": res.get("url"),
                "content": res.get("content", ""),
                "published_date": res.get("published_date"),  # freshness signal
            })
        return results
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return [{"url": "#", "content": f"Tavily error: {e}"}]


def tavily_multi_search(name: str, company: str) -> List[Dict]:
    """
    Run 4 targeted queries in sequence and combine results.
    More specific than a single broad search.

    To make parallel: wrap each call in asyncio.to_thread() in research_node.
    """
    queries = [
        f"{company} {name} investment strategy AUM portfolio news 2024 2025",
        f"{company} AUM fund size assets under management",
        f"{company} biotech healthcare equities focus 2024",
        f"{name} keynote conference publication 2024 2025",
    ]
    all_results = []
    for q in queries:
        results = tavily_search(q, max_results=3)
        for r in results:
            r["query"] = q   # track which query produced this result
            all_results.append(r)
    return all_results
