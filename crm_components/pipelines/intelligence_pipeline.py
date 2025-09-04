"""
Intelligence Gathering Pipeline
Orchestrates intelligence gathering components
"""

from typing import Dict, List, Any
from core.component_base import IntelligenceComponent
from components.intelligence.company_research import CompanyResearchComponent
from components.intelligence.contact_intelligence import ContactIntelligenceComponent

class IntelligencePipeline:
    """Intelligence gathering pipeline - 38 lines"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.components = self._initialize_components()

    def _initialize_components(self) -> List[IntelligenceComponent]:
        """Initialize pipeline components"""
        return [
            CompanyResearchComponent(self.config.get('company_research', {})),
            ContactIntelligenceComponent(self.config.get('contact_intelligence', {}))
        ]

    def execute(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intelligence pipeline"""
        result = {"target": target, "intelligence": {}}

        for component in self.components:
            try:
                component_result = component.execute(target)
                result["intelligence"][component.name] = component_result
            except Exception as e:
                result["intelligence"][component.name] = {"error": str(e)}

        # Aggregate results
        result["aggregated"] = self._aggregate_results(result["intelligence"])

        return result

    def _aggregate_results(self, intelligence: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate intelligence from all components"""
        aggregated = {
            "company_info": {},
            "contacts": [],
            "insights": []
        }

        # Aggregate company information
        if "CompanyResearchComponent" in intelligence:
            company_data = intelligence["CompanyResearchComponent"]
            aggregated["company_info"].update(company_data)

        # Aggregate contacts
        if "ContactIntelligenceComponent" in intelligence:
            contact_data = intelligence["ContactIntelligenceComponent"]
            aggregated["contacts"].extend(contact_data.get("contacts", []))

        return aggregated
