"""
Challenger Email Writer — Two-pass email generation with framework auto-selection.
Stolen patterns: AutomatedEmail's multi-LLM chain + SDR-LangGraph-Agent's context gathering.
Zeta originals: Challenger/PAS/AIDA framework templates with product-specific proof points.

Pass 1 (THINK): Extract 3 talking points from distilled signals.
Pass 2 (WRITE): Write the email using ONLY those talking points + selected framework.
"""
import os
import json
import requests
from typing import Dict, Any, Optional, Tuple
from langchain_core.tools import tool


# ── FRAMEWORK TEMPLATES ──────────────────────────────────────────────────────

FRAMEWORKS = {
    "challenger": {
        "name": "Challenger (Teach → Tailor → Take Control)",
        "when": "HOT leads (score ≥ 70). Decision-makers who think they have it figured out.",
        "pass1_prompt": """You are a B2B sales strategist for Zeta, a genomic data platform.

DISTILLED SIGNALS:
{signals}

PROSPECT:
{prospect_info}

Your job: Extract exactly 3 TALKING POINTS for a Challenger-style email.

TALKING POINT 1 (THE TEASE): A structural blind spot in their specific investment strategy that they probably don't know about. Be specific — reference their actual strategy or sector.

TALKING POINT 2 (THE INSIGHT): An asymmetric insight from Zeta's capabilities that directly addresses their blind spot. Pick ONE:
- PARP Inhibitor Resistance Signal: Quantifies clinical trial failure risk 6 months before earnings. Predicted AstraZeneca Q3 miss on Lynparza.
- KELIM Genotype Convergence: Scores tumor mutational pathways to predict competitor drug synergy/failure.
- Targeted Sector Rotation: Translates biological trial data into macro signals for healthcare/biotech ETFs.

TALKING POINT 3 (THE PROOF): One specific, verifiable proof of Zeta's capability. Not "several firms use us" — name the signal, the prediction, and the outcome.

Return ONLY valid JSON:
{{"tp1_tease": "...", "tp2_insight": "...", "tp3_proof": "...", "selected_capability": "parp|kelim|sector_rotation"}}
""",
        "pass2_prompt": """Write a cold email using ONLY these 3 talking points. Do NOT add anything else.

TALKING POINTS:
{talking_points}

PROSPECT NAME: {name}
PROSPECT COMPANY: {company}

RULES:
- Maximum 65 words in the body. Hard limit. Count carefully.
- BANNED WORDS: Dear, cutting-edge, innovative, leverage, synergy, unlock, revolutionize, unique, advanced, comprehensive, robust, holistic, transform, excited, thrilled, delighted, pleased, enhance, optimize
- BANNED OPENERS: "I hope this", "My name is", "I'm reaching out", "I wanted to", "Dear"
- Address them by FIRST NAME ONLY. Not "Dear Peter McManus" — just "Peter,"
- Tone: Assertive. You are TELLING them about a blind spot, not suggesting "may" or "might". State it as fact.
- Structure: Tease their blind spot → deliver the insight → cite the proof → one-line ask
- CTA must be EXACTLY one of: "Open to seeing the math?" or "Worth a 10 min look?" — no variations
- Subject line: Under 40 chars, provocative, reference their specific situation. No colons.
- PS: One sentence. A specific proof point or stat, NOT generic hype.

Return ONLY valid JSON:
{{"subject": "...", "body": "...", "ps": "..."}}
"""
    },

    "pas": {
        "name": "PAS (Problem → Agitate → Solution)",
        "when": "WARM leads (score 40-69). People who know they have a problem but haven't prioritized it.",
        "pass1_prompt": """You are a B2B sales strategist for Zeta, a genomic data platform.

DISTILLED SIGNALS:
{signals}

PROSPECT:
{prospect_info}

Extract exactly 3 TALKING POINTS for a PAS (Problem → Agitate → Solution) email.

TALKING POINT 1 (PROBLEM): Name a specific problem they have based on the signals. NOT generic "staying competitive". Must reference THEIR situation.

TALKING POINT 2 (AGITATE): Quantify the cost of inaction. Use a real number if available. Example: "Funds trading biotech with macro data alone underperformed clinical-aware peers by 14% in Q3."

TALKING POINT 3 (SOLUTION): Position Zeta as the fix. One specific capability that solves the problem. Show one proof point.

Return ONLY valid JSON:
{{"tp1_problem": "...", "tp2_agitate": "...", "tp3_solution": "...", "selected_capability": "parp|kelim|sector_rotation"}}
""",
        "pass2_prompt": """Write a cold email using ONLY these 3 talking points. Do NOT add anything else.

TALKING POINTS:
{talking_points}

PROSPECT NAME: {name}
PROSPECT COMPANY: {company}

RULES:
- Maximum 70 words in the body. Hard limit.
- BANNED WORDS: Dear, cutting-edge, innovative, leverage, synergy, unlock, revolutionize, unique, advanced, comprehensive, robust, holistic, transform, enhance, optimize, excited, delighted
- BANNED OPENERS: "I hope this", "My name is", "I'm reaching out", "Dear"
- Address by FIRST NAME ONLY.
- Tone: Empathetic but direct. State the problem as a fact, then quantify it, then solve it.
- Structure: Name the problem → quantify the cost with a real number → present Zeta as the fix
- CTA must be EXACTLY: "Quick question — who handles alt-data sourcing on your team?"
- Subject line: Under 40 chars, name the problem directly. No colons.
- PS: One sentence with a specific number or case study.

Return ONLY valid JSON:
{{"subject": "...", "body": "...", "ps": "..."}}
"""
    },

    "aida": {
        "name": "AIDA (Attention → Interest → Desire → Action)",
        "when": "COLD leads (score < 40). People who haven't heard of genomic data for investing.",
        "pass1_prompt": """You are a B2B sales strategist for Zeta, a genomic data platform.

DISTILLED SIGNALS:
{signals}

PROSPECT:
{prospect_info}

Extract exactly 3 TALKING POINTS for an AIDA (Attention → Interest → Desire → Action) email.

TALKING POINT 1 (ATTENTION): A surprising stat or fact about the genomic data market that would hook a quant/systematic investor. Use real data.

TALKING POINT 2 (INTEREST): Why this matters specifically to their firm type. Connect genomic data to their investment style.

TALKING POINT 3 (DESIRE): What other firms like them are doing with genomic data. Social proof without naming confidential clients.

Return ONLY valid JSON:
{{"tp1_attention": "...", "tp2_interest": "...", "tp3_desire": "...", "selected_capability": "parp|kelim|sector_rotation"}}
""",
        "pass2_prompt": """Write a cold email using ONLY these 3 talking points. Do NOT add anything else.

TALKING POINTS:
{talking_points}

PROSPECT NAME: {name}
PROSPECT COMPANY: {company}

RULES:
- Maximum 85 words in the body. Hard limit.
- BANNED WORDS: Dear, cutting-edge, innovative, leverage, synergy, unlock, revolutionize, unique, advanced, comprehensive, robust, holistic, transform, enhance, optimize, excited, fascinating
- BANNED OPENERS: "I hope this", "My name is", "I'm reaching out", "Dear"
- Address by FIRST NAME ONLY.
- Tone: You are sharing intel, not selling. Write like a market research note.
- Structure: Hook with the stat → 1 sentence on why it matters to THEIR firm type → 1 sentence on what peers do → offer a resource link
- CTA must be EXACTLY: "Wrote up how [peer firm type] is using this — want the link?" (replace [peer firm type] with their actual category, e.g. "systematic ETF managers")
- Do NOT ask for a call or meeting.
- Subject line: Under 40 chars, lead with the stat. No colons.
- PS: One sentence — a specific number or stat that adds credibility.

Return ONLY valid JSON:
{{"subject": "...", "body": "...", "ps": "..."}}
"""
    }
}


# ── TWO-PASS ENGINE ──────────────────────────────────────────────────────────

def _call_cohere(prompt: str, cohere_key: str) -> Dict[str, Any]:
    """Call Cohere v2 chat with JSON response format.

    If no real Cohere key is provided (placeholder/empty), delegate to the shared
    llm_json fallback chain (OpenRouter/Gemma, OpenAI, Anthropic) so the writer
    works with whatever provider is configured. Zero changes to call sites.
    """
    if not cohere_key or cohere_key.strip().lower() in ("", "none", "placeholder", "sk-none"):
        from eaia.pipeline.llm import llm_json
        return llm_json(prompt)
    try:
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
    except Exception:
        # Cohere failed (bad key, rate limit, outage) — fall through to shared chain
        from eaia.pipeline.llm import llm_json
        return llm_json(prompt)


def _two_pass_generate(
    framework_key: str,
    signals: Dict[str, Any],
    prospect_info: str,
    name: str,
    company: str,
    cohere_key: str
) -> Dict[str, Any]:
    """
    Pass 1: Extract talking points from signals using the framework's think prompt.
    Pass 2: Write the email using ONLY those talking points.
    """
    fw = FRAMEWORKS[framework_key]

    # ── PASS 1: THINK ────────────────────────────────────────────────────
    p1 = fw["pass1_prompt"].format(
        signals=json.dumps(signals, indent=2),
        prospect_info=prospect_info
    )
    talking_points = _call_cohere(p1, cohere_key)

    # ── PASS 2: WRITE ────────────────────────────────────────────────────
    p2 = fw["pass2_prompt"].format(
        talking_points=json.dumps(talking_points, indent=2),
        name=name,
        company=company
    )
    email = _call_cohere(p2, cohere_key)

    return {
        "framework": framework_key,
        "framework_name": fw["name"],
        "talking_points": talking_points,
        "email": email
    }


def _generate_ab_subjects(
    email_body: str,
    name: str,
    company: str,
    cohere_key: str
) -> list:
    """Generate 2 A/B subject line variants for split testing."""
    prompt = f"""Given this cold email body, generate 2 alternative subject lines for A/B testing.

EMAIL BODY:
{email_body}

PROSPECT: {name} at {company}

RULES:
- Under 50 characters each
- Variant A: Question format
- Variant B: Statement format
- Both must reference something specific about the prospect
- NO generic subjects like "Quick question" or "Partnership opportunity"

Return ONLY valid JSON:
{{"variant_a": "...", "variant_b": "..."}}
"""
    try:
        result = _call_cohere(prompt, cohere_key)
        return [result.get("variant_a", ""), result.get("variant_b", "")]
    except Exception:
        return []


# ── LANGCHAIN TOOL ────────────────────────────────────────────────────────────

@tool
def write_challenger_email(
    prospect_name: str,
    company_name: str,
    distilled_signals_json: str,
    prospect_summary: str,
    framework_override: str = ""
) -> str:
    """
    Two-pass email generation with automatic framework selection.
    
    Args:
        prospect_name: Full name of the prospect (e.g., "Peter McManus")
        company_name: Company name (e.g., "3EDGE Asset Management")
        distilled_signals_json: JSON string from the distill_signals tool
        prospect_summary: One-paragraph summary of the prospect and their firm
        framework_override: Optional — force "challenger", "pas", or "aida". If empty, auto-selects from distilled signals.
    
    Returns:
        JSON with framework used, talking points, email (subject/body/ps), and A/B subject variants.
    """
    cohere_key = os.getenv("COHERE_API_KEY")
    if not cohere_key:
        return json.dumps({"error": "No COHERE_API_KEY set"})

    # Parse distilled signals
    try:
        signals = json.loads(distilled_signals_json)
    except json.JSONDecodeError:
        signals = {
            "specific_number": "UNKNOWN",
            "recent_event": "UNKNOWN",
            "strategic_detail": "UNKNOWN",
            "blind_spot": distilled_signals_json[:500],
            "recommended_framework": "challenger"
        }

    # Select framework
    if framework_override and framework_override in FRAMEWORKS:
        fw_key = framework_override
    else:
        fw_key = signals.get("recommended_framework", "challenger")
        if fw_key not in FRAMEWORKS:
            fw_key = "challenger"

    # Two-pass generation
    try:
        result = _two_pass_generate(
            framework_key=fw_key,
            signals=signals,
            prospect_info=prospect_summary,
            name=prospect_name,
            company=company_name,
            cohere_key=cohere_key
        )

        # A/B subject lines
        email_body = result["email"].get("body", "")
        ab_subjects = _generate_ab_subjects(
            email_body, prospect_name, company_name, cohere_key
        )
        result["ab_subject_variants"] = ab_subjects

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "framework": fw_key})
