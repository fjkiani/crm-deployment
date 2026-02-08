"""
GTM Parser - Extract fields needed for GTM automation
Transplanted and Adapted from Oncology Backend (Agent 1 Seeding)

Extracts:
- Sponsor name, PI name/email, coordinator email
- Primary endpoint
- Mechanism tags (PARPi, anti-angiogenic, etc.)
- Biomarker requirements (formatted for GTM)
"""
from typing import Dict, List, Any, Optional
import logging
import json

# Internal import from sibling module after we port it
# from .biomarker_extractor import extract_biomarkers 

logger = logging.getLogger(__name__)

def parse_gtm_fields(study: Dict[str, Any], relationship_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract GTM-specific fields from ClinicalTrials.gov API v2 study.
    """
    protocol = study.get("protocolSection", {})
    
    # === Sponsor Name ===
    sponsor_name = relationship_data.get("lead_sponsor")
    
    # === Principal Investigator ===
    principal_investigator_name = None
    pi_contact_email = None
    
    pis = relationship_data.get("principal_investigators", [])
    if pis and len(pis) > 0:
        primary_pi = pis[0]  # First PI is usually the lead
        principal_investigator_name = primary_pi.get("name")
        pi_contact_email = primary_pi.get("email") or None
    
    # === Study Coordinator Email ===
    contacts_mod = protocol.get("contactsLocationsModule", {})
    central_contacts = contacts_mod.get("centralContact", [])
    
    study_coordinator_email = None
    if central_contacts and len(central_contacts) > 0:
        primary_contact = central_contacts[0]
        contact_info = primary_contact.get("contact", primary_contact)
        if isinstance(contact_info, dict):
            study_coordinator_email = contact_info.get("email") or None
    
    # === Primary Endpoint ===
    outcomes_mod = protocol.get("outcomesModule", {})
    primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
    
    primary_endpoint = None
    if primary_outcomes and len(primary_outcomes) > 0:
        primary_outcome = primary_outcomes[0]
        measure = primary_outcome.get("measure", "")
        if measure:
            primary_endpoint = measure
    
    # === Site Count ===
    locations_data = relationship_data.get("sites", [])
    site_count = len(locations_data) if locations_data else 0
    
    # === Estimated Enrollment ===
    design_mod = protocol.get("designModule", {})
    enrollment_info = design_mod.get("enrollmentInfo", {})
    
    estimated_enrollment = None
    if enrollment_info:
        estimated_enrollment = (
            enrollment_info.get("count") or
            enrollment_info.get("value") or
            enrollment_info.get("estimatedEnrollment")
        )
    
    return {
        "sponsor_name": sponsor_name,
        "principal_investigator_name": principal_investigator_name,
        "pi_contact_email": pi_contact_email,
        "study_coordinator_email": study_coordinator_email,
        "primary_endpoint": primary_endpoint,
        "site_count": site_count,
        "estimated_enrollment": estimated_enrollment
    }


def tag_mechanisms(interventions: List[str], eligibility_text: str = "") -> List[str]:
    """
    Auto-tag trials with mechanism types based on interventions and eligibility.
    """
    if not interventions:
        return []
    
    interventions_text = " ".join(interventions).upper()
    eligibility_upper = eligibility_text.upper() if eligibility_text else ""
    combined_text = f"{interventions_text} {eligibility_upper}"
    
    mechanism_tags = []
    
    # PARPi keywords
    parpi_keywords = ["olaparib", "niraparib", "rucaparib", "talazoparib", "veliparib", "PARP", "PARPI"]
    if any(keyword.upper() in combined_text for keyword in parpi_keywords):
        mechanism_tags.append("PARPi")
    
    # Anti-angiogenic keywords
    anti_angio_keywords = ["bevacizumab", "aflibercept", "ramucirumab", "pazopanib", "sunitinib", "sorafenib"]
    if any(keyword.upper() in combined_text for keyword in anti_angio_keywords):
        mechanism_tags.append("anti-angiogenic")
    
    # Immunotherapy keywords
    immuno_keywords = ["pembrolizumab", "nivolumab", "atezolizumab", "durvalumab", "ipilimumab", "avelumab", "cemiplimab"]
    if any(keyword.upper() in combined_text for keyword in immuno_keywords):
        mechanism_tags.append("immunotherapy")
    
    # Chemotherapy keywords
    chemo_keywords = ["carboplatin", "paclitaxel", "cisplatin", "doxorubicin", "gemcitabine", "topotecan"]
    if not mechanism_tags and any(keyword.upper() in combined_text for keyword in chemo_keywords):
        mechanism_tags.append("chemotherapy")
    
    # Targeted therapy keywords
    targeted_keywords = ["trastuzumab", "pertuzumab", "cetuximab", "panitumumab", "erlotinib", "gefitinib"]
    if any(keyword.upper() in combined_text for keyword in targeted_keywords):
        mechanism_tags.append("targeted")
    
    return mechanism_tags

# Will be imported after biomarker_extractor is ported
# def extract_biomarker_requirements(eligibility_text: str) -> Optional[List[str]]:
#     biomarkers = extract_biomarkers(eligibility_text)
#     return biomarkers if biomarkers else None
