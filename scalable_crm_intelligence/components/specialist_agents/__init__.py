"""
Specialist Agent Framework
Domain-expert agents that focus on specific intelligence types
"""

from .base_specialist import SpecialistAgent, SpecialistConfig
from .executive_intelligence_agent import ExecutiveIntelligenceAgent
from .investment_intelligence_agent import InvestmentIntelligenceAgent

__all__ = [
    'SpecialistAgent',
    'SpecialistConfig',
    'ExecutiveIntelligenceAgent', 
    'InvestmentIntelligenceAgent'
]
