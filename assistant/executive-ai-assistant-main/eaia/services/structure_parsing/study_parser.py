"""
Main study parser - orchestrates sub-parsers and returns complete schema dict
Transplanted from Oncology Backend
"""
import json
import logging
from typing import Dict, Any

from .parsers.biomarker_extractor import extract_biomarkers
from .parsers.locations_parser import parse_locations_data
from .parsers.gtm_parser import parse_gtm_fields, tag_mechanisms
from .parsers.relationship_parser import parse_relationship_data

logger = logging.getLogger(__name__)

def extract_biomarker_requirements(eligibility_text: str):
    b = extract_biomarkers(eligibility_text)
    return b if b else None

def parse_ctgov_study(study: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse ClinicalTrials.gov API v2 study object.
    
    Orchestrates:
    - ID extraction
    - Status/phase/description parsing
    - Inclusion/exclusion criteria parsing
    - Biomarker extraction
    - Locations data extraction
    - Relationship extraction (Sponsors, PIs)
    - GTM field extraction
    """
    protocol = study.get("protocolSection", {})
    
    # IDs
    ids = protocol.get("identificationModule", {})
    nct_id = ids.get("nctId", "")
    brief_title = ids.get("briefTitle", "")
    primary_id = ids.get("orgStudyId", "")
    
    # Status
    status_mod = protocol.get("statusModule", {})
    overall_status = status_mod.get("overallStatus", "Unknown")
    
    # Phase
    design_mod = protocol.get("designModule", {})
    phases = design_mod.get("phases", [])
    phase = ", ".join(phases) if phases else "N/A"
    
    # Description
    desc_mod = protocol.get("descriptionModule", {})
    brief_summary = desc_mod.get("briefSummary", "")
    
    # Eligibility
    elig_mod = protocol.get("eligibilityModule", {})
    eligibility_criteria = elig_mod.get("eligibilityCriteria", "")
    
    # Parse inclusion/exclusion
    inclusion_text = ""
    exclusion_text = ""
    if eligibility_criteria:
        parts = eligibility_criteria.split("Exclusion Criteria:")
        if len(parts) == 2:
            inclusion_text = parts[0].replace("Inclusion Criteria:", "").strip()
            exclusion_text = parts[1].strip()
        else:
            inclusion_text = eligibility_criteria
    
    # Interventions (for metadata)
    arms_mod = protocol.get("armsInterventionsModule", {})
    interventions = arms_mod.get("interventions", [])
    intervention_names = [i.get("name", "") for i in interventions]
    
    # Extract biomarkers
    biomarkers = extract_biomarkers(eligibility_criteria)
    
    # Parse locations data
    locations_data = parse_locations_data(study)
    
    # Parse relationship data (PI, org, site) - Component 1
    relationship_data = parse_relationship_data(study)
    
    # Parse GTM fields (sponsor, PI, contacts, endpoints) - Component 2
    gtm_fields = parse_gtm_fields(study, relationship_data)
    
    # Tag mechanisms (PARPi, anti-angiogenic, etc.) - Component 3
    mechanism_tags = tag_mechanisms(intervention_names, eligibility_criteria)
    
    # Extract biomarker requirements (formatted for GTM) - Component 4
    biomarker_requirements_gtm = extract_biomarker_requirements(eligibility_criteria)
    
    # Build metadata JSON
    metadata_json = {
        "locations": locations_data,
        "interventions": intervention_names,
        "biomarkers": biomarkers
    }
    
    # Build return dict
    return {
        "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
        "nct_id": nct_id,
        "primary_id": primary_id,
        "title": brief_title,
        "status": overall_status,
        "phase": phase,
        "description_text": brief_summary,
        "inclusion_criteria_text": inclusion_text,
        "exclusion_criteria_text": exclusion_text,
        "eligibility_text": eligibility_criteria,
        "metadata_json": metadata_json,
        
        # Extended Intelligence
        "biomarker_requirements": biomarkers,
        "locations_data": locations_data,
        
        # COMPONENT 1: Relationship data (for graph)
        "relationships": relationship_data,
        
        # COMPONENT 2: GTM fields (for JR2's 1-pager generation)
        "gtm_data": {
            "sponsor_name": gtm_fields.get("sponsor_name"),
            "principal_investigator_name": gtm_fields.get("principal_investigator_name"),
            "pi_contact_email": gtm_fields.get("pi_contact_email"),
            "study_coordinator_email": gtm_fields.get("study_coordinator_email"),
            "primary_endpoint": gtm_fields.get("primary_endpoint"),
            "site_count": gtm_fields.get("site_count", 0),
            "estimated_enrollment": gtm_fields.get("estimated_enrollment"),
            "mechanism_tags": mechanism_tags,
            "biomarker_requirements_gtm": biomarker_requirements_gtm
        }
    }
