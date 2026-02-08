"""
Test Script for The Full Army (Graph Execution)
Scout -> Hunter -> Qualifier -> Sheriff -> Sequencer -> Zo
"""
import sys
import os
import logging
from pprint import pprint

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from eaia.agents.graph import army

import asyncio

async def test_full_army_rotation():
    print("⚔️ Testing Full Army Rotation...")
    
    initial_state = {
        "target_condition": "Ovarian Cancer",
        "errors": [],
        "messages": [],
        "trial_seeds": [],
        "leads": [],
        "lead_scorecards": {},
        "safe_lead_ids": []
    }
    
    try:
        # Run the graph
        # invoke returns the final state
        final_state = await army.ainvoke(initial_state)
        
        print("\n✅ MISSION COMPLETE")
        print(f"Status: {final_state.get('mission_status')}")
        
        # Check Campaign
        campaign = final_state.get("campaign")
        if campaign:
            print("\n📊 Campaign Generated:")
            pprint(campaign)
        else:
            print("⚠️ No campaign generated.")
            
        # Check Compliance
        safe_leads = final_state.get("safe_lead_ids", [])
        print(f"\n🔒 Safe Leads: {len(safe_leads)}")
            
    except Exception as e:
        print(f"❌ Army Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_army_rotation())
