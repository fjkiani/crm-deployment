import os
import requests
from dotenv import load_dotenv

# Load secret path
secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eaia", ".secrets", ".env")
load_dotenv(secret_path)

API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")
SITE = "https://jedilabs2.v.frappe.cloud"

def test_auth():
    print(f"Testing Auth to: {SITE}")
    if not API_KEY or not API_SECRET:
        print("❌ Keys missing.")
        return

    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }
    
    # 1. Test Standard Endpoint (get_logged_user)
    try:
        url = f"{SITE}/api/method/frappe.auth.get_logged_user"
        print(f"1. Hitting {url}...")
        r = requests.get(url, headers=headers)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   ✅ Auth Success! User: {r.json()}")
        else:
            print(f"   ❌ Auth Failed: {r.text[:200]}")
            return
    except Exception as e:
        print(f"   ❌ Network Error: {e}")
        return

    # 2. Test MCP Endpoint
    try:
        url = f"{SITE}/api/method/crm.api.mcp_server.handle_mcp"
        print(f"2. Hitting MCP {url}...")
        payload = {"jsonrpc": "2.0", "method": "echo", "params": {"message": "ping"}, "id": 1}
        r = requests.post(url, headers=headers, json=payload)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text}") # Print full response
    except Exception as e:
        print(f"   ❌ MCP Network Error: {e}")

if __name__ == "__main__":
    test_auth()
