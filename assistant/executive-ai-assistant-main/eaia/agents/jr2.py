"""
Agent JR2: "The Hunter"
Mission: Extract high-value targets (Sponsors, PIs) using the Golden Parser.
"""
import logging
import asyncio
import json
from eaia.agents.state import AgentState
try:
    from eaia.mcp.biomed_mcp.biomed_agents.tools.clinical_tools import get_clinical_trials_client
except (ImportError, ModuleNotFoundError) as _biomed_err:
    import logging as _log
    _log.getLogger(__name__).warning(f"biomed_mcp not available (langgraph compat): {_biomed_err}")
    def get_clinical_trials_client(): return None
from eaia.services.structure_parsing.study_parser import parse_ctgov_study
from eaia.skills.apollo_enrichment import enrich_person
from eaia.skills.air_support import scout_target

logger = logging.getLogger(__name__)

async def jr2_hunter_agent(state: AgentState) -> AgentState:
    """
    JR2 Node Logic:
    1. Iterate trial seeds.
    2. Deep fetch full study JSON.
    3. Parse into Entities and Leads using parse_ctgov_study.
    """
    try:
        seeds = state.get("trial_seeds", [])
        logger.info(f"🏹 JR2 Hunting through {len(seeds)} trials...")
        
        ct = get_clinical_trials_client()
        
        # State Accumulators
        new_entities = {}
        new_leads = []
        
        for seed in seeds:
            nct_id = seed.get("nct_id")
            if not nct_id: continue
            
            # 1. Fetch Full Study Data (API v2)
            # We use direct HTTP because study_parser expects the v2 JSON structure
            try:
                import httpx
                api_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(api_url, timeout=10.0)
                    if resp.status_code != 200:
                        logger.warning(f"Failed to fetch {nct_id}: {resp.status_code}")
                        continue
                    raw_study = resp.json()
            except Exception as e:
                logger.warning(f"Exception fetching {nct_id}: {e}")
                continue
            
            # 2. Parse (The Golden Parser)
            # This returns {gtm, relationship, biomarkers, locations}
            parsed_data = parse_ctgov_study(raw_study)
            
            # 3. Map to Revenue Schema
            # Extract Entities (Sponsor)
            gtm_data = parsed_data.get("gtm_data", {})
            sponsor_name = gtm_data.get("sponsor_name")
            if sponsor_name:
                entity_id = f"ORG_{hash(sponsor_name)}"
                new_entities[entity_id] = {
                    "id": entity_id,
                    "name": sponsor_name,
                    "type": "SPONSOR",
                    "domain": None,
                    "metadata": {"source_nct": nct_id}
                }
            
            # Extract Leads (PIs / Contacts)
            relationships = parsed_data.get("relationships", {})
            principal_investigators = relationships.get("principal_investigators", [])
            
            for pi in principal_investigators:
                pi_name = pi.get("name")
                if not pi_name: continue
                
                # Enrichment (Apollo)
                email = pi.get("email", "")
                linkedin = None
                
                # If no email, try to find it (Limit to first 5 for speed in this demo)
                if not email and len(new_leads) < 5:
                    logger.info(f"🔎 Enriching PI: {pi_name} at {pi.get('affiliation')}")
                    # Clean Name (Remove MD, PhD, etc for better matching)
                    clean_name = pi_name.split(",")[0].strip()
                    org = pi.get("affiliation", "")
                    
                    # 1. Apollo Search
                    profile = await enrich_person(clean_name, org)
                    
                    if profile and profile.get("email"):
                        email = profile.get("email")
                        linkedin = profile.get("linkedin_url")
                        logger.info(f"✨ Apollo Found Email: {email}")
                    else:
                        # Fallback: Air Support (Web Scout)
                        # Only invoke if Apollo failed to get the contact
                        scout_result = await scout_target(clean_name, org)
                        if scout_result:
                            email = scout_result.get("email")
                            logger.info(f"✈️ Air Support Found Email: {email}")

                lead_id = f"LEAD_{hash(pi_name + nct_id)}"
                new_leads.append({
                    "id": lead_id,
                    "name": pi_name,
                    "email": email, 
                    "role": "PI",
                    "organization_id": pi.get("affiliation", ""), 
                    "source_trial": nct_id,
                    "linkedin_url": linkedin,
                    "publications": []
                })
            
            # Extract Central Contacts (Project Managers)
            contacts = parsed_data.get("locations", [])
            for loc in contacts:
                 contact = loc.get("contact", {})
                 if contact.get("email"):
                     c_name = contact.get("name", "Unknown Coordinator")
                     lead_id = f"LEAD_{hash(contact.get('email'))}"
                     new_leads.append({
                        "id": lead_id,
                        "name": c_name,
                        "email": contact.get("email"),
                        "role": "COORDINATOR",
                        "organization_id": loc.get("facility", ""),
                        "source_trial": nct_id,
                        "linkedin_url": None,
                        "publications": []
                     })

        logger.info(f"✅ JR2 Extracted {len(new_entities)} entities and {len(new_leads)} leads.")
        
        return {
            "entities": new_entities,
            "leads": new_leads,
            "mission_status": "ENRICHMENT_COMPLETE",
            "messages": [{"role": "assistant", "content": f"JR2: Extracted {len(new_leads)} leads from {len(seeds)} trials."}]
        }

    except Exception as e:
        logger.error(f"❌ JR2 Failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "mission_status": "FAILED"
        }
