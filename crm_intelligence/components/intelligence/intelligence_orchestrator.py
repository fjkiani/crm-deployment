"""
Intelligence Orchestrator Component
Coordinates the smaller intelligence components to provide the main functionality
Single responsibility: Component orchestration and workflow management
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .intelligence_gatherer import IntelligenceGatherer
from .data_processor import DataProcessor
from .profile_builder import ProfileBuilder
from .lead_selector import LeadSelector

class IntelligenceOrchestrator:
    """Orchestrates the intelligence gathering workflow using smaller components"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("IntelligenceOrchestrator")

        # Initialize components
        self.gatherer = IntelligenceGatherer(config)
        self.processor = DataProcessor(config)
        self.builder = ProfileBuilder(config)
        self.selector = LeadSelector(config)

        self.logger.info("Intelligence Orchestrator initialized")

    def process_company(self, company_name: str, lead_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a single company through the intelligence pipeline"""

        self.logger.info(f"Processing company: {company_name}")

        # Gather raw intelligence data
        raw_data = self._gather_all_intelligence(company_name)

        # Process and extract structured data
        processed_data = self._process_intelligence_data(raw_data)

        # Build comprehensive profile
        profile = self.builder.build_comprehensive_profile(company_name, processed_data)

        # Add original lead data if provided
        if lead_data:
            profile["original_lead_data"] = lead_data

        self.logger.info(f"Completed processing for {company_name}")
        return profile

    def process_multiple_companies(self, company_names: List[str],
                                 lead_data: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Process multiple companies"""

        profiles = []
        lead_dict = {}

        # Create lookup dictionary for lead data
        if lead_data:
            for lead in lead_data:
                company_name = lead.get('company', '').strip()
                if company_name:
                    lead_dict[company_name] = lead

        # Process each company
        for company_name in company_names:
            try:
                company_lead_data = lead_dict.get(company_name)
                profile = self.process_company(company_name, company_lead_data)
                profiles.append(profile)

                self.logger.info(f"Processed {len(profiles)}/{len(company_names)} companies")

            except Exception as e:
                self.logger.error(f"Failed to process {company_name}: {e}")
                # Continue with other companies

        return profiles

    def select_and_process_leads(self, leads_file: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Select high-value leads and process them"""

        # Load leads data
        leads_data = self.selector.load_leads_from_file(leads_file)
        if not leads_data:
            self.logger.error("No leads data loaded")
            return []

        # Select high-value leads
        selected_leads = self.selector.select_high_value_leads(leads_data, limit)

        # Extract company names and lead data
        company_names = []
        lead_data = []

        for lead in selected_leads:
            company_name = lead.get('company', '').strip()
            if company_name:
                company_names.append(company_name)
                lead_data.append(lead)

        # Process selected companies
        profiles = self.process_multiple_companies(company_names, lead_data)

        return profiles

    def _gather_all_intelligence(self, company_name: str) -> Dict[str, Any]:
        """Gather all types of intelligence for a company"""

        intelligence_data = {
            "company_name": company_name,
            "data_sources": set()
        }

        # Gather different types of intelligence
        intelligence_data["overview"] = self.gatherer.gather_company_overview(company_name)
        intelligence_data["executives"] = self.gatherer.gather_executive_info(company_name)
        intelligence_data["investments"] = self.gatherer.gather_investment_info(company_name)
        intelligence_data["news"] = self.gatherer.gather_news_info(company_name)
        intelligence_data["partnerships"] = self.gatherer.gather_partnership_info(company_name)

        # Collect data sources
        for data_list in intelligence_data.values():
            if isinstance(data_list, list):
                for item in data_list:
                    if isinstance(item, dict) and "url" in item:
                        intelligence_data["data_sources"].add(item["url"])

        return intelligence_data

    def _process_intelligence_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw intelligence data into structured format"""

        processed_data = {
            "company_name": raw_data["company_name"],
            "data_sources": raw_data["data_sources"]
        }

        # Process each type of intelligence
        if "executives" in raw_data:
            processed_data["executives"] = self.processor.extract_executive_info(raw_data["executives"])

        if "investments" in raw_data:
            processed_data["investments"] = self.processor.extract_investment_info(raw_data["investments"])

        if "news" in raw_data:
            processed_data["news"] = self.processor.extract_news_info(raw_data["news"])

        if "partnerships" in raw_data:
            processed_data["partnerships"] = self.processor.extract_partnership_info(raw_data["partnerships"])

        return processed_data

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about the intelligence processing"""

        return {
            "orchestrator_status": "active",
            "components": {
                "gatherer": "active",
                "processor": "active",
                "builder": "active",
                "selector": "active"
            },
            "timestamp": datetime.now().isoformat()
        }
