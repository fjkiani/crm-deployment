#!/usr/bin/env python3
"""
Semantic Intelligence Agent
Leverages Tavily's built-in LLM and semantic search capabilities
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime

class SemanticIntelligenceAgent:
    """Simple agent that leverages Tavily's semantic search and LLM capabilities"""
    
    def __init__(self, tavily_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.name = "SemanticIntelligenceAgent"
    
    def semantic_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Use Tavily's semantic search with built-in LLM answer extraction"""
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_type": "general",
            "max_results": max_results,
            "include_answer": True,  # This uses Tavily's LLM to extract answers
            "include_raw_content": False,  # We don't need raw content, just the semantic answer
            "include_domains": [],
            "exclude_domains": ["wikipedia.org", "dictionary.com", "thefreedictionary.com"]
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    return response_data
                else:
                    return {"error": f"API returned status {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_abbey_capital_intelligence(self) -> Dict[str, Any]:
        """Get intelligence on Abbey Capital using Tavily's semantic capabilities"""
        
        print(f"🔍 {self.name}: Using Tavily's semantic search for Abbey Capital")
        
        # Question 1: Decision Makers
        print("\n👥 QUESTION 1: Who are the decision makers at Abbey Capital?")
        decision_makers_query = "Abbey Capital decision makers executives leadership team partners directors investment committee"
        dm_results = self.semantic_search(decision_makers_query, max_results=5)
        
        print(f"📊 Tavily Answer: {dm_results.get('answer', 'No answer provided')}")
        print(f"📄 Sources: {len(dm_results.get('results', []))} found")
        
        # Question 2: Recent Investments  
        print("\n💰 QUESTION 2: What has Abbey Capital invested in recently?")
        investments_query = "Abbey Capital recent investments portfolio companies deals 2023 2024 funding acquisitions"
        inv_results = self.semantic_search(investments_query, max_results=5)
        
        print(f"📊 Tavily Answer: {inv_results.get('answer', 'No answer provided')}")
        print(f"📄 Sources: {len(inv_results.get('results', []))} found")
        
        # Question 3: Investment Gaps
        print("\n🎯 QUESTION 3: What are Abbey Capital's investment gaps and opportunities?")
        gaps_query = "Abbey Capital investment strategy gaps opportunities sectors missing from portfolio whitespace"
        gaps_results = self.semantic_search(gaps_query, max_results=5)
        
        print(f"📊 Tavily Answer: {gaps_results.get('answer', 'No answer provided')}")
        print(f"📄 Sources: {len(gaps_results.get('results', []))} found")
        
        # Compile comprehensive results
        intelligence = {
            "company": "Abbey Capital",
            "analysis_timestamp": datetime.now().isoformat(),
            "decision_makers": {
                "query": decision_makers_query,
                "tavily_answer": dm_results.get('answer', 'No answer provided'),
                "sources": dm_results.get('results', []),
                "source_count": len(dm_results.get('results', []))
            },
            "recent_investments": {
                "query": investments_query,
                "tavily_answer": inv_results.get('answer', 'No answer provided'),
                "sources": inv_results.get('results', []),
                "source_count": len(inv_results.get('results', []))
            },
            "investment_gaps": {
                "query": gaps_query,
                "tavily_answer": gaps_results.get('answer', 'No answer provided'),
                "sources": gaps_results.get('results', []),
                "source_count": len(gaps_results.get('results', []))
            },
            "total_sources": len(dm_results.get('results', [])) + len(inv_results.get('results', [])) + len(gaps_results.get('results', [])),
            "method": "tavily_semantic_search_with_llm"
        }
        
        return intelligence
    
    def display_results(self, intelligence: Dict[str, Any]):
        """Display the semantic intelligence results"""
        
        print("\n" + "="*70)
        print("🧠 SEMANTIC INTELLIGENCE RESULTS")
        print("="*70)
        
        print(f"\n🏢 COMPANY: {intelligence['company']}")
        print(f"⏱️ ANALYZED: {intelligence['analysis_timestamp']}")
        print(f"📊 TOTAL SOURCES: {intelligence['total_sources']}")
        print(f"🔍 METHOD: {intelligence['method']}")
        
        print(f"\n👥 DECISION MAKERS:")
        print(f"   Query: {intelligence['decision_makers']['query']}")
        print(f"   Tavily Answer: {intelligence['decision_makers']['tavily_answer']}")
        print(f"   Sources: {intelligence['decision_makers']['source_count']}")
        
        print(f"\n💰 RECENT INVESTMENTS:")
        print(f"   Query: {intelligence['recent_investments']['query']}")
        print(f"   Tavily Answer: {intelligence['recent_investments']['tavily_answer']}")
        print(f"   Sources: {intelligence['recent_investments']['source_count']}")
        
        print(f"\n🎯 INVESTMENT GAPS:")
        print(f"   Query: {intelligence['investment_gaps']['query']}")
        print(f"   Tavily Answer: {intelligence['investment_gaps']['tavily_answer']}")
        print(f"   Sources: {intelligence['investment_gaps']['source_count']}")
        
        # Show source details
        print(f"\n📄 SOURCE DETAILS:")
        all_sources = (
            intelligence['decision_makers']['sources'] + 
            intelligence['recent_investments']['sources'] + 
            intelligence['investment_gaps']['sources']
        )
        
        for i, source in enumerate(all_sources[:10], 1):  # Show top 10 sources
            print(f"   {i}. {source.get('title', 'No title')}")
            print(f"      URL: {source.get('url', 'No URL')}")
            print(f"      Content: {source.get('content', '')[:100]}...")
            print()

def main():
    """Test semantic intelligence agent"""
    
    print("🔍 SEMANTIC INTELLIGENCE AGENT")
    print("Leveraging Tavily's built-in LLM and semantic search")
    print()
    
    # API key
    TAVILY_API_KEY = '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'
    
    # Initialize agent
    agent = SemanticIntelligenceAgent(TAVILY_API_KEY)
    
    # Run analysis
    start_time = datetime.now()
    intelligence = agent.analyze_abbey_capital_intelligence()
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Display results
    agent.display_results(intelligence)
    
    print(f"\n⏱️ PROCESSING TIME: {processing_time:.2f} seconds")
    
    # Save results
    output_file = f"abbey_capital_SEMANTIC_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(intelligence, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {output_file}")
    
    print(f"\n🎯 KEY INSIGHT:")
    print("This approach leverages Tavily's built-in LLM to extract semantic answers")
    print("instead of writing hundreds of lines of pattern matching code!")

if __name__ == "__main__":
    main()
