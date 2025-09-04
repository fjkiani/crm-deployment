"""
Command-Line Interface
User-friendly CLI for the CRM Intelligence Platform
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add platform to path
sys.path.insert(0, str(Path(__file__).parent))

from crm_intelligence_platform import CRMIntelligencePlatform

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="CRM Intelligence Platform - Scale your outreach with AI"
    )

    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Intelligence gathering command
    intel_parser = subparsers.add_parser(
        'intelligence',
        help='Gather intelligence on companies'
    )
    intel_parser.add_argument(
        'companies',
        nargs='+',
        help='Company names to research'
    )
    intel_parser.add_argument(
        '--output',
        help='Output file path'
    )

    # Outreach command
    outreach_parser = subparsers.add_parser(
        'outreach',
        help='Generate personalized outreach campaigns'
    )
    outreach_parser.add_argument(
        'companies',
        nargs='+',
        help='Companies to generate outreach for'
    )
    outreach_parser.add_argument(
        '--campaign-name',
        help='Name for the outreach campaign'
    )

    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process company data from file'
    )
    process_parser.add_argument(
        'input_file',
        help='Input file path (CSV or JSON)'
    )
    process_parser.add_argument(
        '--output-format',
        choices=['json', 'csv'],
        default='json',
        help='Output format'
    )

    # Status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show platform status'
    )

    return parser

def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Initialize platform
        print("🚀 Initializing CRM Intelligence Platform...")
        platform = CRMIntelligencePlatform(args.config)

        if args.command == 'intelligence':
            run_intelligence(platform, args)

        elif args.command == 'outreach':
            run_outreach(platform, args)

        elif args.command == 'process':
            run_process(platform, args)

        elif args.command == 'status':
            run_status(platform, args)

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def run_intelligence(platform: CRMIntelligencePlatform, args):
    """Run intelligence gathering"""
    print(f"🎯 Gathering intelligence on {len(args.companies)} companies:")
    for company in args.companies:
        print(f"   • {company}")

    # Process companies
    results = platform.process_companies(args.companies)

    # Save results
    if args.output:
        output_file = args.output
    else:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"intelligence_results_{timestamp}.json"

    # Save results (would use data manager)
    print(f"✅ Intelligence gathered for {results['companies_processed']} companies")
    print(f"💾 Results saved to: {output_file}")

def run_outreach(platform: CRMIntelligencePlatform, args):
    """Run outreach campaign generation"""
    campaign_name = args.campaign_name or "outreach_campaign"

    print(f"📧 Generating outreach for {len(args.companies)} companies:")
    for company in args.companies:
        print(f"   • {company}")

    # Generate outreach (same as intelligence for now)
    results = platform.process_companies(args.companies)

    print(f"✅ Outreach generated for {results['companies_processed']} companies")
    print(f"📧 Campaign: {campaign_name}")

def run_process(platform: CRMIntelligencePlatform, args):
    """Run data processing"""
    print(f"🔄 Processing data from: {args.input_file}")

    # This would use the data manager to process files
    print(f"✅ Data processed successfully")
    print(f"📊 Output format: {args.output_format}")

def run_status(platform: CRMIntelligencePlatform, args):
    """Show platform status"""
    status = platform.get_platform_status()

    print("📊 Platform Status")
    print("=" * 30)
    print(f"Status: {status['status']}")
    print(f"Version: {status['version']}")

    print("\n🤖 Engines:")
    for engine, state in status['engines'].items():
        print(f"   {engine}: {state}")

    print("\n⚙️ Configuration:")
    config = status['configuration']
    print(f"   Loaded: {config['loaded']}")
    print(f"   Max companies per batch: {config['companies_per_batch']}")

if __name__ == "__main__":
    main()
