
import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from eaia.frappe_tool import list_leads, update_context
from eaia.brightdata_tool import brightdata_web_search

@tool
def deep_audit_leads(limit: int = 5) -> str:
    """
    Performs a 'Reality Check' on CRM leads.
    1. Fetches recent leads.
    2. Searches specifically for their current professional status using BrightData.
    3. Flags leads that have moved companies or have outdated titles.
    4. Updates the CRM context with the audit findings.
    
    Args:
        limit: Number of leads to audit in this batch (default 5 to avoid rate limits).
        
    Returns:
        A summary report of the audit findings.
    """
    return asyncio.run(_async_deep_audit(limit))

async def _async_deep_audit(limit: int) -> str:
    # 1. Fetch Leads (We'll abstract this to get raw data if possible, or parse the str output)
    # The existing list_leads tool returns a string representation. 
    # For a robust skill, we might want a direct data fetch helper, but we'll parse for now 
    # or rely on the agent to pass specific names.
    # To keep it "Agentic", let's assume this tool is autonomous and fetches its own work queue.
    
    # Ideally, list_leads would return structured data. 
    # For now, let's just fetch a batch and try to parse or use a direct Frappe call if we had the client exposed.
    # Since we are inside the 'eaia' package, we can look at how 'frappe_tool' works.
    
    # Let's blindly try to audit the top 'limit' leads returned by list_leads.
    leads_summary = list_leads(limit) 
    
    # Quick parsing heuristic: "ID: <id> | Name: <name> | Title: <title>"
    # If list_leads returns a string, we need to be careful. 
    # Let's assume for this MVP we just "report" what we would do or try to regex it.
    
    audit_log = []
    
    # Mocking the parsing for the "Mars Rules" speed - in reality we'd upgrade list_leads to return objects
    # But let's try to extract ID and Name from the string output of list_leads
    lines = leads_summary.split('\n')
    processed_count = 0
    
    for line in lines:
        if "ID:" not in line or processed_count >= limit:
            continue
            
        try:
            # Parse typical detailed view or list view
            # This is brittle without structured return, but fits "Mars Rules" MVP
            parts = line.split('|')
            lead_id = next((p.split(':')[1].strip() for p in parts if "ID:" in p), None)
            name = next((p.split(':')[1].strip() for p in parts if "Name:" in p), "Unknown")
            company = next((p.split(':')[1].strip() for p in parts if "Company:" in p), "Unknown")
            
            if not lead_id: 
                continue

            processed_count += 1
            audit_log.append(f"🔍 Auditing {name} ({company})...")
            
            # 2. Reality Check via BrightData
            query = f"current job title {name} {company} linkedin"
            search_result = brightdata_web_search.run(query) # Synchronous call to the tool
            
            # 3. Analyze (Simple Heuristic)
            flagged = False
            notes = f"Audit Run: Verified via BrightData. "
            
            if "former" in search_result.lower() or "past" in search_result.lower():
                flagged = True
                notes += "WARNING: Search results suggest they may have left this role. "
            
            # 4. Update CRM
            update_payload = {
                "audit_status": "Flagged" if flagged else "Verified",
                "audit_source": "BrightData (LinkedIn)",
                "audit_notes": search_result[:200] + "..." # Store snippet
            }
            
            # logic to call update_context
            update_result = update_context(lead_id, json.dumps(update_payload))
            audit_log.append(f"   -> Result: {'🚩 FLAGGED' if flagged else '✅ VERIFIED'}")
            
        except Exception as e:
            audit_log.append(f"   -> Error processing line: {line[:50]}... ({str(e)})")

    return "\n".join(audit_log)

