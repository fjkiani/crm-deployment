"""
Test client for Biomed MCP server
"""
import asyncio
import json
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from dotenv import load_dotenv

load_dotenv()


async def test_mcp_server():
    """Test the MCP server tools via client connection"""
    print("\n=== Testing MCP Server Tools ===")
    
    transport = StdioTransport(
        command="python",
        args=["-m", "biomed_agents"]
    )
    
    client = Client(transport)
    
    print("Starting MCP client connection...")
    async with client:
        try:
            # Test 1: List Available Tools
            print("\n--- Test 1: List Available Tools ---")
            tools = await client.list_tools()
            print("Available Tools:")
            for tool in tools:
                title = tool.annotations.title if tool.annotations else 'No title'
                print(f"  - {tool.name}: {title}")
            
            # Test 2: Biomedical Literature Search
            print("\n--- Test 2: Biomedical Literature Search ---")
            print("Searching for 'machine learning healthcare'...")
            
            search_result = await client.call_tool(
                "biomedical_literature_search",
                {
                    "query": "machine learning healthcare",
                    "max_papers": 3,
                    "include_fulltext": False,
                    "synthesize_findings": True
                }
            )
            
            print(f"Literature search completed ({len(search_result.data)} characters)")
            print(f"Preview: {search_result.data[:300]}...")
            
            # Test 3: Clinical Trials Research
            print("\n--- Test 3: Clinical Trials Research ---")
            print("Researching 'hypertension'...")
            
            trials_result = await client.call_tool(
                "clinical_trials_research",
                {
                    "condition": "hypertension",
                    "study_phase": "Phase 3",
                    "max_studies": 3,
                    "analyze_trends": True
                }
            )
            
            print(f"Clinical trials research completed ({len(trials_result.data)} characters)")
            print(f"Preview: {trials_result.data[:300]}...")
            
            # Test 4: Analyze Specific Clinical Trial
            print("\n--- Test 4: Analyze Specific Clinical Trial ---")
            print("Analyzing NCT04280705...")
            
            trial_analysis = await client.call_tool(
                "analyze_clinical_trial",
                {"nct_id": "NCT04280705"}
            )
            
            print(f"Trial analysis completed ({len(trial_analysis.data)} characters)")
            print(f"Preview: {trial_analysis.data[:300]}...")
            
            # Test 5: Analyze Research Paper
            print("\n--- Test 5: Analyze Research Paper ---")
            print("Analyzing PMID 39661433...")
            
            paper_analysis = await client.call_tool(
                "analyze_research_paper",
                {"pmid": "39661433"}
            )
            
            print(f"Paper analysis completed ({len(paper_analysis.data)} characters)")
            print(f"Preview: {paper_analysis.data[:300]}...")
            
            # Test 6: Health Check Resource
            print("\n--- Test 6: Health Check Resource ---")
            health_result = await client.read_resource("biomed://health_check")
            print(f"Health check: {health_result[0].text}")
            
        except Exception as e:
            print(f"MCP server test failed: {e}")


async def main():
    """Main test execution"""
    try:
        await test_mcp_server()
        print("\n=== All Tests Completed ===")
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())