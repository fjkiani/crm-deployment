"""
Utils and Helper Functions for Personalized Outreach
Transplanted from Oncology Backend
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_pi_information(trial_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract Principal Investigator information from trial data.
    
    Priority: Overall PI > Study Director > Study Chair
    
    Args:
        trial_data: ClinicalTrials.gov API response or parsed trial data
        
    Returns:
        Dict with PI name, email, institution, phone, or None if not found
    """
    try:
        protocol_section = trial_data.get('protocolSection', {})
        contacts_locations = protocol_section.get('contactsLocationsModule', {})
        
        # Try overall PI first
        # API v2 uses 'overallOfficials' (plural), but also check 'overallOfficial' (singular) for compatibility
        overall_officials = contacts_locations.get('overallOfficials', [])
        if not overall_officials:
            overall_officials = contacts_locations.get('overallOfficial', [])

        def _extract_field(official: Dict[str, Any], field: str) -> str:
            """Extract field handling both flat (API v2) and nested structures."""
            value = official.get(field, '')
            if isinstance(value, dict):
                return value.get('value', '')
            return value if isinstance(value, str) else ''

        def _extract_contact_info(official: Dict[str, Any]) -> tuple[str, str]:
            """Extract email and phone from contact object or direct fields."""
            contact = official.get('contact', {})
            if isinstance(contact, dict):
                email = contact.get('email', '') or official.get('email', '')
                phone = contact.get('phone', '') or official.get('phone', '')
            else:
                email = official.get('email', '')
                phone = official.get('phone', '')
            return (email if isinstance(email, str) else '', phone if isinstance(phone, str) else '')

        # Try overall PI first
        for official in overall_officials:
            role = _extract_field(official, 'role')
            if role == 'PRINCIPAL_INVESTIGATOR':
                email, phone = _extract_contact_info(official)
                return {
                    'name': _extract_field(official, 'name'),
                    'email': email,
                    'institution': _extract_field(official, 'affiliation'),
                    'phone': phone,
                    'role': role
                }

        # Try Study Director
        for official in overall_officials:
            role = _extract_field(official, 'role')
            if role == 'STUDY_DIRECTOR':
                email, phone = _extract_contact_info(official)
                return {
                    'name': _extract_field(official, 'name'),
                    'email': email,
                    'institution': _extract_field(official, 'affiliation'),
                    'phone': phone,
                    'role': role
                }

        # Try Study Chair
        for official in overall_officials:
            role = _extract_field(official, 'role')
            if role == 'STUDY_CHAIR':
                email, phone = _extract_contact_info(official)
                return {
                    'name': _extract_field(official, 'name'),
                    'email': email,
                    'institution': _extract_field(official, 'affiliation'),
                    'phone': phone,
                    'role': role
                }

        # Fallback: First overall official
        if overall_officials:
            official = overall_officials[0]
            email, phone = _extract_contact_info(official)
            return {
                'name': _extract_field(official, 'name'),
                'email': email,
                'institution': _extract_field(official, 'affiliation'),
                'phone': phone,
                'role': _extract_field(official, 'role')
            }
        
    except Exception as e:
        logger.warning(f"Failed to extract PI information: {e}")
    
    return None
