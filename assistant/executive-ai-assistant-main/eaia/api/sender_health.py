"""
Sender Health API Router
========================
Exposes deliverability metrics: domain health, warm-up status, rate limits.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sender", tags=["sender"])


@router.get("/health")
async def sender_health_endpoint():
    """Get health stats for all sending domains.

    Returns per-domain:
    - status (active/paused)
    - daily_limit (based on warm-up age)
    - sends_today / sends_total
    - bounce_rate / complaint_rate
    - last_send timestamp
    """
    from eaia.pipeline.deliverability import get_pool
    pool = get_pool()
    return {
        "domains": pool.get_health(),
        "total_domains": len(pool.domains),
        "active_domains": sum(1 for d in pool.domains if not pool._state[d]["paused"]),
    }


@router.post("/reset-daily")
async def reset_daily_endpoint():
    """Reset daily send counts (called by midnight cron)."""
    from eaia.pipeline.deliverability import get_pool
    pool = get_pool()
    pool.reset_daily_counts()
    return {"status": "ok", "message": "Daily send counts reset"}


@router.post("/pause/{domain}")
async def pause_domain_endpoint(domain: str):
    """Manually pause a sending domain."""
    from eaia.pipeline.deliverability import get_pool
    pool = get_pool()
    if domain in pool._state:
        pool._state[domain]["paused"] = True
        return {"status": "paused", "domain": domain}
    return {"status": "error", "detail": f"Domain {domain} not in pool"}


@router.post("/resume/{domain}")
async def resume_domain_endpoint(domain: str):
    """Resume a paused sending domain."""
    from eaia.pipeline.deliverability import get_pool
    pool = get_pool()
    if domain in pool._state:
        pool._state[domain]["paused"] = False
        return {"status": "resumed", "domain": domain}
    return {"status": "error", "detail": f"Domain {domain} not in pool"}
