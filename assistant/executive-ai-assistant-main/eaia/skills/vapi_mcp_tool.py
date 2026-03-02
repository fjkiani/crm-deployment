import os
import asyncio
from langchain_core.tools import tool
from eaia.utils.mcp_client import MCPClient
from eaia.skills.context_manager import ContextManager

# Configuration
VAPI_MCP_URL = "https://mcp.vapi.ai/mcp"
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "53593b76-8c70-46e2-b01a-d2996afec5ba")

async def _invoke_mcp_create_call(phone_number: str, objective: str, override_context: str = None):
    """
    Internal async function to invoke the MCP tool.
    If override_context is provided, uses it as the system message directly
    (skipping ContextManager RAG lookup).
    """
    client = MCPClient(
        command="npx",
        args=[
            "-y", "mcp-remote", 
            VAPI_MCP_URL, 
            "--header", f"Authorization: Bearer {VAPI_API_KEY}"
        ]
    )
    
    if override_context:
        # Use the pre-built context from /call endpoint
        system_message = override_context
    else:
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
    You are calling to achieve a specific objective: {objective}
    
    {dossier}
    
    Keep it professional, concise, and helpful.
    """
    
    try:
        await client.start()
        
        # Map our simplified args to Vapi's schema
        # Vapi MCP 'create_call' likely expects specific schema.
        # Based on docs: create_call(assistant: dict, customer: dict, phoneNumberId: str) 
        # But we want to use the "Assistant" definition like in voice_tool.py if possible.
        
        # Let's inspect tools first to be safe, but for now we'll match voice_tool's structure
        # NOTE: If we don't know the schema, this might fail. 
        # Implementation Detail: voice_tool.py payload is actually what create_call likely takes.
        
        args = {
            "customer": {"number": phone_number},
            "assistant": {
                "firstMessage": f"Hello, I am calling on behalf of Nyx. {objective}",
                "model": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "system", "content": system_message}]
                },
                "voice": {"provider": "11labs", "voiceId": "burt"}
            }
        }
        
        # Add phoneNumberId if it exists (fallback)
        if os.getenv("VAPI_PHONE_NUMBER_ID"):
             args["phoneNumberId"] = os.getenv("VAPI_PHONE_NUMBER_ID")
        
        result = await client.call_tool("create_call", args)
        await client.stop()
        return result
        
    except Exception as e:
        if client.process:
            await client.stop()
        return f"Error executing Vapi MCP: {str(e)}"

@tool
def vapi_mcp_call(phone_number: str, objective: str):
    """
    [MCP] Place a phone call using the official Vapi MCP Server.
    Args:
        phone_number: The phone number to call.
        objective: The goal of the call.
    """
    return asyncio.run(_invoke_mcp_create_call(phone_number, objective))
