"""
Intelligent Q&A Workflow
Main orchestrator for question-driven intelligence gathering
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from components.llm_integration.llm_client import UnifiedLLMClient, LLMConfig
from components.llm_integration.question_decomposer import QuestionDecomposer, QuestionDecomposition
from components.llm_integration.response_synthesizer import IntelligentResponseSynthesizer, SynthesizedIntelligence
from components.specialist_agents.base_specialist import SpecialistAgent, StructuredAnswer
from .agent_router import AgentRouter

class IntelligentQAWorkflow:
    """Main orchestrator for question-driven intelligence workflows"""
    
    def __init__(self, llm_config: LLMConfig = None):
        self.llm_config = llm_config or LLMConfig()
        self.llm_client = UnifiedLLMClient(self.llm_config)
        self.question_decomposer = QuestionDecomposer(self.llm_client)
        self.response_synthesizer = IntelligentResponseSynthesizer(self.llm_client)
        self.agent_router = AgentRouter()
        self.specialist_agents: Dict[str, SpecialistAgent] = {}
        self.logger = logging.getLogger("IntelligentQAWorkflow")
    
    def register_specialist_agent(self, agent: SpecialistAgent):
        """Register a specialist agent for use in workflows"""
        agent_name = agent.__class__.__name__
        self.specialist_agents[agent_name] = agent
        self.agent_router.register_agent(agent_name, agent)
        self.logger.info(f"Registered specialist agent: {agent_name}")
    
    async def answer_question(self, question: str, company: str, context: Dict[str, Any] = None) -> SynthesizedIntelligence:
        """Main entry point for answering questions with intelligent agent coordination"""
        
        self.logger.info(f"Processing question for {company}: {question}")
        start_time = datetime.now()
        
        try:
            # Phase 1: Question Decomposition
            self.logger.info("Phase 1: Decomposing question into sub-questions")
            decomposition = await self.question_decomposer.decompose_question(question, company, context)
            
            # Phase 2: Agent Routing and Execution
            self.logger.info("Phase 2: Routing sub-questions to specialist agents")
            agent_responses = await self._execute_agent_workflow(decomposition)
            
            # Phase 3: Response Synthesis
            self.logger.info("Phase 3: Synthesizing agent responses")
            synthesized_response = await self.response_synthesizer.synthesize_final_answer(
                original_question=question,
                agent_responses=agent_responses,
                company=company,
                question_type=decomposition.question_type
            )
            
            # Add processing metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            synthesized_response.processing_metadata.update({
                "processing_time_seconds": processing_time,
                "sub_questions_count": len(decomposition.sub_questions),
                "agents_executed": len(agent_responses),
                "execution_strategy": decomposition.execution_strategy
            })
            
            self.logger.info(f"Question answered successfully in {processing_time:.2f}s")
            return synthesized_response
            
        except Exception as e:
            self.logger.error(f"Question processing failed: {e}")
            return await self._create_error_response(question, company, str(e))
    
    async def _execute_agent_workflow(self, decomposition: QuestionDecomposition) -> List[StructuredAnswer]:
        """Execute specialist agents based on decomposition plan"""
        
        if decomposition.execution_strategy == "parallel":
            return await self._execute_parallel_workflow(decomposition)
        elif decomposition.execution_strategy == "sequential":
            return await self._execute_sequential_workflow(decomposition)
        else:  # hybrid
            return await self._execute_hybrid_workflow(decomposition)
    
    async def _execute_parallel_workflow(self, decomposition: QuestionDecomposition) -> List[StructuredAnswer]:
        """Execute all sub-questions in parallel"""
        
        self.logger.info("Executing parallel agent workflow")
        
        # Create tasks for all sub-questions
        tasks = []
        for sub_question in decomposition.sub_questions:
            task = self._execute_sub_question(sub_question, decomposition.company)
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = []
        for result in results:
            if isinstance(result, StructuredAnswer):
                successful_results.append(result)
            elif isinstance(result, Exception):
                self.logger.warning(f"Sub-question execution failed: {result}")
        
        return successful_results
    
    async def _execute_sequential_workflow(self, decomposition: QuestionDecomposition) -> List[StructuredAnswer]:
        """Execute sub-questions sequentially, respecting dependencies"""
        
        self.logger.info("Executing sequential agent workflow")
        
        results = []
        completed_questions = set()
        
        # Build dependency map
        dependency_map = {sq.id: sq.dependencies for sq in decomposition.sub_questions}
        
        # Execute in dependency order
        while len(completed_questions) < len(decomposition.sub_questions):
            # Find sub-questions ready to execute
            ready_questions = [
                sq for sq in decomposition.sub_questions
                if sq.id not in completed_questions and
                all(dep in completed_questions for dep in sq.dependencies)
            ]
            
            if not ready_questions:
                self.logger.warning("Circular dependency detected or no ready questions")
                break
            
            # Execute ready questions
            for sub_question in ready_questions:
                try:
                    result = await self._execute_sub_question(sub_question, decomposition.company)
                    results.append(result)
                    completed_questions.add(sub_question.id)
                except Exception as e:
                    self.logger.error(f"Sub-question {sub_question.id} failed: {e}")
                    completed_questions.add(sub_question.id)  # Mark as completed to avoid blocking
        
        return results
    
    async def _execute_hybrid_workflow(self, decomposition: QuestionDecomposition) -> List[StructuredAnswer]:
        """Execute with parallel batches respecting dependencies"""
        
        self.logger.info("Executing hybrid agent workflow")
        
        results = []
        completed_questions = set()
        
        while len(completed_questions) < len(decomposition.sub_questions):
            # Find all questions ready to execute (dependencies satisfied)
            ready_questions = [
                sq for sq in decomposition.sub_questions
                if sq.id not in completed_questions and
                all(dep in completed_questions for dep in sq.dependencies)
            ]
            
            if not ready_questions:
                break
            
            # Execute this batch in parallel
            batch_tasks = [
                self._execute_sub_question(sq, decomposition.company)
                for sq in ready_questions
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            for i, result in enumerate(batch_results):
                question_id = ready_questions[i].id
                if isinstance(result, StructuredAnswer):
                    results.append(result)
                else:
                    self.logger.error(f"Sub-question {question_id} failed: {result}")
                completed_questions.add(question_id)
        
        return results
    
    async def _execute_sub_question(self, sub_question, company: str) -> StructuredAnswer:
        """Execute a single sub-question with appropriate agents"""
        
        self.logger.debug(f"Executing sub-question: {sub_question.question}")
        
        # Find best agent for this sub-question
        best_agent = self.agent_router.find_best_agent(sub_question.question, sub_question.target_agents)
        
        if not best_agent:
            raise ValueError(f"No suitable agent found for sub-question: {sub_question.question}")
        
        # Execute with the selected agent
        agent_instance = self.specialist_agents[best_agent]
        
        # Add sub-question context
        context = {
            "sub_question_id": sub_question.id,
            "priority": sub_question.priority,
            "expected_data_type": sub_question.expected_data_type
        }
        
        return await agent_instance.answer_question(sub_question.question, company, context)
    
    async def _create_error_response(self, question: str, company: str, error_message: str) -> SynthesizedIntelligence:
        """Create error response when workflow fails"""
        
        from components.llm_integration.response_synthesizer import SynthesizedIntelligence
        
        return SynthesizedIntelligence(
            original_question=question,
            company=company,
            executive_summary=f"Intelligence gathering failed for {company}: {error_message}",
            key_insights=[f"System error: {error_message}"],
            actionable_intelligence={
                "error": error_message,
                "recommendations": [
                    "Check system configuration",
                    "Verify API keys and service availability",
                    "Try simpler question format"
                ]
            },
            recommendations=[
                {
                    "action": "Debug system configuration",
                    "priority": "high",
                    "timeline": "immediate",
                    "rationale": "System error prevents intelligence gathering",
                    "resources_needed": "technical support",
                    "expected_outcome": "restored functionality",
                    "risk_level": "low"
                }
            ],
            follow_up_questions=["Would you like to try a simpler question format?"],
            confidence_assessment={
                "overall_confidence": 0.0,
                "data_completeness": 0.0,
                "source_reliability": 0.0,
                "limitations": [f"System error: {error_message}"],
                "improvement_recommendations": ["Fix system error and retry"]
            },
            data_sources=[],
            processing_metadata={
                "error": error_message,
                "workflow_status": "failed"
            },
            generated_at=datetime.now().isoformat()
        )
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get status of the workflow system"""
        
        return {
            "llm_client_status": self.llm_client.get_provider_status(),
            "registered_agents": list(self.specialist_agents.keys()),
            "agent_health": {
                name: agent.health_check()
                for name, agent in self.specialist_agents.items()
            }
        }
    
    async def initialize_workflow(self) -> bool:
        """Initialize all workflow components"""
        
        self.logger.info("Initializing Q&A workflow")
        
        try:
            # Initialize all registered agents
            for name, agent in self.specialist_agents.items():
                if not agent.is_initialized():
                    success = await agent.initialize()
                    if not success:
                        self.logger.warning(f"Failed to initialize agent: {name}")
            
            self.logger.info("Q&A workflow initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize workflow: {e}")
            return False
    
    async def cleanup_workflow(self) -> bool:
        """Cleanup all workflow resources"""
        
        self.logger.info("Cleaning up Q&A workflow")
        
        try:
            # Cleanup all agents
            for agent in self.specialist_agents.values():
                await agent.cleanup()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False
