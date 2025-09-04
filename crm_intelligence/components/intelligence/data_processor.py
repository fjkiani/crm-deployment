"""
Data Processor Component
Focused on processing and extracting structured data from raw search results
Single responsibility: Data extraction and normalization
"""

import re
import logging
from typing import Dict, List, Any, Optional

class DataProcessor:
    """Focused component for processing raw search data into structured information"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("DataProcessor")

    def extract_executive_info(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract executive information from search results"""
        executives = []

        for result in search_results:
            content = result.get("content", "")
            title = result.get("title", "")

            # Extract executive names and titles
            extracted_executives = self._extract_executives_from_content(content, title)
            executives.extend(extracted_executives)

        # Remove duplicates
        unique_executives = self._deduplicate_executives(executives)

        self.logger.info(f"Extracted {len(unique_executives)} unique executives")
        return unique_executives

    def extract_investment_info(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract investment information from search results"""
        investments = []

        for result in search_results:
            content = result.get("content", "")

            # Look for investment mentions
            investment_data = self._extract_investments_from_content(content)
            investments.extend(investment_data)

        # Remove duplicates
        unique_investments = self._deduplicate_investments(investments)

        self.logger.info(f"Extracted {len(unique_investments)} unique investments")
        return unique_investments

    def extract_news_info(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract news information from search results"""
        news_items = []

        for result in search_results:
            news_item = self._process_news_item(result)
            if news_item:
                news_items.append(news_item)

        self.logger.info(f"Extracted {len(news_items)} news items")
        return news_items

    def extract_partnership_info(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract partnership information from search results"""
        partnerships = []

        for result in search_results:
            content = result.get("content", "")
            partnership_data = self._extract_partnerships_from_content(content)
            partnerships.extend(partnership_data)

        self.logger.info(f"Extracted {len(partnerships)} partnerships")
        return partnerships

    def _extract_executives_from_content(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Extract executive information from content"""
        executives = []

        # Simple approach: Look for executive titles and names
        executive_titles = [
            'CEO', 'Chief Executive Officer', 'President', 'Founder', 'Co-founder',
            'Managing Partner', 'Partner', 'Managing Director', 'Director',
            'Chief Operating Officer', 'COO', 'Chief Financial Officer', 'CFO'
        ]

        content_lower = content.lower()
        title_lower = title.lower()

        # Check if content mentions executives
        for exec_title in executive_titles:
            if exec_title.lower() in content_lower or exec_title.lower() in title_lower:
                # Try to extract names around the title
                sentences = content.split('.')
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if exec_title.lower() in sentence_lower:
                        # Look for names in the sentence (capitalized words)
                        words = sentence.split()
                        for i, word in enumerate(words):
                            # Look for proper names (capitalized, not common words)
                            if (word and len(word) > 1 and word[0].isupper() and
                                word.lower() not in ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'been']):
                                # Check if next word is also capitalized (full name)
                                name = word
                                if i + 1 < len(words) and words[i+1][0].isupper():
                                    name += f" {words[i+1]}"

                                # Avoid duplicates
                                if not any(e['name'] == name for e in executives):
                                    executives.append({
                                        "name": name,
                                        "title": exec_title,
                                        "source_content": sentence.strip()[:100],
                                        "confidence": 0.7
                                    })

                                if len(executives) >= 3:  # Limit per result
                                    break

        return executives

    def _extract_investments_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract investment information from content"""
        investments = []

        # Look for investment mentions
        investment_indicators = [
            "invested in", "investment in", "portfolio company", "acquired",
            "merged with", "partnered with", "backed by", "funded"
        ]

        sentences = content.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in investment_indicators):
                # Extract company names and context
                words = sentence.split()
                for i, word in enumerate(words):
                    if word[0].isupper() and len(word) > 3:
                        investments.append({
                            "company": word,
                            "context": sentence.strip(),
                            "type": "portfolio_company"
                        })
                        break

        return investments

    def _extract_partnerships_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract partnership information from content"""
        partnerships = []

        partnership_indicators = {
            "strategic_partner": ["strategic partner", "alliance", "partnership"],
            "association": ["member of", "affiliated with", "part of"],
            "board": ["board member", "board director", "advisory board"],
            "collaboration": ["collaborated with", "joint venture", "cooperation"]
        }

        for partnership_type, indicators in partnership_indicators.items():
            for indicator in indicators:
                if indicator in content.lower():
                    partnerships.append({
                        "type": partnership_type,
                        "context": content[:200],
                        "indicator": indicator
                    })

        return partnerships

    def _process_news_item(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and categorize news items"""
        content = result.get("content", "")
        title = result.get("title", "")

        # Determine news type
        if "press release" in title.lower() or "announces" in title.lower():
            news_type = "press_release"
        elif "interview" in title.lower() or "said" in content.lower():
            news_type = "executive_quote"
        elif "analysis" in title.lower() or "industry" in title.lower():
            news_type = "industry_analysis"
        elif any(word in content.lower() for word in ["milestone", "achievement", "award", "expansion"]):
            news_type = "milestone"
        else:
            news_type = "general_news"

        return {
            "type": news_type,
            "title": title,
            "content": content[:300],
            "url": result.get("url", ""),
            "published_date": result.get("published_date", "")
        }

    def _deduplicate_executives(self, executives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate executives"""
        seen = set()
        unique = []

        for exec in executives:
            key = (exec.get("name", "").lower(), exec.get("title", "").lower())
            if key not in seen:
                seen.add(key)
                unique.append(exec)

        return unique

    def _deduplicate_investments(self, investments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate investments"""
        seen = set()
        unique = []

        for inv in investments:
            company = inv.get("company", "").lower()
            if company not in seen and len(company) > 3:
                seen.add(company)
                unique.append(inv)

        return unique[:20]  # Limit to top 20
