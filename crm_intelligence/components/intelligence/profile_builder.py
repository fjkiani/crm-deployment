"""
Profile Builder Component
Focused on building structured intelligence profiles from processed data
Single responsibility: Data organization and profile construction
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class ProfileBuilder:
    """Focused component for building structured intelligence profiles"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("ProfileBuilder")

    def build_executive_profile(self, executive_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build executive leadership profile"""
        profile = {
            "key_executives": executive_data,
            "leadership_structure": self._analyze_leadership_structure(executive_data),
            "decision_makers": self._identify_decision_makers(executive_data),
            "confidence_score": min(len(executive_data) * 0.15, 1.0)
        }

        self.logger.info(f"Built executive profile with {len(executive_data)} executives")
        return profile

    def build_investment_profile(self, investment_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build investment portfolio profile"""
        profile = {
            "portfolio_companies": investment_data,
            "investment_focus": self._analyze_investment_focus(investment_data),
            "sector_specialization": self._extract_sectors(investment_data),
            "geographic_focus": self._extract_geographies(investment_data),
            "recent_investments": self._filter_recent_investments(investment_data),
            "confidence_score": min(len(investment_data) * 0.1, 1.0)
        }

        self.logger.info(f"Built investment profile with {len(investment_data)} investments")
        return profile

    def build_news_profile(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build news and developments profile"""
        profile = {
            "recent_news": [n for n in news_data if n.get("type") == "general_news"],
            "press_releases": [n for n in news_data if n.get("type") == "press_release"],
            "industry_coverage": [n for n in news_data if n.get("type") == "industry_analysis"],
            "executive_mentions": [n for n in news_data if n.get("type") == "executive_quote"],
            "company_milestones": [n for n in news_data if n.get("type") == "milestone"],
            "confidence_score": min(len(news_data) * 0.07, 1.0)
        }

        self.logger.info(f"Built news profile with {len(news_data)} items")
        return profile

    def build_partnership_profile(self, partnership_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build partnership and network profile"""
        profile = {
            "strategic_partners": [p for p in partnership_data if p.get("type") == "strategic_partner"],
            "industry_associations": [p for p in partnership_data if p.get("type") == "association"],
            "board_memberships": [p for p in partnership_data if p.get("type") == "board"],
            "collaborations": [p for p in partnership_data if p.get("type") == "collaboration"],
            "confidence_score": min(len(partnership_data) * 0.12, 1.0)
        }

        self.logger.info(f"Built partnership profile with {len(partnership_data)} connections")
        return profile

    def build_comprehensive_profile(self, company_name: str, intelligence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete intelligence profile for a company"""

        profile = {
            "company_name": company_name,
            "intelligence_categories": {},
            "confidence_metrics": {},
            "data_sources": intelligence_data.get("data_sources", set()),
            "last_updated": datetime.now().isoformat()
        }

        # Build individual category profiles
        if "executives" in intelligence_data:
            profile["intelligence_categories"]["executive_leadership"] = \
                self.build_executive_profile(intelligence_data["executives"])

        if "investments" in intelligence_data:
            profile["intelligence_categories"]["investment_portfolio"] = \
                self.build_investment_profile(intelligence_data["investments"])

        if "news" in intelligence_data:
            profile["intelligence_categories"]["recent_developments"] = \
                self.build_news_profile(intelligence_data["news"])

        if "partnerships" in intelligence_data:
            profile["intelligence_categories"]["partnerships_networks"] = \
                self.build_partnership_profile(intelligence_data["partnerships"])

        # Calculate overall metrics
        profile["confidence_metrics"] = self._calculate_overall_metrics(profile)

        self.logger.info(f"Built comprehensive profile for {company_name}")
        return profile

    def _analyze_leadership_structure(self, executives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze leadership structure"""
        structure = {
            "c_suite": [],
            "senior_management": [],
            "board_members": [],
            "advisors": []
        }

        for exec in executives:
            title = exec.get("title", "").lower()

            if any(keyword in title for keyword in ["ceo", "chief", "president", "founder"]):
                structure["c_suite"].append(exec)
            elif any(keyword in title for keyword in ["vice president", "vp", "director", "managing"]):
                structure["senior_management"].append(exec)
            elif "board" in title:
                structure["board_members"].append(exec)
            elif any(keyword in title for keyword in ["advisor", "advisory"]):
                structure["advisors"].append(exec)

        return structure

    def _identify_decision_makers(self, executives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify key decision makers"""
        decision_makers = []

        for exec in executives:
            title = exec.get("title", "").lower()
            if any(keyword in title for keyword in ["ceo", "founder", "managing", "chief", "president"]):
                decision_makers.append(exec)

        return decision_makers

    def _analyze_investment_focus(self, investments: List[Dict[str, Any]]) -> List[str]:
        """Analyze investment focus areas"""
        focus_areas = []

        # Combine all context for analysis
        all_context = " ".join([inv.get("context", "") for inv in investments])
        context_lower = all_context.lower()

        focus_keywords = {
            "Technology": ["tech", "software", "saas", "ai", "fintech", "data"],
            "Healthcare": ["health", "medical", "biotech", "pharma", "life sciences"],
            "Consumer": ["consumer", "retail", "ecommerce", "marketplace", "brand"],
            "Enterprise": ["enterprise", "b2b", "business software", "cloud"],
            "Financial Services": ["financial", "banking", "payments", "lending"]
        }

        for focus, keywords in focus_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                focus_areas.append(focus)

        return focus_areas

    def _extract_sectors(self, investments: List[Dict[str, Any]]) -> List[str]:
        """Extract sector specializations"""
        all_context = " ".join([inv.get("context", "") for inv in investments])
        context_lower = all_context.lower()

        sectors = []
        sector_keywords = {
            "Technology": ["tech", "software", "saas", "ai", "fintech", "data"],
            "Healthcare": ["health", "medical", "biotech", "pharma", "life sciences"],
            "Consumer": ["consumer", "retail", "ecommerce", "marketplace", "brand"],
            "Enterprise": ["enterprise", "b2b", "business software", "cloud"],
            "Financial Services": ["financial", "banking", "payments", "lending"],
            "Real Estate": ["real estate", "property", "proptech"],
            "Energy": ["energy", "clean tech", "renewable", "sustainability"]
        }

        for sector, keywords in sector_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                sectors.append(sector)

        return sectors

    def _extract_geographies(self, investments: List[Dict[str, Any]]) -> List[str]:
        """Extract geographic focus"""
        geographies = []
        all_context = " ".join([inv.get("context", "") for inv in investments])
        context_lower = all_context.lower()

        geo_keywords = {
            "North America": ["north america", "us", "usa", "canada"],
            "Europe": ["europe", "uk", "germany", "france", "european"],
            "Asia": ["asia", "china", "india", "japan", "singapore"],
            "Global": ["global", "international", "worldwide"]
        }

        for geo, keywords in geo_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                geographies.append(geo)

        return geographies

    def _filter_recent_investments(self, investments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for recent investments"""
        recent_investments = []

        for inv in investments:
            context = inv.get("context", "").lower()
            recent_indicators = ["2023", "2024", "recent", "latest", "new", "announced"]

            if any(indicator in context for indicator in recent_indicators):
                recent_investments.append(inv)

        return recent_investments

    def _calculate_overall_metrics(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive confidence and quality metrics"""

        categories = profile.get("intelligence_categories", {})
        total_categories = len(categories)
        populated_categories = sum(1 for cat_data in categories.values()
                                 if cat_data and cat_data.get("confidence_score", 0) > 0)

        metrics = {
            "data_completeness": populated_categories / max(total_categories, 1),
            "intelligence_depth": min(len(profile.get("data_sources", [])) / 10, 1.0),
            "source_quality": min(len(profile.get("data_sources", [])) / 15, 1.0),
            "overall_confidence": 0.0
        }

        # Calculate weighted overall confidence
        weights = {
            "data_completeness": 0.3,
            "intelligence_depth": 0.3,
            "source_quality": 0.4
        }

        metrics["overall_confidence"] = sum(
            metrics[key] * weight for key, weight in weights.items()
        )

        return metrics
