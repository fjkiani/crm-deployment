"""
Revenue-Grade State Schema for The Army
Defines the shared memory structure for the circular GTM graph.
"""
from typing import List, Dict, Any, Optional, TypedDict, Annotated
import operator

# --- Sub-Schemas ---

class TrialMetadata(TypedDict):
    """Minimal metadata for a seeded trial."""
    nct_id: str
    title: str
    phase: str
    conditions: str
    # status: str

class Entity(TypedDict):
    """An organization or site (Sponsor, CRO, Hospital)."""
    id: str # internal ID or normalized name
    name: str # display name
    type: str # "SPONSOR", "CRO", "SITE"
    domain: Optional[str]
    metadata: Dict[str, Any] # 'cash_position', 'trial_volume', etc.

class LeadProfile(TypedDict):
    """A human target (PI, Coordinator, Director)."""
    id: str # email or unique hash
    name: str
    email: str
    role: str # "PI", "COORDINATOR", "CLIN_OPS"
    organization_id: str
    source_trial: str # NCT ID that generated this lead
    linkedin_url: Optional[str]
    publications: List[str] # citations

class Score(TypedDict):
    """Qualification Scorecard."""
    total_score: float # 0-100
    icp_fit: str # "A", "B", "C"
    intent_signals: List[str] # ["hiring", "new_trial"]
    why_us: str # The generated "Angle" statement

class CampaignSpecs(TypedDict):
    """Campaign Configuration."""
    name: str
    sequence_template: str # "SITE_ACTIVATION_V1", "SPONSOR_SPEED_V1"
    throttle_limit: int # max emails per day
    target_icp: str # "ICP_A", "ICP_B"

class ComplianceLog(TypedDict):
    """Risk and Deliverability Log."""
    blocked_domains: List[str]
    opt_outs: List[str]
    risk_level: str # "LOW", "MED", "HIGH"

class Event(TypedDict):
    """Outcome Event."""
    timestamp: str
    type: str # "SENT", "OPENED", "REPLIED", "BOOKED"
    lead_id: str
    details: str

# --- Main State ---

class ArmyState(TypedDict):
    """
    The shared state of the GTM Loop.
    """
    # LangGraph Standard
    messages: Annotated[List[Dict[str, Any]], operator.add]
    
    # The Map (JR1)
    trial_seeds: List[TrialMetadata]
    
    # The Entities (JR2)
    entities: Dict[str, Entity] # normalized_name -> Entity
    
    # The Humans (JR2)
    leads: List[LeadProfile]
    
    # The Intelligence (JR3)
    lead_scorecards: Dict[str, Score] # lead_id -> Score
    
    # The Plan (Zo)
    campaign: CampaignSpecs
    
    # The Rules (JR4)
    compliance: ComplianceLog
    
    # The Scoreboard (Zo2)
    outcomes: List[Event]
    
    # Flow Control
    safe_lead_ids: List[str] # Output from JR4
    mission_status: str
    errors: List[str]

    # Dataset Ingest (Zi) — all optional; absent for non-ingest missions
    ingest_file_url: Optional[str]        # File URL of dataset to ingest (JSON/CSV)
    ingest_records_json: Optional[str]    # inline JSON array (alternative to file_url)
    ingest_target_doctype: Optional[str]  # defaults to "Lead Prospect" in the node
    ingest_dry_run: Optional[int]         # defaults to 1 (validate before writing)
    ingest_profile_name: Optional[str]    # explicit CRM Import Column Map name
    ingest_result: Optional[Dict[str, Any]]  # kernel result echoed back

# Backward Compatibility
AgentState = ArmyState
