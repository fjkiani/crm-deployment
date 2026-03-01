"""
Signal Distiller — Stolen from SDR-LangGraph-Agent's citation_combiner pattern.
Sits between raw research (Tavily/Apollo) and the email writer.
Extracts exactly 3 structured, citable facts from raw intel blob.
"""
import os
import json
import requests
from typing import Dict, Any, Optional
from langchain_core.tools import tool

# ── DISTILLATION PROMPT ──────────────────────────────────────────────────────
DISTILL_PROMPT = """You are an intelligence analyst for Zeta, a genomic data platform selling to quantitative investment firms.

Raw research intel on a prospect is below. Your job: extract EXACTLY 3 citable signals. Nothing generic. Only facts with numbers, names, or dates.

RAW INTEL:
{raw_intel}

Return ONLY valid JSON with these exact keys:
{{
    "specific_number": "One hard number — AUM, fund size, headcount, revenue, or return %.  Must include the actual number.",
    "recent_event": "One event from the last 12 months — fund launch, hire, acquisition, regulatory filing, earnings miss.  Include the date or quarter if known.",
    "strategic_detail": "One specific strategic detail — investment thesis, strategy name, sector focus, or competitive positioning.  Must be specific enough that the prospect would recognize it as THEIR business.",
    "blind_spot": "One structural weakness or gap in their approach that Zeta's genomic data could address.  Be specific about WHY they are vulnerable.",
    "recommended_framework": "One of: challenger, pas, aida — based on how warm this lead is and how sophisticated their data stack appears."
}}

RULES:
- If you can't find a real number, use the most specific quantitative detail available.
- Never fabricate. If a field is truly unknown, write "UNKNOWN — requires deeper research".
- The blind_spot must connect to what Zeta sells: biological drug response signals that predict clinical trial outcomes, stock moves, and sector rotation.
"""

def _call_cohere(prompt: str, cohere_key: str) -> Dict[str, Any]:
    """Call Cohere v2 chat with JSON response format."""
    r = requests.post(
        'https://api.cohere.com/v2/chat',
        headers={'Authorization': f'Bearer {cohere_key}'},
        json={
            'model': 'command-r-plus-08-2024',
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_object'}
        },
        timeout=45
    )
    r.raise_for_status()
    return json.loads(r.json()['message']['content'][0]['text'])


@tool
def distill_signals(raw_intel: str) -> str:
    """
    Distill raw research intel (Tavily + Apollo blob) into 3 structured, citable signals.
    Stolen from SDR-LangGraph-Agent's citation_combiner pattern.
    Returns structured JSON string with: specific_number, recent_event, strategic_detail, blind_spot, recommended_framework.
    """
    cohere_key = os.getenv("COHERE_API_KEY")
    if not cohere_key:
        return json.dumps({
            "specific_number": "UNKNOWN",
            "recent_event": "UNKNOWN",
            "strategic_detail": "UNKNOWN",
            "blind_spot": "Systematic macro-only models miss biological mechanism data that drives 40% of healthcare equity variance.",
            "recommended_framework": "challenger",
            "error": "No COHERE_API_KEY — used defaults"
        })

    prompt = DISTILL_PROMPT.format(raw_intel=raw_intel[:4000])  # truncate to avoid token limit
    
    try:
        result = _call_cohere(prompt, cohere_key)
        # Validate required keys
        required = ["specific_number", "recent_event", "strategic_detail", "blind_spot", "recommended_framework"]
        for key in required:
            if key not in result:
                result[key] = "UNKNOWN"
        
        # Normalize framework
        fw = result.get("recommended_framework", "challenger").lower().strip()
        if fw not in ("challenger", "pas", "aida"):
            fw = "challenger"
        result["recommended_framework"] = fw
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "specific_number": "UNKNOWN",
            "recent_event": "UNKNOWN", 
            "strategic_detail": "UNKNOWN",
            "blind_spot": "Systematic macro-only models miss biological mechanism data.",
            "recommended_framework": "challenger",
            "error": str(e)
        })
