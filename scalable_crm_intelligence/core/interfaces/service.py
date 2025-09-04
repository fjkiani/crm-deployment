"""
Service Interface
Defines the contract for external services
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.base.component import BaseComponent, ComponentConfig

class ServiceConfig(ComponentConfig):
    """Configuration for service components"""
    endpoint: str = ""
    api_key: str = ""
    timeout: int = 30
    retry_policy: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.retry_policy is None:
            self.retry_policy = {"max_retries": 3, "backoff_factor": 1.0}

class ServiceComponent(BaseComponent):
    """Abstract base for external service components"""
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.service_config = config
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external service"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the external service"""
        pass
        
    @abstractmethod
    async def call_service(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a call to the external service"""
        pass
        
    @abstractmethod
    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the external service"""
        pass
