
import os
import asyncio
import shutil
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

# Import both stdio and SSE support
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

class MCPClientParams:
    def __init__(self, command: str = None, args: List[str] = None, env: Optional[Dict[str, str]] = None, 
                 transport: str = 'stdio', sse_url: str = None):
        self.command = command
        self.args = args or []
        self.env = env
        self.transport = transport
        self.sse_url = sse_url

class MCPManager:
    """
    Manages connections to MCP servers via stdio or SSE.
    """
    def __init__(self):
        pass

    @asynccontextmanager
    async def connect(self, params: MCPClientParams):
        """
        Connects to an MCP server and yields the session.
        """
        if params.transport == 'sse':
             async with sse_client(params.sse_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session
        
        else: # Default to stdio
            if not params.command or not shutil.which(params.command):
                 raise FileNotFoundError(f"Command not found: {params.command}")

            server_params = StdioServerParameters(
                command=params.command,
                args=params.args,
                env=params.env
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    def get_brightdata_params(self, api_key: str = None) -> MCPClientParams:
        """
        Returns parameters for BrightData MCP (SSE).
        """
        # User provided URL structure
        base_url = "https://mcp.brightdata.com/sse"
        
        # Tools list from user request
        tools = "web_data_linkedin_person_profile,web_data_linkedin_company_profile,web_data_linkedin_job_listings,web_data_linkedin_posts,web_data_linkedin_people_search,web_data_x_posts"
        
        # Construct full URL
        # Note: In a real app we might URL encode, but simple concatenation usually works for these tokens
        sse_url = f"{base_url}?token={api_key}&groups=advanced_scraping&tools={tools}"
        
        return MCPClientParams(
            transport='sse',
            sse_url=sse_url
        )

# Global instance
mcp_manager = MCPManager()
