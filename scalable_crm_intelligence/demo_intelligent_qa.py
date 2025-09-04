#!/usr/bin/env python3
"""
Demo: Intelligent Question-Driven CRM System
Demonstrates the new architecture with Abbey Capital healthcare analysis example
"""

import asyncio
import os
import json
from datetime import datetime

# Import our new intelligent components
from components.llm_integration.llm_client import UnifiedLLMClient, LLMConfig
from components.question_processing.intelligent_qa_workflow import IntelligentQAWorkflow
from components.specialist_agents.executive_intelligence_agent import ExecutiveIntelligenceAgent
from components.specialist_agents.base_specialist import SpecialistConfig

async def demo_abbey_capital_analysis():
    """Demo the intelligent Q&A system with Abbey Capital healthcare question"""
    
    print("🚀 Intelligent Question-Driven CRM Demo")
    print("=" * 60)
    print()
    
    # Example question from user requirements
    question = "For Abbey Capital, find all their decision makers involved in healthcare, what have they invested in recently? what are some gaps?"
    company = "Abbey Capital"
    
    print(f"📋 Question: {question}")
    print(f"🏢 Company: {company}")
    print()
    
    try:
        # Initialize LLM configuration
        llm_config = LLMConfig(
            primary_provider="openai",  # Change to your preferred provider
            fallback_providers=["anthropic"]
        )
        
        # Check if API keys are available
        if not llm_config.openai_api_key and not llm_config.anthropic_api_key:
            print("⚠️ No LLM API keys found - using mock responses for demo")
            return await demo_with_mock_responses(question, company)
        
        # Initialize the intelligent Q&A workflow
        print("🔧 Initializing Intelligent Q&A Workflow...")
        qa_workflow = IntelligentQAWorkflow(llm_config)
        
        # Initialize and register specialist agents
        print("🤖 Registering Specialist Agents...")
        
        # Executive Intelligence Agent
        executive_config = SpecialistConfig(
            name="executive_intelligence",
            api_key=os.getenv('TAVILY_API_KEY', 'demo_key'),
            rate_limit=1.0
        )
        executive_agent = ExecutiveIntelligenceAgent(executive_config)
        qa_workflow.register_specialist_agent(executive_agent)
        
        # Initialize workflow
        print("⚡ Initializing workflow components...")
        await qa_workflow.initialize_workflow()
        
        # Execute the intelligent Q&A
        print("🧠 Processing question with intelligent agents...")
        print("   Phase 1: Question decomposition")
        print("   Phase 2: Agent routing and execution")
        print("   Phase 3: Response synthesis")
        print()
        
        start_time = datetime.now()
        result = await qa_workflow.answer_question(question, company)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print("✅ Analysis Complete!")
        print(f"⏱️ Processing time: {processing_time:.2f} seconds")
        print()
        
        print("📊 EXECUTIVE SUMMARY")
        print("-" * 40)
        print(result.executive_summary)
        print()
        
        print("🔑 KEY INSIGHTS")
        print("-" * 40)
        for i, insight in enumerate(result.key_insights, 1):
            print(f"{i}. {insight}")
        print()
        
        print("🎯 ACTIONABLE INTELLIGENCE")
        print("-" * 40)
        if result.actionable_intelligence:
            for category, data in result.actionable_intelligence.items():
                if isinstance(data, dict) and data:
                    print(f"• {category.replace('_', ' ').title()}:")
                    if isinstance(data, dict):
                        for key, value in list(data.items())[:3]:  # Show first 3 items
                            print(f"  - {key}: {str(value)[:100]}...")
                elif isinstance(data, list) and data:
                    print(f"• {category.replace('_', ' ').title()}: {len(data)} items found")
        print()
        
        print("🚀 IMMEDIATE RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(result.recommendations[:5], 1):  # Show top 5
            if isinstance(rec, dict):
                action = rec.get('action', 'No action specified')
                priority = rec.get('priority', 'medium')
                timeline = rec.get('timeline', 'unspecified')
                print(f"{i}. [{priority.upper()}] {action} (Timeline: {timeline})")
            else:
                print(f"{i}. {rec}")
        print()
        
        print("❓ FOLLOW-UP QUESTIONS")
        print("-" * 40)
        for i, question in enumerate(result.follow_up_questions, 1):
            print(f"{i}. {question}")
        print()
        
        print("📈 CONFIDENCE ASSESSMENT")
        print("-" * 40)
        conf = result.confidence_assessment
        print(f"Overall Confidence: {conf.get('overall_confidence', 0):.1%}")
        print(f"Data Completeness: {conf.get('data_completeness', 0):.1%}")
        print(f"Source Reliability: {conf.get('source_reliability', 0):.1%}")
        
        if conf.get('limitations'):
            print("\nLimitations:")
            for limitation in conf['limitations'][:3]:
                print(f"• {limitation}")
        print()
        
        print("📚 DATA SOURCES")
        print("-" * 40)
        print(f"Total sources: {len(result.data_sources)}")
        for source in result.data_sources[:5]:  # Show first 5 sources
            print(f"• {source}")
        if len(result.data_sources) > 5:
            print(f"• ... and {len(result.data_sources) - 5} more sources")
        print()
        
        # Save detailed results
        output_file = f"abbey_capital_intelligent_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert result to dictionary for JSON serialization
        result_dict = {
            "original_question": result.original_question,
            "company": result.company,
            "executive_summary": result.executive_summary,
            "key_insights": result.key_insights,
            "actionable_intelligence": result.actionable_intelligence,
            "recommendations": result.recommendations,
            "follow_up_questions": result.follow_up_questions,
            "confidence_assessment": result.confidence_assessment,
            "data_sources": result.data_sources,
            "processing_metadata": result.processing_metadata,
            "generated_at": result.generated_at
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        print(f"📄 Detailed results saved to: {output_file}")
        print()
        
        # Cleanup
        await qa_workflow.cleanup_workflow()
        
        print("🎉 Demo completed successfully!")
        print()
        print("🆚 COMPARISON TO OLD SYSTEM:")
        print("  Old: 12,080 lines of redundant data")
        print("  New: Structured, actionable intelligence")
        print("  Old: Manual sifting required")
        print("  New: Direct answers with recommendations")
        print("  Old: Generic data collection")
        print("  New: Question-specific specialist agents")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

async def demo_with_mock_responses(question: str, company: str):
    """Demo with mock responses when API keys are not available"""
    
    print("🎭 Running demo with mock responses...")
    print()
    
    # Mock response that demonstrates the new format
    mock_result = {
        "original_question": question,
        "company": company,
        "executive_summary": f"Abbey Capital has 3 key healthcare decision makers identified and completed 5 healthcare investments totaling $120M in the past 18 months, with strong focus on digital health and AI diagnostics.",
        
        "key_insights": [
            "Dr. Sarah Johnson leads healthcare investments with $50M decision authority",
            "Strong preference for AI-enabled healthcare solutions over traditional medtech",
            "Geographic expansion into European healthcare markets shows growth strategy",
            "Portfolio lacks surgical robotics exposure - significant opportunity gap"
        ],
        
        "actionable_intelligence": {
            "decision_makers": [
                {
                    "name": "Dr. Sarah Johnson",
                    "title": "Healthcare Investment Director",
                    "decision_authority": "Direct approval up to $50M",
                    "expertise": ["Digital Health", "AI Diagnostics", "Biotech"],
                    "contact_info": {"email": "s.johnson@abbeycapital.com"},
                    "approach_strategy": "Focus on AI-driven healthcare innovations"
                }
            ],
            
            "recent_investments": [
                {
                    "company": "HealthAI Corp",
                    "amount": "$30M",
                    "date": "2024-08-15",
                    "stage": "Series B", 
                    "subsector": "AI Diagnostics",
                    "decision_maker": "Dr. Sarah Johnson"
                }
            ],
            
            "identified_gaps": [
                {
                    "gap": "Limited surgical robotics exposure",
                    "opportunity": "$200M+ investable market",
                    "priority": "high",
                    "recommended_action": "Target robotics startups in Series A/B"
                }
            ]
        },
        
        "recommendations": [
            {
                "action": "Schedule intro call with Dr. Sarah Johnson",
                "priority": "high",
                "timeline": "immediate",
                "rationale": "Primary healthcare decision maker with direct authority",
                "resources_needed": "warm introduction, healthcare AI deck"
            },
            {
                "action": "Prepare surgical robotics investment thesis",
                "priority": "medium",
                "timeline": "2 weeks",
                "rationale": "Major portfolio gap with high opportunity value"
            }
        ],
        
        "follow_up_questions": [
            "What specific healthcare AI technologies is Abbey most interested in?",
            "Are there geographic preferences for healthcare investments?",
            "What was the decision criteria for the HealthAI Corp investment?"
        ],
        
        "confidence_assessment": {
            "overall_confidence": 0.87,
            "data_completeness": 0.82,
            "source_reliability": 0.90,
            "limitations": ["Mock data for demo purposes"]
        }
    }
    
    # Display mock results in same format
    print("✅ Mock Analysis Complete!")
    print()
    
    print("📊 EXECUTIVE SUMMARY")
    print("-" * 40)
    print(mock_result["executive_summary"])
    print()
    
    print("🔑 KEY INSIGHTS")
    print("-" * 40)
    for i, insight in enumerate(mock_result["key_insights"], 1):
        print(f"{i}. {insight}")
    print()
    
    print("🎯 DECISION MAKERS FOUND")
    print("-" * 40)
    for dm in mock_result["actionable_intelligence"]["decision_makers"]:
        print(f"• {dm['name']} - {dm['title']}")
        print(f"  Authority: {dm['decision_authority']}")
        print(f"  Email: {dm['contact_info'].get('email', 'Not found')}")
        print(f"  Strategy: {dm['approach_strategy']}")
        print()
    
    print("💰 RECENT INVESTMENTS")
    print("-" * 40)
    for inv in mock_result["actionable_intelligence"]["recent_investments"]:
        print(f"• {inv['company']}: {inv['amount']} ({inv['stage']}) - {inv['date']}")
        print(f"  Sector: {inv['subsector']}")
        print(f"  Decision Maker: {inv['decision_maker']}")
        print()
    
    print("🎯 STRATEGIC GAPS")
    print("-" * 40)
    for gap in mock_result["actionable_intelligence"]["identified_gaps"]:
        print(f"• {gap['gap']}")
        print(f"  Opportunity: {gap['opportunity']}")
        print(f"  Action: {gap['recommended_action']}")
        print()
    
    print("🚀 IMMEDIATE RECOMMENDATIONS")
    print("-" * 40)
    for i, rec in enumerate(mock_result["recommendations"], 1):
        print(f"{i}. [{rec['priority'].upper()}] {rec['action']}")
        print(f"   Timeline: {rec['timeline']}")
        print(f"   Why: {rec['rationale']}")
        print()
    
    print("📈 CONFIDENCE ASSESSMENT")
    print("-" * 40)
    conf = mock_result["confidence_assessment"]
    print(f"Overall Confidence: {conf['overall_confidence']:.1%}")
    print(f"Data Completeness: {conf['data_completeness']:.1%}")
    print(f"Source Reliability: {conf['source_reliability']:.1%}")
    print()
    
    print("🎉 Mock Demo Complete!")
    print()
    print("🆚 THIS IS THE NEW FORMAT vs OLD SYSTEM:")
    print("❌ Old: 12,080 lines of repetitive, meaningless data")
    print("✅ New: Structured answers with specific names, amounts, and actions")
    print("❌ Old: Manual sifting through redundant information")  
    print("✅ New: Direct answers with prioritized recommendations")
    print("❌ Old: Generic data dumps regardless of question")
    print("✅ New: Question-specific intelligence from specialist agents")

def main():
    """Main demo execution"""
    
    print()
    print("🎯 INTELLIGENT QUESTION-DRIVEN CRM SYSTEM")
    print("Transforming from data dumps to actionable intelligence")
    print()
    
    # Check for required environment variables
    tavily_key = os.getenv('TAVILY_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY') 
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not tavily_key:
        print("⚠️ TAVILY_API_KEY not set - will use limited functionality")
    if not openai_key and not anthropic_key:
        print("⚠️ No LLM API keys found - will demonstrate with mock responses")
    
    print()
    
    # Run the demo
    asyncio.run(demo_abbey_capital_analysis())

if __name__ == "__main__":
    main()
