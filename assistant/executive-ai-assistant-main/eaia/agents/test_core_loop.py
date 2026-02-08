"""
Test Script for Phase 2: The Core Loop
Simulates the flow: JR1 (Seed) -> JR2 (Enrich) -> JR3 (Qualify)
"""
import sys
import os
import asyncio
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# eaia/agents -> ../.. -> root
root_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(root_dir)

from eaia.agents.jr1 import jr1_scout_agent
from eaia.agents.jr2 import jr2_hunter_agent
from eaia.agents.jr3 import jr3_qualifier_agent

async def test_core_loop():
    print("🔄 Testing Core Loop (Phase 2)...")
    
    # 1. Initialize State
    state = {
        "target_condition": "Ovarian Cancer",
        "errors": [],
        "messages": []
    }
    
    # 2. Run JR1 (Seed)
    print("\n--- Step 1: JR1 (Scout) ---")
    state_jr1 = jr1_scout_agent(state)
    state.update(state_jr1)
    
    seeds = state.get("trial_seeds", [])
    if not seeds:
        print("❌ JR1 failed to find seeds.")
        sys.exit(1)
    print(f"✅ State updated with {len(seeds)} seeds.")
    
    # 3. Run JR2 (Enrich)
    print("\n--- Step 2: JR2 (Hunter) ---")
    state_jr2 = await jr2_hunter_agent(state)
    state.update(state_jr2)
    
    leads = state.get("leads", [])
    if not leads:
        print("⚠️ JR2 produced no leads (This might be normal if trials have no contacts, or if detailed fetch failed).")
        # Proceeding anyway to test JR3's handling of empty list
    else:
        print(f"✅ State updated with {len(leads)} leads.")
        print(f"   Sample: {leads[0]}")
        
    # 4. Run JR3 (Qualify)
    print("\n--- Step 3: JR3 (Qualifier) ---")
    state_jr3 = jr3_qualifier_agent(state)
    state.update(state_jr3)
    
    scorecards = state.get("lead_scorecards", {})
    print(f"✅ State updated with {len(scorecards)} scorecards.")
    
    if scorecards:
        # Save output
        output_path = os.path.join(os.path.dirname(__file__), "core_loop_output.json")
        with open(output_path, "w") as f:
            json.dump(scorecards, f, indent=2)
        print(f"💾 Scorecards saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(test_core_loop())
