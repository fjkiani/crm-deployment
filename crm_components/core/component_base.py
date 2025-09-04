"""
Base Component Interface
All components inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

class Component(ABC):
    """Base component interface - 35 lines"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.logger = logging.getLogger(self.name)
        self.created_at = datetime.now()

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute component logic"""
        pass

    def validate_config(self) -> bool:
        """Validate component configuration"""
        required_keys = getattr(self, 'required_config_keys', [])
        for key in required_keys:
            if key not in self.config:
                self.logger.error(f"Missing required config: {key}")
                return False
        return True

    def get_metrics(self) -> Dict[str, Any]:
        """Get component performance metrics"""
        return {
            "component_name": self.name,
            "executions": getattr(self, '_execution_count', 0),
            "last_execution": getattr(self, '_last_execution', None),
            "success_rate": getattr(self, '_success_rate', 1.0)
        }

class IntelligenceComponent(Component):
    """Base intelligence gathering component"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.max_results = config.get('max_results', 5)
        self.required_config_keys = ['api_key']

class ProcessingComponent(Component):
    """Base data processing component"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.batch_size = config.get('batch_size', 100)

class OutreachComponent(Component):
    """Base outreach component"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.templates = config.get('templates', {})
        self.sender_info = config.get('sender_info', {})
