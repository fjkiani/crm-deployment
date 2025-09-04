"""
Agent Router
Routes questions to the most appropriate specialist agents
"""

from typing import Dict, Any, List, Optional
import logging
from components.specialist_agents.base_specialist import SpecialistAgent

class AgentRouter:
    """Routes questions to optimal specialist agents"""
    
    def __init__(self):
        self.agents: Dict[str, SpecialistAgent] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.logger = logging.getLogger("AgentRouter")
    
    def register_agent(self, agent_name: str, agent: SpecialistAgent):
        """Register an agent with its capabilities"""
        self.agents[agent_name] = agent
        self.agent_capabilities[agent_name] = agent.get_supported_question_types()
        self.logger.info(f"Registered agent {agent_name} with capabilities: {', '.join(agent.expertise_domains)}")
    
    def find_best_agent(self, question: str, suggested_agents: List[str] = None) -> Optional[str]:
        """Find the best agent for a given question"""
        
        # If specific agents are suggested, check them first
        if suggested_agents:
            for agent_name in suggested_agents:
                if agent_name in self.agents and self.agents[agent_name].can_answer(question):
                    self.logger.debug(f"Using suggested agent {agent_name} for question")
                    return agent_name
        
        # Find all capable agents with relevance scores
        capable_agents = []
        
        for agent_name, agent in self.agents.items():
            if agent.can_answer(question):
                relevance_score = agent.get_relevance_score(question)
                capable_agents.append((agent_name, relevance_score))
        
        if not capable_agents:
            self.logger.warning(f"No capable agents found for question: {question}")
            return None
        
        # Sort by relevance score and return the best
        capable_agents.sort(key=lambda x: x[1], reverse=True)
        best_agent = capable_agents[0][0]
        
        self.logger.debug(f"Selected agent {best_agent} with relevance score {capable_agents[0][1]:.2f}")
        return best_agent
    
    def find_all_capable_agents(self, question: str) -> List[tuple]:
        """Find all agents capable of handling a question with their relevance scores"""
        
        capable_agents = []
        
        for agent_name, agent in self.agents.items():
            if agent.can_answer(question):
                relevance_score = agent.get_relevance_score(question)
                capable_agents.append((agent_name, relevance_score))
        
        # Sort by relevance score
        capable_agents.sort(key=lambda x: x[1], reverse=True)
        return capable_agents
    
    def get_routing_plan(self, questions: List[str]) -> Dict[str, Any]:
        """Create routing plan for multiple questions"""
        
        routing_plan = {
            "questions": len(questions),
            "routing": [],
            "agent_utilization": {},
            "unroutable_questions": []
        }
        
        # Route each question
        for i, question in enumerate(questions):
            best_agent = self.find_best_agent(question)
            
            if best_agent:
                routing_plan["routing"].append({
                    "question_index": i,
                    "question": question,
                    "assigned_agent": best_agent,
                    "alternatives": [agent for agent, score in self.find_all_capable_agents(question)[1:3]]
                })
                
                # Track agent utilization
                if best_agent not in routing_plan["agent_utilization"]:
                    routing_plan["agent_utilization"][best_agent] = 0
                routing_plan["agent_utilization"][best_agent] += 1
            else:
                routing_plan["unroutable_questions"].append({
                    "question_index": i,
                    "question": question,
                    "reason": "No capable agents found"
                })
        
        return routing_plan
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all registered agents"""
        
        status = {
            "total_agents": len(self.agents),
            "agents": {}
        }
        
        for agent_name, agent in self.agents.items():
            status["agents"][agent_name] = {
                "capabilities": agent.expertise_domains,
                "question_patterns": agent.answerable_patterns,
                "health": agent.health_check(),
                "initialized": agent.is_initialized()
            }
        
        return status
    
    def suggest_agent_improvements(self, question: str) -> List[str]:
        """Suggest how to improve agent coverage for unhandled questions"""
        
        suggestions = []
        
        # Check if any agents can handle the question
        capable_agents = self.find_all_capable_agents(question)
        
        if not capable_agents:
            # Analyze question to suggest new agent types
            question_lower = question.lower()
            
            if any(word in question_lower for word in ["investment", "portfolio", "deals"]):
                suggestions.append("Consider adding an InvestmentIntelligenceAgent")
            
            if any(word in question_lower for word in ["contact", "email", "phone"]):
                suggestions.append("Consider adding a ContactDiscoveryAgent")
            
            if any(word in question_lower for word in ["gap", "opportunity", "competition"]):
                suggestions.append("Consider adding a GapAnalysisAgent")
            
            if any(word in question_lower for word in ["trend", "pattern", "prediction"]):
                suggestions.append("Consider adding a TrendAnalysisAgent")
            
            if not suggestions:
                suggestions.append("Consider expanding existing agent capabilities or adding a general research agent")
        
        elif len(capable_agents) == 1:
            suggestions.append("Consider adding redundant agents for better reliability")
        
        return suggestions
