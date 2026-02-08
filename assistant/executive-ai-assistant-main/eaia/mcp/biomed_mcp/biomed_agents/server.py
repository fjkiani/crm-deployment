"""
Biomed MCP Server - Main server exposing ReAct agents as MCP tools
"""
import os
import asyncio
import logging
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables FIRST, before any imports that might need them
load_dotenv()

from .pubmed_agent import PubMedAgent
from .clinical_agent import ClinicalTrialsAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("biomed-mcp-server")

# Initialize FastMCP app
app = FastMCP("biomed-mcp-server")

# Global agent instances (initialized lazily)
_pubmed_agent: Optional[PubMedAgent] = None
_clinical_agent: Optional[ClinicalTrialsAgent] = None


def get_pubmed_agent() -> PubMedAgent:
    """Get or create PubMed agent instance"""
    global _pubmed_agent
    if _pubmed_agent is None:
        logger.info("Initializing PubMed ReAct agent...")
        _pubmed_agent = PubMedAgent()
    return _pubmed_agent


def get_clinical_agent() -> ClinicalTrialsAgent:
    """Get or create Clinical Trials agent instance"""
    global _clinical_agent
    if _clinical_agent is None:
        logger.info("Initializing Clinical Trials ReAct agent...")
        _clinical_agent = ClinicalTrialsAgent()
    return _clinical_agent


@app.tool(
    annotations={
        "title": "Intelligent biomedical literature search and analysis",
        "description": "Advanced literature research using AI agent that can search PubMed, retrieve full-text papers, and provide comprehensive analysis",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
async def biomedical_literature_search(
    query: str,
    max_papers: int = 10,
    include_fulltext: bool = False,
    synthesize_findings: bool = True
) -> str:
    """
    Intelligent biomedical literature search with AI-powered analysis.
    
    This tool uses a ReAct agent that can:
    - Search PubMed database for relevant articles
    - Retrieve full-text content when available
    - Analyze and synthesize findings across multiple papers
    - Provide comprehensive research summaries
    
    Args:
        query: Research question or topic to investigate
        max_papers: Maximum number of papers to analyze (1-20)
        include_fulltext: Whether to attempt full-text retrieval for key papers
        synthesize_findings: Whether to provide synthesized analysis across papers
        
    Returns:
        Comprehensive literature analysis with key insights and citations
    """
    try:
        # Validate parameters
        max_papers = min(max(1, max_papers), 20)
        
        logger.info(f"Starting literature search for: {query}")
        
        # Get the PubMed agent
        agent = get_pubmed_agent()
        
        # Generate unique thread ID for this search
        thread_id = f"lit_search_{hash(query) % 100000}"
        
        # Perform the research
        result = await agent.search_literature(
            query=query,
            thread_id=thread_id,
            max_papers=max_papers,
            include_fulltext=include_fulltext
        )
        
        logger.info(f"Literature search completed for: {query}")
        return result
        
    except Exception as e:
        logger.exception(f"Error in biomedical literature search")
        return f"Error performing literature search: {str(e)}"


@app.tool(
    annotations={
        "title": "Intelligent clinical trials research and analysis",
        "description": "Advanced clinical trials research using AI agent that can search ClinicalTrials.gov, analyze patterns, and provide comprehensive insights",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
async def clinical_trials_research(
    condition: str,
    study_phase: Optional[str] = None,
    max_studies: int = 15,
    analyze_trends: bool = True
) -> str:
    """
    Intelligent clinical trials research with AI-powered analysis.
    
    This tool uses a ReAct agent that can:
    - Search ClinicalTrials.gov for relevant studies
    - Analyze trial patterns and trends
    - Provide detailed trial summaries and insights
    - Compare different interventions and approaches
    
    Args:
        condition: Medical condition or intervention to research
        study_phase: Optional filter for study phase (e.g., "Phase 2", "Phase 3")
        max_studies: Maximum number of studies to analyze (1-25)
        analyze_trends: Whether to perform pattern analysis across trials
        
    Returns:
        Comprehensive clinical trials analysis with insights and NCT IDs
    """
    try:
        # Validate parameters
        max_studies = min(max(1, max_studies), 25)
        
        # Modify search if phase is specified
        search_condition = condition
        if study_phase:
            search_condition = f"{condition} AND {study_phase}"
        
        logger.info(f"Starting clinical trials research for: {search_condition}")
        
        # Get the Clinical Trials agent
        agent = get_clinical_agent()
        
        # Generate unique thread ID for this search
        thread_id = f"ct_research_{hash(search_condition) % 100000}"
        
        # Perform the research
        result = await agent.research_condition(
            condition=search_condition,
            thread_id=thread_id,
            max_studies=max_studies,
            analyze_patterns=analyze_trends
        )
        
        logger.info(f"Clinical trials research completed for: {search_condition}")
        return result
        
    except Exception as e:
        logger.exception(f"Error in clinical trials research")
        return f"Error performing clinical trials research: {str(e)}"


@app.tool(
    annotations={
        "title": "Analyze specific clinical trial by NCT ID",
        "description": "Detailed analysis of a specific clinical trial using its NCT identifier",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
async def analyze_clinical_trial(nct_id: str) -> str:
    """
    Analyze a specific clinical trial in detail using its NCT ID.
    
    Args:
        nct_id: NCT identifier of the trial (e.g., NCT04280705)
        
    Returns:
        Detailed analysis of the trial including design, outcomes, and insights
    """
    try:
        logger.info(f"Analyzing clinical trial: {nct_id}")
        
        # Get the Clinical Trials agent
        agent = get_clinical_agent()
        
        # Generate thread ID for this analysis
        thread_id = f"ct_analysis_{nct_id}"
        
        # Perform the analysis
        result = await agent.analyze_trial_details(
            nct_id=nct_id,
            thread_id=thread_id
        )
        
        logger.info(f"Clinical trial analysis completed for: {nct_id}")
        return result
        
    except Exception as e:
        logger.exception(f"Error analyzing clinical trial {nct_id}")
        return f"Error analyzing clinical trial {nct_id}: {str(e)}"


@app.tool(
    annotations={
        "title": "Analyze specific paper by PMID",
        "description": "Detailed analysis of a specific research paper using its PubMed ID",
        "readOnlyHint": True,
        "openWorldHint": True
    }
)
async def analyze_research_paper(pmid: str) -> str:
    """
    Analyze a specific research paper in detail using its PMID.
    
    Args:
        pmid: PubMed ID of the paper
        
    Returns:
        Detailed analysis of the paper including methodology, findings, and insights
    """
    try:
        logger.info(f"Analyzing research paper: {pmid}")
        
        # Get the PubMed agent
        agent = get_pubmed_agent()
        
        # Generate thread ID for this analysis
        thread_id = f"paper_analysis_{pmid}"
        
        # Perform the analysis
        result = await agent.get_paper_insights(
            pmid=pmid,
            thread_id=thread_id
        )
        
        logger.info(f"Paper analysis completed for: {pmid}")
        return result
        
    except Exception as e:
        logger.exception(f"Error analyzing paper {pmid}")
        return f"Error analyzing research paper {pmid}: {str(e)}"


@app.resource("biomed://health_check")
def health_check() -> str:
    """Health check endpoint for the Biomed MCP server"""
    try:
        # Check environment variables
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY", 
            "PUBMED_EMAIL"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            return f"Missing required environment variables: {', '.join(missing_vars)}"
        
        return "Biomed MCP server is healthy and ready"
        
    except Exception as e:
        return f"Health check failed: {str(e)}"


def main():
    """Run the Biomed MCP server"""
    logger.info("Starting Biomed MCP server...")
    app.run()

if __name__ == "__main__":
    main()