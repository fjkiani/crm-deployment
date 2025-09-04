"""
Intelligent Executive Agent
Advanced agent with contextual reasoning for executive intelligence
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from .agent_brain import AgentBrain, IntelligenceContext

class IntelligentExecutiveAgent:
    """Intelligent agent for executive and decision maker intelligence"""
    
    def __init__(self, tavily_api_key: str, gemini_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.gemini_api_key = gemini_api_key
        self.brain = AgentBrain()
        self.name = "IntelligentExecutiveAgent"
    
    def search_tavily(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Tavily API with intelligent query optimization"""
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_type": "general",
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": True
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    return response_data.get("results", [])
                else:
                    return []
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []
    
    def generate_gemini_response(self, prompt: str) -> str:
        """Generate response using Gemini LLM"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            
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
    
    def build_intelligent_queries(self, company: str, focus_domain: str) -> List[str]:
        """Build intelligent search queries using domain knowledge"""
        
        # Get domain-specific knowledge
        domain_knowledge = self.brain.domain_knowledge.get(focus_domain, {})
        executive_titles = domain_knowledge.get("executive_titles", [])
        
        # Generate company variations
        company_variations = self.brain._generate_company_variations(company)
        
        # Build intelligent queries
        queries = []
        
        # Primary company + domain queries
        for company_var in company_variations[:2]:  # Use top 2 variations
            queries.extend([
                f'"{company_var}" {focus_domain} investment team executives leadership',
                f'"{company_var}" {focus_domain} partners directors management',
                f'"{company_var}" {focus_domain} portfolio team decision makers'
            ])
        
        # Domain-specific executive title queries
        for title in executive_titles[:3]:  # Use top 3 domain titles
            queries.append(f'"{company}" "{title}" {focus_domain}')
        
        # LinkedIn and professional network queries
        queries.extend([
            f'"{company}" linkedin executives {focus_domain}',
            f'"{company}" team page {focus_domain} investment',
            f'"{company}" leadership {focus_domain} portfolio'
        ])
        
        return queries[:8]  # Return top 8 queries
    
    def analyze_executive_intelligence(self, company: str, focus_domain: str = "healthcare") -> Dict[str, Any]:
        """Perform intelligent executive analysis with contextual reasoning"""
        
        print(f"🧠 {self.name}: Analyzing {company} executives in {focus_domain}")
        
        # Create intelligence context
        context = IntelligenceContext(
            company=company,
            industry="investment_management",
            focus_domain=focus_domain,
            search_intent="decision_makers",
            market_context={},
            competitive_landscape=[]
        )
        
        # Build intelligent queries
        queries = self.build_intelligent_queries(company, focus_domain)
        
        # Gather intelligence with contextual analysis
        all_executives = []
        all_sources = []
        relevant_sources = []
        
        for i, query in enumerate(queries, 1):
            print(f"  🔍 Query {i}: {query}")
            
            results = self.search_tavily(query, max_results=3)
            
            for result in results:
                content = result.get('content', '')
                title = result.get('title', '')
                url = result.get('url', '')
                
                all_sources.append(url)
                
                # Analyze content relevance using brain
                relevance = self.brain.analyze_content_relevance(content, title, url, context)
                
                if relevance > 0.3:  # Only process relevant content
                    relevant_sources.append({
                        "url": url,
                        "title": title,
                        "relevance": relevance
                    })
                    
                    # Extract executives with intelligence
                    executives = self.brain._extract_executives_intelligent(content, title, context)
                    all_executives.extend(executives)
                    
                    print(f"    ✅ Relevance: {relevance:.2f} | Executives found: {len(executives)}")
                else:
                    print(f"    ❌ Relevance: {relevance:.2f} | Skipped irrelevant content")
        
        # Deduplicate and rank executives
        unique_executives = self.brain._deduplicate_executives(all_executives)
        unique_executives.sort(key=lambda x: x.get("domain_relevance", 0), reverse=True)
        
        # Generate intelligent synthesis
        synthesis = self._synthesize_executive_intelligence(
            company, focus_domain, unique_executives, relevant_sources
        )
        
        return {
            "company": company,
            "focus_domain": focus_domain,
            "executives_found": len(unique_executives),
            "executives": unique_executives[:5],  # Top 5
            "relevant_sources": len(relevant_sources),
            "total_sources_searched": len(all_sources),
            "intelligence_synthesis": synthesis,
            "confidence_score": self._calculate_confidence(unique_executives, relevant_sources)
        }
    
    def _synthesize_executive_intelligence(
        self, 
        company: str, 
        focus_domain: str, 
        executives: List[Dict], 
        sources: List[Dict]
    ) -> str:
        """Generate intelligent synthesis of executive findings"""
        
        if not executives:
            return f"No {focus_domain} decision makers found at {company} through intelligent analysis of {len(sources)} relevant sources."
        
        # Prepare executive summary for LLM
        exec_summary = []
        for exec_info in executives[:3]:
            exec_summary.append({
                "name": exec_info["name"],
                "title": exec_info["title"],
                "domain_relevance": exec_info["domain_relevance"],
                "confidence": exec_info["confidence"]
            })
        
        prompt = f"""You are an expert executive intelligence analyst. Synthesize this executive intelligence for {company} in {focus_domain}.

EXECUTIVES FOUND: {len(executives)}
TOP EXECUTIVES:
{json.dumps(exec_summary, indent=2)}

ANALYSIS CONTEXT:
- Company: {company}
- Focus Domain: {focus_domain}
- Relevant Sources: {len(sources)}
- Intelligence Method: Contextual pattern recognition with domain expertise

Provide a concise, actionable synthesis that includes:
1. Key decision makers identified
2. Their relevance to {focus_domain} investments
3. Decision-making authority and influence
4. Recommended approach strategies
5. Confidence assessment and limitations

Keep it business-focused and actionable."""

        return self.generate_gemini_response(prompt)
    
    def _calculate_confidence(self, executives: List[Dict], sources: List[Dict]) -> float:
        """Calculate confidence score for executive intelligence"""
        
        if not executives:
            return 0.1
        
        # Base confidence from number of executives found
        base_confidence = min(len(executives) / 5.0, 0.4)
        
        # Source quality bonus
        source_quality = sum(source.get("relevance", 0) for source in sources) / max(len(sources), 1)
        source_bonus = source_quality * 0.3
        
        # Executive quality bonus
        avg_domain_relevance = sum(exec.get("domain_relevance", 0) for exec in executives) / len(executives)
        exec_bonus = avg_domain_relevance * 0.3
        
        return min(base_confidence + source_bonus + exec_bonus, 1.0)
