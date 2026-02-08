#!/usr/bin/env python3
"""Test CRM connection with production credentials"""

import os
os.environ['CRM_BASE_URL'] = 'https://jedilabs2.v.frappe.cloud'
os.environ['CRM_USER'] = 'Fahad@jedilabs.org'
os.environ['CRM_PASSWORD'] = 'Kiani11209!'

from crm.client import CrmClient
from crm.tools import list_docs

try:
    print("🔐 Testing CRM login...")
    client = CrmClient()
    client.login()
    print(f"✅ Login successful! CSRF: {client.csrf[:20]}...")
    
    print("\n📊 Testing list_docs (CRM Call Log)...")
    result = list_docs('CRM Call Log', limit=5)
    print(f"✅ Found {result.get('total', 0)} call logs")
    
    if result.get('data'):
        print(f"   Recent calls: {len(result['data'])}")
    
    print("\n🎉 CRM connection working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

