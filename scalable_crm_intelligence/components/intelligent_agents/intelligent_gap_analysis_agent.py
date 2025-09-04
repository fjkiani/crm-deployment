"""
Intelligent Gap Analysis Agent
Advanced agent with contextual reasoning for strategic gap identification
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from .agent_brain import AgentBrain, IntelligenceContext

class IntelligentGapAnalysisAgent:
    """Intelligent agent for strategic gap analysis and opportunity identification"""
    
    def __init__(self, tavily_api_key: str, gemini_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.gemini_api_key = gemini_api_key
        self.brain = AgentBrain()
        self.name = "IntelligentGapAnalysisAgent"
    
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
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 3000}
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
    
    def build_intelligent_gap_queries(self, company: str, focus_domain: str) -> List[str]:
        """Build intelligent gap analysis search queries"""
        
        # Get domain-specific knowledge
        domain_knowledge = self.brain.domain_knowledge.get(focus_domain, {})
        investment_types = domain_knowledge.get("investment_types", [])
        
        # Generate company variations
        company_variations = self.brain._generate_company_variations(company)
        
        # Build intelligent queries
        queries = []
        
        # Market landscape and competitive analysis
        queries.extend([
            f'{focus_domain} investment market trends 2024 opportunities',
            f'{focus_domain} investment gaps unmet needs market whitespace',
            f'{focus_domain} emerging technologies investment opportunities',
            f'{focus_domain} venture capital trends gaps opportunities'
        ])
        
        # Company-specific strategy and positioning
        for company_var in company_variations[:2]:
            queries.extend([
                f'"{company_var}" {focus_domain} strategy investment focus areas',
                f'"{company_var}" {focus_domain} portfolio gaps missing sectors',
                f'"{company_var}" competitive positioning {focus_domain} investments'
            ])
        
        # Domain-specific gap analysis
        for inv_type in investment_types[:3]:
            queries.append(f'{inv_type} investment opportunities gaps market needs')
        
        # Competitor and benchmark analysis
        queries.extend([
            f'{focus_domain} investment firms portfolio comparison analysis',
            f'{focus_domain} private equity venture capital investment gaps',
            f'underinvested {focus_domain} sectors opportunities 2024'
        ])
        
        return queries[:12]  # Return top 12 queries
    
    def analyze_gap_intelligence(
        self, 
        company: str, 
        focus_domain: str = "healthcare",
        existing_portfolio: List[Dict] = None,
        competitor_data: List[Dict] = None
    ) -> Dict[str, Any]:
        """Perform intelligent gap analysis with contextual reasoning"""
        
        print(f"🧠 {self.name}: Analyzing strategic gaps for {company} in {focus_domain}")
        
        # Create intelligence context
        context = IntelligenceContext(
            company=company,
            industry="investment_management",
            focus_domain=focus_domain,
            search_intent="gaps",
            market_context={"existing_portfolio": existing_portfolio or []},
            competitive_landscape=competitor_data or []
        )
        
        # Build intelligent queries
        queries = self.build_intelligent_gap_queries(company, focus_domain)
        
        # Gather gap intelligence
        all_opportunities = []
        market_insights = []
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
                
                if relevance > 0.2:  # Lower threshold for gap analysis
                    relevant_sources.append({
                        "url": url,
                        "title": title,
                        "relevance": relevance
                    })
                    
                    # Extract opportunities with intelligence
                    opportunities = self.brain._extract_opportunities_intelligent(content, title, context)
                    all_opportunities.extend(opportunities)
                    
                    # Extract market insights
                    insights = self._extract_market_insights(content, title, focus_domain)
                    market_insights.extend(insights)
                    
                    print(f"    ✅ Relevance: {relevance:.2f} | Opportunities: {len(opportunities)} | Insights: {len(insights)}")
                else:
                    print(f"    ❌ Relevance: {relevance:.2f} | Skipped irrelevant content")
        
        # Deduplicate and rank opportunities
        unique_opportunities = self._deduplicate_opportunities(all_opportunities)
        unique_insights = self._deduplicate_insights(market_insights)
        
        unique_opportunities.sort(key=lambda x: x.get("domain_relevance", 0), reverse=True)
        
        # Perform advanced gap analysis using LLM
        advanced_analysis = self._perform_advanced_gap_analysis(
            company, focus_domain, unique_opportunities, unique_insights, 
            existing_portfolio, competitor_data
        )
        
        return {
            "company": company,
            "focus_domain": focus_domain,
            "opportunities_found": len(unique_opportunities),
            "opportunities": unique_opportunities[:5],  # Top 5
            "market_insights": unique_insights[:5],  # Top 5
            "relevant_sources": len(relevant_sources),
            "total_sources_searched": len(all_sources),
            "advanced_gap_analysis": advanced_analysis,
            "confidence_score": self._calculate_confidence(unique_opportunities, unique_insights, relevant_sources)
        }
    
    def _extract_market_insights(self, content: str, title: str, focus_domain: str) -> List[Dict[str, Any]]:
        """Extract market insights and trends"""
        
        insights = []
        
        # Look for trend and market indicators
        trend_keywords = [
            "trend", "growth", "market size", "forecast", "projection",
            "emerging", "opportunity", "demand", "supply", "gap",
            "underserved", "unmet need", "whitespace"
        ]
        
        sentences = content.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or len(sentence) > 250:
                continue
            
            # Check for trend indicators
            has_trend = any(keyword in sentence.lower() for keyword in trend_keywords)
            
            # Check for domain relevance
            domain_indicators = self.brain.domain_knowledge.get(focus_domain, {}).get("company_indicators", [])
            has_domain = any(indicator in sentence.lower() for indicator in domain_indicators)
            
            if has_trend and has_domain:
                insights.append({
                    "insight": sentence,
                    "type": "market_trend",
                    "source": title,
                    "relevance": 0.7
                })
        
        return insights[:3]  # Return top 3
    
    def _deduplicate_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Remove duplicate opportunities"""
        
        seen_opportunities = set()
        unique_opportunities = []
        
        for opp in opportunities:
            # Create a key based on the first 50 characters
            opp_key = opp["opportunity"][:50].lower()
            if opp_key not in seen_opportunities:
                seen_opportunities.add(opp_key)
                unique_opportunities.append(opp)
        
        return unique_opportunities
    
    def _deduplicate_insights(self, insights: List[Dict]) -> List[Dict]:
        """Remove duplicate insights"""
        
        seen_insights = set()
        unique_insights = []
        
        for insight in insights:
            # Create a key based on the first 50 characters
            insight_key = insight["insight"][:50].lower()
            if insight_key not in seen_insights:
                seen_insights.add(insight_key)
                unique_insights.append(insight)
        
        return unique_insights
    
    def _perform_advanced_gap_analysis(
        self,
        company: str,
        focus_domain: str,
        opportunities: List[Dict],
        insights: List[Dict],
        existing_portfolio: List[Dict],
        competitor_data: List[Dict]
    ) -> str:
        """Perform advanced gap analysis using LLM reasoning"""
        
        # Prepare data for LLM analysis
        opportunity_summary = []
        for opp in opportunities[:5]:
            opportunity_summary.append({
                "opportunity": opp["opportunity"][:100] + "...",
                "relevance": opp.get("domain_relevance", 0),
                "source": opp["source"]
            })
        
        insight_summary = []
        for insight in insights[:5]:
            insight_summary.append({
                "insight": insight["insight"][:100] + "...",
                "type": insight.get("type", "general"),
                "source": insight["source"]
            })
        
        prompt = f"""You are a strategic investment analyst specializing in gap analysis. Perform a comprehensive strategic gap analysis for {company} in {focus_domain}.

COMPANY: {company}
FOCUS DOMAIN: {focus_domain}

MARKET OPPORTUNITIES IDENTIFIED:
{json.dumps(opportunity_summary, indent=2)}

MARKET INSIGHTS:
{json.dumps(insight_summary, indent=2)}

EXISTING PORTFOLIO CONTEXT:
{json.dumps(existing_portfolio[:3] if existing_portfolio else [], indent=2)}

COMPETITIVE CONTEXT:
{json.dumps(competitor_data[:3] if competitor_data else [], indent=2)}

Perform a strategic gap analysis that identifies:

1. **STRATEGIC GAPS**: What specific areas in {focus_domain} is {company} not investing in that represent significant opportunities?

2. **MARKET WHITESPACE**: What underserved or emerging areas in {focus_domain} have high growth potential?

3. **COMPETITIVE POSITIONING**: How does {company}'s {focus_domain} strategy compare to market leaders?

4. **INVESTMENT OPPORTUNITIES**: What specific investment themes, sectors, or technologies should {company} consider?

5. **RISK ASSESSMENT**: What are the risks and challenges in pursuing these opportunities?

6. **ACTIONABLE RECOMMENDATIONS**: Specific, prioritized recommendations with rationale and timeline.

Provide a comprehensive, strategic analysis that goes beyond surface-level observations. Focus on actionable insights that can drive investment decisions."""

        return self.generate_gemini_response(prompt)
    
    def _calculate_confidence(self, opportunities: List[Dict], insights: List[Dict], sources: List[Dict]) -> float:
        """Calculate confidence score for gap analysis"""
        
        total_findings = len(opportunities) + len(insights)
        
        if total_findings == 0:
            return 0.2
        
        # Base confidence from findings
        base_confidence = min(total_findings / 10.0, 0.4)
        
        # Source quality bonus
        source_quality = sum(source.get("relevance", 0) for source in sources) / max(len(sources), 1)
        source_bonus = source_quality * 0.3
        
        # Finding quality bonus
        all_findings = opportunities + insights
        avg_relevance = sum(finding.get("domain_relevance", finding.get("relevance", 0)) for finding in all_findings) / max(len(all_findings), 1)
        finding_bonus = avg_relevance * 0.3
        
        return min(base_confidence + source_bonus + finding_bonus, 1.0)
