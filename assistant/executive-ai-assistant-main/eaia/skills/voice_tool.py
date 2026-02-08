import os
import requests
import json
from langchain_core.tools import tool

from eaia.skills.context_manager import ContextManager

# API Key discovered from setup_voice_mvp.sh
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "53593b76-8c70-46e2-b01a-d2996afec5ba")
VAPI_URL = "https://api.vapi.ai/call"

def _make_vapi_call(phone_number: str, prompt: str) -> dict:
    """
    Initiates an outbound call using Vapi.ai
    """
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    # RAG: Fetch Intelligence Dossier
    try:
        ctx = ContextManager() 
        dossier = ctx.get_dossier(phone_number=phone_number)
    except Exception as e:
        print(f"RAG Error: {e}")
        dossier = "No dossier available."
    
    # Construct System Message with RAG
    system_message = f"""
    You are Nyx, an AI Executive Assistant. 
    You are calling to achieve a specific objective: {prompt}
    
    {dossier}
    
    Keep it professional, concise, and helpful.
    """
    
    # Basic Vapi Assistant Configuration (Ephemeral Assistant)
    payload = {
        # "userId": "nyx_agent",  <-- Removed: Invalid field for this endpoint
        "phoneNumberId": os.getenv("VAPI_PHONE_NUMBER_ID", "05559ed7-9762-4887-a690-2f8b3a8a7837"), 
        # Actually, if we don't have a phoneNumberId (Twilio trunk connected to Vapi), 
        # we can't make a call unless we use Vapi's provided numbers or just try sending 'phoneNumber'.
        # Vapi usually requires a phoneNumberId or a configured assistant.
        # Let's try creating an ephemeral assistant config.
        
        "customer": {
            "number": phone_number
        },
        "assistant": {
            "firstMessage": f"Hello, I am calling on behalf of Nyx. {prompt}",
            "model": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": system_message
                    }
                ]
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "burt"
            }
        }
    }
    
    # NOTE: "phoneNumberId" is required for outbound calls. 
    # Since I don't have the user's phoneNumberId from Vapi, 
    # I will rely on the user to provide it in .env OR I will omit it and see if Vapi defaults to a system number (unlikely).
    # Update: setup_voice_mvp.sh didn't have PHONE_NUMBER_ID. Use env if available.
    if os.getenv("VAPI_PHONE_NUMBER_ID"):
        payload["phoneNumberId"] = os.getenv("VAPI_PHONE_NUMBER_ID")
    
    try:
        response = requests.post(VAPI_URL, headers=headers, json=payload, timeout=10)
        # response.raise_for_status() # Let's handle errors gracefully
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@tool
def voice_call(phone_number: str, objective: str):
    """
    Place a phone call to a lead to achieve an objective (e.g. Schedule a meeting, Verify interest).
    Args:
        phone_number: The phone number to call (e.g. +14155551234)
        objective: The goal of the call (e.g. "Ask if they are interested in our Series A round")
    """
    
    # Safety Check: Whitelist (optional, but good practice)
    # allow_list = ["+13476842656"] # From setup script
    # if phone_number not in allow_list:
    #    return f"❌ Call Blocked: Number {phone_number} is not whitelisted for testing."

    result = _make_vapi_call(phone_number, objective)
    
    if "id" in result:
        return f"✅ Call Initiated. Call ID: {result['id']}\nObjective: {objective}"
    else:
        return f"❌ Call Failed. Vapi Response: {json.dumps(result)}"
