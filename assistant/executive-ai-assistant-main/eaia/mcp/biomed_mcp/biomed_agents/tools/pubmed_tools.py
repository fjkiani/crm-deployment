"""
PubMed tool wrappers for LangChain integration
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Import local PubMed clients
from .pubmed_client import PubMedClient
from .fulltext_client import FullTextClient


def get_pubmed_clients():
    """Initialize PubMed clients with environment configuration"""
    email = os.getenv("PUBMED_EMAIL")
    if not email:
        raise ValueError("PUBMED_EMAIL environment variable is required")
    
    tool_name = "biomed-mcp"
    api_key = os.getenv("PUBMED_API_KEY")
    
    pubmed_client = PubMedClient(email=email, tool=tool_name, api_key=api_key)
    fulltext_client = FullTextClient(email=email, tool=tool_name, api_key=api_key)
    
    return pubmed_client, fulltext_client


class PubMedSearchInput(BaseModel):
    """Input schema for PubMed search"""
    query: str = Field(description="Search query for PubMed articles")
    max_results: int = Field(default=10, description="Maximum number of results (1-50)")


class PubMedFullTextInput(BaseModel):
    """Input schema for PubMed full text retrieval"""
    pmid: str = Field(description="PubMed ID of the article")


@tool("search_pubmed_articles", args_schema=PubMedSearchInput)
async def search_pubmed_articles(query: str, max_results: int = 10) -> str:
    """
    Search PubMed for medical and life sciences research articles.
    
    Supports advanced search features:
    - Simple keyword search: "covid vaccine"
    - Field-specific search: "breast cancer"[Title]
    - Date ranges: "2020:2024[Date - Publication]"
    - Boolean operators: AND, OR, NOT
    
    Returns JSON with article metadata including titles, authors, abstracts, DOIs.
    """
    try:
        # Validate and constrain max_results
        max_results = min(max(1, max_results), 50)
        
        pubmed_client, _ = get_pubmed_clients()
        
        # Perform the search
        results = await pubmed_client.search_articles(
            query=query,
            max_results=max_results
        )
        
        # Format results for agent consumption
        if not results:
            return f"No articles found for query: {query}"
        
        formatted_results = []
        for article in results:
            formatted_article = {
                "pmid": article.get("pmid"),
                "title": article.get("title"),
                "authors": article.get("authors"),
                "journal": article.get("journal"),
                "publication_date": article.get("publication_date"),
                "abstract": article.get("abstract", "")[:500] + ("..." if len(article.get("abstract", "")) > 500 else ""),
                "doi": article.get("doi"),
                "keywords": article.get("keywords", [])
            }
            formatted_results.append(formatted_article)
        
        summary = f"Found {len(results)} articles for query '{query}':\n\n"
        for i, article in enumerate(formatted_results, 1):
            summary += f"{i}. {article['title']}\n"
            summary += f"   PMID: {article['pmid']}\n"
            summary += f"   Authors: {', '.join(article['authors'][:3])}{'...' if len(article['authors']) > 3 else ''}\n"
            summary += f"   Journal: {article['journal']}\n"
            if article['abstract']:
                summary += f"   Abstract: {article['abstract']}\n"
            summary += "\n"
        
        return summary
        
    except Exception as e:
        return f"Error searching PubMed: {str(e)}"


@tool("get_pubmed_fulltext", args_schema=PubMedFullTextInput)
async def get_pubmed_fulltext(pmid: str) -> str:
    """
    Retrieve full text of a PubMed article if available through PubMed Central.
    
    Returns the complete text if available, otherwise provides alternative access methods.
    """
    try:
        _, fulltext_client = get_pubmed_clients()
        pubmed_client, _ = get_pubmed_clients()
        
        # Check PMC availability
        available, pmc_id = await fulltext_client.check_full_text_availability(pmid)
        
        if available:
            full_text = await fulltext_client.get_full_text(pmid)
            if full_text:
                # Truncate very long texts
                if len(full_text) > 10000:
                    full_text = full_text[:10000] + "\n\n[Text truncated for length...]"
                return f"Full text for PMID {pmid}:\n\n{full_text}"
        
        # Get article details for alternative access
        article = await pubmed_client.get_article_details(pmid)
        
        message = f"Full text for PMID {pmid} is not available in PubMed Central.\n\n"
        message += "Alternative access methods:\n"
        message += f"- PubMed page: https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n"
        
        if article and "doi" in article:
            message += f"- Publisher's site: https://doi.org/{article['doi']}\n"
        
        # Include abstract if available
        if article and article.get("abstract"):
            message += f"\nAbstract:\n{article['abstract']}"
            
        return message
        
    except Exception as e:
        return f"Error retrieving full text for PMID {pmid}: {str(e)}"


# Export the tools for use in agents
PUBMED_TOOLS = [search_pubmed_articles, get_pubmed_fulltext]