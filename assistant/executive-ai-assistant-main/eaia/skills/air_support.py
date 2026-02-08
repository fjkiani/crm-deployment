"""
Air Support Skill (Web Scouting)
Deploy specialized search agents to scrape contact info from the wild.
Uses Tavily (if available) or generic web search hooks.
"""
import os
import logging
import json
from typing import Optional, Dict, Any

# Assuming we might swap search engines
# For now, we will simulate "Tavily" like behavior using a placeholder that calls the agent tool if possible,
# But since skills run in python, we need a python client.
# The user wants "Tavily". Let's check environment or fail gracefully.

logger = logging.getLogger(__name__)

async def scout_target(name: str, org: str) -> Optional[Dict[str, Any]]:
    """
    Search the web for contact details (Email, Phone, Lab Website).
    Strategy:
    1. Search "{Name} {Org} email address"
    2. Search "{Name} lab contact"
    3. Look for .edu/.org patterns in snippets.
    """
    logger.info(f"✈️ Air Support Launching for: {name} @ {org}")
    
    # 1. Tavily Check
    tavily_key = os.getenv("TAVILY_API_KEY")
    diffbot_token = os.getenv("DIFFBOT_TOKEN")
    
    found_email = None
    found_url = None
    method = ""

    if tavily_key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            
            # Query Strategies
            queries = [
                f"{name} {org} email contact",
                f"{name} email address {org}",
                f"{name} lab contact info"
            ]
            
            for q in queries:
                if found_email: break
                
                logger.info(f"✈️ Air Support Search: {q}")
                response = client.search(q, search_depth="advanced")
                results = response.get("results", [])
                
                # A. Fast Scan (Snippets)
                import re
                email_pattern = r"[\w.+-]+@[\w-]+\.(?:edu|org|com|net)"
                
                for res in results:
                    content = res.get("content", "").lower()
                    # Naive regex
                    emails = re.findall(email_pattern, content)
                    
                    # Filter for 'university' like emails first
                    valid_emails = [e for e in emails if ".edu" in e or ".org" in e]
                    if not valid_emails:
                         # Fallback to any email if no .edu found
                         valid_emails = emails
                         
                    if valid_emails:
                        found_email = valid_emails[0]
                        found_url = res.get("url")
                        method = "TAVILY_SNIPPET"
                        break
                        
                    # B. Deep Scan (Diffbot) - If we have a Profile URL but no email in snippet
                    # Heuristic: If URL looks like a profile page
                    url = res.get("url", "")
                    if diffbot_token and ("profile" in url or "faculty" in url or "lab" in url):
                        if not found_email: # Don't burn tokens if we found one
                            logger.info(f"🕵️ Deep Scan (Diffbot) on: {url}")
                            try:
                                # Diffbot Article/Page API
                                d_url = f"https://api.diffbot.com/v3/article?token={diffbot_token}&url={url}"
                                import httpx
                                async with httpx.AsyncClient() as http_client:
                                    d_resp = await http_client.get(d_url, timeout=10)
                                    if d_resp.status_code == 200:
                                        d_data = d_resp.json()
                                        d_text = d_data.get("objects", [{}])[0].get("text", "")
                                        d_emails = re.findall(email_pattern, d_text)
                                        if d_emails:
                                            found_email = d_emails[0]
                                            found_url = url
                                            method = "DIFFBOT_DEEP_SCAN"
                                            break
                            except Exception as de:
                                logger.warning(f"Diffbot Scan Failed: {de}")

        except ImportError:
            logger.warning("Tavily installed but import failed.")
        except Exception as e:
            logger.warning(f"Tavily Search Failed: {e}")
            
    else:
        logger.warning("⚠️ No TAVILY_API_KEY found. Air Support grounded.")
        
    if found_email:
        logger.info(f"🎯 Target Acquired: {found_email} via {method}")
        return {
            "email": found_email,
            "source_url": found_url,
            "method": method
        }
        
    return None
