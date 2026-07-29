"""Tenant configuration layer — makes the outreach engine multi-tenant.

The TenantPack object carries one tenant's identity, ICP, proof points,
frameworks, CTAs, and lead sources. The engine reads it at runtime so that
tenant identity lives in DATA (packs/<id>.yaml), not in code.
"""
from eaia.tenant.pack import (
    TenantPack,
    ProofPoint,
    Framework,
    LeadSource,
    get_active_pack,
    DEFAULT_TENANT_ID,
)

__all__ = [
    "TenantPack",
    "ProofPoint",
    "Framework",
    "LeadSource",
    "get_active_pack",
    "DEFAULT_TENANT_ID",
]
