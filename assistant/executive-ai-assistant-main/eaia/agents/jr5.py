"""
Agent JR5: "The Sequencer"
Mission: Construct the perfect multi-touch campaign for approved leads.
"""
import logging
from eaia.agents.state import AgentState

logger = logging.getLogger(__name__)

def jr5_sequencer_agent(state: AgentState) -> AgentState:
    """
    JR5 Node Logic:
    1. Filter for safe leads.
    2. Segment by role/ICP.
    3. Assign Sequence Templates.
    """
    try:
        leads = state.get("leads", [])
        safe_ids = state.get("safe_lead_ids", [])
        scorecards = state.get("lead_scorecards", {})
        
        logger.info(f"🧬 JR5 Sequencing {len(safe_ids)} safe leads...")
        
        # In a real CRM, we'd queue objects here. 
        # For this agent, we'll confirm the Strategy.
        
        pi_count = 0
        sponsor_count = 0
        
        for lead in leads:
            if lead["id"] not in safe_ids:
                continue
                
            role = lead.get("role", "UNKNOWN")
            
            # Simple Segmentation Logic
            if role in ["PI", "COORDINATOR"]:
                pi_count += 1
                # Template: SITE_ACTIVATION_V1
            elif role in ["SPONSOR", "CLIN_OPS"]:
                sponsor_count += 1
                # Template: SPONSOR_SPEED_V1
        
        # Define Campaign Specs
        campaign = {
            "name": f"Harvest_Operation_{state.get('target_condition', 'Gen')}",
            "sequence_template": "DYNAMIC_SEGMENTED", # or "SITE_ACTIVATION_V1" if primarily sites
            "throttle_limit": 50,
            "target_icp": "MIXED",
            "stats": {
                "queued_sites": pi_count,
                "queued_sponsors": sponsor_count
            }
        }
        
        logger.info(f"✅ JR5 Sequenced {pi_count} Sites and {sponsor_count} Sponsors.")
        
        return {
            "campaign": campaign,
            "mission_status": "READY_TO_LAUNCH",
            "messages": [{"role": "assistant", "content": f"JR5: Created campaign for {len(safe_ids)} leads."}]
        }

    except Exception as e:
        logger.error(f"❌ JR5 Failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "mission_status": "SEQUENCING_FAILURE"
        }
