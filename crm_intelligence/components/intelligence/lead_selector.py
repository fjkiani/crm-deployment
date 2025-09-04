"""
Lead Selector Component
Focused on selecting and prioritizing high-value leads for intelligence gathering
Single responsibility: Lead evaluation and selection logic
"""

import json
import logging
from typing import Dict, List, Any, Optional

class LeadSelector:
    """Focused component for selecting high-value leads"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("LeadSelector")

    def select_high_value_leads(self, leads_data: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Select top high-value leads based on scoring criteria"""

        if not leads_data:
            self.logger.warning("No leads data provided")
            return []

        # Score and rank leads
        scored_leads = []
        for lead in leads_data:
            score = self._calculate_lead_score(lead)
            scored_leads.append((lead, score))

        # Sort by score (highest first)
        scored_leads.sort(key=lambda x: x[1], reverse=True)

        # Select top leads
        selected_leads = [lead for lead, score in scored_leads[:limit]]

        self.logger.info(f"Selected {len(selected_leads)} high-value leads out of {len(leads_data)} total leads")

        # Log selection details
        for i, (lead, score) in enumerate(scored_leads[:limit], 1):
            company_name = lead.get('company', 'Unknown')
            category = lead.get('category', 'N/A')
            self.logger.info(f"#{i}: {company_name} ({category}) - Score: {score}")

        return selected_leads

    def _calculate_lead_score(self, lead: Dict[str, Any]) -> int:
        """Calculate scoring value for a lead"""
        score = 0

        # Category scoring (highest priority)
        score += self._score_by_category(lead)

        # Contact completeness scoring
        score += self._score_by_contact_info(lead)

        # Digital presence scoring
        score += self._score_by_digital_presence(lead)

        # Company type indicators
        score += self._score_by_indicators(lead)

        return score

    def _score_by_category(self, lead: Dict[str, Any]) -> int:
        """Score based on lead category"""
        category = lead.get('category', '').lower()
        category_scores = {
            'private equity': 3,
            'venture capital': 3,
            'asset management': 3,
            'investment banking': 3,
            'hedge fund': 2,
            'mutual fund': 2,
            'wealth management': 2,
            'financial services': 1
        }

        return category_scores.get(category, 0)

    def _score_by_contact_info(self, lead: Dict[str, Any]) -> int:
        """Score based on contact information completeness"""
        score = 0

        contact_info = lead.get('contact', {})
        if contact_info.get('name'):
            score += 1

        communication = lead.get('communication', {})
        if communication.get('emails'):
            score += 1

        if communication.get('websites'):
            score += 1

        if communication.get('phones'):
            score += 1

        return score

    def _score_by_digital_presence(self, lead: Dict[str, Any]) -> int:
        """Score based on digital presence indicators"""
        score = 0

        communication = lead.get('communication', {})

        # Website presence
        if communication.get('websites'):
            score += 1

        # Social media presence
        if communication.get('linkedin') or communication.get('twitter'):
            score += 1

        return score

    def _score_by_indicators(self, lead: Dict[str, Any]) -> int:
        """Score based on company type indicators"""
        score = 0

        company_name = lead.get('company', '').lower()

        # Single Family Office (SFO) / Multi Family Office (MFO) indicators
        sfo_indicators = ['family office', 'sfo', 'mfo', 'single family', 'multi family']
        if any(indicator in company_name for indicator in sfo_indicators):
            score += 2

        # High-value financial institution indicators
        high_value_indicators = [
            'private equity', 'venture capital', 'asset management',
            'investment banking', 'hedge fund', 'private wealth'
        ]
        if any(indicator in company_name for indicator in high_value_indicators):
            score += 1

        return score

    def load_leads_from_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load leads data from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Extract leads from nested structure
            leads = []
            for category, category_leads in data.get('leads_by_category', {}).items():
                for lead in category_leads:
                    lead_copy = lead.copy()
                    lead_copy['category'] = category
                    leads.append(lead_copy)

            self.logger.info(f"Loaded {len(leads)} leads from {filepath}")
            return leads

        except FileNotFoundError:
            self.logger.error(f"Leads file not found: {filepath}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in leads file: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading leads: {e}")
            return []

    def filter_leads_by_criteria(self, leads: List[Dict[str, Any]],
                               criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter leads based on specific criteria"""

        filtered_leads = []

        for lead in leads:
            if self._matches_criteria(lead, criteria):
                filtered_leads.append(lead)

        self.logger.info(f"Filtered {len(filtered_leads)} leads from {len(leads)} total")
        return filtered_leads

    def _matches_criteria(self, lead: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if lead matches filtering criteria"""

        # Category filter
        if 'categories' in criteria:
            lead_category = lead.get('category', '').lower()
            if lead_category not in [cat.lower() for cat in criteria['categories']]:
                return False

        # Minimum score filter
        if 'min_score' in criteria:
            score = self._calculate_lead_score(lead)
            if score < criteria['min_score']:
                return False

        # Contact info required
        if criteria.get('requires_contact', False):
            contact_info = lead.get('contact', {})
            if not contact_info.get('name'):
                return False

        # Website required
        if criteria.get('requires_website', False):
            communication = lead.get('communication', {})
            if not communication.get('websites'):
                return False

        return True

    def get_lead_statistics(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about the leads dataset"""

        stats = {
            "total_leads": len(leads),
            "categories": {},
            "contact_completeness": {},
            "digital_presence": {},
            "score_distribution": {}
        }

        # Category breakdown
        for lead in leads:
            category = lead.get('category', 'Unknown')
            stats["categories"][category] = stats["categories"].get(category, 0) + 1

        # Contact completeness
        has_name = sum(1 for lead in leads if lead.get('contact', {}).get('name'))
        has_email = sum(1 for lead in leads if lead.get('communication', {}).get('emails'))
        has_website = sum(1 for lead in leads if lead.get('communication', {}).get('websites'))

        stats["contact_completeness"] = {
            "has_name": has_name,
            "has_email": has_email,
            "has_website": has_website,
            "name_percentage": has_name / len(leads) if leads else 0,
            "email_percentage": has_email / len(leads) if leads else 0,
            "website_percentage": has_website / len(leads) if leads else 0
        }

        # Score distribution
        scores = [self._calculate_lead_score(lead) for lead in leads]
        stats["score_distribution"] = {
            "average_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "high_value_leads": sum(1 for score in scores if score >= 3)
        }

        return stats
