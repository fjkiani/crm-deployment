"""
Cron API Router
================
Scheduled maintenance tasks: auto-audit leads, refresh stale data.

These endpoints are designed to be called by cron jobs or manual triggers.
They run batched operations and return summary reports.
"""

import json
import logging
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cron", tags=["cron"])


# ── Auto-Audit Batch ─────────────────────────────────────────────────────────

@router.post("/audit-batch")
async def audit_batch_endpoint(limit: int = 5):
    """
    Run deep audit on a batch of CRM leads:
    1. Fetch N recent leads
    2. BrightData reality-check each (current title, company)
    3. Flag stale leads in CRM
    4. Log audit results as FCRM Notes

    Returns: {verified: N, flagged: N, errors: N, details: [...]}
    """
    logger.info(f"🔄 CRON: audit-batch starting (limit={limit})")

    try:
        from eaia.skills.deep_audit_tool import deep_audit_leads
        result = deep_audit_leads.invoke({"limit": limit})
        # Parse the audit log
        lines = result.split("\n") if isinstance(result, str) else []
        verified = sum(1 for l in lines if "VERIFIED" in l)
        flagged = sum(1 for l in lines if "FLAGGED" in l)
        errors = sum(1 for l in lines if "Error" in l)
        return {
            "status": "completed",
            "verified": verified,
            "flagged": flagged,
            "errors": errors,
            "audit_log": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Audit batch failed: {e}")
        return {"status": "error", "detail": str(e)}


# ── Refresh Stale Leads ──────────────────────────────────────────────────────

@router.post("/refresh-stale")
async def refresh_stale_endpoint(limit: int = 5):
    """
    Re-enrich leads flagged as stale by the audit:
    1. Fetch leads with audit_status = "Flagged"
    2. Re-enrich each via Apollo (email, title, LinkedIn)
    3. Update CRM context with fresh data
    4. Log refresh results

    Returns: {refreshed: N, failed: N, details: [...]}
    """
    logger.info(f"🔄 CRON: refresh-stale starting (limit={limit})")

    results = []
    refreshed = 0
    failed = 0

    try:
        from eaia.frappe_tool import search_leads, update_context
        # Get leads — ideally we'd filter by "Flagged" audit status
        # For now, get recent leads and re-enrich them
        leads_result = search_leads.invoke({
            "query": "",
            "status": "Open",
            "limit": limit,
        })

        leads = []
        if isinstance(leads_result, dict) and leads_result.get("leads"):
            leads = leads_result["leads"]
        elif isinstance(leads_result, list):
            leads = leads_result

        for lead in leads[:limit]:
            lead_name = lead.get("name", "")
            prospect_name = lead.get("lead_name", lead.get("full_name", ""))
            company = lead.get("organization", lead.get("company_name", ""))

            if not (lead_name and prospect_name):
                continue

            try:
                # Re-enrich via Apollo
                from eaia.skills.apollo_enrichment import enrich_person
                import asyncio
                try:
                    apollo_data = asyncio.run(enrich_person(prospect_name, company or ""))
                except RuntimeError:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        apollo_data = pool.submit(
                            asyncio.run,
                            enrich_person(prospect_name, company or "")
                        ).result()

                if apollo_data:
                    update_context.invoke({
                        "lead_name": lead_name,
                        "context_json": json.dumps({
                            "apollo_email": apollo_data.get("email"),
                            "apollo_title": apollo_data.get("title"),
                            "apollo_linkedin": apollo_data.get("linkedin_url"),
                            "refresh_date": datetime.utcnow().isoformat(),
                            "refresh_source": "cron/refresh-stale",
                        }),
                    })
                    refreshed += 1
                    results.append({
                        "lead": lead_name,
                        "status": "refreshed",
                        "apollo_email": apollo_data.get("email"),
                    })
                else:
                    failed += 1
                    results.append({"lead": lead_name, "status": "no_apollo_data"})
            except Exception as e:
                failed += 1
                results.append({"lead": lead_name, "status": "error", "detail": str(e)})

    except Exception as e:
        logger.error(f"Refresh stale failed: {e}")
        return {"status": "error", "detail": str(e)}

    return {
        "status": "completed",
        "refreshed": refreshed,
        "failed": failed,
        "details": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Sequence Tick (Siege Engine Heartbeat) ────────────────────────────────────

@router.post("/sequence-tick")
async def sequence_tick_endpoint():
    """
    Siege engine heartbeat: check all active sequences and fire due steps.

    Designed to be called hourly by cron:
      curl -X POST http://localhost:8002/cron/sequence-tick

    Processes all active 21-day sequences:
    - Day 0: Initial email
    - Day 3: Angle rotation email
    - Day 7: Voice escalation (HOT leads only)
    - Day 14: Break-up email
    - Day 21: Close sequence
    """
    logger.info("🔄 CRON: sequence-tick starting")
    try:
        from eaia.pipeline.sequence_orchestrator import run_sequence_tick
        result = await run_sequence_tick()
        return result
    except Exception as e:
        logger.error(f"Sequence tick failed: {e}")
        return {"status": "error", "detail": str(e)}


# ── Start Sequence ────────────────────────────────────────────────────────────

@router.post("/start-sequence")
async def start_sequence_endpoint(lead_name: str, score: int = 50, framework: str = "pas"):
    """
    Start a new 21-day siege sequence for a lead.

    Called after enrichment + scoring + email approval.
    Immediately fires Day 0 (initial email).
    """
    logger.info(f"🚀 CRON: starting sequence for {lead_name} (score={score}, fw={framework})")
    try:
        from eaia.pipeline.sequence_orchestrator import start_sequence
        result = await start_sequence(lead_name, score, framework)
        return result
    except Exception as e:
        logger.error(f"Start sequence failed: {e}")
        return {"status": "error", "detail": str(e)}


# ── Warm-Up Reset (Midnight Cron) ─────────────────────────────────────────────

@router.post("/warmup-reset")
async def warmup_reset_endpoint():
    """
    Reset daily domain send counts and advance warm-up state.

    Designed to be called daily at midnight by cron:
      curl -X POST http://localhost:8002/cron/warmup-reset

    Resets all per-domain daily send counters to 0.
    """
    logger.info("🔄 CRON: warmup-reset starting")
    try:
        from eaia.pipeline.deliverability import get_pool
        pool = get_pool()
        pool.reset_daily_counts()
        return {
            "status": "ok",
            "domains_reset": len(pool.domains),
            "health": pool.get_health(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Warmup reset failed: {e}")
        return {"status": "error", "detail": str(e)}


# ── Vulture Protocol Scan (Hourly Cron) ───────────────────────────────────────

@router.post("/vulture-scan")
async def vulture_scan_endpoint():
    """
    Run the Phase 9 Vulture Protocol.
    
    Scans recent active leads, identifies their organizations,
    monitors those organizations for negative news (trials, layoffs, etc.),
    and drafts re-engagement emails if negative events are detected.
    
    Designed to be called hourly by cron:
      curl -X POST http://localhost:8002/cron/vulture-scan
    """
    logger.info("🦅 CRON: vulture-scan starting")
    try:
        from eaia.pipeline.agents.vulture_agent import run_vulture_scan
        result = await run_vulture_scan()
        return result
    except Exception as e:
        logger.error(f"Vulture scan failed: {e}")
        return {"status": "error", "detail": str(e)}
