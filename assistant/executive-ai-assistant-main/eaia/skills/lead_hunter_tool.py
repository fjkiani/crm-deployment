
import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from eaia.frappe_tool import create_new_lead
from eaia.brightdata_tool import brightdata_web_search

@tool
def lead_hunter(role: str, industry: str, location: str, limit: int = 5) -> str:
    """
    Hunts for NEW leads matching the criteria using BrightData (LinkedIn).
    1. Constructs a precision search query (e.g. site:linkedin.com/in/ "CIO" "Family Office").
    2. Scrapes the results.
    3. Auto-ingests them into the CRM as new Leads.
    
    Args:
        role: Target Job Title (e.g., "Chief Investment Officer", "CIO").
        industry: Target Industry or Company Type (e.g., "Family Office").
        location: Geographic focus (e.g., "Florida", "New York").
        limit: Number of leads to hunt (default 5).
        
    Returns:
        Summary of leads created.
    """
    return asyncio.run(_async_lead_hunter(role, industry, location, limit))

async def _async_lead_hunter(role: str, industry: str, location: str, limit: int) -> str:
    # 1. Construct Search Query
    # We use a site-specific search to get profiles
    query = f'site:linkedin.com/in/ "{role}" "{industry}" "{location}"'
    
    hunt_log = [f"🏹 Hunting for: {role} in {industry} ({location})"]
    hunt_log.append(f"🔎 Query: {query}")
    
    try:
        # 2. Execute Search via BrightData
        # Note: brightdata_web_search returns a string summary. 
        # In a real impl, we'd want structured JSON. 
        # For now, we assume the tool helps us or we parse the string.
        # Ideally, we should add a 'structured' search to brightdata_tool for this.
        # But let's assume we get a string and try to Regex it or use LLM to parse it (agentic flow).
        
        # ACTUALLY: The agent calls this tool. The agent expects a string back.
        # BUT this tool is supposed to AUTO-INGEST. So this tool acts as a sub-agent.
        # It calls the search, parses, and ingests.
        
        # Since 'brightdata_web_search' currently returns a string of results...
        # We need to be able to extract structured data. 
        # For this MVP, let's use a VERY simple parse or just return the raw data 
        # and let the AGENT parse and call 'create_new_lead' manually?
        # NO, the user asked for "Modular Capability". This tool should do the job.
        
        # Let's perform the search
        raw_results = brightdata_web_search.run(query)
        
        # 3. Parse and Ingest
        ingested_count = 0
        
        try:
            # Try to parse as JSON first
            if isinstance(raw_results, str):
                data = json.loads(raw_results)
            else:
                data = raw_results
                
            items = data.get("organic", []) if isinstance(data, dict) else []
            
            for item in items:
                if ingested_count >= limit:
                    break
                    
                title_text = item.get("title", "")
                snippet = item.get("description", "")
                link = item.get("link", "")
                
                # Heuristic: Name is usually at the start of the title
                # "Faris Ansari - Frappe" -> Name: Faris Ansari, Company: Frappe
                # "Rucha Mahabal - Product Engineer @ Frappe" -> Name: Rucha, Role: Product Engineer
                
                if " - " in title_text:
                    parts = title_text.split(" - ")
                    name_part = parts[0].strip()
                    rest = " - ".join(parts[1:])
                elif " | " in title_text:
                     parts = title_text.split(" | ")
                     name_part = parts[0].strip()
                     rest = " - ".join(parts[1:])
                else:
                    # Fallback
                    name_part = title_text
                    rest = snippet
                
                # Split name
                name_parts = name_part.split(" ")
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Create Lead
                lead_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "organization": f"Target: {industry}", 
                    "title": rest[:40], # extract from title text
                    "email": "",
                    "source": f"BrightData Hunter ({query})"
                }
                
                # Ingest
                result = create_new_lead.run(lead_data)
                
                if "Created Lead" in result or "Error" not in result:
                    hunt_log.append(f"   -> Found & Ingested: {first_name} {last_name}")
                    ingested_count += 1
                else:
                    hunt_log.append(f"   -> Failed to ingest {first_name} {last_name}: {result}")

        except json.JSONDecodeError:
            # Fallback to line-based parsing if JSON fails
            hunt_log.append("⚠️ JSON parsing failed, falling back to text analysis.")
            lines = raw_results.split('\n')
            # ... (existing text logic or just skip) ...
                    
        if ingested_count == 0:
            hunt_log.append("⚠️ No structured profiles found to auto-ingest. Raw results below:")
            hunt_log.append(raw_results[:500])
        else:
            hunt_log.append(f"✅ Successfully ingested {ingested_count} new leads.")
            
    except Exception as e:
        hunt_log.append(f"❌ Error during hunt: {str(e)}")

    return "\n".join(hunt_log)
