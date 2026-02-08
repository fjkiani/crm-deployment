"""
Harvest Tool: Exposes the Army to the Agentic Chat Interface.
Allows the user to say "Run harvest on X" and have the Army execute.
"""
import asyncio
from langchain_core.tools import tool
from eaia.agents.graph import build_army_graph

@tool
def run_harvest_mission(target_disease: str):
    """
    Executes 'Operation Harvest' (The Revenue Army) on a specific disease target.
    Scouts trials, Hunts emails (Apollo+AirSupport), Qualifies, Checks Compliance, 
    Sequences, and Syncs to CRM.
    
    Args:
        target_disease: The condition to scout for (e.g. "Ovarian Cancer").
    """
    # This acts as a synchronous wrapper for the async graph
    # In a real async agent, we might await it directly, but LangChain tools are often sync.
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
        
        # Execute (using asyncio.run since we are inside a sync tool wrapper)
        result = asyncio.run(army.ainvoke(initial_state))
        
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
