import sys
import os

# Ensure we can import from local modules
sys.path.append(os.getcwd())

from eaia.skills.clinical_mcp import search_clinical_trials
from eaia.skills.research_tool import ResearchIntelligence
from eaia.skills.context_manager import ContextManager

def prove_intelligence():
    print("="*60)
    print("🛸 OPERATION IRON SDR: INTELLIGENCE VERIFICATION")
    print("="*60)

    # 1. Level 1: Targeting (ClinicalTrials.gov)
    print("\n[LEVEL 1] 🎯 Targeting Mechanism (BioMed-MCP)")
    print("Searching ClinicalTrials.gov for 'Ovarian Cancer'...")
    
    try:
        trials_output = search_clinical_trials.invoke({"search_expr": "Ovarian Cancer", "max_studies": 3})
        print(trials_output[:500] + "...\n[Truncated]")
    except Exception as e:
        print(f"❌ Level 1 Failed: {e}")
        # Fallback for demo if pytrials missing
        print("(Note: pymed/pytrials might be missing in this env, but logic is planted)")

    # 2. Level 2: Context (PubMed Intelligence)
    print("\n[LEVEL 2] 🧠 Context Enchantment (PubMed)")
    pi_name = "Isabelle Ray-Coquard" # Famous Ovarian Cancer PI (KELIM)
    print(f"Enriching Dossier for PI: {pi_name}...")
    
    try:
        # Direct Research Tool Usage
        pubs = ResearchIntelligence.get_pi_publications(pi_name, limit=3)
        print(f"✅ Found {len(pubs)} Publications:")
        for p in pubs:
            print(f"   - {p['title']} ({p['date']})")
            
        # Context Manager Usage
        print("\n[Generating 'Enchanted Dossier' via ContextManager...]")
        
        # Simulate CRM Data
        mock_crm_data = {
            "pi_name": pi_name,
            "institution": "Centre Léon Bérard",
            "cancer_type": "Ovarian Cancer",
            "source_ref_id": "NCT00000000",
            "tier": "1",
            "recent_papers": "" # INTENTIONALLY EMPTY to trigger enrichment
        }
        
        # We need to hack the ContextManager to use this mock data since we don't have DB access
        ctx = ContextManager(mock_mode=False) 
        # Inject our mock data into the format method for the demo
        mock_crm_data['doctype'] = 'Lead Prospect'
        dossier = ctx._format_dossier(mock_crm_data)
        
        print(dossier)
        
    except Exception as e:
        print(f"❌ Level 2 Failed: {e}")

if __name__ == "__main__":
    prove_intelligence()
