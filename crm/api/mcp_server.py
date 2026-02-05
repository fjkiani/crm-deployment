import frappe
import frappe_mcp
from frappe_mcp import MCP

# Initialize MCP Server for CRM
mcp = MCP("crm-agent")

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
