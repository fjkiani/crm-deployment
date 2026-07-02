"""
pipeline/graph.py — LangGraph Pipeline Assembly.

This file contains ZERO business logic.
It only wires nodes into a graph and exposes run_pipeline().

Adding a new node: import it, add_node, add_edge. Done.
Replacing a node: swap the import. The graph doesn't change.

Pipeline flow:
  research → distill → score → write → review ──[pass]──→ sync → END
                                           ↑                        ↓
                                           └─────[fail + retry]─────

Architecture note:
  Quarantined leads (signal_gate = "quarantine") still flow through all nodes —
  score_node and write_node both check signal_gate and early-return.
  sync_node writes the quarantined state to CRM so the lead is visible in Cockpit.
"""
import asyncio
import logging

from langgraph.graph import StateGraph, END
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.pipeline.nodes.research import research_node
from eaia.pipeline.nodes.distill  import distill_node
from eaia.pipeline.nodes.score    import score_node
from eaia.pipeline.nodes.write    import write_node
from eaia.pipeline.nodes.review   import review_node, should_retry
from eaia.pipeline.nodes.sync     import sync_node

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """
    Assemble and compile the outreach LangGraph.

    Returns a compiled graph ready to invoke.
    Call this once at startup and reuse.
    """
    g = StateGraph(OutreachState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    # NOTE: node id "scoring" (not "score") — LangGraph forbids a node name that
    # collides with a state key, and "score" is a field on OutreachState.
    g.add_node("research", research_node)
    g.add_node("distill",  distill_node)
    g.add_node("scoring",  score_node)
    g.add_node("write",    write_node)
    g.add_node("review",   review_node)
    g.add_node("sync",     sync_node)

    # ── Static edges ───────────────────────────────────────────────────────
    g.set_entry_point("research")
    g.add_edge("research", "distill")
    g.add_edge("distill",  "scoring")
    g.add_edge("scoring",  "write")
    g.add_edge("write",    "review")
    g.add_edge("sync",     END)

    # ── Conditional edge: Review → retry Write or → Sync ──────────────────
    g.add_conditional_edges(
        "review",
        should_retry,
        {"retry": "write", "sync": "sync"},
    )

    return g.compile()


# ── Module-level compiled graph (lazy init) ───────────────────────────────────
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_pipeline(
    prospect_name: str,
    company_name: str,
    callback=None,
) -> OutreachState:
    """
    Run the full outreach pipeline for one prospect.

    Args:
        prospect_name: Full name of the prospect
        company_name:  Company/fund name
        callback:      Async callback(node, event_type, data) for streaming UI updates

    Returns:
        Final OutreachState with all fields populated.

    Usage:
        from eaia.pipeline.graph import run_pipeline
        result = await run_pipeline("Peter McManus", "3EDGE Asset Management")
        print(result["score"], result["email_draft"])
    """
    graph = _get_graph()
    initial_state: OutreachState = {
        "prospect_name": prospect_name,
        "company_name":  company_name,
        "attempt":       1,
    }
    config = RunnableConfig(configurable={"callback": callback})

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        return final_state
    except Exception as e:
        logger.error(f"Pipeline error for {prospect_name} @ {company_name}: {e}")
        return {**initial_state, "error": str(e)}
