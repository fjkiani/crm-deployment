"""
Response Synthesizer
LLM-powered synthesis of specialist agent responses into coherent, actionable intelligence
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from .llm_client import UnifiedLLMClient

@dataclass
class StructuredAnswer:
    """Standard response format from specialist agents"""
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

@dataclass
class SynthesizedIntelligence:
    """Final synthesized intelligence response"""
    original_question: str
    company: str
    executive_summary: str
    key_insights: List[str]
    actionable_intelligence: Dict[str, Any]
    recommendations: List[Dict[str, Any]]  # Prioritized recommendations
    follow_up_questions: List[str]
    confidence_assessment: Dict[str, Any]
    data_sources: List[str]
    processing_metadata: Dict[str, Any]
    generated_at: str

class IntelligentResponseSynthesizer:
    """LLM-powered synthesis of specialist agent responses"""
    
    def __init__(self, llm_client: UnifiedLLMClient):
        self.llm_client = llm_client
    
    async def synthesize_final_answer(
        self, 
        original_question: str, 
        agent_responses: List[StructuredAnswer],
        company: str,
        question_type: str = "general"
    ) -> SynthesizedIntelligence:
        """Combine specialist responses into coherent, actionable answer"""
        
        if not agent_responses:
            return self._create_empty_response(original_question, company)
        
        # Build synthesis prompt
        prompt = self._build_synthesis_prompt(original_question, agent_responses, company, question_type)
        
        try:
            # Get LLM synthesis
            synthesis_data = await self.llm_client.generate_json(
                prompt=prompt,
                task_type="synthesis"
            )
            
            # Parse and structure the response
            return self._parse_synthesis_response(
                original_question, company, agent_responses, synthesis_data
            )
            
        except Exception as e:
            # Fallback to rule-based synthesis
            return self._create_fallback_synthesis(original_question, company, agent_responses)
    
    def _build_synthesis_prompt(
        self, 
        question: str, 
        responses: List[StructuredAnswer], 
        company: str,
        question_type: str
    ) -> str:
        """Build comprehensive synthesis prompt"""
        
        # Format agent responses for LLM
        agent_data = self._format_agent_responses(responses)
        
        # Create question-type specific instructions
        type_instructions = self._get_type_specific_instructions(question_type)
        
        return f"""You are an expert business intelligence analyst synthesizing research from multiple specialist agents to answer a specific business question.

ORIGINAL QUESTION: "{question}"
COMPANY: "{company}"
QUESTION TYPE: {question_type}

SPECIALIST AGENT RESPONSES:
{agent_data}

{type_instructions}

Synthesize this intelligence into a comprehensive, actionable response that:

1. DIRECTLY ANSWERS the original question with specific, concrete details
2. PROVIDES EXECUTIVE SUMMARY (2-3 sentences) of the most important findings
3. IDENTIFIES KEY INSIGHTS that weren't obvious from individual agent responses
4. STRUCTURES ACTIONABLE INTELLIGENCE by importance and business relevance
5. RECOMMENDS SPECIFIC NEXT STEPS with priorities, timelines, and rationale
6. SUGGESTS INTELLIGENT FOLLOW-UP QUESTIONS for deeper investigation
7. ASSESSES CONFIDENCE LEVELS with clear reasoning

Focus on:
- Business relevance and immediate actionability
- Specific names, numbers, contact details, and dates
- Strategic opportunities and concrete risks
- Cross-references and patterns between agent findings
- Clear prioritization of recommendations by impact/effort

Return as structured JSON:
{{
  "direct_answer": {{
    "summary": "2-3 sentence direct answer to the original question",
    "key_findings": [
      "specific finding 1 with concrete details",
      "specific finding 2 with concrete details"
    ],
    "confidence_level": 0.0-1.0
  }},
  "executive_summary": "compelling 2-3 sentence summary for executive consumption",
  "key_insights": [
    "strategic insight 1: pattern or connection not obvious from individual responses",
    "strategic insight 2: business implication or opportunity discovered through synthesis"
  ],
  "actionable_intelligence": {{
    "primary_findings": {{
      "decision_makers": [/* if relevant */],
      "investments": [/* if relevant */], 
      "opportunities": [/* if relevant */],
      "contacts": [/* if relevant */]
    }},
    "supporting_data": {{
      "background_context": "relevant context for findings",
      "data_quality_notes": "assessment of data reliability and completeness"
    }}
  }},
  "prioritized_recommendations": [
    {{
      "action": "specific action to take (e.g., 'Schedule intro call with Dr. Sarah Johnson')",
      "priority": "high|medium|low",
      "timeline": "immediate|1-2 weeks|1 month",
      "rationale": "why this action is recommended and why it's this priority",
      "resources_needed": "what's required to execute (e.g., 'warm introduction, 30-min prep')",
      "expected_outcome": "what success looks like",
      "risk_level": "low|medium|high"
    }}
  ],
  "strategic_opportunities": [
    {{
      "opportunity": "specific strategic opportunity identified",
      "potential_value": "estimated business value or impact",
      "approach_strategy": "how to pursue this opportunity",
      "timeline": "when to act on this opportunity",
      "success_probability": 0.0-1.0
    }}
  ],
  "follow_up_questions": [
    "intelligent follow-up question 1 that would deepen understanding",
    "intelligent follow-up question 2 that would uncover additional opportunities"
  ],
  "confidence_assessment": {{
    "overall_confidence": 0.0-1.0,
    "data_completeness": 0.0-1.0,
    "source_reliability": 0.0-1.0,
    "limitations": [
      "specific limitation 1 (e.g., 'contact information not verified')",
      "specific limitation 2"
    ],
    "improvement_recommendations": [
      "how to get better data for this type of question",
      "what additional sources would improve confidence"
    ]
  }}
}}"""
    
    def _get_type_specific_instructions(self, question_type: str) -> str:
        """Get specific instructions based on question type"""
        
        instructions = {
            "executive_analysis": """
For executive analysis questions, prioritize:
- Specific names and titles of decision makers
- Contact information and approach strategies
- Decision-making authority and processes
- Recent activities and interests
- Best methods for engagement
""",
            "investment_research": """
For investment research questions, prioritize:
- Specific investment amounts, dates, and companies
- Investment patterns and themes
- Decision makers involved in investments
- Investment criteria and preferences
- Recent activity and trends
""",
            "gap_analysis": """
For gap analysis questions, prioritize:
- Specific gaps with quantified opportunities
- Market sizing and competitive landscape
- Strategic recommendations with clear rationale
- Timeline and feasibility assessments
- Risk factors and mitigation strategies
""",
            "contact_research": """
For contact research questions, prioritize:
- Verified contact information (emails, phones, LinkedIn)
- Contact preferences and best approach methods
- Relationship mapping and mutual connections
- Communication history and context
""",
            "comprehensive_analysis": """
For comprehensive analysis questions, balance:
- Executive findings with investment insights
- Strategic opportunities with tactical recommendations
- Current state with future possibilities
- Quantitative data with qualitative insights
"""
        }
        
        return instructions.get(question_type, instructions["comprehensive_analysis"])
    
    def _format_agent_responses(self, responses: List[StructuredAnswer]) -> str:
        """Format agent responses for LLM consumption"""
        
        formatted_responses = []
        
        for response in responses:
            formatted = f"""
AGENT: {response.agent_type}
QUESTION: {response.question}
CONFIDENCE: {response.confidence_score:.2f}
DATA: {json.dumps(response.data, indent=2)}
SOURCES: {', '.join(response.sources[:3])}{'...' if len(response.sources) > 3 else ''}
RECOMMENDATIONS: {'; '.join(response.recommendations)}
"""
            formatted_responses.append(formatted)
        
        return "\n".join(formatted_responses)
    
    def _parse_synthesis_response(
        self,
        original_question: str,
        company: str, 
        agent_responses: List[StructuredAnswer],
        synthesis_data: Dict[str, Any]
    ) -> SynthesizedIntelligence:
        """Parse LLM synthesis response into structured format"""
        
        # Extract and validate synthesis data
        direct_answer = synthesis_data.get("direct_answer", {})
        confidence_assessment = synthesis_data.get("confidence_assessment", {})
        
        # Collect all sources
        all_sources = []
        for response in agent_responses:
            all_sources.extend(response.sources)
        
        # Calculate processing metadata
        processing_metadata = {
            "agents_used": [r.agent_type for r in agent_responses],
            "total_sources": len(set(all_sources)),
            "processing_time": "estimated",
            "synthesis_method": "llm_powered"
        }
        
        return SynthesizedIntelligence(
            original_question=original_question,
            company=company,
            executive_summary=synthesis_data.get("executive_summary", ""),
            key_insights=synthesis_data.get("key_insights", []),
            actionable_intelligence=synthesis_data.get("actionable_intelligence", {}),
            recommendations=synthesis_data.get("prioritized_recommendations", []),
            follow_up_questions=synthesis_data.get("follow_up_questions", []),
            confidence_assessment=confidence_assessment,
            data_sources=list(set(all_sources)),
            processing_metadata=processing_metadata,
            generated_at=datetime.now().isoformat()
        )
    
    def _create_fallback_synthesis(
        self,
        original_question: str,
        company: str,
        agent_responses: List[StructuredAnswer]
    ) -> SynthesizedIntelligence:
        """Create rule-based synthesis if LLM fails"""
        
        # Aggregate data from all responses
        all_data = {}
        all_sources = []
        all_recommendations = []
        
        for response in agent_responses:
            all_data[response.agent_type] = response.data
            all_sources.extend(response.sources)
            all_recommendations.extend(response.recommendations)
        
        # Create basic synthesis
        executive_summary = f"Analysis of {company} based on {len(agent_responses)} specialist agent responses."
        
        key_insights = [
            f"Data collected from {len(set(all_sources))} sources",
            f"Analysis involved {len(agent_responses)} specialist agents"
        ]
        
        basic_recommendations = [
            {
                "action": "Review detailed agent responses for specific insights",
                "priority": "high",
                "timeline": "immediate",
                "rationale": "Fallback synthesis requires manual review",
                "resources_needed": "human analysis",
                "expected_outcome": "better understanding of findings",
                "risk_level": "low"
            }
        ]
        
        confidence_assessment = {
            "overall_confidence": 0.6,
            "data_completeness": 0.7,
            "source_reliability": 0.6,
            "limitations": ["Fallback synthesis used", "Manual review recommended"],
            "improvement_recommendations": ["Use LLM synthesis for better results"]
        }
        
        return SynthesizedIntelligence(
            original_question=original_question,
            company=company,
            executive_summary=executive_summary,
            key_insights=key_insights,
            actionable_intelligence=all_data,
            recommendations=basic_recommendations,
            follow_up_questions=["What specific aspect would you like to explore further?"],
            confidence_assessment=confidence_assessment,
            data_sources=list(set(all_sources)),
            processing_metadata={
                "agents_used": [r.agent_type for r in agent_responses],
                "synthesis_method": "fallback_rules"
            },
            generated_at=datetime.now().isoformat()
        )
    
    def _create_empty_response(self, original_question: str, company: str) -> SynthesizedIntelligence:
        """Create response when no agent data is available"""
        
        return SynthesizedIntelligence(
            original_question=original_question,
            company=company,
            executive_summary=f"No intelligence data available for {company}.",
            key_insights=["No data available from specialist agents"],
            actionable_intelligence={},
            recommendations=[
                {
                    "action": "Configure and run specialist agents",
                    "priority": "high", 
                    "timeline": "immediate",
                    "rationale": "No agent responses available for synthesis",
                    "resources_needed": "agent configuration and execution",
                    "expected_outcome": "actionable intelligence data",
                    "risk_level": "low"
                }
            ],
            follow_up_questions=["What specific information would you like to gather about this company?"],
            confidence_assessment={
                "overall_confidence": 0.0,
                "data_completeness": 0.0,
                "source_reliability": 0.0,
                "limitations": ["No agent responses available"],
                "improvement_recommendations": ["Run specialist agents first"]
            },
            data_sources=[],
            processing_metadata={
                "agents_used": [],
                "synthesis_method": "empty_response"
            },
            generated_at=datetime.now().isoformat()
        )
