"""
Chat API Router
================
SSE chat endpoint with TOOL_REGISTRY pattern.
Replaces the 250-line if/elif tool dispatch from server.py.
New tools = one line in TOOL_REGISTRY dict, not a new elif block.

Supports TWO input formats:
  - POST /chat/stream  → ChatRequest  (internal agent use)
  - POST /chat         → FarfalleChatRequest  (Farfalle frontend — backward compat)
"""

import os
import json
import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from eaia.api.models import ChatRequest, FarfalleChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY — stolen from services/research_framework/orchestrator.py
# Adding a new tool = one line here instead of 15 lines of if/elif.
# ═══════════════════════════════════════════════════════════════════════════════

def _exec_lead_hunter(args):
    from eaia.frappe_tool import search_leads
    result = search_leads.invoke({
        "query": args.get("company", args.get("query", "")),
        "status": args.get("status", ""),
        "limit": args.get("limit", 10),
    })
    return str(result)


def _exec_lead_hunter_apollo(args):
    """Apollo-based lead hunter (the original async version)."""
    # This is synchronous wrapper; actual async handled in event loop
    from eaia.skills.lead_hunter_tool import _async_lead_hunter
    import asyncio
    role = args.get("role", "Executive")
    industry = args.get("industry", "Tech")
    location = args.get("location", "US")
    limit = args.get("limit", 5)
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(asyncio.run, _async_lead_hunter(role, industry, location, limit)).result()
    else:
        result = asyncio.run(_async_lead_hunter(role, industry, location, limit))
    return str(result)


def _exec_create_lead(args):
    from eaia.frappe_tool import create_new_lead
    return str(create_new_lead.invoke(args))


def _exec_update_context(args):
    from eaia.frappe_tool import update_context
    return str(update_context.invoke({
        "lead_name": args.get("lead_name"),
        "context_json": args.get("context_json", args.get("context", "{}")),
    }))


def _exec_web_search(args):
    query = args.get("query", "")
    if not query:
        return "❌ Missing query for web_search."
    try:
        from eaia.skills.search_tool import web_search
        return str(web_search.invoke({"query": query}))
    except ImportError:
        from eaia.research_tool import web_search
        return str(web_search.invoke({"query": query}))


def _exec_brightdata_search(args):
    query = args.get("query", "")
    if not query:
        return "❌ Missing query for brightdata_web_search."
    from eaia.brightdata_tool import brightdata_web_search
    return str(brightdata_web_search.invoke(query))


def _exec_research_company(args):
    company = args.get("company_name", "")
    if not company:
        return "❌ Missing company_name for research_company."
    from eaia.research_tool import research_company
    return str(research_company.invoke({"company_name": company}))


def _exec_voice_call(args):
    from eaia.skills.voice_tool import voice_call
    phone = args.get("phone_number")
    objective = args.get("objective")
    if not (phone and objective):
        return "❌ Missing phone_number or objective."
    return str(voice_call.invoke({"phone_number": phone, "objective": objective}))


def _exec_score_lead(args):
    from eaia.skills.lead_scoring_tool import score_lead
    lead_data_str = args.get("lead_data_str", str(args))
    return str(score_lead.invoke({"lead_data_str": lead_data_str}))


def _exec_vapi_mcp_call(args):
    from eaia.skills.vapi_mcp_tool import vapi_mcp_call
    return str(vapi_mcp_call.invoke({
        "phone_number": args.get("phone_number"),
        "objective": args.get("objective"),
    }))


def _exec_harvest(args):
    from eaia.skills.harvest_tool import run_harvest_mission
    return str(run_harvest_mission.invoke({"target_disease": args.get("target_disease")}))


def _exec_distill_signals(args):
    from eaia.skills.signal_distiller import distill_signals
    return str(distill_signals.invoke({"raw_intel": args.get("raw_intel", "")}))


def _exec_challenger_email(args):
    from eaia.skills.challenger_email_writer import write_challenger_email
    return str(write_challenger_email.invoke({
        "prospect_name": args.get("prospect_name", ""),
        "company_name": args.get("company_name", ""),
        "distilled_signals_json": args.get("distilled_signals_json", "{}"),
        "prospect_summary": args.get("prospect_summary", ""),
        "framework_override": args.get("framework_override", ""),
    }))


def _exec_communication_history(args):
    from eaia.frappe_tool import get_communication_history
    return str(get_communication_history.invoke({
        "lead_name": args.get("lead_name"),
        "limit": args.get("limit", 20),
    }))


def _exec_get_dossier(args):
    from eaia.frappe_tool import get_lead_dossier
    return str(get_lead_dossier.invoke({"lead_name": args.get("lead_name")}))


def _handle_question(args):
    """Agent wants to ask a clarification question."""
    question = args.get("content", "")
    return f"❓ **Clarification Needed**: {question}"


def _handle_draft(args):
    """Agent wants to show an email draft."""
    draft = args.get("content", "")
    return f"📝 **Draft Response**:\n{draft}"


# ── NEW: Dormant skills now wired ────────────────────────────────────────────

def _exec_deep_audit(args):
    """Reality-check CRM leads: verify job title via BrightData, flag stale."""
    from eaia.skills.deep_audit_tool import deep_audit_leads
    limit = args.get("limit", 5)
    return str(deep_audit_leads.invoke({"limit": limit}))


def _exec_air_support(args):
    """Find contact info (email, phone) using Tavily + Diffbot web scouting."""
    import asyncio
    from eaia.skills.air_support import scout_target
    name = args.get("name", "")
    org = args.get("org", args.get("organization", ""))
    if not (name and org):
        return "❌ Missing name or org for scout_target."
    try:
        result = asyncio.run(scout_target(name, org))
        return str(result) if result else "No contact info found."
    except RuntimeError:
        # Already in async event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(asyncio.run, scout_target(name, org)).result()
        return str(result) if result else "No contact info found."


def _exec_clinical_search(args):
    """Search ClinicalTrials.gov for trials by condition or keywords."""
    from eaia.skills.clinical_mcp import search_clinical_trials
    search_expr = args.get("search_expr", args.get("query", ""))
    max_studies = args.get("max_studies", 10)
    if not search_expr:
        return "❌ Missing search_expr for clinical trials search."
    return str(search_clinical_trials.invoke({
        "search_expr": search_expr,
        "max_studies": max_studies,
    }))


def _exec_clinical_details(args):
    """Get detailed info for a specific clinical trial by NCT ID."""
    from eaia.skills.clinical_mcp import get_clinical_trial_details
    nct_id = args.get("nct_id", "")
    if not nct_id:
        return "❌ Missing nct_id for clinical trial details."
    return str(get_clinical_trial_details.invoke({"nct_id": nct_id}))


def _exec_lead_snapshot(args):
    """Get compact real-time lead status from CRM: status, emails, calls."""
    from eaia.skills.communication_history_tool import get_lead_status_snapshot
    lead_name = args.get("lead_name", "")
    if not lead_name:
        return "❌ Missing lead_name for status snapshot."
    return str(get_lead_status_snapshot.invoke({"lead_name": lead_name}))


def _exec_classify_reply(args):
    """Classify inbound email reply: INTERESTED/NOT_INTERESTED/UNSUBSCRIBE/OOO."""
    from eaia.skills.reply_matrix import ReplyMatrix
    content = args.get("content", args.get("email_body", ""))
    if not content:
        return "❌ Missing content for reply classification."
    classification = ReplyMatrix.classify(content)
    return f"Classification: {classification}"


def _exec_apollo_enrich(args):
    """Enrich prospect via Apollo.io: find email, title, LinkedIn URL."""
    import asyncio
    from eaia.skills.apollo_enrichment import enrich_person
    name = args.get("name", args.get("prospect_name", ""))
    org = args.get("organization", args.get("company_name", ""))
    if not (name and org):
        return "❌ Missing name or organization for Apollo enrichment."
    try:
        result = asyncio.run(enrich_person(name, org))
        return str(result) if result else "No Apollo data found."
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(asyncio.run, enrich_person(name, org)).result()
        return str(result) if result else "No Apollo data found."


def _exec_search_leads_faceted(args):
    """Rich facet-aware lead search via the Frappe MCP (intel_facets)."""
    from eaia.frappe_tool import search_leads_faceted
    return str(search_leads_faceted.invoke(args))


def _exec_farfalle_deep_research(args):
    """Deep multi-source web research via the Farfalle RAG pipeline (async tool)."""
    import asyncio
    from eaia.tools.farfalle_tools import farfalle_deep_research
    query = args.get("query", "")
    if not query:
        return "❌ Missing 'query' for Farfalle deep research."
    try:
        return str(asyncio.run(farfalle_deep_research.ainvoke({"query": query})))
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return str(pool.submit(asyncio.run, farfalle_deep_research.ainvoke({"query": query})).result())


# ── The registry: name → handler ──────────────────────────────────────────────

TOOL_REGISTRY = {
    # CRM tools (via MCP)
    "lead_hunter":              _exec_lead_hunter,
    "create_new_lead":          _exec_create_lead,
    "update_context":           _exec_update_context,
    "communication_history":    _exec_communication_history,
    "get_lead_dossier":         _exec_get_dossier,
    "get_lead_status_snapshot": _exec_lead_snapshot,
    "search_leads_faceted":     _exec_search_leads_faceted,
    # Deep research
    "farfalle_deep_research":   _exec_farfalle_deep_research,
    # Research tools
    "brightdata_web_search":    _exec_brightdata_search,
    "web_search":               _exec_web_search,
    "research_company":         _exec_research_company,
    # Pipeline skills
    "voice_call":               _exec_voice_call,
    "score_lead":               _exec_score_lead,
    "vapi_mcp_call":            _exec_vapi_mcp_call,
    "run_harvest_mission":      _exec_harvest,
    "distill_signals":          _exec_distill_signals,
    "write_challenger_email":   _exec_challenger_email,
    # Enrichment + Intelligence
    "deep_audit_leads":         _exec_deep_audit,
    "scout_target":             _exec_air_support,
    "apollo_enrich":            _exec_apollo_enrich,
    "classify_reply":           _exec_classify_reply,
    # Clinical (cross-sell)
    "search_clinical_trials":   _exec_clinical_search,
    "get_clinical_trial_details": _exec_clinical_details,
    # Agent internal
    "Question":                 _handle_question,
    "ResponseEmailDraft":       _handle_draft,
}


# ═══════════════════════════════════════════════════════════════════════════════
# FARFALLE-COMPATIBLE CHAT ENDPOINT (backward compat — /chat)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/chat")
async def farfalle_chat_endpoint(request: FarfalleChatRequest):
    """Farfalle-compatible SSE Chat Endpoint — same URL/contract as old server.py."""
    from eaia.main.draft_response import graph

    async def event_generator():
        try:
            # 1. BEGIN_STREAM
            yield f"data: {json.dumps({'event': 'begin-stream', 'data': {'query': request.query}})}\n\n"

            # Convert history for Agent
            messages = [{"role": m.role, "content": m.content} for m in request.history[-5:]]
            messages.append({"role": "user", "content": request.query})

            initial_state = {
                "messages": messages,
                "email": {
                    "page_content": (
                        f"COMMAND: {request.query}\n"
                        "CONTEXT: The user is interacting via a Chat Interface. "
                        "Do NOT ask for clarification unless critical. "
                        "You have permission to use all tools directly. EXECUTE IMMEDIATELY."
                    ),
                    "from_email": "Admin User",
                    "subject": "URGENT: EXECUTE COMMAND",
                    "to_email": "Nyx Agent",
                },
            }

            # Invoke Graph
            final_state = await graph.ainvoke(initial_state)
            last_message = final_state["messages"][-1]
            content = last_message.content

            # Stream words for typing UX
            for word in content.split(" "):
                yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': word + ' '}})}\n\n"
                await asyncio.sleep(0.01)

            # TOOL EXECUTION via TOOL_REGISTRY
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                action_msg = "\n\n--- ⚡️ Agent Action ---\n"
                yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': action_msg}})}\n\n"

                for tool_call in last_message.tool_calls:
                    name = tool_call.get("name", "")
                    args = tool_call.get("args", {})

                    skill_msg = f"Executing Skill: {name}...\n"
                    yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': skill_msg}})}\n\n"

                    # TOOL_REGISTRY dispatch
                    handler = TOOL_REGISTRY.get(name)
                    if handler:
                        try:
                            tool_output = handler(args)
                        except Exception as tool_e:
                            tool_output = f"❌ Tool Execution Failed: {str(tool_e)}"
                    else:
                        tool_output = f"⚠️ Skill '{name}' not registered in TOOL_REGISTRY"

                    out_msg = tool_output + "\n"
                    yield f"data: {json.dumps({'event': 'text-chunk', 'data': {'text': out_msg}})}\n\n"

            # 3. STREAM END
            yield f"data: {json.dumps({'event': 'stream-end', 'data': {'thread_id': request.thread_id or 'new'}})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'event': 'error', 'data': {'detail': str(e)}})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
