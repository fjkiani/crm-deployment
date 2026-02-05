
import frappe
import requests
import json

@frappe.whitelist()
def ask_nyx(message):
    """
    Proxies a chat message to the local EAIA Agent Service.
    Securely handles the communication without exposing the backend port to the frontend.
    """
    # Security: Ensure user is logged in
    if frappe.session.user == "Guest":
        frappe.throw("You must be logged in to access Intelligence.", frappe.PermissionError)

    # Configuration (Could be moved to site_config or settings)
    AGENT_URL = "http://localhost:8000/chat"
    
    # Context: Provide basic user context
    user_context = {
        "user_id": frappe.session.user,
        "full_name": frappe.utils.get_fullname(frappe.session.user)
    }
    
    # Payload
    payload = {
        "message": message,
        "history": [], # TODO: Fetch conversation history from DB if we want persistence
        "user_context": user_context
    }
    
    try:
        # Call the Agent Service
        response = requests.post(AGENT_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", "Error: No response from Agent.")
        
    except requests.exceptions.ConnectionError:
        frappe.log_error("EAIA Service Unreachable")
        return "⚠️ **System Error**: The Intelligence Core (Nyx) is currently offline. Please contact your administrator."
        
    except Exception as e:
        frappe.log_error(f"EAIA Error: {str(e)}")
        return f"⚠️ **Agent Error**: {str(e)}"
