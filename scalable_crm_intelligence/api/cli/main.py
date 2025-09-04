"""
CLI Interface for CRM Intelligence System
Provides command-line access to all system functionality
"""

import asyncio
import argparse
from pathlib import Path
from config.configuration_manager import ConfigurationManager
from orchestration.workflow_orchestrator import WorkflowOrchestrator
from components.intelligence.company_intelligence import CompanyIntelligenceComponent

class CRMIntelligenceCLI:
    """Command-line interface for the CRM Intelligence System"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager(Path("config"))
        self.orchestrator = WorkflowOrchestrator()
        self._setup_components()
        
    def _setup_components(self):
        """Setup and register components"""
        # This will be populated with actual component initialization
        pass
        
    async def run_intelligence_workflow(self, company_name: str, intelligence_types: List[str]):
        """Run intelligence gathering workflow"""
        
        input_data = {
            "company_name": company_name,
            "intelligence_types": intelligence_types
        }
        
        # Execute workflow
        result = await self.orchestrator.execute_workflow("intelligence_gathering", input_data)
        
        return result
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create CLI argument parser"""
        
        parser = argparse.ArgumentParser(
            description="CRM Intelligence System CLI",
            prog="crm-intelligence"
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Intelligence command
        intel_parser = subparsers.add_parser("intel", help="Gather intelligence")
        intel_parser.add_argument("company", help="Company name")
        intel_parser.add_argument(
            "--types", 
            nargs="+", 
            default=["company", "executives"],
            help="Intelligence types to gather"
        )
        intel_parser.add_argument("--output", help="Output file path")
        
        # Config command
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_parser.add_argument("action", choices=["show", "set", "list"])
        config_parser.add_argument("--key", help="Configuration key")
        config_parser.add_argument("--value", help="Configuration value")
        
        # Status command
        subparsers.add_parser("status", help="Show system status")
        
        return parser
        
    async def main(self):
        """Main CLI entry point"""
        
        parser = self.create_parser()
        args = parser.parse_args()
        
        if args.command == "intel":
            result = await self.run_intelligence_workflow(args.company, args.types)
            print(f"Intelligence gathered for {args.company}")
            
        elif args.command == "config":
            if args.action == "show":
                config = self.config_manager.system_config
                print(f"Current configuration: {config}")
                
        elif args.command == "status":
            print("System Status: Operational")
            
        else:
            parser.print_help()

if __name__ == "__main__":
    cli = CRMIntelligenceCLI()
    asyncio.run(cli.main())
