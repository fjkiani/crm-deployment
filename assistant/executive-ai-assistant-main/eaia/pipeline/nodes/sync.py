"""
pipeline/nodes/sync.py — Node 6: CRM Write-Back.

Pipeline position: LAST. Writes everything to Frappe.
Purpose: Persist enrichment, score, signals, and email draft to CRM Lead + FCRM Note.

What gets written:
  CRM Lead:   lead_name, email, org, title, phone
  FCRM Note:  Full intelligence dossier (score, tier, why_hot, enrichment,
               signals, email draft, quarantine status, A/B subjects)
  Raw JSON:   Second note with machine-readable JSON for Cockpit parsing

The FCRM Note is the source of truth for /fire-sequence.
It reads state["signal_gate"], state["score_why"], enrichment dict from this note.

To improve this node:
  - Write to CRM in parallel (Lead + Note simultaneously)
  - Add a "pipeline_run_id" field to track which run produced this record
  - Add "enrichment_sources_used" list for debugging (which sources returned data)
  - Instead of a second raw JSON note, use a custom Frappe doctype ("Nyx Intel")
    This allows structured querying in the Cockpit (no regex parsing needed)
  - Add webhook trigger after sync: notify Slack/Teams channel with new HOT leads
  - Write A/B subjects to a separate "Email Variants" child table on the Lead
"""
import json
import logging
from langchain_core.runnables.config import RunnableConfig

from eaia.pipeline.state import OutreachState
from eaia.agents.zo import CRMClient
from eaia.skills.context_manager import ContextManager
from eaia.config import NyxConfig

logger = logging.getLogger(__name__)


def _build_intel_data(state: OutreachState) -> dict:
    """
    Build the structured intel dict stored in FCRM Note as NYX_INTEL_JSON.
    This is read by /fire-sequence to re-use enrichment data.

    To improve:
      - Add "pipeline_run_id" for auditability
      - Add "enrichment_sources_attempted" list
      - Add "enrichment_latency_ms" per source
    """
    signals     = state.get("distilled_signals", {})
    enrichment  = state.get("enrichment", {})
    apollo      = state.get("apollo_data", {})
    email_draft = state.get("email_draft", {})
    email       = email_draft.get("email", {})
    score       = state.get("score", 0)
    tier        = "Tier 1" if score > 75 else "Tier 2" if score > 40 else "Tier 3"

    return {
        "score":          score,
        "tier":           tier,
        "signal_gate":    state.get("signal_gate", "unknown"),
        "framework":      state.get("framework", NyxConfig.DEFAULT_FRAMEWORK),
        "score_reasoning":state.get("score_reasoning", ""),
        "score_angle":    state.get("score_angle", ""),
        "score_why":      state.get("score_why", ""),
        "signals": {
            "specific_number":  signals.get("specific_number"),
            "recent_event":     signals.get("recent_event"),
            "strategic_detail": signals.get("strategic_detail"),
            "blind_spot":       signals.get("blind_spot"),
            "competitor_name":  signals.get("competitor_name"),
        },
        "enrichment": {
            "email":                    enrichment.get("apollo_email") or apollo.get("email"),
            "phone":                    apollo.get("phone"),
            "linkedin_url":             enrichment.get("apollo_linkedin_url") or apollo.get("linkedin_url"),
            "title":                    enrichment.get("apollo_title") or apollo.get("title"),
            "headline":                 enrichment.get("linkedin_profile_headline") or apollo.get("headline"),
            "aum_signal":               enrichment.get("aum_signal"),
            "company_strategy":         enrichment.get("company_strategy"),
            "competitor_pressure":      enrichment.get("competitor_pressure"),
            "linkedin_recent_activity": enrichment.get("linkedin_recent_activity", []),
        },
        "email_draft": {
            "subject":     email.get("subject"),
            "body":        email.get("body"),
            "ps":          email.get("ps"),
            "quarantined": email_draft.get("quarantined", False),
        },
        "ab_subjects":   state.get("ab_subjects", []),
        "sequence_step": 0,
    }


def _build_note_content(state: OutreachState, intel: dict) -> str:
    """
    Build the human-readable Frappe Note content (shown in the Notes tab).
    Markdown formatted. Includes everything a sales rep needs to act.
    """
    score       = intel["score"]
    tier        = intel["tier"]
    signals     = intel["signals"]
    enrichment  = intel["enrichment"]
    email_draft = intel["email_draft"]
    signal_gate = intel["signal_gate"]
    quarantined = email_draft.get("quarantined", False)

    gate_badge       = "✅ GATE PASSED" if "pass" in signal_gate else "⛔ QUARANTINED"
    quarantine_reason = state.get("email_draft", {}).get("reason", "") if quarantined else ""

    return f"""## 🎯 Kill Score: {score}/100 | {tier} | {intel.get('framework', 'CHALLENGER').upper()}

**Signal Gate:** {gate_badge}
{f"**Quarantine Reason:** {quarantine_reason}" if quarantined else ""}

---

### WHY THIS LEAD IS {tier.upper()}
{intel.get('score_why') or f"Score: {score}/100 — {intel.get('score_reasoning', '')[:500]}"}

**Sales Angle:** {intel.get('score_angle', 'N/A')}

---

### ENRICHMENT SOURCES
- **Title:** {enrichment.get('title') or 'N/A'}
- **Headline:** {enrichment.get('headline') or 'N/A'}
- **AUM Signal:** {enrichment.get('aum_signal') or 'N/A — 13F not found'}
- **Company Strategy:** {(enrichment.get('company_strategy') or 'N/A')[:300]}
- **Competitor Pressure:** {(enrichment.get('competitor_pressure') or 'N/A')[:200]}
- **LinkedIn Recent Activity:** {' | '.join(enrichment.get('linkedin_recent_activity', [])[:2]) or 'None found'}

---

### DISTILLED SIGNALS
- **Specific Number:** {signals.get('specific_number', 'UNKNOWN')}
- **Recent Event:** {signals.get('recent_event', 'UNKNOWN')}
- **Strategic Detail:** {signals.get('strategic_detail', 'UNKNOWN')}
- **Blind Spot:** {signals.get('blind_spot', 'UNKNOWN')}
- **Competitor Named:** {signals.get('competitor_name', 'UNKNOWN')}

---

### EMAIL DRAFT {'(QUARANTINED — NOT SENT)' if quarantined else ''}
**Subject:** {email_draft.get('subject', 'N/A')}

{email_draft.get('body', 'No draft generated.') if not quarantined else 'Email not drafted — insufficient signals.'}

{'**PS:** ' + email_draft.get('ps', '') if email_draft.get('ps') and not quarantined else ''}

**A/B Subjects:** {' / '.join(intel.get('ab_subjects', [])) or 'N/A'}
"""


async def sync_node(state: OutreachState, config: RunnableConfig) -> OutreachState:
    """
    Node 6 — Write pipeline results to Frappe CRM.

    Writes:
      1. CRM Lead (upsert by email)
      2. FCRM Note with full intelligence dossier (markdown + embedded NYX_INTEL_JSON)
      3. Raw JSON note for Cockpit machine-parsing

    Input:  All state fields
    Output: state["crm_synced"], state["crm_prospect_id"]
    """
    cb = config.get("configurable", {}).get("callback")
    logger.info("💾 SYNC: Writing to Frappe CRM")

    if cb:
        await cb("sync", "thought", {"message": "Syncing lead + dossier to CRM..."})

    try:
        client = CRMClient()
        apollo = state.get("apollo_data", {})
        score  = state.get("score", 0)
        tier   = "Tier 1" if score > 75 else "Tier 2" if score > 40 else "Tier 3"

        # ── 1. Upsert CRM Lead ─────────────────────────────────────────────
        name_parts = (state["prospect_name"] or "").split()
        lead_data  = {
            "lead_name":   state["prospect_name"],
            "first_name":  name_parts[0] if name_parts else "",
            "last_name":   " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            "email":       apollo.get("email") or state.get("enrichment", {}).get("apollo_email", ""),
            "organization":state["company_name"],
            "mobile_no":   apollo.get("phone", ""),
            "job_title":   apollo.get("title", "")
                           or state.get("enrichment", {}).get("apollo_title", ""),
        }
        lead_data = {k: v for k, v in lead_data.items() if v}

        lead_id = client.upsert_lead(lead_data)
        state["crm_synced"]       = bool(lead_id)
        state["crm_prospect_id"]  = lead_id or ""
        logger.info(f"💾 SYNC: {'✅' if lead_id else '❌'} — {lead_id}")

        if not lead_id:
            return state

        # ── 2. Build and write intelligence dossier note ───────────────────
        intel_data   = _build_intel_data(state)
        note_content = _build_note_content(state, intel_data)

        client.create_note(
            lead_name  = lead_id,
            title      = f"Nyx Intel — {state['prospect_name']} [{tier}, Score {score}]",
            content    = note_content,
            intel_data = intel_data,
        )

        # ── 3. Raw JSON note for Cockpit parsing ────────────────────────────
        try:
            enrichment_json = json.dumps(intel_data, indent=2)
            client.create_note(
                lead_id,
                "📊 Raw Enrichment Data",
                f"```json\n{enrichment_json}\n```"
            )
        except Exception:
            pass  # non-fatal

        if cb:
            await cb("sync", "result", {
                "message": f"Synced to CRM: {lead_id} | Score: {score} | Tier: {tier}"
            })

    except Exception as e:
        logger.error(f"Sync node error: {e}")
        state["crm_synced"]      = False
        state["crm_prospect_id"] = ""
        state["error"]           = str(e)

    return state
