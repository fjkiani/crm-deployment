
import os
import asyncio
from typing import Dict, Any, List, Optional
from langchain.tools import tool
from eaia.mcp_client import mcp_manager

@tool
def brightdata_web_search(query: str) -> str:
    """
    Performs a web search using Bright Data's infrastructure.
    Useful for getting real-time information from the web with high reliability.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We are in an event loop, but the tool is synchronous.
        # This is tricky without nest_asyncio or proper refactoring.
        # For this specific case (tool calling tool), we should ideally await.
        # BUT LangChain tools are often synchronous interfaces.
        # HACK: If we are in a loop, we can't use asyncio.run.
        # We should use nest_asyncio if available or raise error?
        # Better: let's try to just return a coroutine if we could, but type signature is str.
        
        # PROPER FIX: Check if nest_asyncio is applied, or apply it.
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(_async_search(query))
    else:
        return asyncio.run(_async_search(query))

@tool
def brightdata_extract(url: str, prompt: str) -> str:
    """
    Extracts structured data from a specific URL using Bright Data and an extraction prompt.
    Useful for scraping specific meaning or fields from a page.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(_async_extract(url, prompt))
    else:
        return asyncio.run(_async_extract(url, prompt))

async def _async_search(query: str) -> str:
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        return "Error: BRIGHTDATA_API_KEY not found in environment."

    params = mcp_manager.get_brightdata_params(api_key)
    
    try:
        async with mcp_manager.connect(params) as session:
            # List tools to find the right one.
            # BrightData MCP likely exposes 'search' or similar.
            # For now, we assume a 'search' tool exists based on standard MCP patterns.
            # In a real scenario, we might want to list tools first.
            
            # Listing tools for robustness (optional optimization: cache this)
            tools = await session.list_tools()
            search_tool = next((t for t in tools.tools if "search" in t.name), None)
            
            if not search_tool:
                tools_names = [t.name for t in tools.tools]
                return f"Error: Could not find a search tool in BrightData MCP. Available tools: {tools_names}"
            
            # Call the tool
            result = await session.call_tool(search_tool.name, arguments={"query": query})
            
            # Result is a CallToolResult object
            # We explicitly convert the content to string
            return "\n".join([c.text for c in result.content if c.type == "text"])
            
    except Exception as e:
        return f"Error executing BrightData search: {str(e)}"

async def _async_extract(url: str, prompt: str) -> str:
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        return "Error: BRIGHTDATA_API_KEY not found in environment."

    params = mcp_manager.get_brightdata_params(api_key)
    
    try:
        async with mcp_manager.connect(params) as session:
            # Look for extraction tool, often named 'extract' or similar
            tools = await session.list_tools()
            # We look for something that takes a URL
            # Common names: 'extract', 'scrape', 'navigate'
            # Let's try to find a relevant tool
            extract_tool = next((t for t in tools.tools if "extract" in t.name or "scrape" in t.name), None)
            
            if not extract_tool:
                # Fallback: maybe 'fetch' or 'browser'
                extract_tool = next((t for t in tools.tools if "fetch" in t.name), None)
            
            if not extract_tool:
                 tools_names = [t.name for t in tools.tools]
                 return f"Error: Could not find an extraction tool. Available tools: {tools_names}"

            # Prepare args - this depends on the specific tool schema
            # We'll try common arguments
            args = {"url": url, "prompt": prompt} # specialized for extraction
            
            result = await session.call_tool(extract_tool.name, arguments=args)
            return "\n".join([c.text for c in result.content if c.type == "text"])

    except Exception as e:
        return f"Error executing BrightData extraction: {str(e)}"
