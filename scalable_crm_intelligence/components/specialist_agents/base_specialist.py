"""
Base Specialist Agent
Abstract base class for all specialist intelligence agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from core.base.component import BaseComponent, ComponentConfig

@dataclass
class SpecialistConfig(ComponentConfig):
    """Configuration for specialist agents"""
    api_key: str = ""
    rate_limit: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    expertise_domains: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.expertise_domains is None:
            self.expertise_domains = []

@dataclass
class StructuredAnswer:
    """Standard response format for all specialist agents"""
    agent_type: str
    question: str
    company: str
    confidence_score: float  # 0.0 to 1.0
    data: Dict[str, Any]
    sources: List[str]
    timestamp: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "agent_type": self.agent_type,
            "question": self.question,
            "company": self.company,
            "confidence_score": self.confidence_score,
            "data": self.data,
            "sources": self.sources,
            "timestamp": self.timestamp,
            "recommendations": self.recommendations
        }

class SpecialistAgent(BaseComponent):
    """Abstract base class for all specialist intelligence agents"""
    
    def __init__(self, config: SpecialistConfig):
        super().__init__(config)
        self.specialist_config = config
        self.expertise_domains = self._define_expertise_domains()
        self.answerable_patterns = self._define_answerable_patterns()
    
    @abstractmethod
    def _define_expertise_domains(self) -> List[str]:
        """Define the specific domains this agent specializes in"""
        pass
    
    @abstractmethod
    def _define_answerable_patterns(self) -> List[str]:
        """Define question patterns this agent can answer"""
        pass
    
    @abstractmethod
    async def answer_question(self, question: str, company: str, context: Dict[str, Any] = None) -> StructuredAnswer:
        """Answer a specific question within the agent's expertise"""
        pass
    
    def can_answer(self, question: str) -> bool:
        """Determine if this agent can handle the question"""
        question_lower = question.lower()
        
        # Check expertise domains
        domain_match = any(domain.lower() in question_lower for domain in self.expertise_domains)
        
        # Check answerable patterns
        pattern_match = any(pattern.lower() in question_lower for pattern in self.answerable_patterns)
        
        return domain_match or pattern_match
    
    def get_relevance_score(self, question: str) -> float:
        """Calculate how relevant this agent is to the question (0.0-1.0)"""
        question_lower = question.lower()
        score = 0.0
        
        # Score based on expertise domains
        domain_matches = sum(1 for domain in self.expertise_domains if domain.lower() in question_lower)
        if self.expertise_domains:
            score += (domain_matches / len(self.expertise_domains)) * 0.6
        
        # Score based on answerable patterns
        pattern_matches = sum(1 for pattern in self.answerable_patterns if pattern.lower() in question_lower)
        if self.answerable_patterns:
            score += (pattern_matches / len(self.answerable_patterns)) * 0.4
        
        return min(score, 1.0)
    
    def get_supported_question_types(self) -> List[str]:
        """Return list of question types this agent supports"""
        return self.expertise_domains + self.answerable_patterns
    
    def _create_structured_answer(
        self,
        question: str,
        company: str,
        data: Dict[str, Any],
        sources: List[str],
        confidence: float = 0.8,
        recommendations: List[str] = None
    ) -> StructuredAnswer:
        """Helper to create standardized StructuredAnswer"""
        
        if recommendations is None:
            recommendations = []
        
        return StructuredAnswer(
            agent_type=self.__class__.__name__,
            question=question,
            company=company,
            confidence_score=confidence,
            data=data,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            recommendations=recommendations
        )
    
    def _calculate_confidence_score(self, data: Dict[str, Any], sources: List[str]) -> float:
        """Calculate confidence score based on data quality and sources"""
        base_score = 0.5
        
        # Data completeness factor
        if data:
            data_completeness = min(len(data) / 5.0, 1.0)  # Normalize to max 5 data points
            base_score += data_completeness * 0.3
        
        # Source reliability factor  
        if sources:
            source_quality = min(len(sources) / 3.0, 1.0)  # Normalize to max 3 sources
            base_score += source_quality * 0.2
        
        return min(base_score, 1.0)
    
    def _extract_recommendations(self, data: Dict[str, Any], question: str, company: str) -> List[str]:
        """Extract actionable recommendations from data"""
        recommendations = []
        
        # Default recommendations based on agent type
        agent_name = self.__class__.__name__.replace("Agent", "").replace("Intelligence", "")
        recommendations.append(f"Review {agent_name.lower()} findings for {company}")
        
        # Data-specific recommendations
        if "contacts" in str(data).lower():
            recommendations.append("Reach out to identified contacts for further information")
        
        if "investments" in str(data).lower():
            recommendations.append("Analyze investment patterns for strategic insights")
        
        return recommendations
    
    async def initialize(self) -> bool:
        """Initialize the specialist agent"""
        try:
            self.logger.info(f"Initializing {self.__class__.__name__}")
            self.logger.info(f"Expertise domains: {', '.join(self.expertise_domains)}")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Cleanup specialist agent resources"""
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Check specialist agent health"""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "agent_type": self.__class__.__name__,
            "expertise_domains": self.expertise_domains,
            "answerable_patterns": self.answerable_patterns,
            "last_check": datetime.now().isoformat()
        }
