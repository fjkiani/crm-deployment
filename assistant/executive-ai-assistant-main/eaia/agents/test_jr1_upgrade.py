"""
Test Script for Upgraded JR1 (Scout)
Verifies that JR1 uses the BioMed-MCP tools correctly.
"""
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# eaia/agents -> ../.. -> root
root_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(root_dir)

from eaia.agents.jr1 import jr1_scout_agent

def test_jr1():
    print("🕵️‍♂️ Testing Upgraded JR1...")
    
    state = {
        "target_condition": "Ovarian Cancer",
        "errors": []
    }
    
    try:
        result = jr1_scout_agent(state)
        
        if result.get("mission_status") == "SEEDING_COMPLETE":
            found_count = result.get("trials_found_count", 0)
            print(f"✅ JR1 Success! Found {found_count} trials.")
            print(f"   Sample Trial: {result['found_trials'][0]['NCT Number']}")
        else:
            print(f"❌ JR1 Failed: {result}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_jr1()
