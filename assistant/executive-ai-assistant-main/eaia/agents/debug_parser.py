"""
Debug script for Study Parser
"""
import sys
import os
import asyncio
import json
import httpx

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from eaia.services.structure_parsing.study_parser import parse_ctgov_study

async def debug_parser():
    nct_id = "NCT04053673" # One of the trials found
    print(f"🔍 Debugging Parser for {nct_id}...")
    
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        raw_study = resp.json()
        
    print("✅ Fetched JSON.")
    # print(json.dumps(raw_study, indent=2))
    
    parsed = parse_ctgov_study(raw_study)
    print("\n--- Parsed Result ---")
    print(json.dumps(parsed, indent=2))
    
    print("\n--- GTM Data ---")
    print(json.dumps(parsed.get("gtm_data"), indent=2))
    
    print("\n--- Relationships ---")
    print(json.dumps(parsed.get("relationships"), indent=2))

if __name__ == "__main__":
    asyncio.run(debug_parser())
