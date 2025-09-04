"""
Base Test Classes
Provides common testing utilities and fixtures
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any
from core.base.component import BaseComponent, ComponentConfig

class ComponentTestCase(unittest.IsolatedAsyncioTestCase):
    """Base test case for component testing"""
    
    def setUp(self):
        """Setup test environment"""
        self.mock_config = ComponentConfig(name="test_component")
        
    async def test_component_lifecycle(self):
        """Test component initialization, execution, and cleanup"""
        # This will be overridden by specific component tests
        pass
        
    def create_mock_component(self, component_class) -> BaseComponent:
        """Create a mock component for testing"""
        mock_component = Mock(spec=component_class)
        mock_component.initialize = AsyncMock(return_value=True)
        mock_component.execute = AsyncMock(return_value={})
        mock_component.cleanup = AsyncMock(return_value=True)
        mock_component.health_check = Mock(return_value={"status": "healthy"})
        return mock_component

class IntegrationTestCase(unittest.IsolatedAsyncioTestCase):
    """Base test case for integration testing"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.test_data = self._load_test_data()
        
    def _load_test_data(self) -> Dict[str, Any]:
        """Load test data fixtures"""
        return {
            "sample_company": "Test Company Inc",
            "sample_intelligence": {
                "company_name": "Test Company Inc",
                "basic_info": {"description": "Test description"}
            }
        }
