import os
import sys

def check_deployment():
    # Define the expected path relative to the bench apps directory
    base_path = os.path.join(os.getcwd(), "apps", "crm", "crm", "fcrm", "doctype", "lead_prospect")
    
    print(f"Checking deployment at: {base_path}")
    
    if not os.path.exists(base_path):
        print(f"❌ CRITICAL: Directory not found: {base_path}")
        return

    files = os.listdir(base_path)
    required = ["__init__.py", "lead_prospect.py", "lead_prospect.js", "lead_prospect.json"]
    
    print(f"Found files: {files}")
    
    for f in required:
        if f in files:
            print(f"✅ Found {f}")
        else:
            print(f"❌ MISSING {f}")

    # Try simple import
    try:
        import crm.fcrm.doctype.lead_prospect.lead_prospect
        print("✅ Module Import Successful")
    except ImportError as e:
        print(f"❌ Module Import Failed: {e}")

if __name__ == "__main__":
    check_deployment()
