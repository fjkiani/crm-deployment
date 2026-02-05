import frappe
import frappe_mcp
import json
from frappe_mcp import MCP

# Initialize MCP Server for CRM
mcp = MCP("crm-agent")

@mcp.tool()
def update_lead_context(lead_name: str, context: str):
    """
    Updates the Flexible Context (additional_data) of a Lead.
    
    Args:
        lead_name: The ID of the lead (e.g. CRM-LEAD-2024-001)
        context: A JSON string containing key-value pairs to upsert.
                 Example: '{"AUM": "$10B", "Focus": "Biotech"}'
    """
    try:
        new_data = json.loads(context)
    except json.JSONDecodeError:
        return "Error: Context must be valid JSON string."

    lead = frappe.get_doc("CRM Lead", lead_name)
    
    # Merge with existing data
    current_data = json.loads(lead.additional_data) if lead.additional_data else {}
    current_data.update(new_data)
    
    lead.additional_data = json.dumps(current_data)
    lead.save(ignore_permissions=True)
    frappe.db.commit()
    
    return f"Updated context for {lead_name}. Keys: {list(new_data.keys())}"

@mcp.tool()
def get_leads_batch(limit: int = 5):
    """Fetches a batch of generic leads for processing."""
    return frappe.get_all("CRM Lead", fields=["name", "lead_name", "organization"], limit=limit)

@mcp.tool()
def cleanup_leads(confirm: bool = False):
    """
    Deletes ALL leads in the system. Use with CAUTION.
    Args:
        confirm: Must be set to True to execute.
    """
    if not confirm:
        return "Operation cancelled. please set confirm=True."
    
    leads = frappe.get_all("CRM Lead", pluck="name")
    count = len(leads)
    for name in leads:
        frappe.delete_doc("CRM Lead", name, force=1, ignore_permissions=True)
    
    frappe.db.commit()
    return f"Deleted {count} leads."

@mcp.tool()
def echo(message: str):
    """Echoes back the message. Useful for testing connectivity."""
    return f"CRM Agent received: {message}"

# Expose the Endpoint
@mcp.register()
def handle_mcp():
    """
    MCP Entry Point.
    URL: /api/method/crm.api.mcp_server.handle_mcp
    """
    pass
