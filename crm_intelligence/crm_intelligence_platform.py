"""
CRM Intelligence Platform - Main Entry Point
Scalable architecture based on our 3EDGE success
"""

from typing import Dict, List, Any, Optional
import logging
import json
from pathlib import Path
from .core.intelligence import IntelligenceEngine
from .core.outreach import OutreachEngine

class CRMIntelligencePlatform:
    """
    Main CRM Intelligence Platform
    Based on our successful 3EDGE implementation
    Scales to handle any number of companies
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger("CRMIntelligencePlatform")

        # Initialize core engines
        self.intelligence_engine = IntelligenceEngine(self.config)
        self.outreach_engine = OutreachEngine(self.config)

        self.logger.info("CRM Intelligence Platform initialized")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load platform configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        # Default configuration
        return {
            "platform": {
                "name": "CRM Intelligence Platform",
                "version": "1.0.0"
            },
            "intelligence": {
                "max_companies_per_batch": 10,
                "cache_enabled": True
            },
            "outreach": {
                "max_emails_per_company": 5,
                "personalization_threshold": 0.7
            },
            "api": {
                "tavily_api_key": os.getenv('TAVILY_API_KEY')
            }
        }

    def process_companies(self, company_names: List[str]) -> Dict[str, Any]:
        """
        Process multiple companies - the scalable version of our 3EDGE work
        """
        self.logger.info(f"Processing {len(company_names)} companies")

        results = {
            "companies_processed": len(company_names),
            "intelligence_gathered": [],
            "outreach_generated": [],
            "processing_stats": {
                "start_time": datetime.now(),
                "successful_companies": 0,
                "failed_companies": 0
            }
        }

        for company_name in company_names:
            try:
                # Step 1: Gather intelligence (our 3EDGE methodology)
                intelligence = self.intelligence_engine.gather_company_intelligence(company_name)

                # Step 2: Generate personalized outreach (our 3EDGE emails)
                outreach_campaign = self._generate_company_outreach(intelligence)

                results["intelligence_gathered"].append({
                    "company": company_name,
                    "intelligence": intelligence
                })

                results["outreach_generated"].append({
                    "company": company_name,
                    "campaign": outreach_campaign
                })

                results["processing_stats"]["successful_companies"] += 1

            except Exception as e:
                self.logger.error(f"Failed to process {company_name}: {e}")
                results["processing_stats"]["failed_companies"] += 1

        results["processing_stats"]["end_time"] = datetime.now()
        return results

    def _generate_company_outreach(self, intelligence) -> Dict[str, Any]:
        """Generate outreach campaign for company - based on our 3EDGE success"""
        campaign = {
            "company": intelligence.company_name,
            "emails": [],
            "total_contacts": len(intelligence.contacts)
        }

        # Generate personalized email for each key contact
        for contact in intelligence.contacts:
            email = self.outreach_engine.generate_personalized_outreach(intelligence, contact)
            campaign["emails"].append(email)

        return campaign

    def get_platform_status(self) -> Dict[str, Any]:
        """Get platform status and metrics"""
        return {
            "status": "operational",
            "version": self.config["platform"]["version"],
            "engines": {
                "intelligence": "active",
                "outreach": "active"
            },
            "configuration": {
                "loaded": bool(self.config),
                "companies_per_batch": self.config["intelligence"]["max_companies_per_batch"]
            }
        }

# Convenience functions for quick usage
def quick_intelligence(company_names: List[str]) -> Dict[str, Any]:
    """Quick intelligence gathering - like our 3EDGE demo"""
    platform = CRMIntelligencePlatform()
    return platform.process_companies(company_names)

def quick_outreach(company_names: List[str]) -> Dict[str, Any]:
    """Quick outreach generation - like our 3EDGE emails"""
    return quick_intelligence(company_names)  # Includes both intelligence and outreach
