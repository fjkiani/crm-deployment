"""
Question Decomposer
LLM-powered question decomposition and analysis for intelligent agent routing
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .llm_client import UnifiedLLMClient, LLMResponse

@dataclass
class SubQuestion:
    """Represents a sub-question for specialist agents"""
    id: str
    question: str
    target_agents: List[str]
    priority: str  # "high", "medium", "low"
    dependencies: List[str]  # IDs of other sub-questions
    rationale: str
    expected_data_type: str  # "executive_info", "investment_data", "gap_analysis"

@dataclass 
class QuestionDecomposition:
    """Result of question decomposition analysis"""
    original_question: str
    company: str
    sub_questions: List[SubQuestion]
    execution_strategy: str  # "sequential", "parallel", "hybrid"
    complexity_score: float  # 0.0-1.0
    estimated_time_minutes: int
    question_type: str  # "executive_analysis", "investment_research", "gap_analysis"

class QuestionDecomposer:
    """LLM-powered question decomposition engine"""
    
    def __init__(self, llm_client: UnifiedLLMClient):
        self.llm_client = llm_client
        self.agent_capabilities = self._load_agent_capabilities()
    
    def _load_agent_capabilities(self) -> Dict[str, List[str]]:
        """Define capabilities of each specialist agent"""
        return {
            "ExecutiveIntelligenceAgent": [
                "decision makers", "leadership", "executives", "board members",
                "management team", "org structure", "decision authority"
            ],
            "InvestmentIntelligenceAgent": [
                "investments", "portfolio", "deals", "funding", "investment activity",
                "investment history", "investment patterns", "portfolio companies"
            ],
            "SectorExpertiseAgent": [
                "sector analysis", "industry expertise", "sector investments",
                "healthcare", "fintech", "enterprise software", "biotech"
            ],
            "GapAnalysisAgent": [
                "gaps", "opportunities", "strategic analysis", "market opportunities",
                "competitive analysis", "portfolio gaps", "investment opportunities"
            ],
            "ContactDiscoveryAgent": [
                "contact information", "email addresses", "phone numbers",
                "linkedin profiles", "contact details"
            ],
            "RelationshipMappingAgent": [
                "relationships", "networks", "connections", "introductions",
                "professional networks", "mutual connections"
            ],
            "TrendAnalysisAgent": [
                "trends", "patterns", "predictions", "market trends",
                "investment trends", "pattern recognition"
            ]
        }
    
    async def decompose_question(self, question: str, company: str, context: Dict[str, Any] = None) -> QuestionDecomposition:
        """Break complex question into specialist-answerable sub-questions"""
        
        prompt = self._build_decomposition_prompt(question, company, context)
        
        try:
            response_data = await self.llm_client.generate_json(
                prompt=prompt,
                task_type="question_decomposition"
            )
            
            return self._parse_decomposition_response(question, company, response_data)
            
        except Exception as e:
            # Fallback to simple decomposition
            return self._create_fallback_decomposition(question, company)
    
    def _build_decomposition_prompt(self, question: str, company: str, context: Dict[str, Any]) -> str:
        """Build intelligent decomposition prompt"""
        
        agent_descriptions = []
        for agent, capabilities in self.agent_capabilities.items():
            agent_descriptions.append(f"- {agent}: {', '.join(capabilities)}")
        
        agent_list = '\n'.join(agent_descriptions)
        context_str = json.dumps(context, indent=2) if context else "None"
        
        return f"""You are an expert business intelligence analyst. Break down this complex question into specific, answerable sub-questions for specialist agents.

QUESTION: "{question}"
COMPANY: "{company}"
CONTEXT: {context_str}

Available Specialist Agents and their capabilities:
{agent_list}

Analyze the question and break it into sub-questions that:
1. Can be answered by specific specialist agents
2. Build upon each other logically (consider dependencies)
3. Cover all aspects of the original question
4. Are specific and actionable
5. Avoid redundancy between agents

For each sub-question:
- Assign to appropriate specialist agents based on their capabilities
- Set priority (high/medium/low) based on importance to answering main question
- Identify dependencies (which sub-questions must complete first)
- Classify expected data type for response formatting

Return as JSON:
{{
  "question_analysis": {{
    "question_type": "executive_analysis|investment_research|gap_analysis|contact_research|comprehensive_analysis",
    "complexity_score": 0.0-1.0,
    "key_entities": ["entity1", "entity2"],
    "focus_areas": ["area1", "area2"]
  }},
  "sub_questions": [
    {{
      "id": "sq_1",
      "question": "specific sub-question text",
      "target_agents": ["AgentName1", "AgentName2"],
      "priority": "high|medium|low",
      "dependencies": ["sq_id1", "sq_id2"],
      "rationale": "why this sub-question is needed",
      "expected_data_type": "executive_info|investment_data|gap_analysis|contact_info|sector_analysis"
    }}
  ],
  "execution_plan": {{
    "strategy": "sequential|parallel|hybrid",
    "estimated_time_minutes": 5-30,
    "reasoning": "explanation of execution strategy"
  }}
}}

Example for "For Abbey Capital, find healthcare decision makers and recent investments":
{{
  "question_analysis": {{
    "question_type": "comprehensive_analysis",
    "complexity_score": 0.7,
    "key_entities": ["Abbey Capital", "healthcare"],
    "focus_areas": ["decision_makers", "recent_investments"]
  }},
  "sub_questions": [
    {{
      "id": "sq_1",
      "question": "Who are the decision makers at Abbey Capital with healthcare focus or authority?",
      "target_agents": ["ExecutiveIntelligenceAgent"],
      "priority": "high",
      "dependencies": [],
      "rationale": "Need to identify key contacts for healthcare investments",
      "expected_data_type": "executive_info"
    }},
    {{
      "id": "sq_2", 
      "question": "What healthcare investments has Abbey Capital made in the past 24 months?",
      "target_agents": ["InvestmentIntelligenceAgent", "SectorExpertiseAgent"],
      "priority": "high",
      "dependencies": [],
      "rationale": "Understanding recent healthcare investment activity and patterns",
      "expected_data_type": "investment_data"
    }},
    {{
      "id": "sq_3",
      "question": "What are the contact details for Abbey Capital's healthcare decision makers?",
      "target_agents": ["ContactDiscoveryAgent"],
      "priority": "medium", 
      "dependencies": ["sq_1"],
      "rationale": "Need contact information for outreach after identifying decision makers",
      "expected_data_type": "contact_info"
    }}
  ],
  "execution_plan": {{
    "strategy": "hybrid",
    "estimated_time_minutes": 15,
    "reasoning": "sq_1 and sq_2 can run in parallel, sq_3 depends on sq_1 results"
  }}
}}"""
    
    def _parse_decomposition_response(self, question: str, company: str, response_data: Dict[str, Any]) -> QuestionDecomposition:
        """Parse LLM response into QuestionDecomposition object"""
        
        # Extract sub-questions
        sub_questions = []
        for sq_data in response_data.get("sub_questions", []):
            sub_question = SubQuestion(
                id=sq_data.get("id", f"sq_{len(sub_questions)+1}"),
                question=sq_data.get("question", ""),
                target_agents=sq_data.get("target_agents", []),
                priority=sq_data.get("priority", "medium"),
                dependencies=sq_data.get("dependencies", []),
                rationale=sq_data.get("rationale", ""),
                expected_data_type=sq_data.get("expected_data_type", "general")
            )
            sub_questions.append(sub_question)
        
        # Extract execution plan
        execution_plan = response_data.get("execution_plan", {})
        question_analysis = response_data.get("question_analysis", {})
        
        return QuestionDecomposition(
            original_question=question,
            company=company,
            sub_questions=sub_questions,
            execution_strategy=execution_plan.get("strategy", "sequential"),
            complexity_score=question_analysis.get("complexity_score", 0.5),
            estimated_time_minutes=execution_plan.get("estimated_time_minutes", 10),
            question_type=question_analysis.get("question_type", "general_analysis")
        )
    
    def _create_fallback_decomposition(self, question: str, company: str) -> QuestionDecomposition:
        """Create simple fallback decomposition if LLM fails"""
        
        # Simple keyword-based decomposition
        question_lower = question.lower()
        
        sub_questions = []
        
        # Check for executive/decision maker questions
        if any(keyword in question_lower for keyword in ["decision maker", "executive", "leadership", "who"]):
            sub_questions.append(SubQuestion(
                id="sq_fallback_1",
                question=f"Who are the key decision makers at {company}?",
                target_agents=["ExecutiveIntelligenceAgent"],
                priority="high",
                dependencies=[],
                rationale="Fallback executive identification",
                expected_data_type="executive_info"
            ))
        
        # Check for investment questions
        if any(keyword in question_lower for keyword in ["investment", "portfolio", "invested", "funding"]):
            sub_questions.append(SubQuestion(
                id="sq_fallback_2", 
                question=f"What are the recent investments by {company}?",
                target_agents=["InvestmentIntelligenceAgent"],
                priority="high",
                dependencies=[],
                rationale="Fallback investment analysis",
                expected_data_type="investment_data"
            ))
        
        # Check for gap/opportunity questions
        if any(keyword in question_lower for keyword in ["gap", "opportunity", "missing", "what are"]):
            sub_questions.append(SubQuestion(
                id="sq_fallback_3",
                question=f"What strategic gaps or opportunities exist for {company}?",
                target_agents=["GapAnalysisAgent"],
                priority="medium",
                dependencies=[],
                rationale="Fallback gap analysis",
                expected_data_type="gap_analysis"
            ))
        
        # Default general question if no specific patterns found
        if not sub_questions:
            sub_questions.append(SubQuestion(
                id="sq_fallback_general",
                question=f"Provide general business intelligence on {company}",
                target_agents=["ExecutiveIntelligenceAgent", "InvestmentIntelligenceAgent"],
                priority="medium",
                dependencies=[],
                rationale="Fallback general analysis",
                expected_data_type="general"
            ))
        
        return QuestionDecomposition(
            original_question=question,
            company=company,
            sub_questions=sub_questions,
            execution_strategy="parallel",
            complexity_score=0.5,
            estimated_time_minutes=10,
            question_type="general_analysis"
        )
    
    def classify_question_type(self, question: str) -> str:
        """Classify question into main category"""
        question_lower = question.lower()
        
        if any(keyword in question_lower for keyword in ["decision maker", "executive", "leadership", "who"]):
            return "executive_analysis"
        elif any(keyword in question_lower for keyword in ["investment", "portfolio", "invested", "funding"]):
            return "investment_research"
        elif any(keyword in question_lower for keyword in ["gap", "opportunity", "missing", "compare"]):
            return "gap_analysis"
        elif any(keyword in question_lower for keyword in ["contact", "email", "phone", "linkedin"]):
            return "contact_research"
        else:
            return "comprehensive_analysis"
    
    def estimate_complexity(self, question: str) -> float:
        """Estimate question complexity score"""
        complexity_factors = {
            "multiple_companies": 0.3,
            "time_ranges": 0.2,
            "multiple_sectors": 0.2,
            "comparative_analysis": 0.4,
            "multi_part_question": 0.3
        }
        
        question_lower = question.lower()
        complexity = 0.3  # Base complexity
        
        # Check for complexity indicators
        if len(question.split(",")) > 2:  # Multi-part question
            complexity += complexity_factors["multi_part_question"]
        
        if any(word in question_lower for word in ["compare", "vs", "versus", "between"]):
            complexity += complexity_factors["comparative_analysis"]
        
        if any(word in question_lower for word in ["recent", "past", "last", "since"]):
            complexity += complexity_factors["time_ranges"]
        
        # Count company mentions
        company_indicators = ["capital", "management", "ventures", "partners", "group"]
        company_count = sum(1 for indicator in company_indicators if indicator in question_lower)
        if company_count > 1:
            complexity += complexity_factors["multiple_companies"]
        
        return min(complexity, 1.0)
