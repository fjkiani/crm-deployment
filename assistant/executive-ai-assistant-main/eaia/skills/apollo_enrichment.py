"""
Apollo.io Enrichment Skill
Provides tools to find people and reveal emails using the Apollo API.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

APOLLO_API_URL = "https://api.apollo.io/v1"

def get_api_key() -> str:
    key = os.getenv("APOLLO_API_KEY")
    if not key:
        raise ValueError("APOLLO_API_KEY not found in environment.")
    return key

async def enrich_person(name: str, organization: str) -> Optional[Dict[str, Any]]:
    """
    Search for a person and return their profile with email.
    """
    key = get_api_key()
    url = f"{APOLLO_API_URL}/people/match"
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": key
    }
    
    # Apollo match requires splitting name usually, or smart query
    # /people/match expects specific fields
    payload = {
        "name": name,
        "organization_name": organization,
        "reveal_personal_emails": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"Apollo Raw: {str(data)[:200]}") # Truncate for safety
                person = data.get("person")
                if person:
                    email = person.get("email")
                    if not email and person.get("contact_emails"): 
                        # Fallback to scraped list if primary nil
                        email = person.get("contact_emails")[0]
                        
                    return {
                        "email": email,
                        "linkedin_url": person.get("linkedin_url"),
                        "title": person.get("title"),
                        "apollo_id": person.get("id")
                    }
            elif resp.status_code == 429:
                logger.warning("Apollo API Rate Limit Hit.")
            else:
                logger.warning(f"Apollo API Error {resp.status_code}: {resp.text}")
                
    except Exception as e:
        logger.error(f"Apollo Enrichment Failed for {name}: {e}")
        
    return None
