"""
Intelligence Runner
Simple script that uses the modular components to run intelligence gathering
Replicates the functionality of the original large script but using clean components
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

from .intelligence_orchestrator import IntelligenceOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/data/output/intelligence_runner.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main intelligence gathering process using modular components"""

    print("🧠 MODULAR INTELLIGENCE RUNNER")
    print("=" * 50)
    print("Using clean, focused components instead of monolithic code")
    print()

    # Check API key
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    if not tavily_api_key:
        print("❌ TAVILY_API_KEY environment variable not set")
        print("Please set: export TAVILY_API_KEY='your_key_here'")
        return

    # Configuration
    config = {
        "tavily_api_key": tavily_api_key,
        "max_results": 5,
        "timeout": 30
    }

    # Initialize orchestrator
    print("🚀 Initializing Intelligence Orchestrator...")
    orchestrator = IntelligenceOrchestrator(config)

    # Select and process leads
    leads_file = "/Users/fahadkiani/Desktop/development/crm-deployment/scripts/data/output/organized_leads.json"

    print("🎯 Selecting high-value leads...")
    profiles = orchestrator.select_and_process_leads(leads_file, limit=3)  # Start with 3 for testing

    if not profiles:
        print("❌ No profiles generated")
        return

    # Generate comprehensive report
    print(f"\n📊 Generating intelligence report for {len(profiles)} companies...")

    final_report = {
        "metadata": {
            "report_generated": datetime.now().isoformat(),
            "intelligence_runner_version": "1.0",
            "total_profiles": len(profiles),
            "processing_method": "modular_components",
            "tavily_api_used": True
        },
        "intelligence_profiles": profiles,
        "processing_summary": generate_processing_summary(profiles)
    }

    # Save report
    output_file = "/Users/fahadkiani/Desktop/development/crm-deployment/scripts/data/output/modular_intelligence_report.json"

    with open(output_file, 'w') as f:
        json.dump(final_report, f, indent=2, default=str)

    # Print results
    print("\n" + "=" * 80)
    print("🎉 MODULAR INTELLIGENCE GATHERING COMPLETE!")
    print("=" * 80)
    print(f"\n📁 Generated File: {output_file}")
    print()

    # Print summary
    print("🎯 INTELLIGENCE SUMMARY:")
    for i, profile in enumerate(profiles, 1):
        company_name = profile["company_name"]
        confidence = profile["confidence_metrics"]["overall_confidence"]
        data_sources = len(profile["data_sources"])
        categories = len(profile["intelligence_categories"])

        print(f"   {i}. {company_name}")
        print(".2f"        print(".2f"        print()

    print("🔥 Your modular intelligence profiles are ready!")
    print("   Benefits of this approach:")
    print("   • Clean, maintainable code")
    print("   • Each component has a single responsibility")
    print("   • Easy to test and modify individual pieces")
    print("   • No more 1100-line monolithic files!")

def generate_processing_summary(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary of the processing results"""

    if not profiles:
        return {"error": "No profiles to summarize"}

    summary = {
        "total_companies": len(profiles),
        "average_confidence": sum(p["confidence_metrics"]["overall_confidence"] for p in profiles) / len(profiles),
        "total_data_sources": sum(len(p["data_sources"]) for p in profiles),
        "intelligence_categories_covered": {},
        "top_performers": []
    }

    # Analyze intelligence categories coverage
    all_categories = set()
    for profile in profiles:
        categories = profile.get("intelligence_categories", {})
        all_categories.update(categories.keys())

    for category in all_categories:
        coverage_count = sum(1 for p in profiles
                           if p.get("intelligence_categories", {}).get(category, {}).get("confidence_score", 0) > 0)
        summary["intelligence_categories_covered"][category] = {
            "profiles_with_data": coverage_count,
            "coverage_percentage": coverage_count / len(profiles)
        }

    # Find top performers
    sorted_profiles = sorted(profiles,
                           key=lambda p: p["confidence_metrics"]["overall_confidence"],
                           reverse=True)
    summary["top_performers"] = [
        {
            "company": p["company_name"],
            "confidence": p["confidence_metrics"]["overall_confidence"],
            "data_sources": len(p["data_sources"])
        }
        for p in sorted_profiles[:3]  # Top 3
    ]

    return summary

if __name__ == "__main__":
    main()
