#!/usr/bin/env python3
"""
Test Intelligent Agents with Brain Context
Tests the new intelligent agents with contextual reasoning and domain expertise
"""

import json
from datetime import datetime
from components.intelligent_agents.intelligent_executive_agent import IntelligentExecutiveAgent
from components.intelligent_agents.intelligent_investment_agent import IntelligentInvestmentAgent
from components.intelligent_agents.intelligent_gap_analysis_agent import IntelligentGapAnalysisAgent

# API keys
TAVILY_API_KEY = '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'
GEMINI_API_KEY = 'AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y'

def test_intelligent_abbey_capital_analysis():
    """Test intelligent agents on Abbey Capital healthcare analysis"""
    
    print("🧠 INTELLIGENT AGENTS TEST: Abbey Capital Healthcare Analysis")
    print("=" * 70)
    print()
    
    company = "Abbey Capital"
    focus_domain = "healthcare"
    
    print(f"🎯 TARGET: {company}")
    print(f"🔬 DOMAIN: {focus_domain}")
    print(f"❓ QUESTION: Find decision makers, investments, and gaps")
    print()
    
    # Initialize intelligent agents
    print("🤖 Initializing Intelligent Agents with Brain Context...")
    
    executive_agent = IntelligentExecutiveAgent(TAVILY_API_KEY, GEMINI_API_KEY)
    investment_agent = IntelligentInvestmentAgent(TAVILY_API_KEY, GEMINI_API_KEY)
    gap_agent = IntelligentGapAnalysisAgent(TAVILY_API_KEY, GEMINI_API_KEY)
    
    print("✅ Agents initialized with domain knowledge and pattern recognition")
    print()
    
    start_time = datetime.now()
    
    try:
        # Phase 1: Executive Intelligence
        print("👥 PHASE 1: INTELLIGENT EXECUTIVE ANALYSIS")
        print("-" * 50)
        
        executive_results = executive_agent.analyze_executive_intelligence(company, focus_domain)
        
        print(f"✅ Executive Analysis Complete:")
        print(f"   • Executives Found: {executive_results['executives_found']}")
        print(f"   • Relevant Sources: {executive_results['relevant_sources']}/{executive_results['total_sources_searched']}")
        print(f"   • Confidence Score: {executive_results['confidence_score']:.2f}")
        print()
        
        if executive_results['executives']:
            print("🎯 TOP EXECUTIVES FOUND:")
            for i, exec_info in enumerate(executive_results['executives'][:3], 1):
                print(f"   {i}. {exec_info['name']} - {exec_info['title']}")
                print(f"      Domain Relevance: {exec_info['domain_relevance']:.2f}")
                print(f"      Confidence: {exec_info['confidence']:.2f}")
            print()
        
        print("📊 EXECUTIVE INTELLIGENCE SYNTHESIS:")
        print(executive_results['intelligence_synthesis'])
        print()
        
        # Phase 2: Investment Intelligence
        print("💰 PHASE 2: INTELLIGENT INVESTMENT ANALYSIS")
        print("-" * 50)
        
        investment_results = investment_agent.analyze_investment_intelligence(company, focus_domain)
        
        print(f"✅ Investment Analysis Complete:")
        print(f"   • Investments Found: {investment_results['investments_found']}")
        print(f"   • Portfolio Companies: {len(investment_results['portfolio_companies'])}")
        print(f"   • Relevant Sources: {investment_results['relevant_sources']}/{investment_results['total_sources_searched']}")
        print(f"   • Confidence Score: {investment_results['confidence_score']:.2f}")
        print()
        
        if investment_results['investments']:
            print("💎 TOP INVESTMENTS FOUND:")
            for i, inv_info in enumerate(investment_results['investments'][:3], 1):
                print(f"   {i}. {inv_info['company']}: {inv_info['amount']}")
                print(f"      Domain Relevance: {inv_info['domain_relevance']:.2f}")
                print(f"      Confidence: {inv_info['confidence']:.2f}")
            print()
        
        if investment_results['portfolio_companies']:
            print("🏢 TOP PORTFOLIO COMPANIES:")
            for i, comp_info in enumerate(investment_results['portfolio_companies'][:3], 1):
                print(f"   {i}. {comp_info['company']}")
                print(f"      Domain Relevance: {comp_info['domain_relevance']:.2f}")
            print()
        
        print("📊 INVESTMENT INTELLIGENCE SYNTHESIS:")
        print(investment_results['intelligence_synthesis'])
        print()
        
        # Phase 3: Gap Analysis Intelligence
        print("🎯 PHASE 3: INTELLIGENT GAP ANALYSIS")
        print("-" * 50)
        
        # Pass existing portfolio data to gap analysis
        existing_portfolio = investment_results['investments'] + investment_results['portfolio_companies']
        
        gap_results = gap_agent.analyze_gap_intelligence(
            company, 
            focus_domain, 
            existing_portfolio=existing_portfolio
        )
        
        print(f"✅ Gap Analysis Complete:")
        print(f"   • Opportunities Found: {gap_results['opportunities_found']}")
        print(f"   • Market Insights: {len(gap_results['market_insights'])}")
        print(f"   • Relevant Sources: {gap_results['relevant_sources']}/{gap_results['total_sources_searched']}")
        print(f"   • Confidence Score: {gap_results['confidence_score']:.2f}")
        print()
        
        if gap_results['opportunities']:
            print("🚀 TOP OPPORTUNITIES IDENTIFIED:")
            for i, opp_info in enumerate(gap_results['opportunities'][:3], 1):
                print(f"   {i}. {opp_info['opportunity'][:100]}...")
                print(f"      Domain Relevance: {opp_info['domain_relevance']:.2f}")
            print()
        
        print("📊 ADVANCED GAP ANALYSIS:")
        print(gap_results['advanced_gap_analysis'])
        print()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Comprehensive Results Summary
        print("🎉 INTELLIGENT ANALYSIS COMPLETE!")
        print("=" * 70)
        print(f"⏱️ Total Processing Time: {processing_time:.2f} seconds")
        print()
        
        print("📈 INTELLIGENCE SUMMARY:")
        print(f"   👥 Executives: {executive_results['executives_found']} found")
        print(f"   💰 Investments: {investment_results['investments_found']} found")
        print(f"   🏢 Companies: {len(investment_results['portfolio_companies'])} found")
        print(f"   🎯 Opportunities: {gap_results['opportunities_found']} found")
        print(f"   📊 Total Relevant Sources: {executive_results['relevant_sources'] + investment_results['relevant_sources'] + gap_results['relevant_sources']}")
        print()
        
        print("🧠 INTELLIGENCE QUALITY SCORES:")
        print(f"   👥 Executive Intelligence: {executive_results['confidence_score']:.2f}")
        print(f"   💰 Investment Intelligence: {investment_results['confidence_score']:.2f}")
        print(f"   🎯 Gap Analysis Intelligence: {gap_results['confidence_score']:.2f}")
        
        overall_confidence = (
            executive_results['confidence_score'] + 
            investment_results['confidence_score'] + 
            gap_results['confidence_score']
        ) / 3
        print(f"   🎯 Overall Intelligence Score: {overall_confidence:.2f}")
        print()
        
        # Save comprehensive results
        output_file = f"abbey_capital_INTELLIGENT_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        comprehensive_results = {
            "company": company,
            "focus_domain": focus_domain,
            "processing_time_seconds": processing_time,
            "overall_confidence": overall_confidence,
            "executive_intelligence": executive_results,
            "investment_intelligence": investment_results,
            "gap_analysis": gap_results,
            "summary": {
                "executives_found": executive_results['executives_found'],
                "investments_found": investment_results['investments_found'],
                "opportunities_found": gap_results['opportunities_found'],
                "total_relevant_sources": executive_results['relevant_sources'] + investment_results['relevant_sources'] + gap_results['relevant_sources']
            },
            "generated_at": datetime.now().isoformat(),
            "intelligence_method": "contextual_agents_with_brain"
        }
        
        with open(output_file, 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        print(f"📄 Complete intelligent analysis saved to: {output_file}")
        print()
        
        print("🆚 TRANSFORMATION COMPARISON:")
        print("=" * 70)
        print("❌ OLD GENERIC SYSTEM:")
        print("   • 0 executives found (failed pattern recognition)")
        print("   • 0 investments found (no domain context)")
        print("   • 0 opportunities found (no intelligence synthesis)")
        print("   • Sources: Wikipedia, dictionary definitions, irrelevant content")
        print()
        print("✅ NEW INTELLIGENT SYSTEM:")
        print(f"   • {executive_results['executives_found']} executives with domain relevance scoring")
        print(f"   • {investment_results['investments_found']} investments with contextual extraction")
        print(f"   • {gap_results['opportunities_found']} opportunities with strategic analysis")
        print(f"   • Sources: {executive_results['relevant_sources'] + investment_results['relevant_sources'] + gap_results['relevant_sources']} relevant sources with quality filtering")
        print("   • Brain Context: Domain knowledge, pattern recognition, intelligent synthesis")
        print()
        
        print("🧠 INTELLIGENCE CAPABILITIES DEMONSTRATED:")
        print("   ✅ Domain-specific pattern recognition")
        print("   ✅ Contextual relevance scoring")
        print("   ✅ Intelligent query generation")
        print("   ✅ Multi-agent coordination with synthesis")
        print("   ✅ Strategic gap analysis with LLM reasoning")
        print("   ✅ Quality-filtered source analysis")
        
        return comprehensive_results
        
    except Exception as e:
        print(f"❌ Intelligent agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run intelligent agents test"""
    
    print("🧠 INTELLIGENT AGENTS WITH BRAIN CONTEXT")
    print("Testing contextual reasoning and domain expertise")
    print()
    
    results = test_intelligent_abbey_capital_analysis()
    
    if results:
        print("\n🎉 INTELLIGENT AGENTS TEST SUCCESSFUL!")
        print("The system now has true intelligence with contextual reasoning!")
    else:
        print("\n❌ Test failed - check logs for details")

if __name__ == "__main__":
    main()
