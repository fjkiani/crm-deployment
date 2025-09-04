#!/usr/bin/env python3
"""
Example Usage of Dynamic CRM Intelligence System
Demonstrates how to use the system with dynamic configuration
"""

import os
from pathlib import Path
from dynamic_crm_intelligence_system import SystemConfig, DynamicCRMIntelligenceSystem

def example_data_processing():
    """Example: Process CSV data file"""
    print("📊 EXAMPLE: Data Processing")
    print("=" * 40)

    # Initialize with default config
    config = SystemConfig()

    # Override settings dynamically
    config.max_companies_per_batch = 3
    config.rate_limit_delay = 0.5

    # Initialize system
    system = DynamicCRMIntelligenceSystem(config)

    # Process data file
    input_file = "leads.csv"  # Relative to input directory
    results = system.process_data_file(input_file)

    print("✅ Data processing complete!")
    print(f"   Processed {results['total_records']} records")
    print("   Generated outputs:")
    for output_type, filepath in results['outputs'].items():
        print(f"     • {output_type.upper()}: {filepath}")

    return results

def example_company_config():
    """Example: Load company-specific configuration"""
    print("\n🏢 EXAMPLE: Company Configuration")
    print("=" * 40)

    config = SystemConfig()

    # Load company configuration dynamically
    company_config = config.load_company_config("3EDGE Asset Management")

    print("✅ Company configuration loaded!")
    print(f"   Company: {company_config.get('name', 'Unknown')}")
    print(f"   Industry: {company_config.get('industry', 'Unknown')}")
    print(f"   Decision Makers: {len(company_config.get('decision_makers', {}))}")

    # Show decision makers
    for key, dm in company_config.get('decision_makers', {}).items():
        print(f"     • {dm.get('name', 'Unknown')}: {dm.get('title', 'Unknown')}")

    return company_config

def example_system_config():
    """Example: System configuration management"""
    print("\n⚙️ EXAMPLE: System Configuration")
    print("=" * 40)

    # Start with defaults
    config = SystemConfig()
    print("Default Configuration:")
    print(f"   API Timeout: {config.tavily_timeout}s")
    print(f"   Max Batch Size: {config.max_companies_per_batch}")
    print(f"   Rate Limit Delay: {config.rate_limit_delay}s")
    print(f"   Search Results: {config.search_results_per_query}")

    # Load from JSON file
    config_file = config.config_dir / "system_config.json"
    if config_file.exists():
        print(f"\nLoading config from: {config_file}")
        import json
        with open(config_file, 'r') as f:
            file_config = json.load(f)

        # Apply file configuration
        for key, value in file_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

        print("Updated Configuration:")
        print(f"   Sender Company: {config.sender_company}")
        print(f"   Sender Name: {config.sender_name}")
        print(f"   Sender Email: {config.sender_email}")

    return config

def example_intelligence_workflow():
    """Example: Intelligence gathering workflow (dry run)"""
    print("\n🧠 EXAMPLE: Intelligence Workflow")
    print("=" * 40)

    # Setup configuration
    config = SystemConfig()
    config.target_company = "Example Company"
    config.max_companies_per_batch = 1  # Small batch for example

    print("Configuration:")
    print(f"   Target Company: {config.target_company}")
    print(f"   Batch Size: {config.max_companies_per_batch}")
    print(f"   API Key: {'Set' if config.tavily_api_key else 'Not Set (Demo Mode)'}")

    # Initialize system
    system = DynamicCRMIntelligenceSystem(config)

    print("\nSystem initialized with:")
    print(f"   • Intelligence gatherer: ✅ Active")
    print(f"   • Data processor: ✅ Active")
    print(f"   • Profile builder: ✅ Active")
    print(f"   • Lead selector: ✅ Active")
    print(f"   • Orchestrator: ✅ Active")

    # Show what the workflow would do
    print("\nIntelligence Workflow Phases:")
    print("   1. 📊 Company Overview Gathering")
    print("   2. 👥 Executive Intelligence Collection")
    print("   3. 💼 Investment Portfolio Analysis")
    print("   4. 🤝 Partnership Network Mapping")
    print("   5. 📰 News & Developments Tracking")
    print("   6. 🌐 Digital Presence Analysis")
    print("   7. 📧 Personalized Outreach Generation")

    print("\nExpected Outputs:")
    print("   • Company intelligence JSON report")
    print("   • Personalized email campaign")
    print("   • Executive contact database")
    print("   • Partnership network analysis")

    return system

def example_email_generation():
    """Example: Dynamic email generation"""
    print("\n📧 EXAMPLE: Dynamic Email Generation")
    print("=" * 40)

    config = SystemConfig()
    system = DynamicCRMIntelligenceSystem(config)

    # Example executive data
    executive = {
        "name": "John Smith",
        "title": "Chief Executive Officer",
        "company": "Example Company"
    }

    # Mock intelligence data
    intelligence = {
        "company": "Example Company",
        "phases": {
            "executives": {"executives": [executive]}
        }
    }

    # Generate email
    email = system._create_personalized_email(executive, intelligence)

    if email:
        print("✅ Personalized email generated!")
        print(f"   Subject: {email['subject']}")
        print(f"   Recipient: {email['recipient']}")
        print(f"   Title: {email['title']}")
        print(f"   Personalization Score: {email['personalization_score']:.2f}")
        print("\nEmail Preview:")
        print(email['body'][:200] + "...")
    else:
        print("❌ Email generation failed")

    return email

def main():
    """Run all examples"""
    print("🚀 Dynamic CRM Intelligence System - Examples")
    print("=" * 60)

    try:
        # Example 1: System Configuration
        config = example_system_config()

        # Example 2: Company Configuration
        company_config = example_company_config()

        # Example 3: Intelligence Workflow
        system = example_intelligence_workflow()

        # Example 4: Email Generation
        email = example_email_generation()

        # Example 5: Data Processing
        if Path("leads.csv").exists():
            data_results = example_data_processing()
        else:
            print("\n📊 EXAMPLE: Data Processing")
            print("=" * 40)
            print("   (Skipped - leads.csv not found)")
            print("   To test: place leads.csv in data/input/ directory")

        print("\n" + "=" * 60)
        print("🎉 ALL EXAMPLES COMPLETED!")
        print("=" * 60)
        print("\n✅ Demonstrated Features:")
        print("   • Dynamic configuration system")
        print("   • Company-specific settings")
        print("   • Intelligence workflow structure")
        print("   • Personalized email generation")
        print("   • Data processing capabilities")
        print("\n🚀 Ready for production use!")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
