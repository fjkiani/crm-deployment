#!/usr/bin/env python3
"""
Real API Test: Intelligent Question-Driven CRM System
Tests with actual Tavily and Gemini API keys
"""

import asyncio
import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set API keys
os.environ['TAVILY_API_KEY'] = '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'
os.environ['GEMINI_API_KEY'] = 'AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y'

# Import our intelligent components
from components.llm_integration.llm_client import UnifiedLLMClient, LLMConfig
from components.question_processing.intelligent_qa_workflow import IntelligentQAWorkflow
from components.specialist_agents.executive_intelligence_agent import ExecutiveIntelligenceAgent
from components.specialist_agents.base_specialist import SpecialistConfig

async def test_real_abbey_capital_analysis():
    """Test the intelligent Q&A system with real APIs for Abbey Capital"""
    
    print("🚀 REAL API TEST: Intelligent Question-Driven CRM System")
    print("=" * 70)
    print()
    
    # Your exact question
    question = "For Abbey Capital, find all their decision makers involved in healthcare, what have they invested in recently? what are some gaps?"
    company = "Abbey Capital"
    
    print(f"📋 QUESTION: {question}")
    print(f"🏢 COMPANY: {company}")
    print()
    
    try:
        print("🔧 Initializing Real API Configuration...")
        
        # Configure for Gemini LLM
        llm_config = LLMConfig(
            primary_provider="gemini",
            fallback_providers=["openai", "anthropic"],
            gemini_api_key=os.environ['GEMINI_API_KEY']
        )
        
        print(f"✅ LLM Provider: {llm_config.primary_provider}")
        print(f"✅ Tavily API Key: {os.environ['TAVILY_API_KEY'][:10]}...")
        print(f"✅ Gemini API Key: {os.environ['GEMINI_API_KEY'][:10]}...")
        print()
        
        # Initialize the intelligent Q&A workflow
        print("🤖 Initializing Intelligent Q&A Workflow...")
        qa_workflow = IntelligentQAWorkflow(llm_config)
        
        # Initialize and register specialist agents
        print("👥 Registering Executive Intelligence Agent...")
        
        # Executive Intelligence Agent with real Tavily API
        executive_config = SpecialistConfig(
            name="executive_intelligence",
            api_key=os.environ['TAVILY_API_KEY'],
            rate_limit=1.0,
            timeout=30
        )
        executive_agent = ExecutiveIntelligenceAgent(executive_config)
        qa_workflow.register_specialist_agent(executive_agent)
        
        # Initialize workflow
        print("⚡ Initializing workflow components...")
        success = await qa_workflow.initialize_workflow()
        
        if not success:
            print("❌ Failed to initialize workflow")
            return
        
        print("✅ Workflow initialized successfully!")
        print()
        
        # Execute the intelligent Q&A with real APIs
        print("🧠 Processing question with REAL intelligence agents...")
        print("   📡 Phase 1: Gemini LLM question decomposition")
        print("   🔍 Phase 2: Tavily API intelligence gathering")
        print("   🎯 Phase 3: Gemini LLM response synthesis")
        print()
        
        start_time = datetime.now()
        
        # Add context for better results
        context = {
            "sector": "healthcare",
            "analysis_type": "comprehensive",
            "focus_areas": ["decision_makers", "investments", "gaps"]
        }
        
        result = await qa_workflow.answer_question(question, company, context)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print("🎉 REAL ANALYSIS COMPLETE!")
        print(f"⏱️ Processing time: {processing_time:.2f} seconds")
        print("=" * 50)
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
            
            # Decision makers
            decision_makers = result.actionable_intelligence.get("primary_findings", {}).get("decision_makers", [])
            if decision_makers:
                print("👥 DECISION MAKERS FOUND:")
                for dm in decision_makers[:3]:  # Show top 3
                    if isinstance(dm, dict):
                        name = dm.get('name', 'Unknown')
                        title = dm.get('title', 'Unknown')
                        print(f"  • {name} - {title}")
                print()
            
            # Investments
            investments = result.actionable_intelligence.get("primary_findings", {}).get("investments", [])
            if investments:
                print("💰 RECENT INVESTMENTS:")
                for inv in investments[:3]:  # Show top 3
                    if isinstance(inv, dict):
                        company_name = inv.get('company', 'Unknown')
                        amount = inv.get('amount', 'Unknown')
                        print(f"  • {company_name}: {amount}")
                print()
            
            # Opportunities
            opportunities = result.actionable_intelligence.get("primary_findings", {}).get("opportunities", [])
            if opportunities:
                print("🎯 OPPORTUNITIES:")
                for opp in opportunities[:3]:  # Show top 3
                    if isinstance(opp, dict):
                        gap = opp.get('gap', opp.get('opportunity', 'Unknown'))
                        print(f"  • {gap}")
                print()
        
        print("🚀 IMMEDIATE RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(result.recommendations[:5], 1):  # Show top 5
            if isinstance(rec, dict):
                action = rec.get('action', 'No action specified')
                priority = rec.get('priority', 'medium')
                timeline = rec.get('timeline', 'unspecified')
                print(f"{i}. [{priority.upper()}] {action}")
                if timeline != 'unspecified':
                    print(f"   Timeline: {timeline}")
            else:
                print(f"{i}. {rec}")
        print()
        
        print("❓ INTELLIGENT FOLLOW-UP QUESTIONS")
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
        output_file = f"abbey_capital_REAL_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
            "generated_at": result.generated_at,
            "api_info": {
                "llm_provider": "gemini",
                "intelligence_provider": "tavily",
                "processing_time_seconds": processing_time
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        print(f"📄 Detailed results saved to: {output_file}")
        print()
        
        # Show processing metadata
        print("⚙️ PROCESSING METADATA")
        print("-" * 40)
        metadata = result.processing_metadata
        print(f"Agents Used: {', '.join(metadata.get('agents_used', []))}")
        print(f"Sub-questions: {metadata.get('sub_questions_count', 0)}")
        print(f"Execution Strategy: {metadata.get('execution_strategy', 'unknown')}")
        print(f"Total Sources: {metadata.get('total_sources', 0)}")
        print()
        
        # Cleanup
        await qa_workflow.cleanup_workflow()
        
        print("🎉 REAL API TEST COMPLETED SUCCESSFULLY!")
        print()
        print("🆚 TRANSFORMATION ACHIEVED:")
        print("  ❌ Old: 12,080 lines of redundant data")
        print("  ✅ New: Structured, actionable intelligence")
        print("  ❌ Old: Hours of manual analysis required")  
        print("  ✅ New: Direct answers in 30 seconds")
        print("  ❌ Old: Generic data collection")
        print("  ✅ New: Question-specific specialist agents")
        print("  ❌ Old: No contact information")
        print("  ✅ New: Ready-to-use contact details and approach strategies")
        
    except Exception as e:
        print(f"❌ Real API test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_llm_connection():
    """Test LLM connection separately"""
    
    print("🧪 Testing Gemini LLM Connection...")
    
    try:
        llm_config = LLMConfig(
            primary_provider="gemini",
            gemini_api_key=os.environ['GEMINI_API_KEY']
        )
        
        llm_client = UnifiedLLMClient(llm_config)
        
        test_prompt = "Hello, please respond with 'Gemini LLM connection successful' if you can understand this message."
        
        response = await llm_client.generate(test_prompt)
        
        print(f"✅ Gemini Response: {response.content}")
        print(f"✅ Tokens Used: {response.tokens_used}")
        print(f"✅ Response Time: {response.response_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini LLM test failed: {e}")
        return False

async def test_tavily_connection():
    """Test Tavily connection separately"""
    
    print("🧪 Testing Tavily API Connection...")
    
    try:
        from services.external.tavily_service import TavilyService, TavilyServiceConfig
        
        tavily_config = TavilyServiceConfig(
            name="test_tavily",
            api_key=os.environ['TAVILY_API_KEY']
        )
        
        tavily_service = TavilyService(tavily_config)
        await tavily_service.initialize()
        
        # Test search
        results = await tavily_service.search("Abbey Capital investment firm", max_results=3)
        
        print(f"✅ Tavily Search Results: {len(results.get('results', []))} results found")
        
        if results.get('results'):
            first_result = results['results'][0]
            print(f"✅ First Result: {first_result.get('title', 'No title')}")
            print(f"✅ URL: {first_result.get('url', 'No URL')}")
        
        await tavily_service.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Tavily API test failed: {e}")
        return False

def main():
    """Main test execution"""
    
    print()
    print("🎯 REAL API TESTING: INTELLIGENT QUESTION-DRIVEN CRM")
    print("Testing with actual Tavily and Gemini APIs")
    print()
    
    async def run_tests():
        # Test individual connections first
        print("🔧 Testing Individual API Connections...")
        print()
        
        gemini_ok = await test_llm_connection()
        print()
        
        tavily_ok = await test_tavily_connection()
        print()
        
        if gemini_ok and tavily_ok:
            print("✅ All API connections successful! Running full test...")
            print()
            await test_real_abbey_capital_analysis()
        else:
            print("❌ API connection issues detected. Please check your keys.")
    
    # Run the tests
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
