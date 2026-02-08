import os
import requests
from typing import List, Dict, Any
from langchain_core.tools import tool

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def _tavily_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Executes a search using Tavily API."""
    if not TAVILY_API_KEY:
        return [{"url": "#", "content": "Error: TAVILY_API_KEY not set in .env. Cannot search."}]
        
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Format results nicely
        results = []
        if data.get("answer"):
            results.append({"url": "tavily_answer", "content": data["answer"]})
            
        for res in data.get("results", []):
            results.append({
                "url": res.get("url"),
                "content": res.get("content")
            })
        return results
    except Exception as e:
        return [{"url": "#", "content": f"Search API Error: {str(e)}"}]

@tool
def research_company(company_name: str):
    """
    Research a company to find AUM, Investment Focus, and Partners.
    Useful for enriching Family Office leads.
    """
    query = f"{company_name} family office investment focus AUM partners portfolio"
    results = _tavily_search(query)
    
    # Format as a string for the LLM
    output = f"Research Results for '{company_name}':\n"
    for r in results:
        output += f"- [{r['url']}]\n  {r['content'][:500]}...\n\n"
    return output

@tool
def web_search(query: str):
    """
    General purpose web search. Use this to find information not known effectively.
    """
    results = _tavily_search(query)
    output = f"Search Results for '{query}':\n"
    for r in results:
        output += f"- [{r['url']}]\n  {r['content'][:500]}...\n\n"
    return output
