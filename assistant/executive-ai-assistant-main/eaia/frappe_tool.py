import os
import requests
from typing import Optional
from langchain_core.tools import tool

FRAPPE_SITE = os.getenv("FRAPPE_SITE_URL", "https://jedilabs2.v.frappe.cloud")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")

def _call_mcp(method: str, params: dict = None):
    url = f"{FRAPPE_SITE}/api/method/crm.api.mcp_server.handle_mcp"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    # MCP Protocol requires method="tools/call" for tool execution
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": method,
            "arguments": params or {}
        },
        "id": 1
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    
    if "error" in result:
        raise Exception(f"MCP Error: {result['error']}")
        
    return result.get("result")

@tool
def delete_all_leads(confirm: bool = False):
    """
    Deletes ALL leads in the CRM. 
    Use this ONLY when explicitly asked to 'nuke', 'delete', or 'clear' all leads.
    Requires confirm=True.
    """
    return _call_mcp("cleanup_leads", {"confirm": confirm})

@tool
def update_context(lead_name: str, context_json: str):
    """
    Updates the Flexible Context (JSON) of a Lead. 
    Use this to save enriched data like AUM, Focus, Partners.
    context_json must be a valid JSON string.
    """
    return _call_mcp("update_lead_context", {"lead_name": lead_name, "context": context_json})

@tool
def list_leads(limit: int = 5):
    """Fetches a batch of leads to process."""
    return _call_mcp("get_leads_batch", {"limit": limit})

@tool
def crm_echo(message: str):
    """Checks connection to CRM Agent."""
    return _call_mcp("echo", {"message": message})

@tool
def create_new_lead(first_name: str, last_name: str, organization: str, title: Optional[str] = None, email: Optional[str] = None, source: str = "Assistant"):
    """
    Creates a new Lead in the CRM.
    """
    params = {
        "first_name": first_name,
        "last_name": last_name,
        "organization": organization,
        "title": title,
        "email": email,
        "source": source
    }
    return _call_mcp("create_lead", params)
