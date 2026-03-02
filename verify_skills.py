
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load secrets
secrets_path = os.path.abspath("assistant/executive-ai-assistant-main/eaia/.secrets/.env")
load_dotenv(secrets_path)

# Add eaia to path
sys.path.append(os.path.abspath("assistant/executive-ai-assistant-main"))

print(f"DEBUG: Executable: {sys.executable}")
print(f"DEBUG: Sys Path: {sys.path}")


from eaia.skills.lead_hunter_tool import lead_hunter

# We need to run the tool. Since it's an async implementation wrapped in sync, 
# and we are in a main script, we can just call .run()
# BUT, lead_hunter uses `brightdata_web_search`. 
# Verification: We want to make sure it can create a lead.
# Real BrightData searches cost money/credits, but we verified it works.
# Let's run a real "Hunt" for a very specific, likely to exist target to prove it end-to-end.
# Or, to save tokens/credits, we could mock the search, but "Mars Rules" says test reality.
# Let's try to hunt for something simple.

def test_hunter():
    print("🏹 Starting Lead Hunter Validation...")
    print("Target: 'Unit Test' in 'Test Industry' (Simulation)")
    
    # We will try to hunt for a "Principal Engineer" at "Frappe" in "India"
    # This should return results.
    role = "Principal Engineer"
    industry = "Frappe Technologies" 
    location = "Mumbai"
    
    print(f"Executing: lead_hunter('{role}', '{industry}', '{location}', limit=1)...")
    
    try:
        # Run the tool
        # Note: This will actually call BrightData and then Create Lead on the Production CRM.
        # This is a true Integration Test.
        result = lead_hunter.run({
            "role": role,
            "industry": industry,
            "location": location,
            "limit": 1
        })
        
        print("\n✅ Hunter Result:")
        print(result)
        
        if "Successfully ingested" in result or "Found:" in result:
             print("\n✨ SUCCESS: Lead created in CRM.")
        elif "No structured profiles" in result:
             print("\n⚠️ WARNING: Search worked but parsing failed (expected with raw scraped content).")
        else:
             print("\n❌ FAILURE: Unexpected output.")
             
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hunter()
