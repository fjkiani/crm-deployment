"""
Intelligent Investment Agent
Advanced agent with contextual reasoning for investment intelligence
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from .agent_brain import AgentBrain, IntelligenceContext

class IntelligentInvestmentAgent:
    """Intelligent agent for investment and portfolio intelligence"""
    
    def __init__(self, tavily_api_key: str, gemini_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.gemini_api_key = gemini_api_key
        self.brain = AgentBrain()
        self.name = "IntelligentInvestmentAgent"
    
    def search_tavily(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using Tavily API"""
        
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
    
    def build_intelligent_investment_queries(self, company: str, focus_domain: str) -> List[str]:
        """Build intelligent investment search queries"""
        
        # Get domain-specific knowledge
        domain_knowledge = self.brain.domain_knowledge.get(focus_domain, {})
        investment_types = domain_knowledge.get("investment_types", [])
        funding_stages = domain_knowledge.get("funding_stages", [])
        
        # Generate company variations
        company_variations = self.brain._generate_company_variations(company)
        
        # Build intelligent queries
        queries = []
        
        # Primary investment queries
        for company_var in company_variations[:2]:
            queries.extend([
                f'"{company_var}" {focus_domain} investments portfolio deals',
                f'"{company_var}" invested {focus_domain} companies funding',
                f'"{company_var}" {focus_domain} portfolio companies acquisitions'
            ])
        
        # Domain-specific investment type queries
        for inv_type in investment_types[:4]:  # Top 4 investment types
            queries.append(f'"{company}" {inv_type} investment deal funding')
        
        # Funding stage queries
        for stage in funding_stages[:3]:  # Top 3 stages
            queries.append(f'"{company}" {stage} {focus_domain} investment')
        
        # News and announcement queries
        queries.extend([
            f'"{company}" announces {focus_domain} investment deal',
            f'"{company}" leads {focus_domain} funding round',
            f'"{company}" portfolio {focus_domain} companies 2023 2024'
        ])
        
        return queries[:10]  # Return top 10 queries
    
    def analyze_investment_intelligence(self, company: str, focus_domain: str = "healthcare") -> Dict[str, Any]:
        """Perform intelligent investment analysis with contextual reasoning"""
        
        print(f"🧠 {self.name}: Analyzing {company} investments in {focus_domain}")
        
        # Create intelligence context
        context = IntelligenceContext(
            company=company,
            industry="investment_management",
            focus_domain=focus_domain,
            search_intent="investments",
            market_context={},
            competitive_landscape=[]
        )
        
        # Build intelligent queries
        queries = self.build_intelligent_investment_queries(company, focus_domain)
        
        # Gather investment intelligence
        all_investments = []
        all_companies = []
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
                    
                    # Extract investments with intelligence
                    investments = self.brain._extract_investments_intelligent(content, title, context)
                    companies = self.brain._extract_companies_intelligent(content, title, context)
                    
                    all_investments.extend(investments)
                    all_companies.extend(companies)
                    
                    print(f"    ✅ Relevance: {relevance:.2f} | Investments: {len(investments)} | Companies: {len(companies)}")
                else:
                    print(f"    ❌ Relevance: {relevance:.2f} | Skipped irrelevant content")
        
        # Deduplicate and rank
        unique_investments = self.brain._deduplicate_investments(all_investments)
        unique_companies = self.brain._deduplicate_companies(all_companies)
        
        unique_investments.sort(key=lambda x: x.get("domain_relevance", 0), reverse=True)
        unique_companies.sort(key=lambda x: x.get("domain_relevance", 0), reverse=True)
        
        # Generate intelligent synthesis
        synthesis = self._synthesize_investment_intelligence(
            company, focus_domain, unique_investments, unique_companies, relevant_sources
        )
        
        return {
            "company": company,
            "focus_domain": focus_domain,
            "investments_found": len(unique_investments),
            "investments": unique_investments[:5],  # Top 5
            "portfolio_companies": unique_companies[:5],  # Top 5
            "relevant_sources": len(relevant_sources),
            "total_sources_searched": len(all_sources),
            "intelligence_synthesis": synthesis,
            "confidence_score": self._calculate_confidence(unique_investments, unique_companies, relevant_sources)
        }
    
    def _synthesize_investment_intelligence(
        self, 
        company: str, 
        focus_domain: str, 
        investments: List[Dict],
        companies: List[Dict], 
        sources: List[Dict]
    ) -> str:
        """Generate intelligent synthesis of investment findings"""
        
        if not investments and not companies:
            return f"No {focus_domain} investments found for {company} through intelligent analysis of {len(sources)} relevant sources."
        
        # Prepare investment summary for LLM
        investment_summary = []
        for inv in investments[:3]:
            investment_summary.append({
                "company": inv["company"],
                "amount": inv["amount"],
                "domain_relevance": inv["domain_relevance"],
                "confidence": inv["confidence"]
            })
        
        company_summary = []
        for comp in companies[:3]:
            company_summary.append({
                "company": comp["company"],
                "domain_relevance": comp["domain_relevance"],
                "confidence": comp["confidence"]
            })
        
        prompt = f"""You are an expert investment intelligence analyst. Synthesize this investment intelligence for {company} in {focus_domain}.

INVESTMENTS FOUND: {len(investments)}
TOP INVESTMENTS:
{json.dumps(investment_summary, indent=2)}

PORTFOLIO COMPANIES FOUND: {len(companies)}
TOP COMPANIES:
{json.dumps(company_summary, indent=2)}

ANALYSIS CONTEXT:
- Company: {company}
- Focus Domain: {focus_domain}
- Relevant Sources: {len(sources)}
- Intelligence Method: Contextual pattern recognition with domain expertise

Provide a concise, actionable synthesis that includes:
1. Key investments and portfolio companies identified
2. Investment patterns and themes in {focus_domain}
3. Deal sizes, stages, and timing analysis
4. Strategic focus areas and preferences
5. Confidence assessment and data limitations

Keep it business-focused and actionable."""

        return self.generate_gemini_response(prompt)
    
    def _calculate_confidence(self, investments: List[Dict], companies: List[Dict], sources: List[Dict]) -> float:
        """Calculate confidence score for investment intelligence"""
        
        total_findings = len(investments) + len(companies)
        
        if total_findings == 0:
            return 0.1
        
        # Base confidence from findings
        base_confidence = min(total_findings / 8.0, 0.4)
        
        # Source quality bonus
        source_quality = sum(source.get("relevance", 0) for source in sources) / max(len(sources), 1)
        source_bonus = source_quality * 0.3
        
        # Finding quality bonus
        all_findings = investments + companies
        avg_domain_relevance = sum(finding.get("domain_relevance", 0) for finding in all_findings) / max(len(all_findings), 1)
        finding_bonus = avg_domain_relevance * 0.3
        
        return min(base_confidence + source_bonus + finding_bonus, 1.0)
