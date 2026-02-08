"""
Base Domain Agent - Template for domain-specific agents

Domain agents extend this class to provide specialized research capabilities
while leveraging the Research Framework for data acquisition.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..orchestrator import ResearchOrchestrator
from ..models import ResearchResult


class BaseDomainAgent(ABC):
    """
    Base class for domain-specific research agents
    
    Domain agents should:
    1. Extend this class
    2. Initialize with ResearchOrchestrator
    3. Implement domain-specific methods
    4. Use self.framework for research operations
    """
    
    def __init__(self, framework: Optional[ResearchOrchestrator] = None):
        """
        Initialize domain agent
        
        Args:
            framework: ResearchOrchestrator instance (creates new if None)
        """
        if framework is None:
            framework = ResearchOrchestrator()
        self.framework = framework
        self.domain = self._get_domain_name()
    
    @abstractmethod
    def _get_domain_name(self) -> str:
        """Return domain name (e.g., 'pgx', 'oncology', 'safety')"""
        pass
    
    async def search(
        self,
        query: str,
        sources: Optional[list] = None,
        **kwargs
    ) -> ResearchResult:
        """
        Generic search method - can be overridden by domain agents
        
        Args:
            query: Search query
            sources: Data sources (defaults to all available)
            **kwargs: Additional arguments passed to framework.search()
        
        Returns:
            ResearchResult
        """
        if sources is None:
            sources = ['pubmed', 'clinical_trials']
        
        return await self.framework.search(
            query=query,
            sources=sources,
            **kwargs
        )
    
    def _build_domain_queries(self, user_query: str) -> list:
        """
        Build domain-specific queries from user query
        
        Override this method to add domain-specific query construction
        
        Args:
            user_query: User's natural language query
        
        Returns:
            List of queries optimized for domain
        """
        # Default: return user query as-is
        return [user_query]
    
    def _interpret_domain_results(self, result: ResearchResult) -> Dict[str, Any]:
        """
        Interpret framework results in domain context
        
        Override this method to add domain-specific interpretation
        
        Args:
            result: ResearchResult from framework
        
        Returns:
            Domain-specific interpretation
        """
        # Default: return result as-is
        return {
            'domain': self.domain,
            'result': result
        }

