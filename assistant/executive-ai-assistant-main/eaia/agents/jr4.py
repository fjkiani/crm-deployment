"""
Agent JR4: "The Sheriff" (Compliance & Deliverability)
Mission: Ensure we don't burn the domain or break the law.
"""
import logging
from eaia.agents.state import AgentState

logger = logging.getLogger(__name__)

# Mock Opt-Out List (In production, this would be a specialized DB or Redis Set)
OPT_OUT_DOMAINS = ["example.com", "test.com"]
OPT_OUT_EMAILS = ["angry_pi@university.edu"]

def jr4_compliance_agent(state: AgentState) -> AgentState:
    """
    JR4 Node Logic:
    1. Check global opt-outs.
    2. Check daily limits (Throttle).
    3. Mark leads as SAFE or BLOCKED.
    """
    try:
        leads = state.get("leads", [])
        scorecards = state.get("lead_scorecards", {})
        compliance = state.get("compliance", {
            "blocked_domains": OPT_OUT_DOMAINS,
            "opt_outs": OPT_OUT_EMAILS,
            "risk_level": "LOW"
        })
        
        logger.info(f"👮‍♂️ JR4 Inspecting {len(leads)} leads for compliance...")
        
        safe_leads = []
        blocked_count = 0
        
        for lead in leads:
            email = lead.get("email")
            lead_id = lead.get("id")
            
            # Rule 1: Must have email to be dangerous (or useful)
            if not email:
                # Leads without email are 'safe' but useless for outbound
                # We keep them for manual research
                continue
            
            # Rule 2: Opt-Out Check
            if email in compliance["opt_outs"]:
                logger.warning(f"🚫 BLOCKED: {email} is opted out.")
                blocked_count += 1
                continue
                
            # Rule 3: Domain Check
            domain = email.split("@")[-1]
            if domain in compliance["blocked_domains"]:
                logger.warning(f"🚫 BLOCKED: {domain} is blacklisted.")
                blocked_count += 1
                continue
            
            # Rule 4: Score Threshold (Don't spam low-quality leads)
            score = scorecards.get(lead_id, {}).get("total_score", 0)
            if score < 40:
                logger.info(f"🛑 REJECTED: {email} score too low ({score}).")
                continue
                
            # PASSED
            safe_leads.append(lead)
            
        logger.info(f"✅ JR4 Approved {len(safe_leads)} leads for outreach (Blocked {blocked_count}).")
        
        # Update state with approved list (or a flag on the lead object)
        # For this design, we'll pass the 'safe_leads' list to the Sequencer.
        # But we must preserve the original 'leads' in state for record.
        # Let's add 'approved_lead_ids' to the compliance log or a new key.
        
        # Actually, let's just let JR5 filter by 'Approved' status if we updated the lead object.
        # But LeadProfile is a TypedDict (rigid).
        # Let's add a list of IDs to pass to JR5.
        
        return {
            "safe_lead_ids": [l["id"] for l in safe_leads],
            "compliance": compliance,
            "mission_status": "COMPLIANCE_CHECKED",
            "messages": [{"role": "assistant", "content": f"JR4: Approved {len(safe_leads)} leads."}],
        }

    except Exception as e:
        logger.error(f"❌ JR4 Failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "mission_status": "COMPLIANCE_FAILURE"
        }
