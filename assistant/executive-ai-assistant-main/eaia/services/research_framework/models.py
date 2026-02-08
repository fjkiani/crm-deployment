"""
Data models for Research Framework
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result from a single research agent"""
    agent_type: str = Field(..., description="Type of agent (pubmed, clinical_trials, etc.)")
    query: str = Field(..., description="Query that was executed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Raw results from agent")
    summary: Optional[str] = Field(None, description="Agent-generated summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific metadata")
    timestamp: datetime = Field(default_factory=datetime.now)


class StructuredData(BaseModel):
    """Structured data extracted from research results"""
    schema_name: str = Field(..., description="Name of extraction schema")
    data: Dict[str, Any] = Field(..., description="Extracted structured data")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    extraction_method: str = Field(..., description="Method used for extraction")


class Synthesis(BaseModel):
    """Synthesized findings across multiple sources"""
    summary: str = Field(..., description="Unified summary across sources")
    key_findings: List[str] = Field(default_factory=list, description="Key findings")
    consensus_points: List[str] = Field(default_factory=list, description="Points of consensus")
    contradictions: List[str] = Field(default_factory=list, description="Contradictory findings")
    confidence: Optional[float] = Field(None, description="Overall confidence (0-1)")


class ResearchResult(BaseModel):
    """Complete research result from framework"""
    query: str = Field(..., description="Original query")
    sources: List[AgentResult] = Field(default_factory=list, description="Results from each source")
    synthesis: Optional[Synthesis] = Field(None, description="Synthesized findings")
    structured_data: Optional[StructuredData] = Field(None, description="Extracted structured data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Framework metadata")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def get_source_result(self, agent_type: str) -> Optional[AgentResult]:
        """Get result from a specific source"""
        for source in self.sources:
            if source.agent_type == agent_type:
                return source
        return None


class MultiSourceResult(BaseModel):
    """Result from multi-query, multi-source search"""
    queries: List[str] = Field(..., description="Queries that were executed")
    results: List[ResearchResult] = Field(default_factory=list, description="Results per query")
    cross_query_synthesis: Optional[Synthesis] = Field(None, description="Synthesis across queries")
    timestamp: datetime = Field(default_factory=datetime.now)

