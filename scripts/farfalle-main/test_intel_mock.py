#!/usr/bin/env python3
"""
Test server with mock intel data for Abbey Capital
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

app = FastAPI(title="Farfalle Intel Mock")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Farfalle Intel Mock Server", "status": "running"}

@app.post("/intel/enrich_lead")
async def enrich_lead(data: dict):
    company = data.get("company", "Unknown Company")
    domain = data.get("domain", "")
    
    # Mock data for Abbey Capital
    if "abbey" in company.lower() or "abbey" in domain.lower():
        return {
            "company": company,
            "summary": [
                "Abbey Capital is a leading private equity firm focused on healthcare and technology investments",
                "Recent $2.5B fundraise demonstrates strong investor confidence and market positioning",
                "Strategic focus on digital health, AI diagnostics, and personalized medicine sectors",
                "Active portfolio includes 15+ healthcare companies with $500M+ in deployed capital",
                "Leadership team combines deep healthcare expertise with technology innovation experience"
            ],
            "key_insights": [
                "Healthcare investment thesis: AI-driven diagnostics and personalized medicine",
                "Geographic focus: US and European markets with growing Asian presence",
                "Investment stage: Primarily Series A-B with select growth equity opportunities",
                "Portfolio companies: HealthAI Corp, MedTech Solutions, BioData Analytics"
            ],
            "results": [
                {
                    "question": "Who are the decision-makers at Abbey Capital?",
                    "answer": "Dr. Sarah Johnson (Healthcare Investment Director), Michael Chen (Managing Partner), Lisa Rodriguez (Head of Technology Investments)",
                    "sources": [
                        {"title": "Abbey Capital Leadership Team", "url": "https://abbeycapital.com/team", "content": "Leadership profiles and investment focus areas"},
                        {"title": "Healthcare Investment Committee", "url": "https://abbeycapital.com/healthcare", "content": "Investment committee structure and decision-making process"}
                    ],
                    "extracted_people": [
                        {"name": "Dr. Sarah Johnson", "title": "Healthcare Investment Director", "source_url": "https://abbeycapital.com/team/sarah-johnson"},
                        {"name": "Michael Chen", "title": "Managing Partner", "source_url": "https://abbeycapital.com/team/michael-chen"},
                        {"name": "Lisa Rodriguez", "title": "Head of Technology Investments", "source_url": "https://abbeycapital.com/team/lisa-rodriguez"}
                    ]
                },
                {
                    "question": "What has Abbey Capital invested in recently?",
                    "answer": "Recent investments include HealthAI Corp ($30M Series B), MedTech Solutions ($25M Series A), and BioData Analytics ($40M Series B) in Q3-Q4 2024",
                    "sources": [
                        {"title": "Abbey Capital Portfolio", "url": "https://abbeycapital.com/portfolio", "content": "Complete portfolio of healthcare and technology investments"},
                        {"title": "Recent Investment Announcements", "url": "https://abbeycapital.com/news", "content": "Latest investment news and portfolio company updates"}
                    ]
                },
                {
                    "question": "What are Abbey Capital's strategic gaps?",
                    "answer": "Limited exposure to Asian healthcare markets, minimal investment in healthcare robotics, and underrepresentation in mental health technology sectors",
                    "sources": [
                        {"title": "Investment Strategy Analysis", "url": "https://abbeycapital.com/strategy", "content": "Strategic focus areas and market opportunities"},
                        {"title": "Market Gap Analysis", "url": "https://abbeycapital.com/research", "content": "Research on emerging healthcare investment opportunities"}
                    ]
                }
            ],
            "total_sources": 6
        }
    
    # Default response for other companies
    return {
        "company": company,
        "summary": [f"Analysis for {company} - mock data"],
        "key_insights": ["Mock insight 1", "Mock insight 2"],
        "results": [
            {
                "question": "Who are the decision-makers?",
                "answer": "Mock decision makers",
                "sources": [{"title": "Mock Source", "url": "https://example.com", "content": "Mock content"}]
            }
        ],
        "total_sources": 1
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

