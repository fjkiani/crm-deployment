"""
Enrichment Agent — LLM-driven lead research and scoring
========================================================
Replaces the fixed research→distill→score pipeline with an LLM agent
that reasons about data to decide which sources to query.

Architecture:
  LangGraph agent loop: agent_node ↔ tool_node
  - agent_node: LLM decides next action (which tool to call)
  - tool_node: executes the tool, returns result
  - Loop continues until agent calls finalize_enrichment

The agent has access to:
  - Research tools: web_search, apollo_enrich, brightdata_search
  - BioMed tools: search_pubmed_articles, search_clinical_trials, etc.
  - CRM tools: crm_get_dossier, crm_update_context, crm_create_note
  - Analysis tools: distill_signals, score_lead
  - Control: finalize_enrichment (signals "I'm done")
"""

import json
import logging
from typing import Annotated, TypedDict, Sequence, Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT STATE
# ══════════════════════════════════════════════════════════════════════════════

class EnrichmentAgentState(TypedDict):
    """State for the enrichment agent's conversation loop."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Final output — populated by finalize_enrichment tool
    result: dict


# ══════════════════════════════════════════════════════════════════════════════
# FINALIZE TOOL — signals agent is done
# ══════════════════════════════════════════════════════════════════════════════

@tool
def finalize_enrichment(
    score: int,
    framework: str,
    reasoning: str,
    signals_json: str,
    detected_context: str,
    enrichment_sources_used: str,
) -> str:
    """Call this when you have completed all enrichment and scoring.

    This signals that you are done researching and the results should be
    persisted. You MUST call this exactly once as your final action.

    Args:
        score: Lead score 0-100
        framework: "challenger", "pas", or "aida"
        reasoning: Score explanation (2-3 sentences)
        signals_json: JSON string of distilled signals
        detected_context: Comma-separated contexts (e.g., "core,financial,clinical")
        enrichment_sources_used: Comma-separated list of sources used (e.g., "tavily,apollo,brightdata_sec,pubmed")
    """
    return json.dumps({
        "status": "finalized",
        "score": score,
        "framework": framework,
        "reasoning": reasoning,
        "signals": json.loads(signals_json) if isinstance(signals_json, str) else signals_json,
        "detected_context": [c.strip() for c in detected_context.split(",")],
        "enrichment_sources_used": [s.strip() for s in enrichment_sources_used.split(",")],
    })


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

ENRICHMENT_SYSTEM_PROMPT = """You are the Nyx Enrichment Agent — an autonomous sales intelligence researcher.

YOUR MISSION: Research a prospect thoroughly and score them for outreach potential.

## Decision Framework

1. ALWAYS start by checking CRM for existing data: call crm_get_dossier
   - If dossier already has a score and recent signals, DO NOT re-enrich. Just finalize.
   - If dossier is empty or stale (>7 days), proceed with full enrichment.

1b. CHECK COMMUNICATION HISTORY: call crm_get_communication_history
   - If 3+ emails sent in last 7 days → COOL DOWN. Set signal_gate = "cooldown" and finalize.
   - If previous emails exist, note their subjects. You MUST use a DIFFERENT angle.
   - Previous subjects: {previous_subjects} → pick a contrasting approach.

2. ALWAYS run these two tools first:
   - web_search("{prospect_name} {company_name} news strategy 2024 2025")
   - apollo_enrich("{prospect_name}", "{company_name}")

3. REASON about the web_search results. Ask yourself:
   - Is this a FINANCIAL firm? (hedge fund, PE, VC, family office, asset manager)
     → Call brightdata_search(company, "sec") for AUM from SEC 13F filing
     → Call brightdata_search(company, "strategy") for investment thesis
   - Is this a CLINICAL/BIOTECH/PHARMA company?
     → Call search_clinical_trials(company_name) for active trials
     → Call search_pubmed_articles(company_name + " drug" or relevant compound)
   - Is this a CROSSOVER investor (finance + healthcare)?
     → Call BOTH financial AND clinical tools
     → Look for portfolio companies' clinical trials
   - Is this a TECH company?
     → Call brightdata_search(company, "competitor") for competitive landscape

4. After gathering 3+ quality signals, call distill_signals with ALL raw research.

5. Call score_lead with the distilled signals.

6. Write findings to CRM:
   - crm_update_context(lead_name, enrichment_data)
   - crm_create_note(lead_name, title, summary)

7. Call finalize_enrichment with the final score and signals.

## What Counts as a Quality Signal
- A SPECIFIC NUMBER: "$3.2B AUM", "Phase 3 trial with 450 patients", "$200M Series C"
- A RECENT EVENT: "Appointed new CTO in Q3 2025", "FDA Fast Track granted"
- A STRATEGIC DETAIL: "Focuses on RNA therapeutics", "Specializes in distressed debt"
- A COMPETITIVE ANGLE: "Competitor X just failed Phase 2, creating opportunity"

## Rules
- NEVER fabricate data. If you can't find a signal, mark it UNKNOWN.
- DO NOT call the same tool twice with the same arguments.
- Call finalize_enrichment EXACTLY ONCE when done. This is mandatory.
- Maximum 10 tool calls before you must finalize (avoid infinite loops).
- If a tool returns an error, try an alternative approach, don't retry the same call.
"""


# ══════════════════════════════════════════════════════════════════════════════
# BUILD AGENT
# ══════════════════════════════════════════════════════════════════════════════

def build_enrichment_agent(llm=None):
    """Build and compile the enrichment agent graph.

    Args:
        llm: LangChain chat model. If None, uses Cohere command-r-plus.

    Returns:
        Compiled LangGraph agent ready to .ainvoke()
    """
    # ── Import tools ──────────────────────────────────────────────────────
    from eaia.tools.research_tools import ALL_RESEARCH_TOOLS
    from eaia.tools.frappe_mcp_tools import (
        crm_get_dossier, crm_update_context, crm_search_leads, crm_create_note,
        crm_get_communication_history,
    )

    # Import BioMed tools (graceful fallback if not installed)
    biomed_tools = []
    try:
        from eaia.mcp.biomed_mcp.biomed_agents.tools.clinical_tools import CLINICAL_TOOLS
        biomed_tools.extend(CLINICAL_TOOLS)
    except ImportError:
        logger.warning("Clinical tools not available — skipping")
    try:
        from eaia.mcp.biomed_mcp.biomed_agents.tools.pubmed_tools import PUBMED_TOOLS
        biomed_tools.extend(PUBMED_TOOLS)
    except ImportError:
        logger.warning("PubMed tools not available — skipping")

    # Combine all tools
    all_tools = [
        *ALL_RESEARCH_TOOLS,
        crm_get_dossier,
        crm_update_context,
        crm_search_leads,
        crm_create_note,
        crm_get_communication_history,
        *biomed_tools,
        finalize_enrichment,
    ]

    # ── LLM setup ─────────────────────────────────────────────────────────
    if llm is None:
        import os
        cohere_key = os.getenv("COHERE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if cohere_key:
            from langchain_cohere import ChatCohere
            llm = ChatCohere(
                model="command-r-plus-08-2024",
                cohere_api_key=cohere_key,
                temperature=0.2,
            )
        elif openai_key:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0.2,
            )
        else:
            raise RuntimeError("No LLM key — set COHERE_API_KEY or OPENAI_API_KEY")

    llm_with_tools = llm.bind_tools(all_tools)

    # ── Agent node (with Phase 10 trace logging) ────────────────────────────
    async def agent_node(state: EnrichmentAgentState):
        msg_count = len(state["messages"])
        logger.info(f"🔱 TRACE agent_node: {msg_count} messages, invoking LLM")
        response = await llm_with_tools.ainvoke(state["messages"])
        
        # Log tool calls for observability
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_names = [tc.get("name", "?") for tc in response.tool_calls]
            logger.info(f"🔱 TRACE agent_node: LLM chose tools → {', '.join(tool_names)}")
        else:
            content_preview = str(response.content)[:100] if hasattr(response, "content") else "?"
            logger.info(f"🔱 TRACE agent_node: LLM final response → {content_preview}")
        
        return {"messages": [response]}

    # ── Should continue? ──────────────────────────────────────────────────
    def should_continue(state: EnrichmentAgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            # Check if the agent is calling finalize_enrichment
            for tc in last.tool_calls:
                if tc.get("name") == "finalize_enrichment":
                    return "tools"  # Execute finalize, then extract result
            return "tools"
        return "end"

    # ── Result extractor ──────────────────────────────────────────────────
    def extract_result(state: EnrichmentAgentState):
        """Extract the finalization result from the last tool message."""
        for msg in reversed(state["messages"]):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if data.get("status") == "finalized":
                        return {"result": data}
                except (json.JSONDecodeError, TypeError):
                    continue
        # If no finalization found, return empty result
        return {"result": {"status": "incomplete", "error": "Agent did not call finalize_enrichment"}}

    # ── Build graph ───────────────────────────────────────────────────────
    tool_node = ToolNode(all_tools)
    graph = StateGraph(EnrichmentAgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("extract", extract_result)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": "extract"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract", END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════════════════════
# RUN ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════════

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_enrichment_agent()
    return _agent


async def run_enrichment(
    prospect_name: str,
    company_name: str,
    lead_name: str = "",
) -> dict:
    """Run the agentic enrichment for a single prospect.

    Args:
        prospect_name: Full name of the prospect
        company_name: Company name
        lead_name: Optional CRM Lead ID for CRM lookups

    Returns:
        Dict with score, framework, signals, detected_context, enrichment_sources_used
    """
    agent = _get_agent()

    initial_message = HumanMessage(
        content=(
            f"Enrich this lead:\n"
            f"- Prospect: {prospect_name}\n"
            f"- Company: {company_name}\n"
            f"- CRM Lead ID: {lead_name or 'not yet in CRM'}\n\n"
            f"Research them thoroughly, score them, write findings to CRM, "
            f"and call finalize_enrichment when done."
        )
    )

    initial_state = {
        "messages": [
            SystemMessage(content=ENRICHMENT_SYSTEM_PROMPT),
            initial_message,
        ],
        "result": {},
    }

    try:
        final_state = await agent.ainvoke(initial_state)
        result = final_state.get("result", {})

        # Add metadata
        result["prospect_name"] = prospect_name
        result["company_name"] = company_name
        result["lead_name"] = lead_name

        # ── SIGNAL QUALITY GATE ──────────────────────────────────────
        # If distilled signals are mostly UNKNOWN, quarantine the lead.
        # This prevents generic emails from being sent (capability_breakdown.md Failure 1).
        signals = result.get("signals", {})
        if isinstance(signals, str):
            try:
                signals = json.loads(signals)
            except Exception:
                signals = {}

        unknown_count = 0
        gate_fields = ["specific_number", "recent_event", "strategic_detail"]
        for field in gate_fields:
            val = str(signals.get(field, "UNKNOWN")).strip()
            if not val or val.upper() == "UNKNOWN" or len(val) < 10:
                unknown_count += 1

        if unknown_count >= 3:
            result["quarantined"] = True
            result["quarantine_reason"] = f"Signal gate failed: {unknown_count}/3 key signals are UNKNOWN"
            result["email_status"] = "Quarantined"
            logger.warning(
                f"⚠️ QUARANTINE: {prospect_name} at {company_name} — "
                f"{unknown_count}/3 signals UNKNOWN. No email will be generated."
            )
            # Schedule automatic retry with different enrichment strategy
            if lead_name:
                try:
                    from eaia.pipeline.retry_queue import quarantine_for_retry
                    retry_res = await quarantine_for_retry(
                        lead_name, result["quarantine_reason"]
                    )
                    result["retry_scheduled"] = retry_res
                except Exception as e:
                    logger.error(f"Retry scheduling failed: {e}")
        else:
            result["quarantined"] = False
            result["email_status"] = "Draft Ready"

        # Phase 9: Zeta Entanglement Protocol 🕸️
        # Automatically run entanglement to find and group coworkers
        if lead_name and company_name:
            try:
                from eaia.pipeline.agents.entanglement_agent import process_entanglement
                from eaia.mcp_client import FrappeMCPClient
                d = await FrappeMCPClient().get_lead_dossier(lead_name)
                email = d.get("email", "") or d.get("email_id", "")
                
                entangle_res = await process_entanglement(lead_name, company_name, email)
                result["entanglement"] = entangle_res
            except Exception as e:
                logger.error(f"Entanglement failed for {lead_name}: {e}")

        # ── Sync enrichment to Frappe custom fields ──────────────────
        # Writes nyx_score, nyx_enriched, email_status, nyx_signal_gate etc.
        # to REAL Frappe fields (not just additional_data JSON).
        if lead_name:
            try:
                from eaia.mcp_client import FrappeMCPClient
                sync_result = await FrappeMCPClient().sync_nyx_fields(lead_name, result)
                result["field_sync"] = sync_result
            except Exception as e:
                logger.warning(f"Nyx field sync failed (non-fatal) for {lead_name}: {e}")

        return result

    except Exception as e:
        logger.error(f"Enrichment agent error for {prospect_name}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "prospect_name": prospect_name,
            "company_name": company_name,
        }
