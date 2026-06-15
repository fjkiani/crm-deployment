"""
The Battlefield: LangGraph Definition for The Army
Wires together JR1, JR2, JR3 and Zo into a circular revenue loop.
"""
import logging
from langgraph.graph import StateGraph, END
from eaia.agents.state import ArmyState

# Agents
from eaia.agents.jr1 import jr1_scout_agent
from eaia.agents.jr2 import jr2_hunter_agent
from eaia.agents.jr3 import jr3_qualifier_agent
from eaia.agents.jr4 import jr4_compliance_agent
from eaia.agents.jr5 import jr5_sequencer_agent
from eaia.agents.zo import zo_crm_sync
from eaia.agents.zo2 import zo2_closer_agent
from eaia.agents.ingest import zi_ingest_agent

logger = logging.getLogger(__name__)

# --- Graph Construction ---

def build_army_graph():
    """Constructs the Revenue-Grade Graph."""
    workflow = StateGraph(ArmyState)
    
    # 1. Add Nodes
    workflow.add_node("scout", jr1_scout_agent)
    workflow.add_node("hunter", jr2_hunter_agent)
    workflow.add_node("qualifier", jr3_qualifier_agent)
    workflow.add_node("sheriff", jr4_compliance_agent)
    workflow.add_node("sequencer", jr5_sequencer_agent)
    workflow.add_node("crm_sync", zo_crm_sync)
    
    # 2. Add Edges (The Pipeline)
    workflow.set_entry_point("scout")
    
    # Scout -> Hunter
    workflow.add_edge("scout", "hunter")
    
    # Hunter -> Qualifier
    workflow.add_edge("hunter", "qualifier")
    
    # Qualifier -> Sheriff (Gatekeeper)
    workflow.add_edge("qualifier", "sheriff")
    
    # Sheriff -> Sequencer
    workflow.add_edge("sheriff", "sequencer")
    
    # Sequencer -> CRM Sync
    workflow.add_edge("sequencer", "crm_sync")
    
    # CRM Sync -> End
    workflow.add_edge("crm_sync", END)
    
    # 3. Compile
    return workflow.compile()

# For direct execution
army = build_army_graph()


# --- Dataset-Ingest Graph (separate mission, not a stage of the GTM loop) ---

def build_ingest_graph():
    """Single-node graph for autonomous dataset ingest into the staging doctype.

    Kept separate from the GTM loop on purpose: ingest is its own mission (drop a
    dataset → map → normalize → stage), not a step that should run scout/hunter/etc.
    The node (`zi_ingest_agent`) invokes the server-side kernel
    `crm.api.leadgen.run_dataset_ingest`, which performs propose-and-pause mapping
    (Tier-1 deterministic + Tier-2 Gemini) and drives Frappe's native Data Import.
    """
    workflow = StateGraph(ArmyState)
    workflow.add_node("ingestor", zi_ingest_agent)
    workflow.set_entry_point("ingestor")
    workflow.add_edge("ingestor", END)
    return workflow.compile()

# For direct execution
ingest_army = build_ingest_graph()
