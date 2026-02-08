import re
from typing import Dict, Any, List
from langchain_core.tools import tool
from eaia.main.config import get_config

# ------------------------------------------------------------------------------
# SCORING CRITERIA (Harvested from lead_qualification_agent.py)
# ------------------------------------------------------------------------------
SCORING_WEIGHTS = {
    "company_size": 0.25,
    "job_title": 0.25,
    "industry": 0.20,
    "engagement": 0.15,
    "budget_signals": 0.15
}

SCORING_PROMPT_TEMPLATE = """
Score this lead from 0-100 based on qualification criteria.

Lead Data:
{lead_data}

Scoring Criteria:
- Company size (25%): Enterprise > Large > Medium > Small
- Job title (25%): Executive > Director > Manager > Individual Contributor
- Industry (20%): Tech, Finance, Healthcare = high value
- Engagement (15%): Multiple touchpoints, content downloads
- Budget signals (15%): Mentions pricing, demo requests, timeline questions

Return ONLY the numeric score (0-100).
"""

ROUTING_THRESHOLDS = {
    "enterprise": 80,
    "mid_market": 60,
    "smb": 40
}

# ------------------------------------------------------------------------------
# TOOL DEFINITION
# ------------------------------------------------------------------------------

@tool
def score_lead(lead_data_str: str):
    """
    Score a lead from 0-100 and determine routing.
    Args:
        lead_data_str: Analysis string or JSON containing lead details (Title, Industry, Size, Signals).
    Returns:
        String with Score, Routing Decision, and Rationale.
    """
    # In a real implementation, we'd use the LLM to score based on the prompt.
    # For now, as a tool usage, we mock the "Thinking" logic or we can use the Agent's own LLM if we had access here.
    # Since tools are often synchronous functions, we'll implement a heuristic fallback 
    # OR we assume the agent calling this tool provides the RAW data and we process it.
    
    # Heuristic Fallback (Simulation of the Harvested Logic)
    score = 50 # Base
    data = lead_data_str.lower()
    
    # 1. Title Scoring
    if any(x in data for x in ["cto", "ceo", "vp", "founder", "partner"]):
        score += 20
    elif "director" in data:
        score += 10
        
    # 2. Industry Scoring
    if any(x in data for x in ["fintech", "biotech", "tech", "finance"]):
        score += 15
        
    # 3. Signals
    if any(x in data for x in ["pricing", "cost", "demo", "urgent"]):
        score += 15
        
    # Cap at 100
    score = min(100, score)
    
    # Routing Logic
    if score >= ROUTING_THRESHOLDS["enterprise"]:
        team = "Enterprise Sales"
        priority = "High"
    elif score >= ROUTING_THRESHOLDS["mid_market"]:
        team = "Mid-Market Sales"
        priority = "Medium"
    else:
        team = "Marketing Nurture"
        priority = "Low"
        
    return f"Lead Score: {score}/100\nRouted To: {team}\nPriority: {priority}\nRationale: Derived from keywords in '{lead_data_str[:50]}...'"

