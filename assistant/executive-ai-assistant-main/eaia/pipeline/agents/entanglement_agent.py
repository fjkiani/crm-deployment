"""
Entanglement Agent — Phase 9 Zeta Protocol
==========================================
Discovers links between leads at the same firm (portfolio entanglement).
When a new lead is enriched, this agent checks if we already have other leads
at the same company. If so, it groups them and injects this context so the
email drafter can reference coworkers (e.g. "I'm also speaking with Jane...").
"""

import logging
from eaia.mcp_client import FrappeMCPClient

logger = logging.getLogger(__name__)

async def process_entanglement(lead_name: str, organization: str, email: str) -> dict:
    """Run Entanglement Protocol for a specific lead.
    
    1. Uses get_portfolio_links to find coworkers.
    2. Updates the lead's context with coworkers info.
    3. Adds a Note to the CRM timeline.
    
    Args:
        lead_name: CRM Lead ID
        organization: The lead's company name
        email: The lead's email address
    """
    if not organization and not email:
        return {"status": "skipped", "reason": "No organization or email provided"}
        
    client = FrappeMCPClient()
    
    email_domain = email.split("@")[1] if email and "@" in email else None
    
    # Exclude common free email domains from entanglement
    free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
    if email_domain in free_domains:
        email_domain = None
        
    logger.info(f"🕸️ Running Entanglement Protocol for {lead_name} ({organization})")
    
    result = await client.get_portfolio_links(
        organization=organization,
        email_domain=email_domain
    )
    
    if "error" in result:
        logger.error(f"Entanglement Error: {result['error']}")
        return {"status": "error", "error": result["error"]}
        
    leads = result.get("leads", [])
    
    # Filter out the current lead itself
    coworkers = [l for l in leads if l.get("name") != lead_name]
    
    if not coworkers:
        return {"status": "no_links_found"}
        
    # We found coworkers!
    coworker_names = [f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('lead_name', '') for c in coworkers]
    coworker_roles = [f"{name} ({c.get('job_title', 'Unknown Role')})" for name, c in zip(coworker_names, coworkers)]
    
    logger.info(f"🕸️ Entanglement found {len(coworkers)} links for {lead_name}: {', '.join(coworker_names)}")
    
    # Add a note to the CRM
    note_content = "**Zeta Protocol: Entanglement Detected**\n\nThis lead is connected to the following existing leads in our pipeline:\n"
    for role in coworker_roles:
        note_content += f"- {role}\n"
        
    await client.create_note(
        lead_name=lead_name,
        title="🕸️ Entanglement Links Discovered",
        content=note_content
    )
    
    # Inject context for the outreach drafting step
    # The email prompt can use `entanglement_context` to drop coworker names
    entanglement_context = f"Also mention that we are speaking with their colleagues: {', '.join(coworker_names)}."
    
    await client.update_lead_context(lead_name, {
        "entangled": True,
        "entangled_coworkers": coworker_roles,
        "entanglement_context": entanglement_context
    })
    
    return {
        "status": "entangled",
        "coworkers_found": len(coworkers),
        "coworkers": coworker_roles
    }
