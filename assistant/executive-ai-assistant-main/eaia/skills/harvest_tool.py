"""
Harvest Tool: Exposes the Army to the Agentic Chat Interface.
Allows the user to say "Run harvest on X" and have the Army execute.
"""
import asyncio
import concurrent.futures
from langchain_core.tools import tool
from eaia.agents.graph import build_army_graph


def _run_in_new_loop(coro):
    """Run a coroutine in a brand-new event loop in a separate thread.
    This avoids the 'asyncio.run() cannot be called from a running event loop' error
    when the tool is called from within uvicorn's async context."""
    def _target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_target)
        return future.result(timeout=120)


@tool
def run_harvest_mission(target_disease: str):
    """
    Executes 'Operation Harvest' (The Revenue Army) on a specific disease target.
    Scouts trials, Hunts emails (Apollo+AirSupport), Qualifies, Checks Compliance,
    Sequences, and Syncs to CRM.

    Args:
        target_disease: The condition to scout for (e.g. "Ovarian Cancer").
    """
    try:
        print(f"🚀 Launching Harvest Mission for: {target_disease}")

        # Build the Graph
        army = build_army_graph()

        # Define Input
        initial_state = {
            "mission": f"Find leads for {target_disease}",
            "leads": [],
            "safe_lead_ids": [],
            "campaign": {"name": f"Harvest_{target_disease}", "target_icp": "MIXED"},
            "lead_scorecards": {},
            "mission_status": "START",
            "errors": []
        }

        # Execute in isolated thread (safe to call from async context)
        result = _run_in_new_loop(army.ainvoke(initial_state))

        # Parse Result
        leads = result.get("leads", [])
        safe_leads = result.get("safe_lead_ids", [])

        summary = (
            f"✅ Mission Complete for '{target_disease}'.\n"
            f"Scouted: {len(leads)} leads.\n"
            f"Safe/Synced: {len(safe_leads)} leads.\n"
            f"Status: {result.get('mission_status')}"
        )
        return summary

    except Exception as e:
        return f"❌ Harvest Failed: {str(e)}"
