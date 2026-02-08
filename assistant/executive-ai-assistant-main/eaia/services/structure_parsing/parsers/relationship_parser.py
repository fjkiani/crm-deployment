"""
Relationship Parser - Extract PI, Organization, Site data from ClinicalTrials.gov API v2
Component 1: Data Relationship Extraction
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def parse_relationship_data(study: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract graph-ready relationship data from ClinicalTrials.gov API v2.
    """
    protocol = study.get("protocolSection", {})
    
    # === Sponsor/Collaborator Hierarchy ===
    sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
    
    # Lead sponsor
    lead_sponsor_obj = sponsor_mod.get("leadSponsor", {})
    lead_sponsor = None
    if lead_sponsor_obj:
        lead_sponsor_name = lead_sponsor_obj.get("name", {})
        if isinstance(lead_sponsor_name, dict):
            lead_sponsor = lead_sponsor_name.get("value")
        elif isinstance(lead_sponsor_name, str):
            lead_sponsor = lead_sponsor_name
    
    # Collaborators
    collaborators = []
    collaborator_list = sponsor_mod.get("collaborators", [])
    for collab in collaborator_list:
        collab_name = collab.get("name", {})
        if isinstance(collab_name, dict):
            name_value = collab_name.get("value")
        elif isinstance(collab_name, str):
            name_value = collab_name
        else:
            name_value = None
        
        if name_value:
            collaborators.append(name_value)
    
    # === Principal Investigators ===
    contacts_mod = protocol.get("contactsLocationsModule", {})
    overall_officials = contacts_mod.get("overallOfficials", [])  # Try plural first
    if not overall_officials:
        overall_officials = contacts_mod.get("overallOfficial", [])  # Fallback
    
    principal_investigators = []
    for official in overall_officials:
        role_obj = official.get("role", "")
        role = role_obj.get("value", "") if isinstance(role_obj, dict) else (role_obj if isinstance(role_obj, str) else "")
        
        if role == "PRINCIPAL_INVESTIGATOR" or "PRINCIPAL" in role.upper():
            name_obj = official.get("name", {})
            name_value = name_obj.get("value", "") if isinstance(name_obj, dict) else (name_obj if isinstance(name_obj, str) else "")
            
            affil_obj = official.get("affiliation", {})
            affil_value = affil_obj.get("value", "") if isinstance(affil_obj, dict) else (affil_obj if isinstance(affil_obj, str) else "")
            
            contact = official.get("contact", {})
            email = contact.get("email", "") if isinstance(contact, dict) else ""
            phone = contact.get("phone", "") if isinstance(contact, dict) else ""
            
            if name_value:
                principal_investigators.append({
                    "name": name_value,
                    "affiliation": affil_value,
                    "email": email,
                    "phone": phone,
                    "role": role
                })
    
    # === Sites with PI Assignments ===
    locations = contacts_mod.get("locations", [])
    sites = []
    
    for loc in locations:
        facility = loc.get("facility", "")
        if not facility:
            continue
        
        city = loc.get("city", "")
        state = loc.get("state", "")
        country = loc.get("country", "United States")
        zip_code = loc.get("zip", "")
        status = loc.get("status", "")
        
        site_contacts = loc.get("contacts", [])
        site_pis = []
        for contact in site_contacts:
            contact_name = contact.get("name", {})
            pi_name = contact_name.get("value", "") if isinstance(contact_name, dict) else (contact_name if isinstance(contact_name, str) else "")
            if pi_name:
                site_pis.append(pi_name)
        
        sites.append({
            "facility": facility,
            "city": city,
            "state": state,
            "country": country,
            "zip": zip_code,
            "status": status,
            "site_pis": site_pis
        })
    
    return {
        "lead_sponsor": lead_sponsor,
        "collaborators": collaborators,
        "principal_investigators": principal_investigators,
        "sites": sites
    }
