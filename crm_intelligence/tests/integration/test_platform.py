"""
Integration Tests
Test the complete platform workflow
"""

import pytest
from crm_intelligence_platform import CRMIntelligencePlatform

class TestCRMIntelligencePlatform:
    """Test the complete platform"""

    def test_intelligence_gathering(self):
        """Test intelligence gathering workflow"""
        platform = CRMIntelligencePlatform()

        # Test with our 3EDGE success case
        companies = ["3EDGE Asset Management"]
        results = platform.process_companies(companies)

        assert results["companies_processed"] == 1
        assert len(results["intelligence_gathered"]) == 1
        assert len(results["outreach_generated"]) == 1

    def test_multiple_companies(self):
        """Test processing multiple companies"""
        platform = CRMIntelligencePlatform()

        companies = ["3EDGE Asset Management", "Sequoia Capital"]
        results = platform.process_companies(companies)

        assert results["companies_processed"] == 2
        assert len(results["intelligence_gathered"]) == 2

    def test_platform_status(self):
        """Test platform status reporting"""
        platform = CRMIntelligencePlatform()

        status = platform.get_platform_status()

        assert status["status"] == "operational"
        assert "engines" in status
        assert "configuration" in status

# Quick test runner
def run_integration_tests():
    """Run integration tests"""
    print("🧪 Running Integration Tests...")
    print("=" * 40)

    platform = CRMIntelligencePlatform()

    # Test 1: Single company processing
    print("Test 1: Single company processing")
    results = platform.process_companies(["3EDGE Asset Management"])
    assert results["companies_processed"] == 1
    print("✅ PASSED")

    # Test 2: Platform status
    print("Test 2: Platform status")
    status = platform.get_platform_status()
    assert status["status"] == "operational"
    print("✅ PASSED")

    print("\n🎉 All integration tests passed!")
    print("=" * 40)

if __name__ == "__main__":
    run_integration_tests()
