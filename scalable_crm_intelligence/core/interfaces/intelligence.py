"""
Intelligence Component Interface
Defines the contract for all intelligence gathering components
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.base.component import BaseComponent, ComponentConfig

class IntelligenceConfig(ComponentConfig):
    """Configuration for intelligence components"""
    api_key: str = ""
    rate_limit: float = 1.0
    max_retries: int = 3
    timeout: int = 30

class IntelligenceComponent(BaseComponent):
    """Abstract base for intelligence gathering components"""
    
    def __init__(self, config: IntelligenceConfig):
        super().__init__(config)
        self.intelligence_config = config
        
    @abstractmethod
    async def gather_intelligence(self, target: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather intelligence for a specific target"""
        pass
        
    @abstractmethod
    def get_supported_intelligence_types(self) -> List[str]:
        """Return list of intelligence types this component supports"""
        pass
        
    @abstractmethod
    def validate_target(self, target: str) -> bool:
        """Validate if target is suitable for this intelligence component"""
        pass
