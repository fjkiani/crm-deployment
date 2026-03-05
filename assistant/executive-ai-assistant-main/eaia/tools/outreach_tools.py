"""
Outreach Tools — LangChain @tool wrappers for email, voice, and sequences
==========================================================================
These tools let the enrichment/outreach agent autonomously:
  - Write and draft emails (via Cohere/OpenAI)
  - Place voice calls (via Vapi MCP)
  - Manage multi-touch sequences (via Frappe MCP)
"""

import os
import json
import asyncio
import logging
from langchain_core.tools import tool
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@tool
async def write_email_draft(
    prospect_name: str,
    company_name: str,
    signals_json: str,
    framework: str = "challenger",
) -> str:
    """Write a personalized email draft using distilled intelligence signals.

    The framework determines the email style:
    - "challenger" (for HOT leads, score >= 70): Teach something, challenge status quo
    - "pas" (for WARM leads, score 40-69): Problem → Agitate → Solution
    - "aida" (for COLD leads, score < 40): Attention → Interest → Desire → Action

    Args:
        prospect_name: Full name of the prospect
        company_name: Company name
        signals_json: JSON string of distilled signals from distill_signals tool
        framework: Email framework — "challenger", "pas", or "aida"
    """
    try:
        from eaia.pipeline.llm import llm_json
        signals = json.loads(signals_json) if isinstance(signals_json, str) else signals_json
        first_name = prospect_name.split()[0]

        prompt = f"""Write a cold outreach email using the {framework.upper()} framework.

PROSPECT: {prospect_name} (address as "{first_name}")
COMPANY: {company_name}

INTELLIGENCE SIGNALS:
- Specific Number: {signals.get('specific_number', 'UNKNOWN')}
- Recent Event: {signals.get('recent_event', 'UNKNOWN')}
- Strategic Detail: {signals.get('strategic_detail', 'UNKNOWN')}
- Blind Spot: {signals.get('blind_spot', 'UNKNOWN')}
- Competitor: {signals.get('competitor_name', 'UNKNOWN')}

FRAMEWORK RULES ({framework.upper()}):
{"- Teach something they don't know. Challenge their current approach. Cite specific proof." if framework == "challenger" else "- Name the Problem. Cost the pain ($ or time). Present the fix." if framework == "pas" else "- Hook stat (Attention). Amplify with peer proof (Interest). Show the gap (Desire). Simple CTA (Action)."}

RULES:
- Every sentence must reference a signal above. No generic lines.
- If a signal is UNKNOWN, do NOT reference that topic.
- Max 4 sentences + 1 CTA.
- Subject line must be specific to them (no "Quick question" garbage).

Return JSON:
{{
  "subject": "specific subject line",
  "body": "email body text",
  "ps": "P.S. one-liner that creates FOMO or urgency"
}}"""
        result = llm_json(prompt)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Email drafting error: {e}"


@tool
async def voice_call(
    phone_number: str,
    prospect_name: str,
    objective: str,
    signals_json: str = "{}",
) -> str:
    """Place an AI voice call to a prospect using Vapi.

    Use this as an escalation tool when:
    - Email was sent but no response after 7+ days
    - Score is >= 70 (HOT lead worth the call)
    - Phone number is available

    The call will use intelligence signals to personalize the conversation.

    Args:
        phone_number: Phone number to call (with country code)
        prospect_name: Name of the person being called
        objective: Goal of the call (e.g., "Schedule a demo", "Follow up on email")
        signals_json: Optional JSON of intelligence signals for context
    """
    try:
        signals = json.loads(signals_json) if isinstance(signals_json, str) else signals_json

        context = f"""You are calling {prospect_name}.
Objective: {objective}

Intelligence Brief:
- Company Strategy: {signals.get('strategic_detail', 'Unknown')}
- Recent Event: {signals.get('recent_event', 'Unknown')}
- Key Number: {signals.get('specific_number', 'Unknown')}

Keep it under 90 seconds. Be specific. Reference their recent activity.
If they're not available, leave a voicemail referencing the specific number or event."""

        from eaia.skills.vapi_mcp_tool import _invoke_mcp_create_call
        result = await _invoke_mcp_create_call(phone_number, objective, override_context=context)
        return str(result)
    except Exception as e:
        return f"Voice call error: {e}"


@tool
async def manage_sequence(
    lead_name: str,
    action: str = "status",
    dry_run: bool = True,
) -> str:
    """Manage a multi-touch outreach sequence for a lead.

    Actions:
    - "status": Check current sequence status (step, days elapsed, next fire)
    - "fire": Execute the next step in the sequence
    - "pause": Pause the sequence for this lead

    The 21-day siege sequence is:
    Day 0: Initial email (after enrichment + scoring)
    Day 3: Follow-up email (different angle)
    Day 7: Voice call if score >= 70
    Day 14: Final email (break-up angle)
    Day 21: Close sequence, mark as exhausted

    Args:
        lead_name: CRM Lead ID
        action: "status", "fire", or "pause"
        dry_run: If True, preview the action without executing
    """
    try:
        from eaia.mcp_client import FrappeMCPClient
        client = FrappeMCPClient()

        if action == "status":
            result = await client.get_sequence_status(lead_name)
        elif action == "fire":
            result = await client.fire_sequence_step(lead_name, dry_run=dry_run)
        elif action == "pause":
            result = await client.pause_outreach(lead_name)
        else:
            return f"Unknown action: {action}. Use 'status', 'fire', or 'pause'."

        return json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
    except Exception as e:
        return f"Sequence management error: {e}"


ALL_OUTREACH_TOOLS = [
    write_email_draft,
    voice_call,
    manage_sequence,
]
