"""
Outreach Pipeline
Orchestrates outreach components
"""

from typing import Dict, List, Any
from core.component_base import OutreachComponent
from components.outreach.email_generator import EmailGeneratorComponent

class OutreachPipeline:
    """Outreach pipeline - 35 lines"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.components = self._initialize_components()

    def _initialize_components(self) -> List[OutreachComponent]:
        """Initialize pipeline components"""
        return [
            EmailGeneratorComponent(self.config.get('email_generator', {}))
        ]

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute outreach pipeline"""
        targets = input_data.get('targets', [])
        campaign_config = input_data.get('campaign_config', {})

        results = []
        for target in targets:
            target_result = self._process_target(target, campaign_config)
            results.append(target_result)

        return {
            "campaign_id": campaign_config.get('id', 'unknown'),
            "total_targets": len(targets),
            "results": results
        }

    def _process_target(self, target: Dict[str, Any], campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual target"""
        # Get contacts for target (would come from intelligence)
        contacts = self._get_contacts_for_target(target)

        emails = []
        for contact in contacts:
            email_input = {
                "recipient": contact,
                "intelligence": target,
                "campaign_config": campaign_config
            }

            for component in self.components:
                try:
                    email_result = component.execute(email_input)
                    emails.append(email_result)
                except Exception as e:
                    emails.append({"error": str(e), "recipient": contact})

        return {
            "target": target,
            "emails_generated": len(emails),
            "emails": emails
        }

    def _get_contacts_for_target(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get contacts for target (mock implementation)"""
        # In real implementation, this would come from intelligence data
        return [
            {
                "name": "John CEO",
                "title": "CEO",
                "email": f"john@{target.get('company', '').lower().replace(' ', '')}.com"
            }
        ]
