"""
Location data extraction from ClinicalTrials.gov API v2 study
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def parse_locations_data(study: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse location data from ClinicalTrials.gov API v2 study.
    """
    protocol = study.get("protocolSection", {})
    contacts_mod = protocol.get("contactsLocationsModule", {})
    locations = contacts_mod.get("locations", [])
    
    locations_data = []
    
    for loc in locations:
        location_entry: Dict[str, Any] = {
            "facility": loc.get("facility", ""),
            "city": loc.get("city", ""),
            "state": loc.get("state", ""),
            "zip": loc.get("zip", ""),
            "country": loc.get("country", "United States"),
            "status": loc.get("status", ""),
            "contact_name": "",
            "contact_phone": "",
            "contact_email": ""
        }
        
        # Extract contact info if available
        contacts = loc.get("contacts", [])
        if contacts and len(contacts) > 0:
            primary_contact = contacts[0]
            location_entry["contact_name"] = primary_contact.get("name", "")
            location_entry["contact_phone"] = primary_contact.get("phone", "")
            location_entry["contact_email"] = primary_contact.get("email", "")
        
        # Validate critical fields - skip if missing
        if not location_entry.get("facility") or not location_entry.get("state"):
            continue
        
        locations_data.append(location_entry)
    
    return locations_data
