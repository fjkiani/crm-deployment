"""
pipeline/enrichment/brightdata.py — Deep web enrichment via BrightData Web Unlocker.

What it does:
  Uses BrightData's residential proxy network to extract data from sites
  that block normal scrapers: LinkedIn profiles, SEC EDGAR, company websites.

Four targeted extractors:
  linkedin_profile(linkedin_url)   → headline, summary, recent posts, positions
  aum_from_sec(company)            → SEC 13F filing → AUM dollar amount
  company_strategy(company, site)  → investment thesis, focus sectors
  competitor_intel(company)        → who's eating their lunch

Current limitations:
  - LinkedIn returns raw HTML/JSON — parsing is regex-based (brittle)
  - SEC EDGAR endpoint may not return dollar amounts in all 13F formats
  - No caching — same company scraped on every pipeline run (costly)
  - BrightData zone "web_unlocker1" must exist in your BrightData account

How to improve:
  - Use BrightData's LinkedIn Dataset API (structured, not scraped HTML)
  - Cache results in Redis/Frappe custom doctype with TTL = 7 days
  - Add Proxycurl as fallback for LinkedIn (cleaner structured output)
  - Add Pitchbook/Crunchbase scraping for AUM (more reliable than SEC for PE/VC)
  - Use BrightData SERP API for competitor search (not raw web_unlocker)
"""
import os
import re
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _brightdata_get(url: str, timeout: int = 20) -> str:
    """
    Base BrightData Web Unlocker GET request.
    Returns raw response text, or empty string on failure.

    Cost: ~$0.001 per request on BrightData pay-per-request plan.
    """
    key = os.getenv("BRIGHTDATA_API_KEY")
    if not key:
        logger.debug("BRIGHTDATA_API_KEY not set — skipping BrightData call")
        return ""
    try:
        r = requests.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"zone": "web_unlocker1", "url": url, "format": "raw"},
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.text[:8000]
        logger.debug(f"BrightData {r.status_code} for {url[:80]}")
    except Exception as e:
        logger.debug(f"BrightData error ({url[:60]}): {e}")
    return ""


def linkedin_profile(linkedin_url: str) -> Dict:
    """
    Extract structured intelligence from a LinkedIn profile URL.

    Signals returned:
        headline         → "Portfolio Manager at Citadel" (used in scoring + email)
        summary          → Bio text (strategy/thesis signal)
        positions        → List of job titles (career trajectory signal)
        recent_activity  → List of recent posts (interest/intent signal)

    To improve:
        - Use Proxycurl API: GET /v2/linkedin?url={linkedin_url}
          Returns fully structured JSON (positions, education, skills, posts)
          Cost: $0.01/profile. Far more reliable than regex parsing.
        - Cache by linkedin_url with 7-day TTL
    """
    if not linkedin_url:
        return {}
    raw = _brightdata_get(linkedin_url)
    if not raw:
        return {}

    try:
        headline_m = re.search(r'"headline":"([^"]{5,200})"', raw)
        summary_m = re.search(r'"summary":"([^"]{20,600})"', raw)
        positions = re.findall(r'"title":"([^"]{5,100})"', raw)
        posts = re.findall(r'"commentary":\{"text":"([^"]{20,300})"', raw)

        result = {
            "headline": headline_m.group(1) if headline_m else "",
            "summary": summary_m.group(1) if summary_m else "",
            "positions": positions[:5],
            "recent_activity": posts[:3],
        }
        return {k: v for k, v in result.items() if v}
    except Exception as e:
        logger.debug(f"LinkedIn parse error: {e}")
    return {}


def aum_from_sec(company: str) -> str:
    """
    Search SEC EDGAR for 13F filings to extract AUM signal.

    What AUM tells us:
        > $1B   → HOT (+40 score pts) — full Challenger email justified
        $500M-1B → HOT (+30 score pts)
        < $500M → COLD (+0 score pts) — not in ICP

    To improve:
        - Use SEC EDGAR full-text search: https://efts.sec.gov/LATEST/search-index
        - Parse actual 13F XML filing for exact portfolio value (not regex on snippets)
        - Add Pitchbook/PEI scraping as parallel source (better PE/VC AUM coverage)
        - Cache by company name with 30-day TTL (13F filings are quarterly)
    """
    url = (
        f"https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{company.replace(' ', '+')}%22"
        f"&dateRange=custom&startdt=2024-01-01&forms=13F-HR"
    )
    raw = _brightdata_get(url)
    if not raw:
        return ""

    aum_matches = re.findall(r"\$[\d,\.]+\s*(?:billion|million|B|M|bn)", raw, re.IGNORECASE)
    holdings_matches = re.findall(r"total value[:\s]+[\$]?([\d,]+)", raw, re.IGNORECASE)

    if aum_matches:
        return f"SEC 13F AUM signal: {', '.join(aum_matches[:3])}"
    if holdings_matches:
        return f"SEC 13F holdings value: {holdings_matches[0]}"
    return ""


def company_strategy(company: str, website: str = "") -> str:
    """
    Extract investment thesis and strategy from company website or Tavily fallback.

    Signals returned:
        "Company strategy: [systematic + biotech focus sentences]"

    Injected into:
        - Email dossier as "Company Investment Strategy"
        - Score prompt as "strategy={strategy}"
        - Challenger framework: used to identify the specific blind spot to challenge

    To improve:
        - Use LLM extraction instead of regex (pass raw HTML to Cohere with extraction prompt)
        - Add Crunchbase API for structured company description
        - Add PitchBook API for fund mandate description
    """
    from eaia.pipeline.enrichment.tavily import tavily_search

    # Try website pages first if we have a URL
    if website:
        for path in ["/about", "/strategy", "/investment-philosophy", "/approach", "/team"]:
            raw = _brightdata_get(f"{website.rstrip('/')}{path}")
            if raw and len(raw) > 300:
                sentences = re.findall(r"[A-Z][^.!?]{30,200}[.!?]", raw)
                strategy_sentences = [
                    s for s in sentences
                    if any(kw in s.lower() for kw in [
                        "invest", "portfolio", "strategy", "fund", "alpha",
                        "biotech", "healthcare", "sector", "quant", "systematic", "focus"
                    ])
                ]
                if strategy_sentences:
                    return "Company strategy: " + " ".join(strategy_sentences[:4])

    # Fallback: Tavily search
    results = tavily_search(
        f"{company} investment strategy thesis focus sectors 2024 2025", max_results=3
    )
    if results:
        return "Company strategy signals: " + " | ".join([r["content"][:300] for r in results[:2]])
    return ""


def competitor_intel(company: str) -> str:
    """
    Find competitive pressure signals — who is winning the alpha race they're losing.

    Why this matters for emails:
        "[Competitor] deployed genomic biomarker data last quarter and is up 18%.
         Here's what they're doing that your model is missing."

    Signals returned:
        "Competitor signals: [Rival A] [Rival B] alternative data genomic..."

    To improve:
        - Use SimilarWeb API for digital competitive landscape
        - Use Crunchbase to find same-category companies with recent funding
        - Use LinkedIn to find ex-employees who moved to competitors (hiring signal)
    """
    from eaia.pipeline.enrichment.tavily import tavily_search

    results = tavily_search(
        f"{company} competitors alternative data genomic biomarker 2024 2025",
        max_results=3,
    )
    if results:
        return "Competitor signals: " + " ".join([r["content"][:200] for r in results[:2]])
    return ""
