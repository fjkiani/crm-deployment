"""
Sequence Orchestrator — 21-Day Siege Engine
============================================
Autonomous multi-touch outreach automation.

Sequence Steps:
  Day 0:  Email #1 — Initial outreach (framework based on score)
  Day 3:  Email #2 — Different angle (rotate framework)
  Day 7:  Voice Call — If score >= 70 AND phone available
  Day 14: Email #3 — Break-up email (create FOMO)
  Day 21: Close — Mark exhausted, archive

The orchestrator runs as a cron job, checking all active sequences
and firing the next step when the time is right.
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ── Sequence Definition ───────────────────────────────────────────────────────

SIEGE_STEPS = [
    {"day": 0,  "type": "email",  "framework": None,         "label": "Initial Outreach"},
    {"day": 3,  "type": "email",  "framework": "pas",        "label": "Angle Rotate"},
    {"day": 7,  "type": "voice",  "min_score": 70,           "label": "Voice Escalation"},
    {"day": 14, "type": "email",  "framework": "aida",       "label": "Break-Up Email"},
    {"day": 21, "type": "close",                             "label": "Sequence Complete"},
]


def get_sequence_plan(score: int, framework: str, has_phone: bool) -> List[Dict]:
    """Generate a personalized sequence plan based on lead profile.

    Args:
        score: Lead score (0-100)
        framework: Initial email framework from scoring
        has_phone: Whether phone number is available

    Returns:
        List of sequence steps with adjustments
    """
    plan = []
    for step in SIEGE_STEPS:
        entry = {**step}

        # Day 0: Use the scored framework
        if step["day"] == 0:
            entry["framework"] = framework

        # Day 3: Rotate to a different framework
        if step["day"] == 3:
            rotation = {"challenger": "pas", "pas": "aida", "aida": "challenger"}
            entry["framework"] = rotation.get(framework, "pas")

        # Day 7: Skip voice if no phone or cold lead
        if step["type"] == "voice":
            if not has_phone or score < step.get("min_score", 0):
                entry["skip"] = True
                entry["skip_reason"] = (
                    "No phone number" if not has_phone
                    else f"Score {score} < {step['min_score']} threshold"
                )

        plan.append(entry)

    return plan


async def run_sequence_tick():
    """Cron-callable: check all active sequences and fire due steps.

    This is the heartbeat of the siege engine. Called by the cron endpoint
    every hour (or every 15 minutes for aggressive campaigns).

    Returns:
        Summary of actions taken
    """
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    # Get all active sequences
    result = await client.get_sequence_status("")  # empty = all active

    if "error" in result:
        logger.error(f"Sequence tick error: {result['error']}")
        return {"error": result["error"], "actions": []}

    active = result.get("sequences", result.get("result", []))
    if not active:
        return {"actions": [], "message": "No active sequences"}

    actions_taken = []

    for seq in active:
        lead_name = seq.get("lead_name", "")
        current_step = seq.get("current_step", 0)
        started_at = seq.get("started_at", "")
        score = seq.get("score", 0)

        if not lead_name or not started_at:
            continue

        # Calculate days elapsed
        try:
            start_date = datetime.fromisoformat(started_at)
            days_elapsed = (datetime.now() - start_date).days
        except (ValueError, TypeError):
            continue

        # Find the next due step
        for step in SIEGE_STEPS:
            if step["day"] <= days_elapsed and step["day"] > current_step:
                if step.get("skip"):
                    actions_taken.append({
                        "lead_name": lead_name,
                        "step": step["label"],
                        "action": "skipped",
                        "reason": step.get("skip_reason", ""),
                    })
                    continue

                # Fire the step
                try:
                    if step["type"] == "email":
                        fire_result = await client.fire_sequence_step(lead_name, dry_run=False)
                        actions_taken.append({
                            "lead_name": lead_name,
                            "step": step["label"],
                            "action": "fired",
                            "result": fire_result,
                        })

                    elif step["type"] == "voice":
                        # Voice call via Vapi — get phone from lead
                        dossier = await client.get_lead_dossier(lead_name)
                        phone = dossier.get("phone") or dossier.get("mobile_no")
                        if phone:
                            from eaia.tools.outreach_tools import voice_call
                            await voice_call.ainvoke({
                                "phone_number": phone,
                                "prospect_name": dossier.get("lead_name", lead_name),
                                "objective": "Follow up on our recent email about strategic partnership",
                            })
                            actions_taken.append({
                                "lead_name": lead_name,
                                "step": step["label"],
                                "action": "voice_call_placed",
                            })

                    elif step["type"] == "close":
                        await client.update_lead_context(lead_name, {
                            "sequence_status": "exhausted",
                            "sequence_completed_at": datetime.now().isoformat(),
                        })
                        actions_taken.append({
                            "lead_name": lead_name,
                            "step": step["label"],
                            "action": "sequence_closed",
                        })

                except Exception as e:
                    actions_taken.append({
                        "lead_name": lead_name,
                        "step": step["label"],
                        "action": "error",
                        "error": str(e),
                    })

    logger.info(f"🔄 Sequence tick: {len(actions_taken)} actions on {len(active)} active sequences")
    return {
        "active_sequences": len(active),
        "actions": actions_taken,
        "timestamp": datetime.now().isoformat(),
    }


async def start_sequence(lead_name: str, score: int, framework: str) -> dict:
    """Start a new 21-day siege sequence for a lead.

    Called after enrichment + scoring + email draft approval.

    Args:
        lead_name: CRM Lead ID
        score: Lead score from enrichment
        framework: Email framework from scoring
    """
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()

    # Get lead data for phone check
    dossier = await client.get_lead_dossier(lead_name)
    has_phone = bool(dossier.get("phone") or dossier.get("mobile_no"))

    plan = get_sequence_plan(score, framework, has_phone)

    # Store sequence plan in CRM
    await client.update_lead_context(lead_name, {
        "sequence_status": "active",
        "sequence_started_at": datetime.now().isoformat(),
        "sequence_plan": plan,
        "sequence_current_step": 0,
        "sequence_score": score,
        "sequence_framework": framework,
    })

    # Fire Day 0 immediately
    fire_result = await client.fire_sequence_step(lead_name, dry_run=False)

    return {
        "status": "started",
        "lead_name": lead_name,
        "plan": plan,
        "day_0_result": fire_result,
    }
