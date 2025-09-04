"""
Agent Brain: Contextual Intelligence and Reasoning Engine
Provides agents with domain knowledge, pattern recognition, and intelligent extraction
"""

import json
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IntelligenceContext:
    """Context for intelligent reasoning"""
    company: str
    industry: str
    focus_domain: str  # "healthcare", "fintech", etc.
    search_intent: str  # "decision_makers", "investments", "gaps"
    market_context: Dict[str, Any]
    competitive_landscape: List[str]
    
class AgentBrain:
    """Central intelligence engine for contextual reasoning"""
    
    def __init__(self):
        self.domain_knowledge = self._load_domain_knowledge()
        self.pattern_library = self._build_pattern_library()
        self.intelligence_extractors = self._build_extractors()
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Load domain-specific knowledge bases"""
        return {
            "healthcare": {
                "investment_types": [
                    "biotech", "pharmaceuticals", "medical devices", "digital health",
                    "healthtech", "medtech", "diagnostics", "therapeutics",
                    "clinical trials", "drug discovery", "medical AI", "telemedicine"
                ],
                "executive_titles": [
                    "Healthcare Investment Director", "Life Sciences Partner", 
                    "Biotech Investment Manager", "Healthcare Portfolio Manager",
                    "Medical Technology Analyst", "Pharmaceutical Investment Lead"
                ],
                "company_indicators": [
                    "bio", "pharma", "medical", "health", "clinical", "therapeutic",
                    "diagnostic", "genomic", "biotech", "medtech", "drug", "device"
                ],
                "funding_stages": [
                    "seed", "series a", "series b", "series c", "growth", "ipo",
                    "acquisition", "merger", "licensing deal", "partnership"
                ],
                "key_metrics": [
                    "clinical trial", "fda approval", "regulatory", "pipeline",
                    "patient outcomes", "efficacy", "safety", "market access"
                ]
            },
            "fintech": {
                "investment_types": [
                    "payments", "lending", "insurtech", "wealthtech", "regtech",
                    "blockchain", "cryptocurrency", "digital banking", "robo-advisor"
                ],
                "executive_titles": [
                    "Fintech Investment Director", "Financial Services Partner",
                    "Digital Banking Analyst", "Payments Investment Lead"
                ],
                "company_indicators": [
                    "pay", "bank", "finance", "credit", "loan", "insurance",
                    "wealth", "trading", "crypto", "blockchain", "digital wallet"
                ]
            }
        }
    
    def _build_pattern_library(self) -> Dict[str, List[str]]:
        """Build intelligent pattern recognition library"""
        return {
            "executive_patterns": [
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]*(?:is|serves as|works as)?\s*(CEO|Chief Executive Officer|President|Managing Partner|Partner|Director|VP|Vice President|Head of|Lead)',
                r'(CEO|Chief Executive Officer|President|Managing Partner|Partner|Director|VP|Vice President|Head of|Lead)[,\s]*([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]*leads?\s+(?:the\s+)?(healthcare|investment|portfolio|fund)',
                r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]*(?:is\s+)?responsible\s+for\s+(healthcare|investment|portfolio)'
            ],
            "investment_patterns": [
                r'(?:invested|investment|funding|raised|acquired|purchased)\s+(?:in\s+)?([A-Z][a-zA-Z\s&\-]+?)(?:\s+for\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k)',
                r'\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k)\s+(?:investment\s+)?(?:in\s+)?([A-Z][a-zA-Z\s&\-]+)',
                r'([A-Z][a-zA-Z\s&\-]+?)\s+(?:received|raised|secured)\s+\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k)',
                r'(?:Series\s+[A-Z]|seed|growth)\s+(?:round\s+)?(?:of\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k)\s+(?:in\s+)?([A-Z][a-zA-Z\s&\-]+)',
                r'([A-Z][a-zA-Z\s&\-]+?)\s+(?:completed|closed)\s+(?:its\s+)?(?:Series\s+[A-Z]|seed|growth)\s+(?:round\s+)?(?:of\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B|k)'
            ],
            "company_patterns": [
                r'([A-Z][a-zA-Z\s&\-]+?)(?:\s+Inc\.?|\s+LLC|\s+Ltd\.?|\s+Corporation|\s+Corp\.?|\s+Limited|\s+LP|\s+LLP)',
                r'([A-Z][a-zA-Z\s&\-]+?)\s+(?:is\s+a|develops|provides|offers|specializes\s+in)',
                r'(?:startup|company|firm|business)\s+([A-Z][a-zA-Z\s&\-]+)',
                r'([A-Z][a-zA-Z\s&\-]+?)\s+(?:platform|solution|technology|software|device|drug|treatment)'
            ],
            "opportunity_patterns": [
                r'(?:opportunity|gap|potential|growth|expansion|market|emerging|trend|unmet\s+need|whitespace)',
                r'(?:could|should|might|may)\s+(?:invest|explore|consider|target)',
                r'(?:lacking|missing|absent|underserved|untapped|unexplored)',
                r'(?:future|next|upcoming|emerging|growing|expanding)\s+(?:market|sector|area|opportunity)'
            ]
        }
    
    def _build_extractors(self) -> Dict[str, Any]:
        """Build intelligent extraction engines"""
        return {
            "executive_extractor": self._extract_executives_intelligent,
            "investment_extractor": self._extract_investments_intelligent,
            "opportunity_extractor": self._extract_opportunities_intelligent,
            "company_extractor": self._extract_companies_intelligent
        }
    
    def analyze_content_relevance(self, content: str, title: str, url: str, context: IntelligenceContext) -> float:
        """Analyze how relevant content is to the intelligence context"""
        
        relevance_score = 0.0
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Company name relevance
        company_variations = self._generate_company_variations(context.company)
        company_matches = sum(1 for var in company_variations if var.lower() in content_lower or var.lower() in title_lower)
        relevance_score += min(company_matches * 0.3, 0.6)
        
        # Domain relevance
        domain_keywords = self.domain_knowledge.get(context.focus_domain, {}).get("company_indicators", [])
        domain_matches = sum(1 for keyword in domain_keywords if keyword in content_lower)
        relevance_score += min(domain_matches * 0.1, 0.3)
        
        # Intent relevance
        if context.search_intent == "decision_makers":
            executive_keywords = ["ceo", "president", "partner", "director", "executive", "management", "leadership"]
            intent_matches = sum(1 for keyword in executive_keywords if keyword in content_lower)
            relevance_score += min(intent_matches * 0.05, 0.2)
        
        elif context.search_intent == "investments":
            investment_keywords = ["investment", "funding", "portfolio", "deal", "acquisition", "merger", "raised"]
            intent_matches = sum(1 for keyword in investment_keywords if keyword in content_lower)
            relevance_score += min(intent_matches * 0.05, 0.2)
        
        # URL quality scoring
        if any(domain in url for domain in [".com", ".org", ".net"]):
            if "linkedin" in url or "crunchbase" in url or "bloomberg" in url:
                relevance_score += 0.1
            elif "wikipedia" in url or "dictionary" in url or "gov" in url:
                relevance_score -= 0.2
        
        return min(relevance_score, 1.0)
    
    def _generate_company_variations(self, company: str) -> List[str]:
        """Generate variations of company name for better matching"""
        variations = [company]
        
        # Add common variations
        if "Capital" in company:
            variations.append(company.replace("Capital", "Cap"))
            variations.append(company.replace(" Capital", ""))
        
        if "Management" in company:
            variations.append(company.replace("Management", "Mgmt"))
            variations.append(company.replace(" Management", ""))
        
        if "Partners" in company:
            variations.append(company.replace("Partners", "Partner"))
        
        # Add abbreviations
        words = company.split()
        if len(words) > 1:
            abbreviation = "".join([word[0] for word in words if word[0].isupper()])
            if len(abbreviation) > 1:
                variations.append(abbreviation)
        
        return variations
    
    def _extract_executives_intelligent(self, content: str, title: str, context: IntelligenceContext) -> List[Dict[str, Any]]:
        """Intelligently extract executive information with domain context"""
        
        executives = []
        
        # Use domain-specific executive titles
        domain_titles = self.domain_knowledge.get(context.focus_domain, {}).get("executive_titles", [])
        all_titles = ["CEO", "President", "Partner", "Director", "VP", "Head of"] + domain_titles
        
        for pattern in self.pattern_library["executive_patterns"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                name = None
                exec_title = None
                
                # Extract name and title from match groups
                for group in groups:
                    if group and len(group) > 2:
                        if any(title_word in group for title_word in all_titles):
                            exec_title = group.strip()
                        elif self._is_valid_person_name(group):
                            name = group.strip()
                
                if name and exec_title:
                    # Calculate domain relevance
                    domain_relevance = self._calculate_executive_domain_relevance(
                        name, exec_title, context.focus_domain
                    )
                    
                    if domain_relevance > 0.3:  # Only include relevant executives
                        executives.append({
                            "name": name,
                            "title": exec_title,
                            "domain_relevance": domain_relevance,
                            "context": match.group(0),
                            "source": title,
                            "confidence": 0.8 + domain_relevance * 0.2
                        })
        
        # Deduplicate and sort by relevance
        executives = self._deduplicate_executives(executives)
        executives.sort(key=lambda x: x["domain_relevance"], reverse=True)
        
        return executives[:5]  # Return top 5
    
    def _extract_investments_intelligent(self, content: str, title: str, context: IntelligenceContext) -> List[Dict[str, Any]]:
        """Intelligently extract investment information with domain context"""
        
        investments = []
        
        for pattern in self.pattern_library["investment_patterns"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                groups = match.groups()
                company_name = None
                amount = None
                unit = None
                
                # Extract investment details from match groups
                for i, group in enumerate(groups):
                    if group:
                        if re.match(r'^[0-9]+(\.[0-9]+)?$', group):
                            amount = group
                        elif group.lower() in ['million', 'billion', 'm', 'b', 'k']:
                            unit = group
                        elif len(group) > 3 and group[0].isupper():
                            company_name = group.strip()
                
                if company_name and amount and unit:
                    # Calculate domain relevance
                    domain_relevance = self._calculate_investment_domain_relevance(
                        company_name, context.focus_domain
                    )
                    
                    if domain_relevance > 0.2:  # Only include relevant investments
                        investments.append({
                            "company": company_name,
                            "amount": f"${amount}{unit}",
                            "domain_relevance": domain_relevance,
                            "context": match.group(0),
                            "source": title,
                            "confidence": 0.7 + domain_relevance * 0.3
                        })
        
        # Deduplicate and sort by relevance
        investments = self._deduplicate_investments(investments)
        investments.sort(key=lambda x: x["domain_relevance"], reverse=True)
        
        return investments[:5]  # Return top 5
    
    def _extract_opportunities_intelligent(self, content: str, title: str, context: IntelligenceContext) -> List[Dict[str, Any]]:
        """Intelligently extract opportunity information with domain context"""
        
        opportunities = []
        
        # Split content into sentences for analysis
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue
            
            # Check for opportunity indicators
            has_opportunity_pattern = any(
                re.search(pattern, sentence, re.IGNORECASE) 
                for pattern in self.pattern_library["opportunity_patterns"]
            )
            
            if has_opportunity_pattern:
                # Calculate domain relevance
                domain_relevance = self._calculate_opportunity_domain_relevance(
                    sentence, context.focus_domain
                )
                
                if domain_relevance > 0.3:  # Only include relevant opportunities
                    opportunities.append({
                        "opportunity": sentence,
                        "domain_relevance": domain_relevance,
                        "source": title,
                        "confidence": 0.6 + domain_relevance * 0.4
                    })
        
        # Sort by relevance
        opportunities.sort(key=lambda x: x["domain_relevance"], reverse=True)
        
        return opportunities[:3]  # Return top 3
    
    def _extract_companies_intelligent(self, content: str, title: str, context: IntelligenceContext) -> List[Dict[str, Any]]:
        """Intelligently extract company information with domain context"""
        
        companies = []
        
        for pattern in self.pattern_library["company_patterns"]:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                company_name = match.group(1).strip()
                
                if len(company_name) > 3 and company_name[0].isupper():
                    # Calculate domain relevance
                    domain_relevance = self._calculate_company_domain_relevance(
                        company_name, context.focus_domain
                    )
                    
                    if domain_relevance > 0.4:  # Only include relevant companies
                        companies.append({
                            "company": company_name,
                            "domain_relevance": domain_relevance,
                            "context": match.group(0),
                            "source": title,
                            "confidence": 0.7 + domain_relevance * 0.3
                        })
        
        # Deduplicate and sort by relevance
        companies = self._deduplicate_companies(companies)
        companies.sort(key=lambda x: x["domain_relevance"], reverse=True)
        
        return companies[:5]  # Return top 5
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Validate if string looks like a person name"""
        
        if len(name) < 4 or len(name) > 50:
            return False
        
        words = name.split()
        if len(words) < 2:
            return False
        
        # Check if all words start with capital letter
        if not all(word[0].isupper() for word in words):
            return False
        
        # Avoid common false positives
        false_positives = [
            "Asset Management", "Capital Partners", "Investment Group",
            "Financial Services", "Private Equity", "Venture Capital",
            "Healthcare Solutions", "Medical Technology"
        ]
        
        if any(fp.lower() in name.lower() for fp in false_positives):
            return False
        
        return True
    
    def _calculate_executive_domain_relevance(self, name: str, title: str, domain: str) -> float:
        """Calculate how relevant an executive is to the domain"""
        
        relevance = 0.0
        title_lower = title.lower()
        
        # Domain-specific title matching
        domain_titles = self.domain_knowledge.get(domain, {}).get("executive_titles", [])
        for domain_title in domain_titles:
            if domain_title.lower() in title_lower:
                relevance += 0.8
                break
        
        # General healthcare keywords in title
        if domain == "healthcare":
            healthcare_keywords = ["healthcare", "health", "medical", "bio", "pharma", "clinical", "life sciences"]
            for keyword in healthcare_keywords:
                if keyword in title_lower:
                    relevance += 0.6
                    break
        
        # Investment-related titles
        investment_keywords = ["investment", "portfolio", "fund", "partner", "director"]
        for keyword in investment_keywords:
            if keyword in title_lower:
                relevance += 0.3
                break
        
        return min(relevance, 1.0)
    
    def _calculate_investment_domain_relevance(self, company_name: str, domain: str) -> float:
        """Calculate how relevant an investment is to the domain"""
        
        relevance = 0.0
        company_lower = company_name.lower()
        
        # Domain-specific company indicators
        domain_indicators = self.domain_knowledge.get(domain, {}).get("company_indicators", [])
        for indicator in domain_indicators:
            if indicator in company_lower:
                relevance += 0.7
                break
        
        return min(relevance, 1.0)
    
    def _calculate_opportunity_domain_relevance(self, opportunity_text: str, domain: str) -> float:
        """Calculate how relevant an opportunity is to the domain"""
        
        relevance = 0.0
        text_lower = opportunity_text.lower()
        
        # Domain-specific keywords
        domain_indicators = self.domain_knowledge.get(domain, {}).get("company_indicators", [])
        matches = sum(1 for indicator in domain_indicators if indicator in text_lower)
        relevance += min(matches * 0.3, 0.9)
        
        return min(relevance, 1.0)
    
    def _calculate_company_domain_relevance(self, company_name: str, domain: str) -> float:
        """Calculate how relevant a company is to the domain"""
        
        return self._calculate_investment_domain_relevance(company_name, domain)
    
    def _deduplicate_executives(self, executives: List[Dict]) -> List[Dict]:
        """Remove duplicate executives"""
        
        seen_names = set()
        unique_executives = []
        
        for exec_info in executives:
            name_key = exec_info["name"].lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_executives.append(exec_info)
        
        return unique_executives
    
    def _deduplicate_investments(self, investments: List[Dict]) -> List[Dict]:
        """Remove duplicate investments"""
        
        seen_companies = set()
        unique_investments = []
        
        for inv_info in investments:
            company_key = inv_info["company"].lower()
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_investments.append(inv_info)
        
        return unique_investments
    
    def _deduplicate_companies(self, companies: List[Dict]) -> List[Dict]:
        """Remove duplicate companies"""
        
        seen_companies = set()
        unique_companies = []
        
        for company_info in companies:
            company_key = company_info["company"].lower()
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_companies.append(company_info)
        
        return unique_companies
