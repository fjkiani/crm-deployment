#!/usr/bin/env python3
"""
Test script for AI-powered email capabilities in CRM.
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Configuration
SITE_URL = os.getenv("SITE_URL", "https://jedilabs2.v.frappe.cloud")
API_KEY = os.getenv("API_KEY", "f36656740d0f4b5")
API_SECRET = os.getenv("API_SECRET", "d12cf89c0ea878f")

def make_api_call(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make API call to CRM."""
    url = f"{SITE_URL}/api/method/{method}"
    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    
    data = {"params": params} if params else {}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}")
        return {"error": str(e)}

def test_ai_triage():
    """Test AI email triage functionality."""
    print("🧪 Testing AI Email Triage...")
    
    # First, create a test communication
    test_comm = make_api_call("crm.api.agent.run", {
        "command": "email.draft",
        "params": {
            "reference_doctype": "CRM Lead",
            "reference_name": "CRM-LEAD-2025-00001",
            "to": "test@example.com",
            "subject": "Meeting Request",
            "html": "<p>Hi, I would like to schedule a meeting to discuss our proposal. When are you available?</p>"
        }
    })
    
    if "error" in test_comm:
        print(f"❌ Failed to create test communication: {test_comm['error']}")
        return False
    
    comm_name = test_comm.get("message")
    print(f"✅ Created test communication: {comm_name}")
    
    # Test AI triage
    triage_result = make_api_call("crm.api.agent.run", {
        "command": "email.triage",
        "params": {"communication_name": comm_name}
    })
    
    if "error" in triage_result:
        print(f"❌ AI triage failed: {triage_result['error']}")
        return False
    
    result = triage_result.get("message", {})
    print(f"✅ AI Triage Result:")
    print(f"   Action: {result.get('action', 'N/A')}")
    print(f"   Reason: {result.get('reason', 'N/A')}")
    print(f"   Priority: {result.get('priority', 'N/A')}")
    print(f"   Suggested: {result.get('suggested_response', 'N/A')}")
    
    return True

def test_ai_drafting():
    """Test AI response drafting functionality."""
    print("\n🧪 Testing AI Response Drafting...")
    
    # Create a test communication to respond to
    test_comm = make_api_call("crm.api.agent.run", {
        "command": "email.draft",
        "params": {
            "reference_doctype": "CRM Lead",
            "reference_name": "CRM-LEAD-2025-00001",
            "to": "client@example.com",
            "subject": "Product Inquiry",
            "html": "<p>Hello, I'm interested in your CRM solution. Can you tell me more about the pricing and features?</p>"
        }
    })
    
    if "error" in test_comm:
        print(f"❌ Failed to create test communication: {test_comm['error']}")
        return False
    
    comm_name = test_comm.get("message")
    print(f"✅ Created test communication: {comm_name}")
    
    # Test AI drafting
    draft_result = make_api_call("crm.api.agent.run", {
        "command": "email.draft_ai",
        "params": {
            "communication_name": comm_name,
            "tone": "professional",
            "include_context": True
        }
    })
    
    if "error" in draft_result:
        print(f"❌ AI drafting failed: {draft_result['error']}")
        return False
    
    result = draft_result.get("message", {})
    print(f"✅ AI Draft Result:")
    print(f"   Subject: {result.get('subject', 'N/A')}")
    print(f"   Summary: {result.get('summary', 'N/A')}")
    print(f"   Content: {result.get('content', 'N/A')[:200]}...")
    
    return True

def test_human_inbox_page():
    """Test Human Inbox page accessibility."""
    print("\n🧪 Testing Human Inbox Page...")
    
    try:
        response = requests.get(f"{SITE_URL}/human_inbox", timeout=10)
        if response.status_code == 200:
            print("✅ Human Inbox page is accessible")
            return True
        else:
            print(f"❌ Human Inbox page returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to access Human Inbox page: {e}")
        return False

def test_email_sending():
    """Test email sending functionality."""
    print("\n🧪 Testing Email Sending...")
    
    # Create a draft
    draft_result = make_api_call("crm.api.agent.run", {
        "command": "email.draft",
        "params": {
            "reference_doctype": "CRM Lead",
            "reference_name": "CRM-LEAD-2025-00001",
            "to": "fjkiani1@gmail.com",
            "subject": "AI Test Email",
            "html": "<p>This is a test email sent via AI-powered CRM.</p>"
        }
    })
    
    if "error" in draft_result:
        print(f"❌ Failed to create draft: {draft_result['error']}")
        return False
    
    comm_name = draft_result.get("message")
    print(f"✅ Created draft: {comm_name}")
    
    # Send the email
    send_result = make_api_call("crm.api.agent.run", {
        "command": "email.send",
        "params": {"communication_name": comm_name}
    })
    
    if "error" in send_result:
        print(f"❌ Failed to send email: {send_result['error']}")
        return False
    
    result = send_result.get("message", {})
    if result.get("ok"):
        print("✅ Email sent successfully!")
        return True
    else:
        print(f"❌ Email sending failed: {result}")
        return False

def main():
    """Run all AI capability tests."""
    print("🚀 Testing AI-Powered Email Capabilities")
    print("=" * 50)
    
    tests = [
        ("AI Email Triage", test_ai_triage),
        ("AI Response Drafting", test_ai_drafting),
        ("Human Inbox Page", test_human_inbox_page),
        ("Email Sending", test_email_sending),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! AI capabilities are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
