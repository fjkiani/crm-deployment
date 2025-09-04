"""
Intelligent Agents with Brain Context
Domain-expert agents with contextual reasoning and intelligence extraction
"""

from .intelligent_executive_agent import IntelligentExecutiveAgent
from .intelligent_investment_agent import IntelligentInvestmentAgent
from .intelligent_gap_analysis_agent import IntelligentGapAnalysisAgent
from .agent_brain import AgentBrain, IntelligenceContext

__all__ = [
    'IntelligentExecutiveAgent',
    'IntelligentInvestmentAgent', 
    'IntelligentGapAnalysisAgent',
    'AgentBrain',
    'IntelligenceContext'
]
