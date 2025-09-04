"""
Intelligence Gathering Workflow
Predefined workflow for comprehensive company intelligence gathering
"""

from typing import Dict, Any
from orchestration.workflow_orchestrator import WorkflowConfig, WorkflowStep

def create_intelligence_workflow() -> WorkflowConfig:
    """Create the standard intelligence gathering workflow"""
    
    return WorkflowConfig(
        name="intelligence_gathering",
        description="Comprehensive company intelligence gathering workflow",
        parallel_execution=False,
        failure_strategy="continue",
        steps=[
            # Step 1: Company Overview Intelligence
            WorkflowStep(
                component_name="company_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "search_depth": "input.search_depth"
                },
                output_mapping={
                    "company_overview": "company_data",
                    "company_confidence": "company_data.confidence_score"
                },
                dependencies=[],
                optional=False
            ),
            
            # Step 2: Executive Intelligence (depends on company data)
            WorkflowStep(
                component_name="executive_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "company_context": "company_data"
                },
                output_mapping={
                    "executive_data": "executives",
                    "leadership_structure": "executives.leadership_structure"
                },
                dependencies=["company_intelligence"],
                optional=False
            ),
            
            # Step 3: Investment Intelligence (parallel with executives)
            WorkflowStep(
                component_name="investment_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "company_type": "company_data.business_model.type"
                },
                output_mapping={
                    "investment_data": "investments",
                    "portfolio_companies": "investments.portfolio_companies"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            # Step 4: News Intelligence (can run in parallel)
            WorkflowStep(
                component_name="news_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "time_range": "input.news_time_range"
                },
                output_mapping={
                    "recent_news": "news",
                    "press_releases": "news.press_releases"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            # Step 5: Data Processing and Synthesis
            WorkflowStep(
                component_name="data_processor",
                input_mapping={
                    "company_data": "company_data",
                    "executive_data": "executives",
                    "investment_data": "investments",
                    "news_data": "news"
                },
                output_mapping={
                    "processed_intelligence": "final_intelligence",
                    "intelligence_score": "final_intelligence.overall_score"
                },
                dependencies=["company_intelligence", "executive_intelligence"],
                optional=False
            ),
            
            # Step 6: Outreach Generation (if enabled)
            WorkflowStep(
                component_name="outreach_generator",
                input_mapping={
                    "intelligence_data": "final_intelligence",
                    "target_executives": "executives.decision_makers",
                    "outreach_config": "input.outreach_settings"
                },
                output_mapping={
                    "outreach_campaign": "outreach"
                },
                dependencies=["data_processor"],
                optional=True
            )
        ]
    )

def create_quick_intelligence_workflow() -> WorkflowConfig:
    """Create a quick intelligence workflow for basic information"""
    
    return WorkflowConfig(
        name="quick_intelligence",
        description="Quick company intelligence gathering for basic information",
        parallel_execution=True,
        failure_strategy="continue",
        steps=[
            # Quick company overview
            WorkflowStep(
                component_name="company_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "search_depth": "basic"
                },
                output_mapping={
                    "company_overview": "company_data"
                },
                dependencies=[],
                optional=False
            ),
            
            # Basic executive info
            WorkflowStep(
                component_name="executive_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "max_executives": "3"
                },
                output_mapping={
                    "key_executives": "executives"
                },
                dependencies=[],
                optional=True
            )
        ]
    )

def create_comprehensive_intelligence_workflow() -> WorkflowConfig:
    """Create a comprehensive intelligence workflow with all available components"""
    
    return WorkflowConfig(
        name="comprehensive_intelligence",
        description="Comprehensive intelligence gathering with all available sources",
        parallel_execution=True,
        failure_strategy="continue",
        steps=[
            # All intelligence components in parallel after company overview
            WorkflowStep(
                component_name="company_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "search_depth": "comprehensive"
                },
                output_mapping={
                    "company_overview": "company_data"
                },
                dependencies=[],
                optional=False
            ),
            
            WorkflowStep(
                component_name="executive_intelligence",
                input_mapping={
                    "company_name": "input.company_name",
                    "company_context": "company_data"
                },
                output_mapping={
                    "executive_data": "executives"
                },
                dependencies=["company_intelligence"],
                optional=False
            ),
            
            WorkflowStep(
                component_name="investment_intelligence",
                input_mapping={
                    "company_name": "input.company_name"
                },
                output_mapping={
                    "investment_data": "investments"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            WorkflowStep(
                component_name="partnership_intelligence",
                input_mapping={
                    "company_name": "input.company_name"
                },
                output_mapping={
                    "partnership_data": "partnerships"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            WorkflowStep(
                component_name="news_intelligence",
                input_mapping={
                    "company_name": "input.company_name"
                },
                output_mapping={
                    "news_data": "news"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            WorkflowStep(
                component_name="digital_presence_intelligence",
                input_mapping={
                    "company_name": "input.company_name"
                },
                output_mapping={
                    "digital_data": "digital_presence"
                },
                dependencies=["company_intelligence"],
                optional=True
            ),
            
            # Synthesis and processing
            WorkflowStep(
                component_name="intelligence_synthesizer",
                input_mapping={
                    "all_intelligence": "."
                },
                output_mapping={
                    "synthesized_intelligence": "final_intelligence"
                },
                dependencies=["company_intelligence", "executive_intelligence"],
                optional=False
            ),
            
            # Generate comprehensive outreach
            WorkflowStep(
                component_name="outreach_generator",
                input_mapping={
                    "intelligence_data": "final_intelligence"
                },
                output_mapping={
                    "outreach_campaign": "outreach"
                },
                dependencies=["intelligence_synthesizer"],
                optional=True
            )
        ]
    )

# Workflow registry for easy access
WORKFLOW_REGISTRY = {
    "standard": create_intelligence_workflow,
    "quick": create_quick_intelligence_workflow,
    "comprehensive": create_comprehensive_intelligence_workflow
}

def get_workflow(workflow_type: str = "standard") -> WorkflowConfig:
    """Get a predefined workflow by type"""
    
    if workflow_type not in WORKFLOW_REGISTRY:
        raise ValueError(f"Unknown workflow type: {workflow_type}. Available: {list(WORKFLOW_REGISTRY.keys())}")
        
    return WORKFLOW_REGISTRY[workflow_type]()
