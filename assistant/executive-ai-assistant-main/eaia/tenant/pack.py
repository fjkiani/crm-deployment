"""
TenantPack — the per-tenant configuration object that makes the outreach engine
domain-blind. The engine reads a TenantPack at runtime; the tenant's identity,
ICP, proof points, frameworks, CTAs, and lead sources live in DATA (a YAML pack
under eaia/tenant/packs/<tenant_id>.yaml), not in code.

This supersedes the scattered NYX_* ICP env vars in eaia.config.NyxConfig. For
backward-compatibility, every field falls back to NyxConfig (which itself reads
env), so the 13 files already honoring that seam do not regress.

Design goals:
  - Zero heavy deps (dataclasses + yaml + os only).
  - One load per request: TenantPack.load(tenant_id).
  - Skills stay thin: the pack renders the tenant-specific prompt fragments.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

try:
    import yaml  # PyYAML
except Exception:  # pragma: no cover - yaml is expected to be present
    yaml = None

from eaia.config import NyxConfig

# Where per-tenant YAML packs live.
_PACKS_DIR = os.path.join(os.path.dirname(__file__), "packs")

# Which tenant to load when none is specified (env override for deploys).
DEFAULT_TENANT_ID = os.getenv("NYX_TENANT_ID", "crispro")


@dataclass
class ProofPoint:
    """A single verifiable capability/proof the writer may cite."""
    key: str                      # short id, e.g. "parp"
    label: str                    # human label, e.g. "PARP Inhibitor Resistance Signal"
    claim: str                    # the verifiable claim/proof sentence

    def render(self) -> str:
        return f"- {self.label}: {self.claim}"


@dataclass
class Framework:
    """A persuasion framework: structural template + tenant-agnostic rules.

    The STRUCTURE (word limits, banned words, CTA shape) is tenant-agnostic and
    lives here. The tenant-specific content (who we are, proof points, exact CTA
    text) is injected from the pack at render time.
    """
    key: str                      # "challenger" | "pas" | "aida" | ...
    name: str
    when: str                     # selection guidance (which lead tier)
    max_words: int
    cta: str                      # exact CTA text for this framework (tenant-specific)
    # Optional per-framework prompt scaffolds. If empty, the skill supplies
    # a default scaffold and injects {persona}/{proof_block}/{cta}.
    pass1_prompt: str = ""
    pass2_prompt: str = ""


@dataclass
class LeadSource:
    """A source the scout (jr1) can pull leads from."""
    kind: str                     # "clinicaltrials" | "apollo" | "sheet" | "csv" | ...
    default_query: str = ""       # default search/seed query for this source


@dataclass
class TenantPack:
    """Everything the outreach engine needs to act AS a given tenant."""
    tenant_id: str

    # ── Identity ──────────────────────────────────────────────────────────
    company_name: str
    company_description: str      # e.g. "a genomic data platform"
    value_prop: str
    what_we_sell: str             # one-paragraph "what we sell + who buys"
    industry: str
    sender_signature: str = "—"   # how emails sign off (e.g. "— Nyx")
    data_gap_label: str = "data gap"

    # ── ICP / scoring ─────────────────────────────────────────────────────
    icp_criteria: List[str] = field(default_factory=list)
    scoring_rubric: str = ""      # free-text HOT/WARM/COLD rules
    default_angle: str = ""       # fallback sales angle when LLM unavailable
    score_hot: int = 70
    score_warm: int = 40
    signal_gate_min: int = 2

    # ── Messaging assets ──────────────────────────────────────────────────
    proof_points: List[ProofPoint] = field(default_factory=list)
    frameworks: Dict[str, Framework] = field(default_factory=dict)
    default_framework: str = "challenger"
    voice_guide: str = ""         # the gold-standard voice description

    # ── Sourcing ──────────────────────────────────────────────────────────
    lead_sources: List[LeadSource] = field(default_factory=list)

    # ── Sending ───────────────────────────────────────────────────────────
    send_domains: List[str] = field(default_factory=list)

    # ── render helpers used by the skills ─────────────────────────────────
    def persona_line(self) -> str:
        """The 'You are a B2B sales strategist for <X>, <desc>.' opener."""
        return f"You are a B2B sales strategist for {self.company_name}, {self.company_description}."

    def scoring_persona_line(self) -> str:
        return (
            f"You are a B2B sales intelligence analyst for {self.company_name}, "
            f"{self.company_description}."
        )

    def proof_block(self) -> str:
        """Bullet list of proof points for injection into a writer prompt."""
        if not self.proof_points:
            return "- (no specific proof points configured)"
        return "\n".join(p.render() for p in self.proof_points)

    def proof_keys(self) -> List[str]:
        return [p.key for p in self.proof_points]

    def icp_block(self) -> str:
        if not self.icp_criteria:
            return "- (no ICP criteria configured)"
        return "\n".join(f"- {c}" for c in self.icp_criteria)

    def framework(self, key: str) -> Optional[Framework]:
        return self.frameworks.get(key)

    def default_source_query(self) -> str:
        for s in self.lead_sources:
            if s.default_query:
                return s.default_query
        return ""

    # ── loading ───────────────────────────────────────────────────────────
    @classmethod
    def load(cls, tenant_id: Optional[str] = None) -> "TenantPack":
        """Load a tenant pack from YAML, falling back to NyxConfig env defaults.

        Resolution order per field: YAML pack value -> NyxConfig (env) -> hardcoded default.
        """
        tid = tenant_id or DEFAULT_TENANT_ID
        data: Dict[str, Any] = {}
        path = os.path.join(_PACKS_DIR, f"{tid}.yaml")
        if yaml is not None and os.path.exists(path):
            with open(path, "r") as fh:
                data = yaml.safe_load(fh) or {}

        # ── identity (YAML -> NyxConfig env -> default) ──────────────────
        company_name = data.get("company_name", NyxConfig.COMPANY_NAME)
        company_description = data.get("company_description", NyxConfig.COMPANY_DESCRIPTION)
        value_prop = data.get("value_prop", NyxConfig.VALUE_PROP)
        industry = data.get("industry", NyxConfig.INDUSTRY)
        data_gap_label = data.get("data_gap_label", NyxConfig.DATA_GAP_LABEL)
        what_we_sell = data.get("what_we_sell", value_prop)
        sender_signature = data.get("sender_signature", "—")

        # ── proof points ─────────────────────────────────────────────────
        proof_points = [
            ProofPoint(key=p["key"], label=p["label"], claim=p["claim"])
            for p in data.get("proof_points", [])
        ]

        # ── frameworks ───────────────────────────────────────────────────
        frameworks: Dict[str, Framework] = {}
        for fw in data.get("frameworks", []):
            frameworks[fw["key"]] = Framework(
                key=fw["key"],
                name=fw.get("name", fw["key"]),
                when=fw.get("when", ""),
                max_words=int(fw.get("max_words", 75)),
                cta=fw.get("cta", ""),
                pass1_prompt=fw.get("pass1_prompt", ""),
                pass2_prompt=fw.get("pass2_prompt", ""),
            )

        # ── lead sources ─────────────────────────────────────────────────
        lead_sources = [
            LeadSource(kind=s["kind"], default_query=s.get("default_query", ""))
            for s in data.get("lead_sources", [])
        ]

        # ── send domains (YAML -> env) ───────────────────────────────────
        send_domains = data.get("send_domains", NyxConfig.SEND_DOMAINS)

        return cls(
            tenant_id=tid,
            company_name=company_name,
            company_description=company_description,
            value_prop=value_prop,
            what_we_sell=what_we_sell,
            industry=industry,
            sender_signature=sender_signature,
            data_gap_label=data_gap_label,
            icp_criteria=data.get("icp_criteria", []),
            scoring_rubric=data.get("scoring_rubric", ""),
            default_angle=data.get("default_angle", f"Pitch {company_name} as a fit for their needs."),
            score_hot=int(data.get("score_hot", NyxConfig.SCORE_HOT)),
            score_warm=int(data.get("score_warm", NyxConfig.SCORE_WARM)),
            signal_gate_min=int(data.get("signal_gate_min", NyxConfig.SIGNAL_GATE_MIN)),
            proof_points=proof_points,
            frameworks=frameworks,
            default_framework=data.get("default_framework", NyxConfig.DEFAULT_FRAMEWORK),
            voice_guide=data.get("voice_guide", ""),
            lead_sources=lead_sources,
            send_domains=send_domains,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Module-level convenience: lazy singleton for the active tenant.
_active: Optional[TenantPack] = None


def get_active_pack(tenant_id: Optional[str] = None) -> TenantPack:
    """Return the active tenant pack (cached). Pass tenant_id to force a specific one."""
    global _active
    if tenant_id is not None:
        return TenantPack.load(tenant_id)
    if _active is None:
        _active = TenantPack.load()
    return _active
