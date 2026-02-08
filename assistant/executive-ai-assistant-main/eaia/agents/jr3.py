"""
Agent JR3: "The Qualifier"
Mission: Score leads against Ideal Customer Profile (ICP).
"""
import logging
from eaia.agents.state import AgentState

logger = logging.getLogger(__name__)

def jr3_qualifier_agent(state: AgentState) -> AgentState:
    """
    JR3 Node Logic:
    1. Iterate leads.
    2. Apply Scoring Logic.
    3. Generate Scorecards.
    """
    try:
        leads = state.get("leads", [])
        logger.info(f"⚖️ JR3 Qualifying {len(leads)} leads...")
        
        scorecards = {}
        
        for lead in leads:
            score = 0
            signals = []
            why_us = ""
            
            # --- Scoring Logic (Heuristic) ---
            
            # 1. Contactability (Critical)
            if lead.get("email"):
                score += 50
                signals.append("has_email")
            else:
                signals.append("no_email")
            
            # 2. Role Value
            role = lead.get("role", "UNKNOWN")
            if role == "PI":
                score += 30
                signals.append("key_decision_maker")
                why_us = "We can fast-track your biomarker feasibility response."
            elif role == "COORDINATOR":
                score += 40 # Coordinators are often better entry points for feasibility
                signals.append("gatekeeper")
                why_us = "We reduce your feasibility paperwork burden."
                
            # 3. Organization (Metadata check would go here)
            
            # 4. Biomarker Signals (From Source Trial Metadata - Advanced)
            # Future: check if trial has 'Biomarker' tag
            
            # --- Categorization ---
            if score >= 80:
                icp_fit = "A"
            elif score >= 50:
                icp_fit = "B"
            else:
                icp_fit = "C"
                
            scorecards[lead["id"]] = {
                "total_score": score,
                "icp_fit": icp_fit,
                "intent_signals": signals,
                "why_us": why_us
            }
            
        logger.info(f"✅ JR3 Scored {len(scorecards)} leads.")
        
        return {
            "lead_scorecards": scorecards,
            "mission_status": "QUALIFICATION_COMPLETE",
            "messages": [{"role": "assistant", "content": f"JR3: Scored {len(scorecards)} leads."}]
        }

    except Exception as e:
        logger.error(f"❌ JR3 Failed: {e}")
        # Don't fail the whole mission, just log error
        return {
            "errors": state.get("errors", []) + [str(e)],
            "mission_status": "PARTIAL_FAILURE"
        }
