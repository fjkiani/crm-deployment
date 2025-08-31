#!/usr/bin/env python3
"""
Script to set up OpenAI API key for AI capabilities.
"""

import os
import sys
import requests
from getpass import getpass

# Configuration
SITE_URL = os.getenv("SITE_URL", "https://jedilabs2.v.frappe.cloud")
API_KEY = os.getenv("API_KEY", "f36656740d0f4b5")
API_SECRET = os.getenv("API_SECRET", "d12cf89c0ea878f")

def set_openai_key(api_key: str):
    """Set OpenAI API key via Frappe API."""
    url = f"{SITE_URL}/api/method/frappe.client.set_value"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    
    data = {
        "doctype": "System Settings",
        "name": "System Settings",
        "fieldname": {
            "openai_api_key": api_key
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("message"):
            print("✅ OpenAI API key set successfully!")
            return True
        else:
            print(f"❌ Failed to set API key: {result}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed: {e}")
        return False

def test_openai_connection():
    """Test if OpenAI API key is working."""
    print("🧪 Testing OpenAI connection...")
    
    url = f"{SITE_URL}/api/method/crm.api.agent.run"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    
    # Create a simple test communication
    test_data = {
        "command": "email.draft",
        "params": {
            "reference_doctype": "CRM Lead",
            "reference_name": "CRM-LEAD-2025-00001",
            "to": "test@example.com",
            "subject": "Test Email",
            "html": "<p>This is a test email for AI triage.</p>"
        }
    }
    
    try:
        # First create a test communication
        response = requests.post(url, headers=headers, json=test_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            print(f"❌ Failed to create test communication: {result['error']}")
            return False
        
        comm_name = result.get("message")
        print(f"✅ Created test communication: {comm_name}")
        
        # Now test AI triage
        triage_data = {
            "command": "email.triage",
            "params": {"communication_name": comm_name}
        }
        
        response = requests.post(url, headers=headers, json=triage_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            print(f"❌ AI triage failed: {result['error']}")
            return False
        
        triage_result = result.get("message", {})
        print(f"✅ AI Triage successful!")
        print(f"   Action: {triage_result.get('action', 'N/A')}")
        print(f"   Reason: {triage_result.get('reason', 'N/A')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 OpenAI API Key Setup for CRM AI Capabilities")
    print("=" * 50)
    
    # Check if API key is already set
    print("🔍 Checking current OpenAI configuration...")
    
    # Get current settings
    url = f"{SITE_URL}/api/method/frappe.client.get_value"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    
    data = {
        "doctype": "System Settings",
        "filters": {"name": "System Settings"},
        "fieldname": ["openai_api_key"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        current_key = result.get("message", {}).get("openai_api_key")
        
        if current_key:
            print(f"✅ OpenAI API key is already configured")
            print(f"   Current key: {current_key[:10]}...{current_key[-4:]}")
            
            # Test the current key
            if test_openai_connection():
                print("🎉 OpenAI is working correctly!")
                return True
            else:
                print("⚠️  Current key may be invalid. Let's update it.")
        else:
            print("❌ No OpenAI API key found.")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to check current settings: {e}")
    
    # Get new API key from user
    print("\n📝 Please provide your OpenAI API key:")
    print("   Get one from: https://platform.openai.com/api-keys")
    print("   (The key will be hidden when you type)")
    
    api_key = getpass("OpenAI API Key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return False
    
    if not api_key.startswith("sk-"):
        print("❌ Invalid API key format. Should start with 'sk-'")
        return False
    
    # Set the API key
    print("\n🔧 Setting OpenAI API key...")
    if set_openai_key(api_key):
        print("\n🧪 Testing the new API key...")
        if test_openai_connection():
            print("🎉 Setup complete! AI capabilities are now ready.")
            return True
        else:
            print("❌ API key test failed. Please check your key.")
            return False
    else:
        print("❌ Failed to set API key.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
