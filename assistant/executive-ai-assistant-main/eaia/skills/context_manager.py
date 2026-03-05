import os
import requests
import json
from datetime import datetime
try:
    from .research_tool import ResearchIntelligence
except ImportError:
    ResearchIntelligence = None

class ContextManager:
    """
    Manages pre-call intelligence.
    Fetches the pipeline dossier for a lead, or falls back to basic DB lookup if not available.
    """
    def __init__(self):
        self.frappe_url = NyxConfig.FRAPPE_URL
        self.api_key = os.getenv("FRAPPE_API_KEY")
        self.api_secret = os.getenv("FRAPPE_API_SECRET")

    def get_dossier(self, phone_number=None, email=None, lead_id=None):
        """
        Retrieves the 'Dossier' for a target.
        Priority: Lead Prospect > CRM Contact > Lead
        """
        if self.mock_mode:
            return self._get_mock_dossier()

        try:
            # 1. Try to find a Lead Prospect (The Iron SDR Target)
            dossier = self._fetch_from_api(phone_number, email)
            if dossier:
                return dossier
            
            return "No dossier found. Unknown caller. Treat as cold call."
            
        except Exception as e:
            print(f"⚠️ API Error in ContextManager: {e}")
            return self._get_mock_dossier()

    def _fetch_from_api(self, phone_number, email):
        """Fetches dossier data from Frappe Backend."""
        url = f"{self.frappe_url}/api/method/crm.api.intelligence.get_dossier"
        headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
        params = {"phone": phone_number, "email": email}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("message")
                if data:
                    return self._format_dossier(data)
        except:
            pass
        return None

    def _format_dossier(self, data):
        """Formats the raw JSON into a prompt-ready string."""
        if data.get("doctype") == "Lead Prospect":
            # ENRICHMENT: Fetch Real-Time Research if missing
            research_text = data.get('recent_papers')
            
            # Check if we should enrich (if research_tool is available and data is thin)
            if ResearchIntelligence and data.get('pi_name') and (not research_text or len(str(research_text)) < 10):
                try:
                    print(f"🧠 Enchanting Dossier with PubMed Data for {data.get('pi_name')}...")
                    pubs = ResearchIntelligence.get_pi_publications(data.get('pi_name'), limit=3)
                    if pubs:
                        research_text = ", ".join([f"{p['title']} ({p['date']})" for p in pubs])
                except Exception as e:
                    print(f"⚠️ Research Enrichment Warning: {e}")
            
            return f"""
            TARGET DOSSIER (Priority: {data.get('tier')})
            ---------------------------------------------
            NAME: Dr. {data.get('pi_name')}
            INSTITUTION: {data.get('institution')}
            RESEARCH: {data.get('cancer_type')}
            RECENT PUBLICATIONS: {research_text}
            
            GOAL: Recruit for Trial {data.get('source_ref_id')}
            """
        else:
            return f"""
            CONTACT DOSSIER
            ---------------
            NAME: {data.get('first_name')} {data.get('last_name')}
            COMPANY: {data.get('company_name')}
            """

    def _get_mock_dossier(self):
        """Rich Fallback for Iron SDR Logic Testing."""
        return """
        [SIMULATED DOSSIER - IRON SDR MODE]
        -----------------------------------
        TARGET: Dr. Sarah Connor
        ROLE: Principal Investigator, Oncology
        INSTITUTION: Cyberdyne Medical Center
        
        INTELLIGENCE:
        - Recent Paper: "Targeting p53 mutations in Metastatic NSCLC" (2025)
        - Grant Funding: $2.5M (NIH)
        - Tier: 1 (High Priority)
        
        MISSION OBJECTIVE:
        - Acknowledge her recent paper on p53.
        - Propose 20-min strategy session for the "Skynet" Phase 3 Trial.
        - Handle Objection: "I am too busy" -> Offer async review.
        """
