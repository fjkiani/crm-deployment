"""
Retry Queue — Sprint 12: UNKNOWN Signal Guard
==============================================
When enrichment quarantines a lead (insufficient signals), this module
schedules a retry with different tool ordering.

Retry strategy:
  1st retry: BrightData first (instead of Tavily)
  2nd retry: Farfalle deep research
  3rd retry: Manual flag — needs human SDR attention

Cron: crm.api.nyx_retry_queue.run_retry_tick (hourly)
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def quarantine_for_retry(lead_name: str, reason: str, retry_after_hours: int = 24) -> dict:
    """Schedule a quarantined lead for re-enrichment.

    Args:
        lead_name: CRM Lead ID
        reason: Why it was quarantined
        retry_after_hours: Hours before retry (default 24)
    """
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    retry_at = (datetime.utcnow() + timedelta(hours=retry_after_hours)).isoformat()

    # Get current retry count
    dossier = await client.get_lead_dossier(lead_name)
    current_count = 0
    try:
        intel = dossier.get("intel", {})
        current_count = int(intel.get("nyx_retry_count", 0))
    except (ValueError, TypeError):
        pass

    new_count = current_count + 1

    # After 3 retries, escalate to manual
    if new_count > 3:
        await client.update_lead_context(lead_name, {
            "nyx_signal_gate": "manual_review",
            "nyx_quarantine_reason": f"Exhausted {new_count - 1} retries. Original: {reason}",
            "outreach_status": "Manual Review",
        })
        await client.create_note(
            lead_name=lead_name,
            title="⚠️ Manual Review Required",
            content=f"Lead exhausted all {new_count - 1} auto-retries.\n\nOriginal quarantine: {reason}\n\nNeeds human SDR attention.",
        )
        return {"status": "escalated_to_manual", "retry_count": new_count - 1}

    # Determine retry strategy based on count
    strategies = {
        1: "brightdata_first",    # Try BrightData before Tavily
        2: "farfalle_deep",       # Use Farfalle RAG for deep research
        3: "all_sources_parallel", # Hit everything at once
    }
    strategy = strategies.get(new_count, "all_sources_parallel")

    await client.update_lead_context(lead_name, {
        "nyx_retry_count": new_count,
        "nyx_retry_at": retry_at,
        "nyx_retry_strategy": strategy,
        "nyx_quarantine_reason": reason,
    })

    logger.info(
        f"🔄 Retry scheduled for {lead_name}: "
        f"attempt {new_count}, strategy={strategy}, at {retry_at}"
    )

    return {
        "status": "retry_scheduled",
        "lead_name": lead_name,
        "retry_count": new_count,
        "retry_at": retry_at,
        "strategy": strategy,
    }


async def get_retry_queue() -> list:
    """Return all leads due for retry enrichment."""
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    # Find quarantined leads with nyx_retry_at in the past
    result = await client.search_leads("", status="Quarantined", limit=50)
    leads = result.get("leads", result.get("result", []))

    due = []
    now = datetime.utcnow().isoformat()
    for lead in leads:
        retry_at = lead.get("nyx_retry_at", "")
        if retry_at and retry_at <= now:
            due.append(lead)

    return due


async def run_retry_tick() -> dict:
    """Cron-callable: re-enrich quarantined leads that are due for retry.

    Call from bench:
        bench --site crm.localhost execute crm.api.nyx_retry_queue.run_retry_tick
    """
    due_leads = await get_retry_queue()

    if not due_leads:
        return {"retried": 0, "message": "No leads due for retry"}

    results = []
    for lead in due_leads:
        lead_name = lead.get("name", "")
        strategy = lead.get("nyx_retry_strategy", "brightdata_first")

        try:
            # Trigger re-enrichment via EAIA
            import httpx
            from eaia.config import NyxConfig

            async with httpx.AsyncClient(timeout=60.0) as http:
                resp = await http.post(
                    f"{NyxConfig.EAIA_URL}/enrich",
                    json={
                        "lead_name": lead_name,
                        "strategy": strategy,
                        "is_retry": True,
                    },
                    timeout=60.0,
                )
                results.append({
                    "lead_name": lead_name,
                    "strategy": strategy,
                    "status": "triggered",
                    "http_status": resp.status_code,
                })

        except Exception as e:
            results.append({
                "lead_name": lead_name,
                "status": "error",
                "error": str(e),
            })

    logger.info(f"🔄 Retry tick: processed {len(results)} leads")
    return {
        "retried": len(results),
        "results": results,
        "timestamp": datetime.utcnow().isoformat(),
    }
