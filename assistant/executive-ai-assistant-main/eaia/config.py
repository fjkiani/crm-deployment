"""
config.py — Runtime configuration for Nyx Orchestration System
Loaded from environment + Frappe Settings DocType (via API or manual override).
This eliminates hardcoded brittleness points across the backend.
"""
import os

class NyxConfig:
    # ── Connections ────────────────────────────────────────────────────────────
    EAIA_URL = os.getenv("EAIA_URL", "http://127.0.0.1:8787")
    FRAPPE_URL = os.getenv("FRAPPE_SITE_URL", "http://localhost:8000")
    
    # ── ICP Identity (configurable per client/tenant) ─────────────────────────
    # Change these to rebrand the entire pipeline for a different company.
    COMPANY_NAME = os.getenv("NYX_COMPANY_NAME", "Zeta")
    COMPANY_DESCRIPTION = os.getenv(
        "NYX_COMPANY_DESCRIPTION",
        "a genomic data analytics platform"
    )
    VALUE_PROP = os.getenv(
        "NYX_VALUE_PROP",
        "Proprietary genomic datasets that quantify biological drug response signals"
    )
    DATA_TYPE = os.getenv("NYX_DATA_TYPE", "genomic data")
    DATA_GAP_LABEL = os.getenv("NYX_DATA_GAP_LABEL", "biomarker data gap")
    INDUSTRY = os.getenv("NYX_INDUSTRY", "life sciences")

    # ── Sandbox Mode ──────────────────────────────────────────────────────────
    # When SANDBOX_MODE=true, ALL outbound emails redirect to SANDBOX_EMAIL.
    # Original recipient is logged but never contacted. Keeps dev safe.
    SANDBOX_MODE = os.getenv("NYX_SANDBOX_MODE", "true").lower() == "true"
    SANDBOX_EMAIL = os.getenv("NYX_SANDBOX_EMAIL", "fjkiani1@gmail.com")

    # ── A/B Testing ───────────────────────────────────────────────────────────
    AB_ENABLED = os.getenv("NYX_AB_ENABLED", "true").lower() == "true"
    AB_MIN_SAMPLE = int(os.getenv("NYX_AB_MIN_SAMPLE", "20"))  # min sends before declaring winner

    # ── LLM Fallback Chain ────────────────────────────────────────────────────
    LLM_FALLBACK_ORDER = os.getenv("NYX_LLM_FALLBACK", "cohere,openai,anthropic").split(",")
    LLM_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("NYX_LLM_CIRCUIT_BREAKER", "3"))

    # ── Domain Pool ───────────────────────────────────────────────────────────
    SEND_DOMAINS = os.getenv("NYX_SEND_DOMAINS", "").split(",") if os.getenv("NYX_SEND_DOMAINS") else []
    DOMAIN_DAILY_MAX = int(os.getenv("NYX_DOMAIN_DAILY_MAX", "50"))

    # ── LinkedIn Outreach ─────────────────────────────────────────────────────
    LINKEDIN_DAILY_CONNECTION_LIMIT = int(os.getenv("NYX_LINKEDIN_CONN_LIMIT", "20"))
    LINKEDIN_DAILY_DM_LIMIT = int(os.getenv("NYX_LINKEDIN_DM_LIMIT", "50"))

    # ── Pipeline Audit ────────────────────────────────────────────────────────
    AUDIT_TRAIL_ENABLED = os.getenv("NYX_AUDIT_TRAIL", "true").lower() == "true"

    # ── Thresholds ─────────────────────────────────────────────────────────────
    SCORE_HOT = int(os.getenv("NYX_SCORE_HOT", "70"))
    SCORE_WARM = int(os.getenv("NYX_SCORE_WARM", "40"))
    SIGNAL_GATE_MIN = int(os.getenv("NYX_SIGNAL_GATE_MIN", "2"))
    
    # ── Registry ───────────────────────────────────────────────────────────────
    FRAMEWORKS = ["challenger", "pas", "aida"]
    DEFAULT_FRAMEWORK = "challenger"
    
    # ── Sequences ──────────────────────────────────────────────────────────────
    DEFAULT_SEQUENCE = [
        {"day": 0,  "framework": "challenger", "action": "send",    "label": "Day 0 — Initial Strike"},
        {"day": 3,  "framework": "challenger", "action": "send_ab", "label": "Day 3 — A/B Subject Pivot"},
        {"day": 7,  "framework": "pas",        "action": "send",    "label": "Day 7 — Framework Switch (PAS)"},
        {"day": 14, "framework": "aida",       "action": "send",    "label": "Day 14 — Framework Switch (AIDA)"},
        {"day": 21, "framework": "breakup",    "action": "send",    "label": "Day 21 — Breakup"},
    ]

    @classmethod
    def breakup_template(cls):
        """Generate breakup template using ICP config."""
        return {
            "subject": "Closing your file",
            "body": (
                "{first_name},\n\n"
                f"I've reached out a few times about {{company}}'s {cls.DATA_GAP_LABEL}. "
                "No response usually means it's not a priority right now — totally understood.\n\n"
                "I'm closing your file today. If the thesis changes, reach back whenever.\n\n"
                "— Nyx"
            ),
            "ps": f"If someone else on your team owns alt-data sourcing, happy to loop them in instead.",
        }

    # Legacy alias for backward compatibility
    BREAKUP_TEMPLATE = {
        "subject": "Closing your file",
        "body": (
            "{first_name},\n\n"
            "I've reached out a few times about {company}'s data gap. "
            "No response usually means it's not a priority right now — totally understood.\n\n"
            "I'm closing your file today. If the thesis changes, reach back whenever.\n\n"
            "— Nyx"
        ),
        "ps": "If someone else on your team owns alt-data sourcing, happy to loop them in instead.",
    }

