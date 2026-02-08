"""
Research Orchestrator - Unified interface for intelligent biomedical research

This is the core product that enables agents to perform intelligent research
across multiple data sources with synthesis and structured extraction.
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# BioMed-MCP Import
try:
    from eaia.mcp.biomed_mcp.biomed_agents import PubMedAgent, ClinicalTrialsAgent
except ImportError as e:
    raise ImportError(f"BioMed-MCP agents not found. Error: {e}")

from .models import ResearchResult, AgentResult, MultiSourceResult, Synthesis, StructuredData


class ResearchOrchestrator:
    """
    Unified research framework orchestrator
    
    Provides a single interface for intelligent biomedical research across
    multiple data sources with synthesis and structured extraction.
    """
    
    # Agent type mapping
    AGENT_MAP = {
        'pubmed': PubMedAgent,
        'clinical_trials': ClinicalTrialsAgent,
        'clinicaltrials': ClinicalTrialsAgent,  # Alias
    }
    
    def __init__(self):
        """Initialize the research orchestrator"""
        self._agents: Dict[str, Any] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize available research agents"""
        # Lazy initialization - agents created on first use
        # This avoids expensive initialization if not needed
        pass
    
    def _get_agent(self, agent_type: str):
        """Get or create an agent instance"""
        if agent_type not in self._agents:
            if agent_type not in self.AGENT_MAP:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            agent_class = self.AGENT_MAP[agent_type]
            self._agents[agent_type] = agent_class()
        
        return self._agents[agent_type]
    
    def _select_agents(self, sources: List[str]) -> List[tuple]:
        """Select agents for given sources"""
        agents = []
        for source in sources:
            if source in self.AGENT_MAP:
                agents.append((source, self._get_agent(source)))
            else:
                raise ValueError(f"Unknown source: {source}")
        return agents
    
    async def search(
        self,
        query: str,
        sources: List[str] = ['pubmed', 'clinical_trials'],
        max_results: int = 20,
        include_fulltext: bool = True,
        synthesize: bool = True,
        extract_structured: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> ResearchResult:
        """
        Unified search interface
        
        Args:
            query: Natural language or structured query
            sources: Which data sources to search (pubmed, clinical_trials)
            max_results: Maximum results per source
            include_fulltext: Retrieve full-text when available
            synthesize: Combine results across sources
            extract_structured: Schema for structured extraction
                Format: {"field_name": "extraction instruction"}
            thread_id: Optional thread ID for context management
        
        Returns:
            ResearchResult with findings, synthesis, structured data
        """
        # Generate thread ID if not provided
        if not thread_id:
            thread_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Select agents
        agent_tuples = self._select_agents(sources)
        
        # Execute searches in parallel
        search_tasks = []
        for agent_type, agent in agent_tuples:
            if agent_type == 'pubmed':
                task = self._search_pubmed(
                    agent, query, max_results, include_fulltext, thread_id
                )
            elif agent_type in ['clinical_trials', 'clinicaltrials']:
                task = self._search_clinical_trials(
                    agent, query, max_results, thread_id
                )
            else:
                continue
            
            search_tasks.append((agent_type, task))
        
        # Wait for all searches to complete
        source_results = []
        for agent_type, task in search_tasks:
            try:
                result = await task
                source_results.append(AgentResult(
                    agent_type=agent_type,
                    query=query,
                    results=result.get('results', []),
                    summary=result.get('summary'),
                    metadata=result.get('metadata', {}),
                    timestamp=datetime.now()
                ))
            except Exception as e:
                # Log error but continue with other sources
                source_results.append(AgentResult(
                    agent_type=agent_type,
                    query=query,
                    results=[],
                    summary=f"Error: {str(e)}",
                    metadata={'error': str(e)},
                    timestamp=datetime.now()
                ))
        
        # Synthesize if requested
        synthesis = None
        if synthesize and len(source_results) > 1:
            synthesis = await self._synthesize_results(source_results, query)
        
        # Extract structured data if schema provided
        structured_data = None
        if extract_structured:
            structured_data = await self._extract_structured(
                source_results, extract_structured
            )
        
        return ResearchResult(
            query=query,
            sources=source_results,
            synthesis=synthesis,
            structured_data=structured_data,
            metadata={
                'sources_searched': sources,
                'thread_id': thread_id,
                'max_results': max_results
            },
            timestamp=datetime.now()
        )
    
    async def _search_pubmed(
        self,
        agent: PubMedAgent,
        query: str,
        max_results: int,
        include_fulltext: bool,
        thread_id: str
    ) -> Dict[str, Any]:
        """Search PubMed using PubMedAgent"""
        result = await agent.search_literature(
            query=query,
            max_papers=max_results,
            include_fulltext=include_fulltext,
            thread_id=thread_id
        )
        return result
    
    async def _search_clinical_trials(
        self,
        agent: ClinicalTrialsAgent,
        query: str,
        max_results: int,
        thread_id: str
    ) -> Dict[str, Any]:
        """Search ClinicalTrials.gov using ClinicalTrialsAgent"""
        result = await agent.research_condition(
            condition=query,
            max_studies=max_results,
            analyze_patterns=True,
            thread_id=thread_id
        )
        return result
    
    async def _synthesize_results(
        self,
        source_results: List[AgentResult],
        original_query: str
    ) -> Synthesis:
        """
        Synthesize results across multiple sources
        
        TODO: Implement LLM-powered synthesis
        For now, returns basic synthesis
        """
        # Combine summaries
        summaries = [r.summary for r in source_results if r.summary]
        combined_summary = "\n\n".join(summaries) if summaries else "No summaries available"
        
        # Extract key findings (simplified)
        key_findings = []
        for result in source_results:
            if result.summary:
                # Simple extraction - in production, use LLM
                key_findings.append(f"[{result.agent_type}] {result.summary[:200]}...")
        
        return Synthesis(
            summary=combined_summary,
            key_findings=key_findings,
            consensus_points=[],
            contradictions=[],
            confidence=0.7  # Placeholder
        )
    
    async def _extract_structured(
        self,
        source_results: List[AgentResult],
        schema: Dict[str, Any]
    ) -> StructuredData:
        """
        Extract structured data from results using schema
        
        TODO: Implement LLM-powered extraction
        For now, returns placeholder
        """
        # Combine all result text
        all_text = []
        for result in source_results:
            if result.summary:
                all_text.append(result.summary)
            for item in result.results:
                if isinstance(item, dict):
                    all_text.append(str(item))
        
        combined_text = "\n\n".join(all_text)
        
        # TODO: Use LLM to extract structured data based on schema
        # For now, return placeholder
        extracted_data = {
            field: f"Extracted from: {instruction}"
            for field, instruction in schema.items()
        }
        
        return StructuredData(
            schema_name="custom",
            data=extracted_data,
            confidence=0.5,  # Placeholder
            extraction_method="llm_extraction"  # TODO: Implement
        )
    
    async def multi_source_search(
        self,
        queries: List[str],
        sources: List[str] = ['pubmed', 'clinical_trials'],
        synthesis: bool = True
    ) -> MultiSourceResult:
        """
        Search multiple queries across multiple sources
        
        Args:
            queries: List of queries to execute
            sources: Data sources to search
            synthesis: Whether to synthesize across queries
        
        Returns:
            MultiSourceResult with results per query
        """
        # Execute all queries in parallel
        results = await asyncio.gather(*[
            self.search(query=query, sources=sources, synthesize=False)
            for query in queries
        ])
        
        # Cross-query synthesis if requested
        cross_query_synthesis = None
        if synthesis and len(results) > 1:
            # TODO: Implement cross-query synthesis
            pass
        
        return MultiSourceResult(
            queries=queries,
            results=results,
            cross_query_synthesis=cross_query_synthesis,
            timestamp=datetime.now()
        )
    
    def register_agent(self, agent_type: str, agent_class):
        """Register a new agent type"""
        self.AGENT_MAP[agent_type] = agent_class
        # Clear cached agent if exists
        if agent_type in self._agents:
            del self._agents[agent_type]

