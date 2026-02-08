import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    """
    Setup Custom Fields on CRM Lead to support Hybrid Ingestion of LeadGen data.
    Adds: lead_score, tier, cancer_type, source_ref_id.
    """
    print("Setting up LeadGen Custom Fields on CRM Lead...")

    custom_fields = {
        "CRM Lead": [
            {
                "fieldname": "leadgen_section",
                "fieldtype": "Section Break",
                "label": "LeadGen Intelligence",
                "insert_after": "details" 
            },
            {
                "fieldname": "lead_score",
                "fieldtype": "Float",
                "label": "Lead Score",
                "precision": "2",
                "read_only": 1,
                "in_list_view": 1,
                "insert_after": "leadgen_section"
            },
            {
                "fieldname": "tier",
                "fieldtype": "Select",
                "label": "Tier",
                "options": "\nTier 1\nTier 2\nTier 3\nUnassigned",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "lead_score"
            },
            {
                "fieldname": "cancer_type",
                "fieldtype": "Data",
                "label": "Focus Area / Cancer Type",
                "insert_after": "tier",
                "hidden": 1
            },
            {
                "fieldname": "investment_focus",
                "fieldtype": "Data",
                "label": "Investment Focus",
                "insert_after": "tier",
                "description": "e.g. B2B SaaS, Biotech, Real Estate"
            },
            {
                "fieldname": "aum",
                "fieldtype": "Data",
                "label": "AUM (Assets Under Management)",
                "insert_after": "investment_focus"
            },
            {
                "fieldname": "key_partners",
                "fieldtype": "Small Text",
                "label": "Key Partners / Decision Makers",
                "insert_after": "aum"
            },
            {
                "fieldname": "source_ref_id",
                "fieldtype": "Data",
                "label": "Source Reference ID",
                "read_only": 1,
                "hidden": 0,
                "insert_after": "key_partners",
                "description": "Unique ID from external source"
            }
        ]
    }

    create_custom_fields(custom_fields)
    
    # Ensure Property Setters for List View if needed
    frappe.clear_cache(doctype="CRM Lead")
    print("✅ Custom Fields Created successfully.")

    setup_mapping_profile()

def setup_mapping_profile():
    """
    Create the 'LeadGen Standard' Column Map for ETL.
    Maps Standard CSV Scheme to CRM Lead Fields.
    """
    profile_name = "LeadGen Standard"
    print(f"Setting up Mapping Profile: {profile_name}...")
    
    # Schema Definition
    # Source Header -> (Target DocType, Target Field)
    mapping = [
        {"source": "first_name", "dt": "CRM Lead", "df": "first_name"},
        {"source": "last_name", "dt": "CRM Lead", "df": "last_name"},
        {"source": "email", "dt": "CRM Lead", "df": "email"},
        {"source": "mobile_no", "dt": "CRM Lead", "df": "mobile_no"},
        {"source": "job_title", "dt": "CRM Lead", "df": "job_title"},
        {"source": "organization_name", "dt": "CRM Organization", "df": "organization_name"},
        {"source": "website", "dt": "CRM Organization", "df": "website"},
        {"source": "lead_source", "dt": "CRM Lead", "df": "source"},
        # MAP Custom Fields
        {"source": "lead_score", "dt": "CRM Lead", "df": "lead_score"},
        {"source": "tier", "dt": "CRM Lead", "df": "tier"},
        {"source": "cancer_type", "dt": "CRM Lead", "df": "cancer_type"},
        {"source": "source_ref_id", "dt": "CRM Lead", "df": "source_ref_id"},
    ]

    columns = []
    for m in mapping:
        columns.append({
            "source_header": m["source"],
            "target_doctype": m["dt"],
            "target_field": m["df"]
        })

    # Upsert Mapping Doc
    if frappe.db.exists("CRM Import Column Map", profile_name):
        doc = frappe.get_doc("CRM Import Column Map", profile_name)
        doc.columns = [] # Reset
        for c in columns:
            doc.append("columns", c)
        doc.save()
        print("Updated existing mapping.")
    else:
        doc = frappe.get_doc({
            "doctype": "CRM Import Column Map",
            "title": profile_name,
            "columns": columns
        })
        doc.insert()
        print("Created new mapping.")
