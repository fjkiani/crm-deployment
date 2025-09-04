"""
Executive Intelligence Agent
Specialist agent for finding and analyzing decision makers, executives, and leadership
"""

import re
from typing import Dict, Any, List, Optional
from .base_specialist import SpecialistAgent, SpecialistConfig, StructuredAnswer
from services.external.tavily_service import TavilyService, TavilyServiceConfig

class ExecutiveIntelligenceAgent(SpecialistAgent):
    """Expert in executive and leadership intelligence"""
    
    def __init__(self, config: SpecialistConfig):
        super().__init__(config)
        self.tavily_service = None
    
    def _define_expertise_domains(self) -> List[str]:
        """Define executive intelligence expertise domains"""
        return [
            "executives", "leadership", "decision makers", "board members",
            "management team", "org structure", "decision authority",
            "CEO", "CTO", "CFO", "President", "Partner", "Director"
        ]
    
    def _define_answerable_patterns(self) -> List[str]:
        """Define question patterns this agent can answer"""
        return [
            "who are", "who makes", "decision maker", "executive team",
            "leadership structure", "management", "board", "key personnel",
            "contact person", "in charge of", "responsible for"
        ]
    
    async def initialize(self) -> bool:
        """Initialize the executive intelligence agent"""
        if not await super().initialize():
            return False
        
        try:
            # Initialize Tavily service for external intelligence
            tavily_config = TavilyServiceConfig(
                name="tavily_executive_service",
                api_key=self.specialist_config.api_key,
                timeout=self.specialist_config.timeout
            )
            self.tavily_service = TavilyService(tavily_config)
            await self.tavily_service.initialize()
            
            self.logger.info("Executive Intelligence Agent initialized with Tavily service")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Tavily service: {e}")
            return False
    
    async def answer_question(self, question: str, company: str, context: Dict[str, Any] = None) -> StructuredAnswer:
        """Answer executive intelligence questions"""
        
        self.logger.info(f"Answering executive question for {company}: {question}")
        
        try:
            # Build search queries for executive intelligence
            search_queries = self._build_executive_search_queries(company, question, context)
            
            # Gather intelligence from multiple sources
            executive_data = {
                "decision_makers": [],
                "leadership_structure": {},
                "org_chart": {},
                "board_members": [],
                "key_contacts": []
            }
            
            all_sources = []
            
            # Execute searches
            for query_type, query in search_queries.items():
                try:
                    results = await self.tavily_service.search(query, max_results=5)
                    processed_data = await self._process_search_results(query_type, results, company)
                    
                    # Merge results into executive data
                    if query_type == "executives":
                        executive_data["decision_makers"].extend(processed_data.get("executives", []))
                    elif query_type == "leadership":
                        executive_data["leadership_structure"].update(processed_data.get("structure", {}))
                    elif query_type == "board":
                        executive_data["board_members"].extend(processed_data.get("board", []))
                    
                    # Track sources
                    for result in results.get("results", []):
                        if result.get("url"):
                            all_sources.append(result["url"])
                            
                except Exception as e:
                    self.logger.warning(f"Search failed for {query_type}: {e}")
            
            # Remove duplicates and enhance data
            executive_data = self._deduplicate_and_enhance_executives(executive_data)
            
            # Calculate confidence based on data quality
            confidence = self._calculate_executive_confidence(executive_data, all_sources)
            
            # Generate recommendations
            recommendations = self._generate_executive_recommendations(executive_data, question, company)
            
            return self._create_structured_answer(
                question=question,
                company=company,
                data=executive_data,
                sources=list(set(all_sources)),
                confidence=confidence,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Executive intelligence failed for {company}: {e}")
            return self._create_fallback_answer(question, company)
    
    def _build_executive_search_queries(self, company: str, question: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Build targeted search queries for executive intelligence"""
        
        base_queries = {
            "executives": f'"{company}" CEO president founder executive leadership team management',
            "leadership": f'"{company}" leadership structure org chart management team',
            "board": f'"{company}" board of directors board members advisory board',
            "contacts": f'"{company}" contact information executive contact leadership contact'
        }
        
        # Enhance queries based on question context
        question_lower = question.lower()
        
        # If question mentions specific sector, add sector context
        if context and "sector" in context:
            sector = context["sector"]
            for key in base_queries:
                base_queries[key] += f" {sector}"
        
        # If question is about specific roles, focus on those
        executive_roles = ["ceo", "cto", "cfo", "president", "founder", "partner", "director"]
        mentioned_roles = [role for role in executive_roles if role in question_lower]
        
        if mentioned_roles:
            role_query = f'"{company}" {" ".join(mentioned_roles)} executive leadership'
            base_queries["specific_roles"] = role_query
        
        # If question is about decision making, focus on authority
        if any(word in question_lower for word in ["decision", "authority", "responsible", "in charge"]):
            base_queries["decision_authority"] = f'"{company}" decision making authority investment committee executive committee'
        
        return base_queries
    
    async def _process_search_results(self, query_type: str, results: Dict[str, Any], company: str) -> Dict[str, Any]:
        """Process search results for executive intelligence"""
        
        processed_data = {"executives": [], "structure": {}, "board": []}
        
        for result in results.get("results", []):
            content = result.get("content", "")
            title = result.get("title", "")
            url = result.get("url", "")
            
            # Extract executives from content
            executives = self._extract_executives_from_content(content, title, url, company)
            processed_data["executives"].extend(executives)
            
            # Extract organizational structure
            structure = self._extract_org_structure(content, company)
            if structure:
                processed_data["structure"].update(structure)
        
        return processed_data
    
    def _extract_executives_from_content(self, content: str, title: str, url: str, company: str) -> List[Dict[str, Any]]:
        """Extract executive information from content using pattern matching"""
        
        executives = []
        
        # Define executive title patterns
        executive_patterns = [
            r'(CEO|Chief Executive Officer)',
            r'(CTO|Chief Technology Officer)',
            r'(CFO|Chief Financial Officer)', 
            r'(President)',
            r'(Founder|Co-founder)',
            r'(Managing Partner|Partner)',
            r'(Managing Director|Director)',
            r'(Chairman|Chairwoman)',
            r'(Board Member)',
            r'(Vice President|VP)'
        ]
        
        # Look for name + title patterns
        for pattern in executive_patterns:
            # Pattern: Name + Title
            name_title_pattern = rf'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]*{pattern}'
            matches = re.finditer(name_title_pattern, content, re.IGNORECASE)
            
            for match in matches:
                name = match.group(1).strip()
                title = match.group(2).strip()
                
                # Validate name (avoid false positives)
                if self._is_valid_executive_name(name):
                    executive = {
                        "name": name,
                        "title": title,
                        "company": company,
                        "source_url": url,
                        "source_title": title,
                        "context": match.group(0),
                        "confidence": 0.8
                    }
                    executives.append(executive)
        
        # Alternative pattern: Title + Name
        for pattern in executive_patterns:
            title_name_pattern = rf'{pattern}[,\s]*([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
            matches = re.finditer(title_name_pattern, content, re.IGNORECASE)
            
            for match in matches:
                title = match.group(1).strip()
                name = match.group(2).strip()
                
                if self._is_valid_executive_name(name):
                    # Check if we already have this person
                    existing = any(exec["name"].lower() == name.lower() for exec in executives)
                    if not existing:
                        executive = {
                            "name": name,
                            "title": title,
                            "company": company,
                            "source_url": url,
                            "source_title": title,
                            "context": match.group(0),
                            "confidence": 0.7
                        }
                        executives.append(executive)
        
        return executives
    
    def _is_valid_executive_name(self, name: str) -> bool:
        """Validate if extracted name looks like a real person name"""
        
        # Basic validation rules
        if len(name) < 4 or len(name) > 50:
            return False
        
        # Must have at least 2 words (first and last name)
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should start with capital letter
        if not all(word[0].isupper() for word in words):
            return False
        
        # Avoid common false positives
        false_positives = [
            "Asset Management", "Capital Partners", "Investment Group",
            "Financial Services", "Private Equity", "Venture Capital"
        ]
        
        if any(fp.lower() in name.lower() for fp in false_positives):
            return False
        
        return True
    
    def _extract_org_structure(self, content: str, company: str) -> Dict[str, Any]:
        """Extract organizational structure information"""
        
        structure = {}
        
        # Look for organizational mentions
        org_patterns = [
            r'reports to ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'managed by ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'under ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'team led by ([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in org_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                manager = match.group(1).strip()
                if self._is_valid_executive_name(manager):
                    if "reporting_structure" not in structure:
                        structure["reporting_structure"] = []
                    structure["reporting_structure"].append({
                        "manager": manager,
                        "context": match.group(0)
                    })
        
        return structure
    
    def _deduplicate_and_enhance_executives(self, executive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicates and enhance executive information"""
        
        # Deduplicate executives by name
        seen_names = set()
        unique_executives = []
        
        for exec_info in executive_data["decision_makers"]:
            name_key = exec_info["name"].lower()
            if name_key not in seen_names:
                seen_names.add(name_key)
                
                # Enhance with additional analysis
                exec_info["decision_level"] = self._assess_decision_level(exec_info["title"])
                exec_info["likely_focus_areas"] = self._infer_focus_areas(exec_info["title"])
                
                unique_executives.append(exec_info)
        
        executive_data["decision_makers"] = unique_executives
        
        # Sort by decision level (CEO, President, etc. first)
        executive_data["decision_makers"].sort(
            key=lambda x: self._get_title_priority(x["title"]),
            reverse=True
        )
        
        return executive_data
    
    def _assess_decision_level(self, title: str) -> str:
        """Assess the decision-making level of an executive"""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["ceo", "chief executive", "founder", "president"]):
            return "high"
        elif any(word in title_lower for word in ["cfo", "cto", "coo", "managing partner"]):
            return "high"
        elif any(word in title_lower for word in ["vice president", "vp", "director", "partner"]):
            return "medium"
        else:
            return "medium"
    
    def _infer_focus_areas(self, title: str) -> List[str]:
        """Infer likely focus areas based on executive title"""
        title_lower = title.lower()
        focus_areas = []
        
        if "technology" in title_lower or "cto" in title_lower:
            focus_areas.extend(["technology", "innovation", "product development"])
        elif "financial" in title_lower or "cfo" in title_lower:
            focus_areas.extend(["finance", "investments", "fundraising"])
        elif "investment" in title_lower or "portfolio" in title_lower:
            focus_areas.extend(["investments", "portfolio management", "deal sourcing"])
        elif "ceo" in title_lower or "president" in title_lower:
            focus_areas.extend(["strategy", "partnerships", "business development"])
        
        return focus_areas
    
    def _get_title_priority(self, title: str) -> int:
        """Get priority score for sorting executives"""
        title_lower = title.lower()
        
        priority_map = {
            "ceo": 100, "chief executive": 100, "founder": 95, "co-founder": 90,
            "president": 85, "chairman": 80, "managing partner": 75,
            "cfo": 70, "cto": 70, "coo": 70,
            "vice president": 60, "vp": 60, "director": 50, "partner": 45
        }
        
        for key, priority in priority_map.items():
            if key in title_lower:
                return priority
        
        return 30  # Default priority
    
    def _calculate_executive_confidence(self, executive_data: Dict[str, Any], sources: List[str]) -> float:
        """Calculate confidence score for executive intelligence"""
        
        base_confidence = 0.4
        
        # Factor in number of executives found
        num_executives = len(executive_data.get("decision_makers", []))
        if num_executives > 0:
            base_confidence += min(num_executives / 5.0, 0.3)
        
        # Factor in source quality
        if sources:
            source_bonus = min(len(sources) / 3.0, 0.2)
            base_confidence += source_bonus
        
        # Factor in data richness
        has_titles = any(exec.get("title") for exec in executive_data.get("decision_makers", []))
        has_context = any(exec.get("context") for exec in executive_data.get("decision_makers", []))
        
        if has_titles:
            base_confidence += 0.1
        if has_context:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _generate_executive_recommendations(self, executive_data: Dict[str, Any], question: str, company: str) -> List[str]:
        """Generate actionable recommendations based on executive findings"""
        
        recommendations = []
        executives = executive_data.get("decision_makers", [])
        
        if not executives:
            recommendations.append(f"No executives found for {company} - consider additional research sources")
            recommendations.append("Try searching LinkedIn or company website directly")
            return recommendations
        
        # Prioritize top executives for outreach
        high_level_execs = [e for e in executives if e.get("decision_level") == "high"]
        if high_level_execs:
            top_exec = high_level_execs[0]
            recommendations.append(f"Priority contact: {top_exec['name']} ({top_exec['title']}) - highest decision authority")
        
        # Suggest approach strategies
        if len(executives) > 1:
            recommendations.append(f"Multi-stakeholder approach: engage {len(executives)} identified decision makers")
        
        # Focus area recommendations
        focus_areas = set()
        for exec in executives:
            focus_areas.update(exec.get("likely_focus_areas", []))
        
        if focus_areas:
            recommendations.append(f"Tailor messaging to: {', '.join(list(focus_areas)[:3])}")
        
        # Contact discovery recommendations
        recommendations.append("Next step: gather contact information for identified executives")
        
        return recommendations
    
    def _create_fallback_answer(self, question: str, company: str) -> StructuredAnswer:
        """Create fallback answer when search fails"""
        
        fallback_data = {
            "decision_makers": [],
            "leadership_structure": {},
            "error": "Executive intelligence search failed",
            "suggestions": [
                "Check company website leadership page",
                "Search LinkedIn for company executives",
                "Look up recent press releases for executive mentions"
            ]
        }
        
        return self._create_structured_answer(
            question=question,
            company=company,
            data=fallback_data,
            sources=[],
            confidence=0.1,
            recommendations=["Manual research required - automated search failed"]
        )
    
    async def cleanup(self) -> bool:
        """Cleanup resources"""
        if self.tavily_service:
            await self.tavily_service.cleanup()
        return await super().cleanup()
