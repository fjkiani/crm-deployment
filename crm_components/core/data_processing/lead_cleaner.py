"""
Lead Cleaner Component
Cleans and normalizes lead data
"""

from core.component_base import ProcessingComponent
from typing import Dict, List, Any
import re

class LeadCleanerComponent(ProcessingComponent):
    """Clean lead data - 42 lines"""

    def execute(self, input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean lead data"""
        cleaned_leads = []

        for lead in input_data:
            cleaned = self._clean_lead(lead)
            if cleaned:
                cleaned_leads.append(cleaned)

        self.logger.info(f"Cleaned {len(cleaned_leads)} out of {len(input_data)} leads")
        self._execution_count = getattr(self, '_execution_count', 0) + 1

        return cleaned_leads

    def _clean_lead(self, lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean individual lead"""
        cleaned = lead.copy()

        # Clean text fields
        text_fields = ['name', 'company', 'title', 'notes']
        for field in text_fields:
            if field in cleaned and cleaned[field]:
                cleaned[field] = self._clean_text(cleaned[field])

        # Standardize company names
        if cleaned.get('company'):
            cleaned['company_clean'] = self._standardize_company(cleaned['company'])

        # Extract contact info
        all_text = ' '.join(str(v) for v in cleaned.values() if v)
        emails = self._extract_emails(all_text)
        phones = self._extract_phones(all_text)

        if emails and not cleaned.get('email'):
            cleaned['email'] = emails[0]
        if phones and not cleaned.get('phone'):
            cleaned['phone'] = phones[0]

        return cleaned

    def _clean_text(self, text: str) -> str:
        """Clean text data"""
        if not isinstance(text, str):
            return str(text)

        # Remove extra whitespace
        cleaned = ' '.join(text.split())

        # Remove excessive special characters
        cleaned = re.sub(r'[^\w\s.,!?-]', '', cleaned)

        return cleaned.strip()

    def _standardize_company(self, company: str) -> str:
        """Standardize company names"""
        suffixes = [' Inc', ' LLC', ' Ltd', ' Corp', ' Corporation']
        for suffix in suffixes:
            if company.endswith(suffix):
                return company[:-len(suffix)].strip()

        return company.strip().title()

    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)

    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers"""
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        return re.findall(phone_pattern, text)
