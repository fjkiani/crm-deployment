#!/usr/bin/env python3
"""
Simple test script for Voice MVP functionality
"""

import os
import sys
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_crm_tools():
    """Test CRM tools import and basic functionality"""
    try:
        from crm.tools import initiate_voice_call, get_call_status, get_voice_dashboard_data
        print("✅ CRM tools imported successfully")
        
        # Test voice dashboard data (should work even without CRM connection)
        result = get_voice_dashboard_data()
        print(f"✅ Voice dashboard test: {result['success']}")
        
        return True
    except Exception as e:
        print(f"❌ CRM tools test failed: {e}")
        return False

def test_voice_endpoints():
    """Test voice endpoints if server is running"""
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Server health check: {response.status_code}")
        
        # Test voice dashboard endpoint
        response = requests.get("http://localhost:8000/voice/dashboard-data", timeout=15)
        print(f"✅ Voice dashboard endpoint: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Voice endpoints test failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    required_vars = ['VAPI_API_KEY', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False
    else:
        print("✅ Required environment variables present")
        return True

def main():
    """Main test function"""
    print("🚀 Voice MVP Testing")
    print("=" * 40)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    tests = [
        ("Environment", test_environment),
        ("CRM Tools", test_crm_tools),
        ("Voice Endpoints", test_voice_endpoints),
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n📋 Testing {name}...")
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results[name] = False
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    overall = all(results.values())
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if overall else '❌ SOME TESTS FAILED'}")
    
    if not overall:
        print("\n💡 Next Steps:")
        if not results.get("Environment"):
            print("  - Check your .env file has correct credentials")
        if not results.get("CRM Tools"):
            print("  - Verify CRM tools are properly configured")
        if not results.get("Voice Endpoints"):
            print("  - Start the Farfalle backend server first")

if __name__ == "__main__":
    main()
