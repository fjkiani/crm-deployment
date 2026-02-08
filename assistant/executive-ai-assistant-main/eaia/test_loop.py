import sys
import os

# Ensure we can import from local modules
sys.path.append(os.getcwd())

from eaia.skills.clinical_mcp import search_clinical_trials
from eaia.skills.research_tool import ResearchIntelligence

def simulate_loop():
    print("="*60)
    print("🔄 OPERATION IRON SDR: LOOP SIMULATION (LEVEL 4)")
    print("="*60)

    # 1. The Trigger (Mock Scheduler)
    prospect_name = "Isabelle Ray-Coquard"
    cancer_type = "Ovarian Cancer"
    print(f"\n[SCHEDULER] Found due step for Prospect: {prospect_name}")
    print(f"[CONTEXT] Campaign Target: {cancer_type} KELIM Validation")

    # 2. The Brain (Research Intelligence)
    print("\n[BRAIN] Fetching Intelligence to personalize email...")
    research_summary = "No research found."
    
    try:
        pubs = ResearchIntelligence.get_pi_publications(prospect_name, limit=1)
        if pubs:
            paper = pubs[0]
            research_summary = f"recent paper '{paper['title']}' ({paper['date']})"
            print(f"✅ Found Paper: {paper['title']}")
        else:
            print("❌ No papers found.")
    except Exception as e:
        print(f"❌ Intelligence Error: {e}")

    # 3. The Generator (Template Injection)
    print("\n[GENERATOR] Drafting Personalized Email...")
    
    email_body = f"""
    Subject: Question about your research on {cancer_type}
    
    Hi Dr. Ray-Coquard,
    
    I was reading your {research_summary} and found it fascinating, particularly how it relates to platinum resistance in recurrent ovarian cancer.
    
    We are validating the KELIM score as a predictive biomarker and I believe your dataset would be perfect for this.
    
    Could we discuss this next week?
    
    Best,
    The Iron SDR
    """
    
    print("-" * 40)
    print(email_body)
    print("-" * 40)
    
    print("\n✅ Loop Simulation Complete. This logic is now live in 'automation.py'.")

if __name__ == "__main__":
    simulate_loop()
