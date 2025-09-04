"""
Company Intelligence Component
Specialized component for gathering company overview and basic information
"""

import asyncio
from typing import Dict, Any, List
from core.interfaces.intelligence import IntelligenceComponent, IntelligenceConfig
from services.external.tavily_service import TavilyService

class CompanyIntelligenceConfig(IntelligenceConfig):
    """Configuration for company intelligence gathering"""
    search_depth: str = "basic"  # basic, detailed, comprehensive
    include_subsidiaries: bool = False
    include_financials: bool = True

class CompanyIntelligenceComponent(IntelligenceComponent):
    """Gathers comprehensive company intelligence"""
    
    def __init__(self, config: CompanyIntelligenceConfig):
        super().__init__(config)
        self.company_config = config
        self.tavily_service = None
        
    async def initialize(self) -> bool:
        """Initialize the company intelligence component"""
        try:
            self.tavily_service = TavilyService(self.intelligence_config.api_key)
            await self.tavily_service.connect()
            self._initialized = True
            self.logger.info("Company Intelligence Component initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
            
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute company intelligence gathering"""
        company_name = input_data.get("company_name")
        if not company_name:
            raise ValueError("company_name is required")
            
        return await self.gather_intelligence(company_name, input_data)
        
    async def gather_intelligence(self, target: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather company intelligence"""
        
        self.logger.info(f"Gathering company intelligence for: {target}")
        
        intelligence = {
            "company_name": target,
            "basic_info": {},
            "business_model": {},
            "market_position": {},
            "financial_info": {},
            "leadership": [],
            "data_sources": [],
            "confidence_score": 0.0
        }
        
        # Define search queries based on depth
        queries = self._build_search_queries(target)
        
        # Execute searches
        for query_type, query in queries.items():
            try:
                results = await self.tavily_service.search(query, max_results=5)
                processed_data = self._process_search_results(query_type, results)
                intelligence[query_type].update(processed_data)
                
                # Track data sources
                for result in results.get("results", []):
                    if result.get("url"):
                        intelligence["data_sources"].append(result["url"])
                        
            except Exception as e:
                self.logger.error(f"Search failed for {query_type}: {e}")
                
        # Calculate confidence score
        intelligence["confidence_score"] = self._calculate_confidence(intelligence)
        
        return intelligence
        
    def _build_search_queries(self, company_name: str) -> Dict[str, str]:
        """Build search queries based on configuration"""
        
        base_queries = {
            "basic_info": f'"{company_name}" company overview background',
            "business_model": f'"{company_name}" business model products services',
            "market_position": f'"{company_name}" market position industry standing',
            "leadership": f'"{company_name}" leadership team executives'
        }
        
        if self.company_config.include_financials:
            base_queries["financial_info"] = f'"{company_name}" revenue funding valuation'
            
        if self.company_config.include_subsidiaries:
            base_queries["subsidiaries"] = f'"{company_name}" subsidiaries acquisitions'
            
        return base_queries
        
    def _process_search_results(self, query_type: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Process search results for specific query type"""
        
        processed = {}
        
        for result in results.get("results", []):
            content = result.get("content", "")
            title = result.get("title", "")
            
            if query_type == "basic_info":
                processed["description"] = content[:500]
                processed["title"] = title
            elif query_type == "leadership":
                executives = self._extract_executives(content)
                processed["executives"] = executives
            elif query_type == "financial_info":
                financial_data = self._extract_financial_info(content)
                processed.update(financial_data)
                
        return processed
        
    def _extract_executives(self, content: str) -> List[Dict[str, Any]]:
        """Extract executive information from content"""
        # Implementation for executive extraction
        return []
        
    def _extract_financial_info(self, content: str) -> Dict[str, Any]:
        """Extract financial information from content"""
        # Implementation for financial data extraction
        return {}
        
    def _calculate_confidence(self, intelligence: Dict[str, Any]) -> float:
        """Calculate confidence score for gathered intelligence"""
        score = 0.0
        total_categories = len([k for k in intelligence.keys() if k not in ["data_sources", "confidence_score"]])
        
        for key, value in intelligence.items():
            if key in ["data_sources", "confidence_score"]:
                continue
                
            if value:
                score += 1.0
                
        return score / total_categories if total_categories > 0 else 0.0
        
    def get_supported_intelligence_types(self) -> List[str]:
        """Return supported intelligence types"""
        return ["company_overview", "business_model", "market_position", "leadership", "financial_info"]
        
    def validate_target(self, target: str) -> bool:
        """Validate company name target"""
        return bool(target and len(target.strip()) > 2)
        
    async def cleanup(self) -> bool:
        """Cleanup resources"""
        if self.tavily_service:
            await self.tavily_service.disconnect()
        return True
        
    def health_check(self) -> Dict[str, Any]:
        """Check component health"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "service_connected": bool(self.tavily_service),
            "last_check": "timestamp"
        }
