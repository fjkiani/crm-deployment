"""
Test Script for BioMed-MCP Verification
"""
import sys
import os
import json

# Add current dir to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from biomed_agents.tools.clinical_tools import get_clinical_trials_client

def test_clinical_client():
    print("🧪 Starting BioMed-MCP Client Test...")
    try:
        ct = get_clinical_trials_client()
        fields = ["NCT Number", "Study Title", "Conditions"]
        print("🌍 Fetching trials for 'Ovarian Cancer'...")
        results = ct.get_study_fields(
            search_expr="Ovarian Cancer",
            fields=fields,
            max_studies=5
        )
        
        # Results is list of lists, first is header
        if len(results) > 1:
            print(f"✅ Success! Found {len(results)-1} trials.")
            print(f"   Header: {results[0]}")
            print(f"   First Row: {results[1]}")
            
            # Save to file
            output_path = os.path.join(current_dir, "biomed_test_output.json")
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"💾 Saved to {output_path}")
        else:
            print("⚠️ No trials found (check internet connection?).")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_clinical_client()
