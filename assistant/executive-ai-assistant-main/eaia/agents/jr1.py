"""
Agent JR1: "The Scout"
Mission: Find and seed relevant trials from ClinicalTrials.gov.
"""
import logging
import json
from eaia.agents.state import AgentState
# from eaia.skills.clinical_mcp import search_clinical_trials

logger = logging.getLogger(__name__)

def jr1_scout_agent(state: AgentState) -> AgentState:
    """
    JR1 Node Logic:
    1. Search for trials based on target_condition.
    2. Store raw results.
    """
    try:
        query = state.get("target_condition", "Ovarian Cancer")
        logger.info(f"🕵️‍♂️ JR1 Scouting for: {query}")
        
        # Search using harvested skill (limit for demo/safety)
        # Taking raw string output from tool and doing simple parse if possible, 
        # or we might need to adjust clinical_mcp to return structured data if we want it perfect.
        # For now, let's assume we can parse extracting NCT IDs from the text string or modify tool.
        # Wait, I harvested clinical_mcp.py and it returns a formatted string.
        # To be "Agentic", I should probably make it return JSON or parse the string.
        # Let's import the client directly for cleaner data access since we are "internal".
        
        from eaia.mcp.biomed_mcp.biomed_agents.tools.clinical_tools import get_clinical_trials_client
        ct = get_clinical_trials_client()
        
        # Using raw client for data access
        fields = ["NCT Number", "Study Title", "Conditions"]
        results = ct.get_study_fields(
            search_expr=query,
            fields=fields,
            max_studies=10 # Limit for MVP speed
        )
        
        # Results[0] is header, [1:] are rows
        found_trials = []
        if len(results) > 1:
            headers = results[0]
            for row in results[1:]:
                trial = dict(zip(headers, row))
                found_trials.append(trial)
        
        logger.info(f"✅ JR1 Found {len(found_trials)} trials.")
        
        # Map to TrialMetadata schema
        trial_seeds = []
        for trial in found_trials:
             trial_seeds.append({
                 "nct_id": trial.get("NCT Number", ""),
                 "title": trial.get("Study Title", ""),
                 "conditions": trial.get("Conditions", ""),
                 "phase": trial.get("Study Phase", "Unknown") # Field might be missing if we didn't request it
             })

        return {
            "trial_seeds": trial_seeds,
            "mission_status": "SEEDING_COMPLETE",
            # Add to messages log
            "messages": [{"role": "assistant", "content": f"JR1: Scouted {len(trial_seeds)} trials for {query}."}]
        }

    except Exception as e:
        logger.error(f"❌ JR1 Failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "mission_status": "FAILED",
            "next_step": "STOP"
        }
