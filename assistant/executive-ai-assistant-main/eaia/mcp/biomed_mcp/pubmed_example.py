"""
PubMed Literature Analysis Example
Connects to Biomed MCP server and performs literature research
"""
import asyncio
import json
import os
from datetime import datetime
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from dotenv import load_dotenv

load_dotenv()


async def analyze_literature():
    """Connect to MCP server and perform literature analysis"""
    
    # Setup MCP client connection
    transport = StdioTransport(
        command="python",
        args=["-m", "biomed_agents"]
    )
    
    client = Client(transport)
    
    print("PubMed Literature Analysis Example")
    print("Connecting to Biomed MCP server...")
    
    async with client:
        try:
            # Analyze CRISPR gene editing literature
            print("\nAnalyzing CRISPR gene editing literature...")
            result = await client.call_tool(
                "biomedical_literature_search",
                {
                    "query": "CRISPR gene editing therapeutic applications",
                    "max_papers": 10,
                    "include_fulltext": True,
                    "synthesize_findings": True
                }
            )
            
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"example/crispr_gene_editing_literature_{timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write("CRISPR Gene Editing Literature Analysis\n")
                f.write("=" * 50 + "\n\n")
                f.write(result.data)
            
            print(f"Analysis saved to {output_file}")
            print("Literature analysis completed successfully!")
            
        except Exception as e:
            print(f"Error during literature analysis: {e}")


if __name__ == "__main__":
    print("Starting PubMed Literature Analysis Example...")
    asyncio.run(analyze_literature())