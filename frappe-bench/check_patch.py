import frappe
import sys

def check():
    print("🔍 Checking Patch Status...")
    
    # 1. Check DocType
    exists = frappe.db.exists("DocType", "CRM Import Job")
    if exists:
        print("✅ DocType 'CRM Import Job' found in database.")
    else:
        print("❌ DocType 'CRM Import Job' MISSING in database.")
        
    # 2. Check Module Import
    try:
        import crm.api.etl
        print("✅ Module 'crm.api.etl' imported successfully.")
    except ImportError as e:
        print(f"❌ Module 'crm.api.etl' failed to import: {e}")
    except Exception as e:
        print(f"❌ Module 'crm.api.etl' error: {e}")

    # 3. Check Method
    try:
        method = frappe.get_attr("crm.api.etl.autogenerate_mapping")
        print("✅ Method 'autogenerate_mapping' found.")
    except Exception as e:
        print(f"❌ Method 'autogenerate_mapping' missing: {e}")

if __name__ == "__main__":
    frappe.init(site="crm.localhost")
    frappe.connect()
    check()
