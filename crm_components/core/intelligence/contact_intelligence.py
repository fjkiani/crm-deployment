"""
Contact Intelligence Component
Gathers contact information and executive details
"""

from core.component_base import IntelligenceComponent
from typing import Dict, List, Any

class ContactIntelligenceComponent(IntelligenceComponent):
    """Gather contact intelligence - 45 lines"""

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gather contact intelligence"""
        company = input_data.get('company', '')
        self.logger.info(f"Gathering contacts for: {company}")

        # Gather contact information
        contacts = self._gather_contacts(company)
        executives = self._identify_executives(contacts)

        result = {
            "contacts": contacts,
            "executives": executives,
            "total_contacts": len(contacts),
            "executive_contacts": len(executives)
        }

        self._execution_count = getattr(self, '_execution_count', 0) + 1
        return result

    def _gather_contacts(self, company: str) -> List[Dict[str, Any]]:
        """Gather contact information (mock)"""
        mock_contacts = [
            {
                "name": "John CEO",
                "title": "CEO",
                "email": f"john@{company.lower().replace(' ', '')}.com",
                "confidence": 0.8,
                "source": "company_website"
            },
            {
                "name": "Jane President",
                "title": "President",
                "email": f"jane@{company.lower().replace(' ', '')}.com",
                "confidence": 0.7,
                "source": "linkedin"
            }
        ]
        return mock_contacts

    def _identify_executives(self, contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify executive contacts"""
        executive_titles = ['CEO', 'Chief', 'President', 'Director', 'VP', 'Managing']

        executives = []
        for contact in contacts:
            title = contact.get('title', '')
            if any(exec_title in title for exec_title in executive_titles):
                executives.append(contact)

        return executives
