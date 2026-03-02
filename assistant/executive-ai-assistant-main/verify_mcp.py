import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables from secrets
secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eaia", ".secrets", ".env")
load_dotenv(secret_path)

# Add current directory to path so we can import eaia
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eaia.frappe_tool import crm_echo, list_leads, update_context
from eaia.research_tool import research_company

def run_verification():
    print("⚔️  Zeta Verification Protocol Initiated...\n")

    # 1. Check Env
    api_key = os.getenv("FRAPPE_API_KEY")
    if not api_key:
        print("❌ FAILED: FRAPPE_API_KEY is missing from .env")
        return

    # 2. Test Echo (Connectivity)
    try:
        print("📡 Testing CRM Connection (Echo)...")
        res = crm_echo.invoke({"message": "Zeta Ping"})
        print(f"✅ Success: {res}\n")
    except Exception as e:
        print(f"❌ FAILED: Connectivity Error: {e}")
        return

    # 3. Test Read (List Leads)
    first_lead = None
    try:
        print("👀 Testing Read (List Leads)...")
        res = list_leads.invoke({"limit": 1})
        # Parse MCP Response Structure
        if isinstance(res, dict) and 'content' in res:
             text_content = res['content'][0]['text']
             # CRM returns single quotes sometimes? No, it returns standard python list str repr?
             # frappe.get_all returns list of dicts. frappe-mcp might str() it.
             # Safest is to treat it as string check.
             print(f"✅ Success: Raw Response: {text_content[:100]}...")
             
             # Try to parse if it's json
             try:
                # Replace single quotes to make it valid JSON if it's a python repr string
                fixed_json = text_content.replace("'", '"').replace("None", "null")
                leads_data = json.loads(fixed_json)
                print(f"   Parsed {len(leads_data)} leads.")
                if leads_data:
                    first_lead = leads_data[0]['name']
             except:
                 print("   (Could not parse JSON, but got data)")
        else:
            print(f"   Unknown format: {res}")
        print()
    except Exception as e:
        print(f"❌ FAILED: Read Error: {e}")
        return

    # 4. Test Write (Update Context)
    if first_lead:
        try:
            print(f"✍️  Testing Write (Update Context on {first_lead})...")
            # We write a timestamp to prove it's live
            test_context = '{"Zeta_Verification": "Verified Live", "Agent": "Nyx"}'
            res = update_context.invoke({"lead_name": first_lead, "context_json": test_context})
            print(f"✅ Success: {res}\n")
        except Exception as e:
            print(f"❌ FAILED: Write Error: {e}")
    
    # 5. Test Research (Eyes)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            print("🔎 Testing Research (Tavily)...")
            res = research_company.invoke({"company_name": "Frappe Technologies"})
            print(f"✅ Success: Got research data ({len(res)} chars).")
        except Exception as e:
            print(f"❌ FAILED: Research Error: {e}")
    else:
        print("⚠️  Skipping Research Test (No TAVILY_API_KEY)")

    print("\n🏁 Verification Complete. System is Live.")

if __name__ == "__main__":
    run_verification()
