"""
Vulture Agent — Phase 9 Zeta Protocol
=====================================
Monitors news for competitor failures and company-level disasters.
When a negative signal is detected (e.g. clinical trial failure, layoffs),
it automatically drafts re-engagement emails for leads at that company.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict

from eaia.mcp_client import FrappeMCPClient
from eaia.tools.competitive_tools import monitor_competitor_news
from eaia.pipeline.llm import llm_json

logger = logging.getLogger(__name__)

async def run_vulture_scan() -> dict:
    """Cron-callable: scan for negative news on companies in the CRM.
    
    1. Gets recent active leads.
    2. Extracts unique organizations.
    3. Scans each organization for negative news.
    4. If found, drafts 'Vulture' re-engagement emails.
    """
    client = FrappeMCPClient()
    
    # 1. Fetch leads
    # In a real system we'd paginate or use a dedicated 'Competitor' table.
    # Here, we sample active leads to find organizations to monitor.
    result = await client.search_leads(query="", status="Draft Ready", limit=50)
    leads = result.get("leads", result.get("result", []))
    
    if not leads:
        return {"scanned": 0, "actions": [], "message": "No Active/Draft Ready leads to monitor"}
        
    organizations = set()
    org_to_leads = {}
    
    for lead in leads:
        org = lead.get("organization")
        contact_name = lead.get("lead_name")
        if not org or not contact_name:
            continue
            
        organizations.add(org)
        if org not in org_to_leads:
            org_to_leads[org] = []
        org_to_leads[org].append(lead)
        
    logger.info(f"🦅 Vulture Protocol: Monitoring {len(organizations)} organizations.")
    
    actions_taken = []
    
    for org in organizations:
        logger.info(f"Secondary scan for negative events: {org}")
        news_result = await monitor_competitor_news.ainvoke({"competitor_name": org})
        
        # If no news found or error, it returns a string like "No recent negative events..."
        if "No recent negative events" in news_result or "error" in news_result.lower():
            continue
            
        # Negative news found!
        logger.warning(f"🚨 Vulture Event Detected for {org}:\n{news_result[:200]}...")
        
        # Action: Draft Vulture emails for all leads at this org
        for lead in org_to_leads[org]:
            lead_name = lead["name"]
            prospect_name = lead["lead_name"]
            
            # Draft email using LLM
            prompt = f"""Draft a highly targeted, empathetic but firm 'Vulture' re-engagement email.
            
PROSPECT: {prospect_name}
COMPANY: {org}
NEGATIVE NEWS EVENT:
{news_result}

GOAL: Offer our CRM/Revenue orchestration services as the solution for stability, efficiency, and pipeline generation during their current crisis/reorganization. 
TONE: Empathetic, not overly eager, professional, highlighting automation. Limit to 5 sentences.

Return EXACTLY a JSON object with a single key 'email_body'.
"""
            result = llm_json(prompt)
            email_body = result.get("email_body", "Error generating draft.")
            subject = f"Navigating recent changes at {org}"
            
            # Save the draft to the CRM using the update_context or by creating a note
            await client.create_note(
                lead_name=lead_name,
                title=f"🦅 VULTURE PROTOCOL TRIGGERED: {org}",
                content=f"**Event Detected:**\n{news_result}\n\n**Drafted Response:**\nSubject: {subject}\n\n{email_body}"
            )
            
            # Also update lead status context context
            await client.update_lead_context(lead_name, {
                "vulture_event_detected": True,
                "vulture_event_date": datetime.now().isoformat(),
                "vulture_draft_subject": subject,
                "vulture_draft_body": email_body,
            })
            
            actions_taken.append({
                "lead_name": lead_name,
                "organization": org,
                "action": "vulture_draft_created"
            })

    return {
        "organizations_scanned": len(organizations),
        "vulture_events_detected": len(actions_taken),
        "actions": actions_taken,
        "timestamp": datetime.now().isoformat()
    }
