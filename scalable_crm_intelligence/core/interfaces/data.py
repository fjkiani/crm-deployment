"""
Data Component Interface
Defines the contract for all data processing components
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from core.base.component import BaseComponent, ComponentConfig

class DataConfig(ComponentConfig):
    """Configuration for data components"""
    input_format: str = "json"
    output_format: str = "json"
    validation_enabled: bool = True
    transformation_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.transformation_rules is None:
            self.transformation_rules = {}

class DataComponent(BaseComponent):
    """Abstract base for data processing components"""
    
    def __init__(self, config: DataConfig):
        super().__init__(config)
        self.data_config = config
        
    @abstractmethod
    async def process_data(self, data: Any) -> Any:
        """Process input data and return transformed data"""
        pass
        
    @abstractmethod
    async def validate_data(self, data: Any) -> bool:
        """Validate input data format and content"""
        pass
        
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the expected data schema"""
        pass
