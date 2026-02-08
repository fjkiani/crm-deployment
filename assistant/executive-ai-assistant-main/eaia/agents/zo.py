"""
Agent Zo: "The Integrator"
Mission: Sync verified intelligence into Farfalle CRM (Leaf Prospect).
"""
import logging
import os
import json
import requests
from dotenv import load_dotenv

# Load secrets relative to this file
params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".secrets", ".env"))
load_dotenv(params_path)

from eaia.agents.state import AgentState

logger = logging.getLogger(__name__)

class CRMClient:
    def __init__(self):
        self.base_url = os.getenv("FRAPPE_URL", "http://localhost:8000")
        self.api_key = os.getenv("FRAPPE_API_KEY")
        self.api_secret = os.getenv("FRAPPE_API_SECRET")
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
        
    def upsert_prospect(self, data: dict):
        """
        Creates or updates a Lead Prospect.
        Uses pi_email as the key.
        """
        if not self.api_key:
            logger.warning("mocking CRM sync (no keys)")
            return "MOCK_ID"
            
        try:
            # 1. Check existence
            email = data.get("pi_email")
            filters = json.dumps([["pi_email", "=", email]])
            check_url = f"{self.base_url}/api/resource/Lead Prospect?filters={filters}"
            
            resp = requests.get(check_url, headers=self.headers)
            existing = resp.json().get("data", [])
            
            if existing:
                # Update
                doc_name = existing[0]["name"]
                update_url = f"{self.base_url}/api/resource/Lead Prospect/{doc_name}"
                requests.put(update_url, headers=self.headers, json=data)
                logger.info(f"🔄 Zo Updated Prospect: {email}")
                return doc_name
            else:
                # Create
                create_url = f"{self.base_url}/api/resource/Lead Prospect"
                resp = requests.post(create_url, headers=self.headers, json=data)
                if resp.status_code == 200:
                    logger.info(f"✨ Zo Created Prospect: {email}")
                    return resp.json()["data"]["name"]
                else:
                    logger.error(f"❌ Zo Create Failed: {resp.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ CRM Error: {e}")
            return None

    def create_sequence_instance(self, prospect_name: str, sequence_name: str):
        """
        Links a Prospect to an Outreach Sequence.
        """
        if not self.api_key: return
        
        try:
            data = {
                "prospect": prospect_name,
                "sequence": sequence_name,
                "status": "Active",
                "start_date": "2026-02-06" # In real app, use today
            }
            url = f"{self.base_url}/api/resource/Outreach Sequence Instance"
            resp = requests.post(url, headers=self.headers, json=data)
            if resp.status_code == 200:
                logger.info(f"🧬 Sequence Started: {sequence_name} -> {prospect_name}")
            else:
                logger.warning(f"⚠️ Sequence Failed: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Sequence Error: {e}")


def zo_crm_sync(state: AgentState) -> AgentState:
    """
    Zo Node Logic:
    1. Iterate Safe Leads.
    2. Sync to 'Lead Prospect'.
    3. Trigger Sequence if applicable.
    """
    leads = state.get("leads", [])
    safe_ids = state.get("safe_lead_ids", [])
    scorecards = state.get("lead_scorecards", {})
    campaign = state.get("campaign", {})
    
    client = CRMClient()
    
    synced_count = 0
    
    # 1. Find the safe lead objects
    safe_lead_objects = [l for l in leads if l["id"] in safe_ids]
    
    logger.info(f"🧠 Zo Syncing {len(safe_lead_objects)} leads to Farfalle...")
    
    for lead in safe_lead_objects:
        lead_id = lead["id"]
        score_data = scorecards.get(lead_id, {})
        score = score_data.get("total_score", 0)
        
        # Map to DocType: Lead Prospect
        prospect_data = {
            "pi_name": lead["name"],
            "pi_email": lead["email"],
            "institution": lead["organization_id"],
            "source": "ClinicalTrials",
            "source_ref_id": lead["source_trial"],
            "lead_score": score,
            "tier": "Tier 1" if score > 75 else "Tier 2" if score > 40 else "Tier 3",
            "notes": f"Role: {lead.get('role', 'Unknown')} | Harvested by EAIA."
        }
        
        # Sync
        prospect_name = client.upsert_prospect(prospect_data)
        
        # Sequence Trigger
        # Only if we got a prospect ID and campaign has a template
        if prospect_name and campaign.get("sequence_template"):
            # We assume the sequence document "SITE_ACTIVATION_V1" exists in CRM.
            # If not, it might fail. Ideally we check or create text version.
            # Using the campaign template name directly.
            seq_template = campaign.get("sequence_template")
            # Override for demo if "DYNAMIC_SEGMENTED" is passed
            if seq_template == "DYNAMIC_SEGMENTED":
                # Heuristic
                if lead.get("role") == "PI":
                    seq_template = "Site Activation V1" # Assumed Name
                else:
                    seq_template = "Sponsor Introduction V1"
            
            # Create Instance
            client.create_sequence_instance(prospect_name, seq_template)
            
        synced_count += 1
        
    return {
        "mission_status": "SYNCED",
        "messages": [{"role": "assistant", "content": f"Zo: Synced {synced_count} prospects to CRM."}]
    }
