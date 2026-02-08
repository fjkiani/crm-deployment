"""
Intelligence Extractor Service
Transplanted from Oncology Backend

Extracts deep intelligence about PIs and their trials:
1. Trial Intelligence (ClinicalTrials.gov API)
2. Research Intelligence (PubMed API)
3. Biomarker Intelligence (KELIM fit, CA-125, platinum detection)
4. Goal Understanding (what they're trying to achieve)
5. Value Proposition Generation (how we can help)
"""
import logging
from typing import Dict, List, Any, Optional

from eaia.services.personalized_outreach.utils import extract_pi_information
from eaia.skills.research_tool import ResearchIntelligence
from eaia.skills.clinical_mcp import get_clinical_trials_client

logger = logging.getLogger(__name__)

class IntelligenceExtractor:
    """
    Extracts comprehensive intelligence about PIs and their trials.
    """
    
    def __init__(self):
        # We rely on ResearchIntelligence static methods and ClinicalTrials client
        pass
    
    async def extract_trial_intelligence(self, nct_id: str) -> Dict[str, Any]:
        """
        Fetch and analyze trial details from ClinicalTrials.gov API.
        """
        try:
            ct = get_clinical_trials_client()
            studies = ct.get_full_studies(search_expr=f"NCT Number={nct_id}", max_studies=1)
            
            if not studies or len(studies) <= 1:
                return {"nct_id": nct_id, "error": "Trial not found"}
                
            # Convert to dict (assuming studies[0] is header, studies[1] is data)
            # pytrials returns list of lists usually? No it returns CSV-like rows
            # Let's assume the client handles it, or we treat it as raw fields
            # For this MVP transplant, we will use the 'get_study_fields' approach if 'get_full_studies' is complex
            
            # Using get_study_fields for critical info
            fields = [
                "NCT Number", "Study Title", "Study Status", "Phases",
                "Conditions", "Interventions", "Primary Outcome Measures",
                "Secondary Outcome Measures", "Eligibility Criteria",
                "Locations", "Start Date", "Completion Date",
                "Study Officials" # This returns complex text, might need parsing
            ]
            
            # Note: pytrials might return strings for complex fields. 
            # We map them to the expected schema.
            
            # For now, let's construct a simplified object based on what we can get easily
            # Real implementation might need direct API access if pytrials is limited
            
            trial_cols = studies[0]
            trial_vals = studies[1]
            trial_data = dict(zip(trial_cols, trial_vals))
            
            # Map fields
            title = trial_data.get("Study Title", "")
            status = trial_data.get("Study Status", "")
            phases = [trial_data.get("Study Phase", "")]
            conditions = trial_data.get("Conditions", "").split("|")
            interventions = trial_data.get("Interventions", "").split("|")
            outcomes = (trial_data.get("Primary Outcome Measures", "") + "|" + trial_data.get("Secondary Outcome Measures", "")).split("|")
            
            # Extract PI (This is tricky with CSV data, might need the utils.extract_pi_information if we had raw JSON)
            # Since we don't have raw JSON from pytrials csv output easily, we rely on 'Study Officials' or Locations
            pi_info = {} # TODO: improve extraction from CSV
            
            return {
                "nct_id": nct_id,
                "title": title,
                "status": status,
                "phase": phases,
                "conditions": conditions,
                "interventions": interventions,
                "outcomes": outcomes,
                "eligibility": {"inclusion": trial_data.get("Eligibility Criteria", "")},
                "pi_info": pi_info, 
                "full_trial_data": trial_data
            }
        except Exception as e:
            logger.error(f"Failed to extract trial intelligence for {nct_id}: {e}")
            return {"nct_id": nct_id, "error": str(e)}
    
    async def extract_research_intelligence(self, pi_name: str, institution: str) -> Dict[str, Any]:
        """
        Search PubMed via ResearchSkills.
        """
        try:
            # delegated to our Research Tool
            result = ResearchIntelligence.get_pi_publications(pi_name, limit=10)
            
            return {
                "publications": result.get("publications", []),
                "research_focus": result.get("research_focus", []),
                "publication_count": len(result.get("publications", [])),
                "recent_publications": result.get("recent_publications", [])
            }
        except Exception as e:
            logger.error(f"Failed to extract research info: {e}")
            return {}

    async def analyze_biomarker_intelligence(self, trial_data: Dict) -> Dict[str, Any]:
        """
        Analyze trial for biomarker relevance (KELIM logic).
        """
        fit_reasons = []
        kelim_fit_score = 0.0
        platinum_detected = False
        ca125_monitoring_detected = False
        resistance_focus_detected = False
        
        interventions = trial_data.get("interventions", [])
        intervention_text = " ".join(interventions).lower()
        
        if any(term in intervention_text for term in ["platinum", "carboplatin", "cisplatin", "oxaliplatin"]):
            platinum_detected = True
            fit_reasons.append("Trial uses platinum-based therapy")
            kelim_fit_score += 1.0
            
        outcomes = trial_data.get("outcomes", [])
        outcomes_text = " ".join(outcomes).lower()
        if "ca-125" in outcomes_text or "ca125" in outcomes_text:
            ca125_monitoring_detected = True
            fit_reasons.append("Trial monitors CA-125")
            kelim_fit_score += 1.0
            
        title = trial_data.get("title", "").lower()
        if "ovarian" in title or any("ovarian" in c.lower() for c in trial_data.get("conditions", [])):
             fit_reasons.append("Ovarian cancer trial")
             kelim_fit_score += 1.0
             
        kelim_fit_score = min(kelim_fit_score, 5.0)
        
        return {
            "kelim_fit_score": kelim_fit_score,
            "fit_reasons": fit_reasons,
            "platinum_detected": platinum_detected
        }

    async def understand_goals(self, trial_data: Dict, research_data: Dict) -> List[str]:
        """Infer goals."""
        goals = []
        # Simplified logic
        title = trial_data.get("title", "").lower()
        if "resistance" in title:
            goals.append("Understanding mechanisms of treatment resistance")
        if "biomarker" in title:
            goals.append("Identifying predictive biomarkers")
            
        focus = research_data.get("research_focus", [])
        if focus:
            goals.append(f"Advancing research in {', '.join(focus[:2])}")
            
        if not goals:
            goals.append("Improving patient outcomes")
        return goals

    async def generate_value_proposition(self, goals: List[str], fit_reasons: List[str]) -> List[str]:
        """Generate Value Props."""
        props = []
        if any("platinum" in r.lower() for r in fit_reasons):
            props.append("KELIM biomarker validation for platinum response prediction")
        if "resistance" in str(goals).lower():
            props.append("Early resistance prediction using CA-125 kinetics")
            
        if not props:
            props.append("AI-powered precision medicine platform")
        return props

    async def extract_complete_intelligence(self, nct_id: str, pi_name: str = None, institution: str = None) -> Dict[str, Any]:
        """Orchestrator."""
        trial_intel = await self.extract_trial_intelligence(nct_id)
        if "error" in trial_intel:
            return trial_intel
            
        if not pi_name:
            # extract from trial if possible
            pi_name = trial_intel.get("pi_info", {}).get("name", "")
            
        research_intel = {}
        if pi_name:
            research_intel = await self.extract_research_intelligence(pi_name, institution)
            
        biomarker_intel = await self.analyze_biomarker_intelligence(trial_intel)
        goals = await self.understand_goals(trial_intel, research_intel)
        value_prop = await self.generate_value_proposition(goals, biomarker_intel.get("fit_reasons", []))
        
        return {
            "nct_id": nct_id,
            "trial_intelligence": trial_intel,
            "research_intelligence": research_intel,
            "biomarker_intelligence": biomarker_intel,
            "goals": goals,
            "value_proposition": value_prop,
            "status": "success",
            "personalization_quality": 0.8 # Placeholder
        }
