"""
Component Tests
Tests for individual intelligence components
"""

from tests.base_test import ComponentTestCase
from components.intelligence.company_intelligence import CompanyIntelligenceComponent, CompanyIntelligenceConfig

class TestCompanyIntelligenceComponent(ComponentTestCase):
    """Test cases for Company Intelligence Component"""
    
    def setUp(self):
        """Setup component test"""
        super().setUp()
        self.config = CompanyIntelligenceConfig(
            name="company_intelligence",
            api_key="test_key"
        )
        self.component = CompanyIntelligenceComponent(self.config)
        
    async def test_initialization(self):
        """Test component initialization"""
        # Mock external dependencies
        self.component.tavily_service = self.create_mock_external_service()
        
        result = await self.component.initialize()
        self.assertTrue(result)
        self.assertTrue(self.component.is_initialized())
        
    async def test_intelligence_gathering(self):
        """Test intelligence gathering functionality"""
        # Setup mocks
        self.component.tavily_service = self.create_mock_external_service()
        await self.component.initialize()
        
        # Test data
        test_company = "Test Company"
        test_context = {"priority": "high"}
        
        # Execute
        result = await self.component.gather_intelligence(test_company, test_context)
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result["company_name"], test_company)
        self.assertIn("basic_info", result)
        self.assertGreaterEqual(result["confidence_score"], 0.0)
        
    def create_mock_external_service(self):
        """Create mock external service"""
        mock_service = Mock()
        mock_service.connect = AsyncMock(return_value=True)
        mock_service.search = AsyncMock(return_value={
            "results": [
                {
                    "title": "Test Company Overview",
                    "content": "Test company description",
                    "url": "https://example.com"
                }
            ]
        })
        return mock_service
