"""
Tavily Service Implementation
External service component for Tavily API integration
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from core.interfaces.service import ServiceComponent, ServiceConfig

class TavilyServiceConfig(ServiceConfig):
    """Configuration for Tavily service"""
    endpoint: str = "https://api.tavily.com/search"
    search_depth: str = "basic"  # basic, advanced
    include_raw_content: bool = True
    include_answer: bool = True
    max_results: int = 5

class TavilyService(ServiceComponent):
    """Tavily API service integration"""
    
    def __init__(self, config: TavilyServiceConfig):
        super().__init__(config)
        self.tavily_config = config
        self.session = None
        
    async def initialize(self) -> bool:
        """Initialize the Tavily service"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.service_config.timeout)
            )
            self._initialized = True
            self.logger.info("Tavily service initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Tavily service: {e}")
            return False
            
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Tavily search"""
        query = input_data.get("query", "")
        search_type = input_data.get("search_type", "general")
        max_results = input_data.get("max_results", self.tavily_config.max_results)
        
        return await self.search(query, search_type, max_results)
        
    async def connect(self) -> bool:
        """Establish connection to Tavily API"""
        return await self.initialize()
        
    async def disconnect(self) -> bool:
        """Disconnect from Tavily API"""
        if self.session:
            await self.session.close()
            self.session = None
        return True
        
    async def call_service(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a call to Tavily service"""
        if method == "search":
            return await self.search(
                params.get("query", ""),
                params.get("search_type", "general"),
                params.get("max_results", 5)
            )
        else:
            raise ValueError(f"Unsupported method: {method}")
            
    async def search(self, query: str, search_type: str = "general", max_results: int = 5) -> Dict[str, Any]:
        """Perform Tavily search"""
        
        if not self.service_config.api_key:
            raise ValueError("Tavily API key not configured")
            
        if not self.session:
            await self.initialize()
            
        payload = {
            "api_key": self.service_config.api_key,
            "query": query,
            "search_depth": self.tavily_config.search_depth,
            "include_raw_content": self.tavily_config.include_raw_content,
            "include_answer": self.tavily_config.include_answer,
            "max_results": max_results
        }
        
        if search_type != "general":
            payload["search_type"] = search_type
            
        try:
            async with self.session.post(
                self.service_config.endpoint,
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.logger.debug(f"Tavily search successful for query: {query}")
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error(f"Tavily API error {response.status}: {error_text}")
                    return {"results": [], "error": f"API error {response.status}"}
                    
        except asyncio.TimeoutError:
            self.logger.error(f"Tavily search timeout for query: {query}")
            return {"results": [], "error": "Timeout"}
        except Exception as e:
            self.logger.error(f"Tavily search failed for query '{query}': {e}")
            return {"results": [], "error": str(e)}
            
    def get_service_status(self) -> Dict[str, Any]:
        """Get Tavily service status"""
        return {
            "service": "tavily",
            "status": "connected" if self.session else "disconnected",
            "endpoint": self.service_config.endpoint,
            "api_key_configured": bool(self.service_config.api_key),
            "timeout": self.service_config.timeout
        }
        
    async def cleanup(self) -> bool:
        """Cleanup service resources"""
        return await self.disconnect()
        
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "session_active": bool(self.session),
            "api_key_set": bool(self.service_config.api_key)
        }
