"""
Research Framework - Agentic Biomedical Research Framework

A unified framework for intelligent biomedical research that enables agents to:
- Search multiple data sources (PubMed, ClinicalTrials.gov, etc.)
- Synthesize findings across sources
- Extract structured insights
- Maintain context across sessions
"""

from .orchestrator import ResearchOrchestrator
from .models import ResearchResult, AgentResult, MultiSourceResult
from .agents.base_agent import BaseDomainAgent

__all__ = [
    "ResearchOrchestrator",
    "ResearchResult",
    "AgentResult",
    "MultiSourceResult",
    "BaseDomainAgent",
]

__version__ = "0.1.0"

