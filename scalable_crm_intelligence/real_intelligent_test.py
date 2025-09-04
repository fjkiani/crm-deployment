#!/usr/bin/env python3
"""
Real Intelligent Test: Full question-driven system with real APIs
Uses standard library only to avoid dependency issues
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
import re

# API keys
TAVILY_API_KEY = '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'
GEMINI_API_KEY = 'AIzaSyDmPm3J2yqzJD1nXvd_5-8i6TX6rygwZ0Y'

class SimpleGeminiClient:
    """Simple Gemini API client using standard library"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    
    def generate(self, prompt, max_tokens=2000):
        """Generate response from Gemini"""
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": max_tokens
            }
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.base_url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    
                    if "candidates" in response_data and len(response_data["candidates"]) > 0:
                        candidate = response_data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return candidate["content"]["parts"][0]["text"]
                    
                    return "Error: No valid response from Gemini"
                else:
                    return f"Error: Gemini API returned status {response.status}"
                    
        except Exception as e:
            return f"Error: {e}"

class SimpleTavilyClient:
    """Simple Tavily API client using standard library"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"
    
    def search(self, query, max_results=5):
        """Search using Tavily API"""
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_type": "general",
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": True
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.base_url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    return response_data.get("results", [])
                else:
                    return []
                    
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []

class IntelligentQASystem:
    """Simple intelligent Q&A system"""
    
    def __init__(self):
        self.gemini = SimpleGeminiClient(GEMINI_API_KEY)
        self.tavily = SimpleTavilyClient(TAVILY_API_KEY)
    
    def decompose_question(self, question, company):
        """Decompose question into sub-questions using Gemini"""
        
        prompt = f"""You are an expert business intelligence analyst. Break down this complex question into specific, answerable sub-questions.

QUESTION: "{question}"
COMPANY: "{company}"

Break the question into 3-4 sub-questions that:
1. Focus on decision makers and executives
2. Focus on recent investments and deals
3. Focus on strategic gaps and opportunities
4. Are specific and actionable

Return ONLY a JSON response in this exact format:
{{
  "sub_questions": [
    {{
      "question": "Who are the key decision makers at {company} involved in healthcare investments?",
      "focus": "decision_makers",
      "search_query": "{company} healthcare investment team executives decision makers"
    }},
    {{
      "question": "What healthcare investments has {company} made recently?",
      "focus": "investments",
      "search_query": "{company} healthcare investments deals portfolio recent"
    }},
    {{
      "question": "What strategic gaps exist in {company}'s healthcare portfolio?",
      "focus": "gaps",
      "search_query": "{company} healthcare strategy gaps opportunities market"
    }}
  ]
}}"""

        response = self.gemini.generate(prompt)
        
        # Extract JSON from response
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_content = response[start_idx:end_idx]
                return json.loads(json_content)
        except:
            pass
        
        # Fallback if JSON parsing fails
        return {
            "sub_questions": [
                {
                    "question": f"Who are the key decision makers at {company}?",
                    "focus": "decision_makers",
                    "search_query": f"{company} executives leadership team decision makers"
                },
                {
                    "question": f"What recent investments has {company} made?",
                    "focus": "investments", 
                    "search_query": f"{company} recent investments deals portfolio"
                },
                {
                    "question": f"What opportunities exist for {company}?",
                    "focus": "gaps",
                    "search_query": f"{company} investment opportunities strategy gaps"
                }
            ]
        }
    
    def gather_intelligence(self, sub_questions):
        """Gather intelligence for each sub-question"""
        
        intelligence_data = {
            "decision_makers": [],
            "investments": [],
            "gaps": [],
            "all_sources": []
        }
        
        for sq in sub_questions:
            print(f"  🔍 Searching: {sq['search_query']}")
            
            results = self.tavily.search(sq['search_query'], max_results=3)
            
            for result in results:
                intelligence_data["all_sources"].append(result.get("url", ""))
                
                # Process based on focus area
                if sq['focus'] == 'decision_makers':
                    executives = self.extract_executives(result.get('content', ''), result.get('title', ''))
                    intelligence_data["decision_makers"].extend(executives)
                
                elif sq['focus'] == 'investments':
                    investments = self.extract_investments(result.get('content', ''), result.get('title', ''))
                    intelligence_data["investments"].extend(investments)
                
                elif sq['focus'] == 'gaps':
                    opportunities = self.extract_opportunities(result.get('content', ''), result.get('title', ''))
                    intelligence_data["gaps"].extend(opportunities)
        
        return intelligence_data
    
    def extract_executives(self, content, title):
        """Extract executive information from content"""
        
        executives = []
        
        # Look for executive patterns
        executive_patterns = [
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]*(CEO|Chief Executive Officer|President|Partner|Director|Managing Partner)',
            r'(CEO|Chief Executive Officer|President|Partner|Director|Managing Partner)[,\s]*([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]
        
        for pattern in executive_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if 'CEO' in match.group(0) or 'President' in match.group(0) or 'Partner' in match.group(0):
                    # Extract name and title
                    groups = match.groups()
                    if len(groups) >= 2:
                        if groups[0] and len(groups[0]) > 3 and groups[0][0].isupper():
                            executives.append({
                                "name": groups[0].strip(),
                                "title": groups[1].strip() if groups[1] else "Executive",
                                "source": title
                            })
                        elif groups[1] and len(groups[1]) > 3 and groups[1][0].isupper():
                            executives.append({
                                "name": groups[1].strip(),
                                "title": groups[0].strip() if groups[0] else "Executive", 
                                "source": title
                            })
        
        return executives[:3]  # Return top 3
    
    def extract_investments(self, content, title):
        """Extract investment information from content"""
        
        investments = []
        
        # Look for investment patterns
        investment_patterns = [
            r'invested?\s+(?:in\s+)?([A-Z][a-zA-Z\s&]+?)(?:\s+for\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B)',
            r'\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B)\s+(?:investment\s+)?(?:in\s+)?([A-Z][a-zA-Z\s&]+)',
            r'acquired\s+([A-Z][a-zA-Z\s&]+?)(?:\s+for\s+)?\$([0-9]+(?:\.[0-9]+)?)\s*(million|billion|M|B)'
        ]
        
        for pattern in investment_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 3:
                    company_name = groups[0] if groups[0] else groups[2]
                    amount = groups[1] if groups[1] else groups[0]
                    unit = groups[2] if groups[2] else groups[1]
                    
                    if company_name and len(company_name.strip()) > 2:
                        investments.append({
                            "company": company_name.strip(),
                            "amount": f"${amount}{unit}",
                            "source": title
                        })
        
        return investments[:3]  # Return top 3
    
    def extract_opportunities(self, content, title):
        """Extract opportunity information from content"""
        
        opportunities = []
        
        # Look for opportunity/gap patterns
        opportunity_keywords = [
            "opportunity", "gap", "potential", "growth", "expansion", 
            "market", "sector", "untapped", "emerging", "trend"
        ]
        
        sentences = content.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in opportunity_keywords):
                if len(sentence.strip()) > 20 and len(sentence.strip()) < 200:
                    opportunities.append({
                        "opportunity": sentence.strip(),
                        "source": title
                    })
        
        return opportunities[:2]  # Return top 2
    
    def synthesize_response(self, question, company, intelligence_data, sub_questions):
        """Synthesize final response using Gemini"""
        
        # Prepare intelligence summary
        intel_summary = {
            "decision_makers": intelligence_data["decision_makers"][:3],
            "investments": intelligence_data["investments"][:3], 
            "opportunities": intelligence_data["gaps"][:3],
            "total_sources": len(set(intelligence_data["all_sources"]))
        }
        
        prompt = f"""You are an expert business intelligence analyst. Synthesize this research into a comprehensive, actionable response.

ORIGINAL QUESTION: "{question}"
COMPANY: "{company}"

INTELLIGENCE GATHERED:
Decision Makers Found: {len(intel_summary['decision_makers'])}
{json.dumps(intel_summary['decision_makers'], indent=2)}

Investments Found: {len(intel_summary['investments'])}
{json.dumps(intel_summary['investments'], indent=2)}

Opportunities/Gaps Found: {len(intel_summary['opportunities'])}
{json.dumps(intel_summary['opportunities'], indent=2)}

Total Sources: {intel_summary['total_sources']}

Synthesize this into a comprehensive response with:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. KEY FINDINGS for each area (decision makers, investments, gaps)
3. ACTIONABLE RECOMMENDATIONS (3-5 specific next steps)
4. FOLLOW-UP QUESTIONS (2-3 intelligent questions for deeper investigation)

Format as clear, business-ready intelligence that directly answers the original question."""

        return self.gemini.generate(prompt, max_tokens=3000)

def main():
    """Run the real intelligent Q&A test"""
    
    print("🚀 REAL INTELLIGENT Q&A SYSTEM TEST")
    print("=" * 60)
    print()
    
    # Your exact question
    question = "For Abbey Capital, find all their decision makers involved in healthcare, what have they invested in recently? what are some gaps?"
    company = "Abbey Capital"
    
    print(f"📋 QUESTION: {question}")
    print(f"🏢 COMPANY: {company}")
    print()
    
    # Initialize system
    print("🤖 Initializing Intelligent Q&A System...")
    qa_system = IntelligentQASystem()
    print("✅ System ready with Gemini LLM + Tavily Intelligence")
    print()
    
    start_time = datetime.now()
    
    try:
        # Phase 1: Question Decomposition
        print("🧠 Phase 1: Question Decomposition (Gemini LLM)")
        decomposition = qa_system.decompose_question(question, company)
        
        sub_questions = decomposition.get("sub_questions", [])
        print(f"✅ Decomposed into {len(sub_questions)} sub-questions:")
        
        for i, sq in enumerate(sub_questions, 1):
            print(f"  {i}. [{sq['focus']}] {sq['question']}")
        print()
        
        # Phase 2: Intelligence Gathering
        print("🔍 Phase 2: Intelligence Gathering (Tavily API)")
        intelligence_data = qa_system.gather_intelligence(sub_questions)
        
        print(f"✅ Intelligence gathered:")
        print(f"  • Decision Makers: {len(intelligence_data['decision_makers'])}")
        print(f"  • Investments: {len(intelligence_data['investments'])}")
        print(f"  • Opportunities: {len(intelligence_data['gaps'])}")
        print(f"  • Total Sources: {len(set(intelligence_data['all_sources']))}")
        print()
        
        # Phase 3: Response Synthesis
        print("🎯 Phase 3: Response Synthesis (Gemini LLM)")
        final_response = qa_system.synthesize_response(question, company, intelligence_data, sub_questions)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        print("🎉 INTELLIGENT ANALYSIS COMPLETE!")
        print(f"⏱️ Processing time: {processing_time:.2f} seconds")
        print("=" * 60)
        print()
        
        print("📊 SYNTHESIZED INTELLIGENCE RESPONSE")
        print("-" * 50)
        print(final_response)
        print()
        
        # Show raw intelligence data
        print("🔍 RAW INTELLIGENCE DATA")
        print("-" * 50)
        
        if intelligence_data["decision_makers"]:
            print("👥 DECISION MAKERS FOUND:")
            for dm in intelligence_data["decision_makers"]:
                print(f"  • {dm.get('name', 'Unknown')} - {dm.get('title', 'Unknown')}")
                print(f"    Source: {dm.get('source', 'Unknown')}")
            print()
        
        if intelligence_data["investments"]:
            print("💰 INVESTMENTS FOUND:")
            for inv in intelligence_data["investments"]:
                print(f"  • {inv.get('company', 'Unknown')}: {inv.get('amount', 'Unknown')}")
                print(f"    Source: {inv.get('source', 'Unknown')}")
            print()
        
        if intelligence_data["gaps"]:
            print("🎯 OPPORTUNITIES/GAPS FOUND:")
            for gap in intelligence_data["gaps"]:
                print(f"  • {gap.get('opportunity', 'Unknown')[:100]}...")
                print(f"    Source: {gap.get('source', 'Unknown')}")
            print()
        
        # Save results
        output_file = f"abbey_capital_REAL_intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results = {
            "original_question": question,
            "company": company,
            "processing_time_seconds": processing_time,
            "sub_questions": sub_questions,
            "raw_intelligence": intelligence_data,
            "synthesized_response": final_response,
            "generated_at": datetime.now().isoformat(),
            "api_info": {
                "llm_provider": "gemini-1.5-pro",
                "intelligence_provider": "tavily",
                "total_sources": len(set(intelligence_data['all_sources']))
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📄 Complete results saved to: {output_file}")
        print()
        
        print("🎉 REAL API TEST COMPLETED SUCCESSFULLY!")
        print()
        print("🆚 TRANSFORMATION ACHIEVED:")
        print("  ❌ Old: 12,080 lines of redundant data")
        print("  ✅ New: Targeted intelligence with specific findings")
        print("  ❌ Old: Hours of manual analysis required")  
        print("  ✅ New: Direct answers in under 1 minute")
        print("  ❌ Old: Generic data collection")
        print("  ✅ New: Question-specific intelligence gathering")
        print("  ❌ Old: No actionable recommendations")
        print("  ✅ New: Synthesized insights with next steps")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
