"""
pipeline/enrichment/apollo.py — Apollo.io contact enrichment.

What it does:
  Given a name + company, returns email, title, LinkedIn URL, phone, headline.

Coverage:
  - /v1/people/match endpoint (name + org matching)
  - Reveals personal emails when available

Current limitations:
  - No phone reveal (requires Apollo Credit Plan)
  - No org-level data (headcount, revenue, tech stack) — needs /organizations/enrich
  - Rate limit: 600 req/min on paid plans, 50/min on free
  - Apollo DB coverage: ~300M contacts, strongest in US tech/finance

How to improve:
  - Add /v1/organizations/enrich call (same API key) for headcount, revenue, founded
  - Add retry with backoff on 429 (rate limit)
  - Chain with Hunter.io as fallback if Apollo returns no email
  - Use "reveal_personal_emails: true" AND "reveal_phone_number: true" (Enterprise plan)
"""
import os
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def apollo_match(name: str, org: str) -> Optional[Dict[str, Any]]:
    """
    Find a person in Apollo.io by name + organization.

    Args:
        name: Full name of the prospect (e.g. "Peter McManus")
        org:  Organization name (e.g. "3EDGE Asset Management")

    Returns:
        Dict with: email, title, linkedin_url, organization, city, headline
        None if not found or API unavailable.

    Signals returned:
        - email          → used for outreach + CRM
        - title          → used for scoring (PM/CIO = +25 pts)
        - linkedin_url   → fed to BrightData profile extract
        - headline       → injected into email dossier as "LinkedIn Headline"
    """
    key = os.getenv("APOLLO_API_KEY")
    if not key:
        logger.warning("APOLLO_API_KEY not set — skipping Apollo enrichment")
        return None

    try:
        r = requests.post(
            "https://api.apollo.io/v1/people/match",
            headers={"Content-Type": "application/json", "X-Api-Key": key},
            json={
                "name": name,
                "organization_name": org,
                "reveal_personal_emails": True,
            },
            timeout=10,
        )
        if r.status_code == 200:
            person = r.json().get("person")
            if person:
                result = {
                    "email": person.get("email"),
                    "title": person.get("title"),
                    "linkedin_url": person.get("linkedin_url"),
                    "organization": person.get("organization", {}).get("name"),
                    "city": person.get("city"),
                    "headline": person.get("headline"),
                    "phone": person.get("phone_number"),       # usually None on free plan
                    "seniority": person.get("seniority"),      # "senior", "director", "c_suite"
                    "departments": person.get("departments", []),  # ["finance", "executive"]
                }
                # Strip None values
                return {k: v for k, v in result.items() if v is not None}
        elif r.status_code == 429:
            logger.warning("Apollo rate limited — backing off")
        else:
            logger.debug(f"Apollo returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"Apollo match failed: {e}")

    return None


def apollo_org_enrich(domain: str) -> Optional[Dict[str, Any]]:
    """
    [FUTURE] Enrich organization-level data from Apollo.
    Requires Enterprise plan for full data.

    Returns:
        headcount, revenue, founded_year, tech_stack, industry
    """
    # TODO: Implement when Apollo Enterprise plan is available
    # POST /v1/organizations/enrich {"domain": domain}
    return None
