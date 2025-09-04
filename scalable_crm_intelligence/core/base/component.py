"""
Base Component Interface
All system components inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class ComponentConfig:
    """Base configuration for all components"""
    name: str
    enabled: bool = True
    log_level: str = "INFO"
    dependencies: list = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

class BaseComponent(ABC):
    """Abstract base class for all system components"""
    
    def __init__(self, config: ComponentConfig):
        self.config = config
        self.logger = self._setup_logger()
        self._initialized = False
        
    def _setup_logger(self) -> logging.Logger:
        """Setup component-specific logging"""
        logger = logging.getLogger(f"CRM.{self.config.name}")
        logger.setLevel(getattr(logging, self.config.log_level))
        return logger
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the component"""
        pass
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the component's main functionality"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup component resources"""
        pass
        
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check component health status"""
        pass
        
    def is_initialized(self) -> bool:
        """Check if component is initialized"""
        return self._initialized
