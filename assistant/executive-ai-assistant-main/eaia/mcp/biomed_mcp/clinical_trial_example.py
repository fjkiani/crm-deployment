"""
Clinical Trial Analysis Example
Connects to Biomed MCP server and performs clinical trial research
"""
import asyncio
import json
import os
from datetime import datetime
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from dotenv import load_dotenv

load_dotenv()


async def analyze_clinical_trials():
    """Connect to MCP server and perform clinical trial analysis"""
    
    # Setup MCP client connection
    transport = StdioTransport(
        command="python",
        args=["-m", "biomed_agents"]
    )
    
    client = Client(transport)
    
    print("Clinical Trial Analysis Example")
    print("Connecting to Biomed MCP server...")
    
    async with client:
        try:
            # Analyze COVID-19 vaccine trials
            print("\nAnalyzing COVID-19 vaccine trials...")
            result = await client.call_tool(
                "clinical_trials_research",
                {
                    "condition": "COVID-19 vaccine",
                    "study_phase": "Phase 3",
                    "max_studies": 10,
                    "analyze_trends": True
                }
            )
            
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"example/covid19_vaccine_trials_{timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write("COVID-19 Vaccine Clinical Trials Analysis\n")
                f.write("=" * 50 + "\n\n")
                f.write(result.data)
            
            print(f"Analysis saved to {output_file}")
            print("Clinical trial analysis completed successfully!")
            
        except Exception as e:
            print(f"Error during clinical trial analysis: {e}")


if __name__ == "__main__":
    print("Starting Clinical Trial Analysis Example...")
    asyncio.run(analyze_clinical_trials())