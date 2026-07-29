# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt
"""
crm/api/plan_generator.py — On-the-fly engagement-card generation.

PROBLEM THIS SOLVES
-------------------
The 10 curated pharma engagements (Inhibrx, Agenus, ...) are HARD-CODED in
`crm/industry_data/engagements.json`. Their rich detail cards (snapshot + fit
table + Option A/B outreach steps + governance) are hand-authored. There is no
path to produce that same card for a company or lead that is NOT one of the 10.

This module builds `generate_plan(subject_type, subject_key)` which assembles a
card in the EXACT SAME SHAPE as an engagements.json entry, but sourced
dynamically from live data:

    live enrich signals  (crm.api.enrichment_api)
  ⊕ AACR Intel narrative (crm.api.intel_bridge: synthesize_narrative + compute_score)
  ⊕ matched KOL deep block (kol_targets_v2, when the lead matches a KOL)
  ⊕ ordered outreach steps (crm.api.nyx_agent._default_plan)

Because the emitted card has the same 7-key shape (slug / front_matter /
snapshot / fit / contacts / message_options / governance), it feeds UNCHANGED
into the existing seeder `crm.api.industry._seed_one`, which materializes:
Email Templates + Outreach Sequence + Lead Prospect + Instance + CRM Tasks +
inbox drafts. So `generate_and_seed_plan` fixes the "empty task descriptions /
No templates found" symptoms as a by-product — those were a SEED GAP (the
seeder was never run live), not a logic bug.

SAFETY / HONESTY
----------------
- No LLM fabrication. Every field is derived from a real source or left as a
  neutral, clearly-labeled default. Governance `safe_to_say` is built only from
  enrichment signals that carry a source; `not_safe_to_say` always carries the
  standing CrisPRO "no model has been run on their data" guardrail.
- Nothing transmits. Seeding produces Draft sequences + Todo tasks + Inbox
  drafts only, exactly like the curated seed path (human-gated).
- Deterministic and idempotent: same inputs -> same card; re-seeding upserts.
"""

from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, List, Optional

import frappe
from frappe import _


logger = logging.getLogger(__name__)
# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #
# The 4 CrisPRO fit dimensions, mirrored from enrichment_api._FIT_DIMS so the
# generated score_table uses the SAME vocabulary as the curated cards + the live
# _map_fit() corroboration output.
_FIT_DIMENSIONS = [
    ("BG", "Biomarker Gap (BG)"),
    ("CN", "Comparator Need (CN)"),
    ("PC", "Population Complexity (PC)"),
    ("TI", "Translational Interpretability (TI)"),
]

# Standing governance guardrails that apply to EVERY CrisPRO outreach, curated
# or generated. These mirror the recurring not_safe_to_say entries across the 10
# hand-authored engagements (no model has been run; no efficacy claims; etc.).
_STANDING_NOT_SAFE = [
    {"claim": "CrisPRO has run a model / simulation on this company's or lead's dataset",
     "reason": "No model has been run — this would be a false claim."},
    {"claim": "CrisPRO can predict clinical response / ORR / PFS for their asset",
     "reason": "CrisPRO stratifies and simulates trial design; it does not promise clinical outcomes."},
    {"claim": "Any statement implying a partnership, data access, or prior collaboration exists",
     "reason": "No agreement or data exchange is in place — implying one is misleading."},
]

_STANDING_CONSTRAINTS = [
    "LinkedIn-first: most contacts have no verified public email; do not send cold email to an unverified address.",
    "Scientific-positioning tone only; no sales/marketing framing.",
    "Every efficacy or trial figure cited must carry its public source (trial ID / abstract / publication).",
    "This card is machine-assembled from public + internal intel; a human reviews before any send.",
]


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "target"


def _clip(text: str, n: int = 240) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _safe_json_loads(raw, default):
    try:
        v = json.loads(raw) if raw else default
        return v if v is not None else default
    except Exception:
        logger.debug("plan_generator._safe_json_loads: bad JSON, using default", exc_info=True)
        return default


def _first_nonempty(*vals) -> str:
    for v in vals:
        if v and str(v).strip():
            return str(v).strip()
    return ""


# Neutral placeholder for a generated card whose indication cannot be reliably
# derived. The 10 curated engagements are all MSS CRC; a generated lead may be
# ANY indication (ovarian, Ewing sarcoma, myeloma, ...), and the AACR/KOL data
# carries the indication only as free text (talk titles, opportunity descriptions),
# not a clean field. Rather than mislabel a non-CRC lead as "Colorectal Cancer"
# (the seeder's legacy default) OR guess an indication from free text, we emit an
# explicit "Unspecified" sentinel that _seed_one honors verbatim.
_UNSPECIFIED_INDICATION = "Unspecified (auto-generated — verify indication)"


def _lead_indication(lead) -> str:
    """Best-effort, HONEST indication for a generated lead's front_matter.cancer_type.
    Uses a real stored indication field if the CRM Lead carries one; otherwise
    returns the neutral sentinel. Never assumes colorectal for a generated lead."""
    for field in ("cancer_type", "indication", "disease", "primary_indication"):
        val = getattr(lead, field, None)
        if val and str(val).strip():
            return str(val).strip()
    return _UNSPECIFIED_INDICATION


# --------------------------------------------------------------------------- #
# KOL match lookup (kol_targets_v2, ingested in Phase 2)
# --------------------------------------------------------------------------- #
def _norm_name(name: str) -> str:
    """Mirror of intel_bridge/ingest name normalization: strip credentials +
    honorifics, lowercase, keep [a-z0-9 ], collapse whitespace."""
    n = (name or "").lower()
    n = re.sub(r"\b(dr|prof|md|phd|mba|do|msc|ms|pharmd|jr|sr|ii|iii)\b\.?", " ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _kol_deep_for_lead(lead_name_display: str, lead_id: str) -> Optional[dict]:
    """Return the kol_targets_v2 deep GTM block for a lead if one was matched in
    Phase 2. Reads additional_data.nyx_kol on the live lead (written by the
    apply_kol_gtm ingest); falls back to matching by normalized name against the
    KOL manifest bundled with the app (if present)."""
    # 1) live: the ingest writes the deep block under additional_data.nyx_kol
    if lead_id and frappe.db.exists("CRM Lead", lead_id):
        ad = _safe_json_loads(frappe.db.get_value("CRM Lead", lead_id, "additional_data"), {})
        nyx_kol = (ad.get("nyx_gtm", {}) or {}).get("nyx_kol") or ad.get("nyx_kol")
        if nyx_kol:
            return nyx_kol
    return None


# --------------------------------------------------------------------------- #
# fit-table assembly (shared by company + lead paths)
# --------------------------------------------------------------------------- #
# Map AACR-Intel / KOL opportunity_type vocabulary onto the 4 CrisPRO fit
# dimensions, so a real Schema-B gap raises the RIGHT dimension's score (not just
# live-enrich corroboration). Keys are substrings matched against opportunity_type.
_OPP_TO_DIM = {
    "biomarker": "BG", "stratif": "BG", "signature": "BG", "enrich": "BG",
    "comparator": "CN", "control": "CN", "benchmark": "CN", "combination": "CN",
    "population": "PC", "co-mutation": "PC", "resistance": "PC", "subgroup": "PC",
    "interpret": "TI", "validation": "TI", "prospective": "TI", "endpoint": "TI",
    "mechanis": "TI",
}


def _opp_types(gtm: dict | None, kol: dict | None) -> Dict[str, str]:
    """Collect opportunity_type strings from AACR-Intel narrative + KOL block and
    map each to a fit-dimension code -> the concrete opportunity text (evidence)."""
    hits: Dict[str, str] = {}
    pools = []
    if kol and kol.get("crispro_opportunities"):
        pools += [(o.get("opportunity_type", ""), o.get("description", "") or o.get("crispro_angle", ""))
                  for o in kol["crispro_opportunities"]]
    # narrative carries opportunity descriptions in crispro_fit lines; also inspect
    # current_focus / pain_points as a coarse type hint
    if gtm:
        pools.append(((gtm.get("current_focus") or ""), (gtm.get("current_focus") or "")))
        pools.append(((gtm.get("pain_points") or ""), (gtm.get("pain_points") or "")))
    for otype, evidence in pools:
        low = (otype or "").lower()
        for kw, code in _OPP_TO_DIM.items():
            if kw in low and code not in hits:
                hits[code] = _clip(evidence or otype, 160)
    return hits


def _score_table_from_signals(fit_dimensions: dict, gtm: dict | None,
                              kol: dict | None) -> List[dict]:
    """Build the score_table in engagements.json shape:
    [{dimension, score, rationale}, ...]. Score (qualitative 1-5) reflects BOTH
    (a) live-enrichment corroboration of a dimension AND (b) a real AACR-Intel/KOL
    opportunity mapped to that dimension. This is NOT the governance-locked
    production ranker — it is a presentation-layer heuristic, same spirit as the
    curated cards (which score each dimension from the actual gap)."""
    table = []
    corr = fit_dimensions or {}
    opp_hits = _opp_types(gtm, kol)
    for code, label in _FIT_DIMENSIONS:
        dim = corr.get(code, {})
        live = bool(dim.get("live_evidence"))
        matched = dim.get("matched") or []
        opp_ev = opp_hits.get(code)
        if live and opp_ev:
            score = "5"
            rationale = f"Live intel + AACR gap both hit {label}: {opp_ev} (live: {matched})."
        elif opp_ev:
            score = "4"
            rationale = f"AACR/KOL gap maps to {label}: {opp_ev}."
        elif live:
            score = "4"
            rationale = f"Live intel corroborates {label}: matched signals {matched}."
        else:
            score, why = _signal_floor(kol, _n_signals_hint(corr))
            rationale = why.replace("this dimension", label)
        table.append({"dimension": label, "score": score, "rationale": rationale})
    return table


def _n_signals_hint(corr: dict) -> int:
    """How many dimensions carry live evidence — a cheap proxy for overall signal depth."""
    try:
        return sum(1 for d in (corr or {}).values()
                   if isinstance(d, dict) and d.get("live_evidence"))
    except Exception:
        logger.debug("plan_generator._n_signals_hint failed", exc_info=True)
        return 0


def _composite(score_table: List[dict], kol: dict | None) -> str:
    vals = []
    for r in score_table:
        try:
            vals.append(float(r.get("score", 0)))
        except (TypeError, ValueError):
            logger.warning("plan_generator._composite: non-numeric score %r in dimension %r",
                           r.get("score"), r.get("dimension"))
    base = round(sum(vals) / len(vals), 2) if vals else 0.0
    # if a KOL fit_score exists, blend it onto the 1-5 scale (fit_score is 0-1)
    if kol and isinstance(kol.get("fit_score"), (int, float)):
        base = round((base + kol["fit_score"] * 5.0) / 2.0, 2)
    return f"{base:.2f}"


# --------------------------------------------------------------------------- #
# KOL field access — tolerant of BOTH shapes actually observed in the data
#   * live CRM path (additional_data.nyx_kol): native list / dict values
#   * offline fixture (kol_targets_v2.json):   values stringified AND hard-clipped
#     at exactly 200 chars, so most are unparseable mid-literal.
# A truncated fragment must never be emitted as a citable claim, so the string
# branch keeps only fully-closed items and reports that it dropped a fragment.
# --------------------------------------------------------------------------- #
def _kol_list(kol: dict | None, key: str) -> tuple[list, bool]:
    """-> (items, truncated). Never raises."""
    raw = (kol or {}).get(key)
    if raw in (None, "", [], {}):
        return [], False
    if isinstance(raw, (list, tuple)):
        return list(raw), False
    if isinstance(raw, dict):
        return [raw], False
    text = str(raw).strip()
    if text in ("[]", "{}"):
        return [], False
    # JSON first (correct, complete payloads)
    try:
        val = json.loads(text)
        return (list(val) if isinstance(val, (list, tuple)) else [val]), False
    except Exception:
        pass
    # Python-repr-ish and very likely clipped: salvage only complete quoted items.
    items = re.findall(r"'((?:[^'\\]|\\.)*)'", text)
    items += re.findall(r'"((?:[^"\\]|\\.)*)"', text)
    items = [i.strip() for i in items if len(i.strip()) > 15]
    truncated = not text.rstrip().endswith(("]", "}"))
    if not items:
        logger.debug("plan_generator._kol_list: %s unparseable and unsalvageable", key)
    return items, truncated


def _kol_truncation_flags(kol: dict | None) -> dict:
    flags = (kol or {}).get("data_flags")
    return flags if isinstance(flags, dict) else {}


def _kol_institution(kol: dict | None, fallback: str) -> tuple[str, str]:
    """-> (institution, provenance). The ingest currently drops institution from the
    nyx_kol block (it lives one level up under _match), so both are probed before
    falling back to the CRM organization. Provenance is recorded, not guessed."""
    k = kol or {}
    for src_key, prov in (("institution", "kol.institution"),
                          ("affiliation", "kol.affiliation")):
        v = _first_nonempty(k.get(src_key))
        if v and v != "—":
            return v, prov
    match = k.get("_match")
    if isinstance(match, dict):
        v = _first_nonempty(match.get("institution"))
        if v and v != "—":
            return v, "kol._match.institution"
    return fallback, "crm.lead.organization"


def _resolve_sender() -> str:
    """Outreach sender: configured default -> session user's full name -> honest label.
    Replaces the hardcoded personal name that was baked into every generated step."""
    try:
        from crm.api.nyx_email_brain import _get_conf
        v = _first_nonempty(_get_conf("outreach_sender_name", "crispro_sender_name", default=""))
        if v:
            return v
    except Exception:
        logger.debug("plan_generator._resolve_sender: settings lookup failed", exc_info=True)
    try:
        user = getattr(frappe.session, "user", None)
        if user and user not in ("Guest", "Administrator"):
            full = frappe.db.get_value("User", user, "full_name")
            if full:
                return full
    except Exception:
        logger.debug("plan_generator._resolve_sender: user lookup failed", exc_info=True)
    return "CrisPRO / Brenus Pharma"


def _kol_evidence(kol: dict | None) -> List[dict]:
    """KOL AACR findings as SOURCED evidence records. Source is the real AACR talk id
    when carried; a finding with no resolvable source is dropped, not guessed."""
    if not kol:
        return []
    flags = _kol_truncation_flags(kol)
    out = []
    findings, salvage_trunc = _kol_list(kol, "schema_a_key_findings")
    talk_id = _first_nonempty(kol.get("schema_a_talk_id"))
    title = _first_nonempty(kol.get("schema_a_title"))
    source = talk_id or title
    if findings and source:
        clipped = bool(flags.get("key_findings_truncated")) or salvage_trunc
        for f in findings[:3]:
            if not isinstance(f, str) or len(f.strip()) < 16:
                continue
            out.append({
                "text": f.strip(),
                "source": f"AACR 2026 talk {source}" + (f" — {title}" if title and talk_id else ""),
                "kind": "aacr_key_finding",
                "truncated_upstream": clipped,
            })
    vulns, v_trunc = _kol_list(kol, "schema_b_vulnerability")
    v_source = _first_nonempty(kol.get("schema_b_talk_id"))
    for v in vulns[:2]:
        text = v.get("mechanistic_blindspot") if isinstance(v, dict) else (v if isinstance(v, str) else "")
        target = v.get("failing_compound_or_target") if isinstance(v, dict) else ""
        if not text or len(str(text).strip()) < 16:
            continue
        if not v_source:
            continue  # unsourced vulnerability is not citable
        out.append({
            "text": (f"{target}: {text}" if target else str(text)).strip(),
            "source": f"AACR 2026 talk {v_source}",
            "kind": "aacr_vulnerability",
            "truncated_upstream": bool(flags.get("vulnerability_truncated")) or v_trunc,
        })
    return out


def _signal_floor(kol: dict | None, n_signals: int) -> tuple[str, str]:
    """Derive the no-direct-signal dimension score from real corpus statistics instead
    of the flat literal '2'. axis_stats is present on 20/20 live KOL blocks.

    total_records / high_fit_count / gap_score describe how much evidence exists on the
    KOL's primary axis, so a KOL sitting on a wide, well-populated gap floors higher than
    a lead with nothing behind it. Bounded to 1..3 so a floor can never masquerade as a
    corroborated signal (4-5 stay reserved for live/opportunity hits).
    """
    stats = (kol or {}).get("axis_stats")
    if not isinstance(stats, dict):
        if n_signals:
            return "2", f"No direct signal for this dimension; {n_signals} live signal(s) on the lead overall."
        return "1", "No signal for this dimension and no live intel yet (floor, not evidence)."
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    total = _num(stats.get("total_records"))
    high = _num(stats.get("high_fit_count"))
    gap = _num(stats.get("gap_score"))
    mean_fit = _num(stats.get("mean_fit"))
    pts = 0
    if total >= 5:
        pts += 1
    if high >= 2:
        pts += 1
    if gap >= 5.0:
        pts += 1
    if mean_fit >= 0.30:
        pts += 1
    score = str(max(1, min(3, 1 + pts // 2)))
    return score, (
        f"No direct signal for this dimension; floor derived from axis corpus "
        f"(records={int(total)}, high-fit={int(high)}, gap={gap:g}, mean-fit={mean_fit:g})."
    )


def _trial_phase_from_sources(intel, narrative: dict, signals: List[dict]) -> tuple[str, str]:
    """Best-effort trial id + phase from linked intel / live signals. Honest em-dash when
    nothing real is available — never a plausible-looking guess."""
    trial, phase = "", ""
    for cand in (narrative.get("trial"), narrative.get("lead_trial"),
                 getattr(intel, "trial", None) if intel else None):
        v = _first_nonempty(cand)
        if v and v != "—":
            trial = v
            break
    for cand in (narrative.get("phase"), getattr(intel, "phase", None) if intel else None):
        v = _first_nonempty(cand)
        if v and v != "—":
            phase = v
            break
    if not trial:
        for s in signals or []:
            m = re.search(r"\bNCT\d{6,}\b", f"{s.get('text','')} {s.get('source','')}")
            if m:
                trial = m.group(0)
                break
    if not phase:
        for s in signals or []:
            m = re.search(r"\bPhase\s*(?:I{1,3}|IV|[1-4])\b", str(s.get("text", "")), re.I)
            if m:
                phase = m.group(0)
                break
    return (trial or "—"), (phase or "—")


# --------------------------------------------------------------------------- #
# governance assembly
# --------------------------------------------------------------------------- #
def _safe_to_say_from_signals(signals: List[dict]) -> List[dict]:
    """Only signals that carry a source become safe-to-say claims (VERIFIED-PUBLIC),
    matching the curated cards' evidence discipline. Signals with no source are
    dropped from safe_to_say (they may still inform the snapshot)."""
    out = []
    for s in signals or []:
        text = _first_nonempty(s.get("text"))
        src = _first_nonempty(s.get("source"))
        if text and src:
            note = f"Auto-extracted {s.get('kind','signal')} — verify wording before citing."
            if s.get("truncated_upstream"):
                # Upstream clipped this field; the salvaged text is complete but the
                # finding list is not, so the claim must not be presented as exhaustive.
                note += (" Upstream source field was truncated: this is a complete salvaged "
                         "statement, but the finding list may be incomplete.")
            out.append({
                "claim": _clip(text, 300),
                "source": _clip(src, 200),
                "evidence_status": "VERIFIED-PUBLIC",
                "notes": note,
            })
    return out


# --------------------------------------------------------------------------- #
# message-step assembly (reuse nyx_agent ordering, render bodies from intel)
# --------------------------------------------------------------------------- #
def _steps_from_plan(subject_type: str, subject_key: str, ctx: dict,
                     hook: str, angle: str, company: str, contact: str,
                     evidence: List[dict] | None = None,
                     subject_hint: str = "", kol: dict | None = None) -> dict:
    """Produce message_options {option_a, option_b, which_option} in the curated shape.

    Bodies now go through nyx_email_brain.draft_outreach_body(), which drafts prose with
    the configured LLM and REJECTS any output introducing a number, NCT id or drug name
    that is not present verbatim in `evidence`. On rejection, on LLM absence, or on any
    failure it returns a deterministic body and says so in `method`. Claims and scores are
    never LLM-generated (governance decision), only the prose is.
    """
    hook = hook or ""
    angle = angle or ("CrisPRO's in-silico trial-simulation and patient-stratification "
                      "platform for biomarker-defined subgroups")
    evidence = evidence or []
    sender = _resolve_sender()
    open_qs = [q for q in (_kol_list(kol, "open_questions")[0] if kol else []) if isinstance(q, str)]

    base_ctx = {
        "display_name": contact or "",
        "company": company or "",
        "institution": ctx.get("institution") or "",
        "aacr_topic": ctx.get("aacr_topic") or "",
        "hook": hook,
        "crispro_angle": angle,
        "open_questions": open_qs,
        "sender": sender,
    }

    def _draft(step_number: int, hint: str) -> dict:
        try:
            from crm.api.nyx_email_brain import draft_outreach_body
            c = dict(base_ctx)
            c["step_number"] = step_number
            return draft_outreach_body(c, evidence, subject_hint=hint) or {}
        except Exception:
            # The seam is contracted never to raise; if the import itself fails we still
            # must produce a card, so fall back locally and label it.
            logger.warning("plan_generator: draft_outreach_body unavailable; using local fallback",
                           exc_info=True)
            return {}

    opener_ref = "your AACR 2026 work" if ctx.get("aacr_topic") else "your recent work"
    hook_line = (f"Your finding — {_clip(hook, 220)} — is exactly the kind of "
                 f"biomarker/subgroup gap CrisPRO is built to address."
                 if hook else
                 f"{opener_ref.capitalize()} raises a subgroup/stratification question "
                 f"CrisPRO is built to address.")
    q_line = (f"\n\nOne question your talk left open: {_clip(open_qs[0], 200)}"
              if open_qs else "")

    local_warm = (
        f"Hi {contact or 'there'},\n\n{hook_line}{q_line}\n\n"
        f"CrisPRO ({angle}) could help pressure-test the responder-enrichment "
        f"hypothesis in silico before the next trial iteration. Would a 20-minute "
        f"scientific exchange be useful?\n\n— {sender}"
    )
    local_direct = (
        f"Hi {contact or 'there'},\n\nReaching out on {opener_ref} at "
        f"{ctx.get('institution') or company or 'your group'}. {hook_line}{q_line}\n\n"
        f"No ask beyond a short scientific conversation — happy to share how CrisPRO "
        f"frames the stratification problem. Open to a brief call?\n\n— {sender}"
    )

    d1 = _draft(1, subject_hint)
    d2 = _draft(2, subject_hint)
    d1b = _draft(1, subject_hint)

    def _body(d, fallback):
        html = (d or {}).get("html")
        return html if html else fallback

    def _meta(d, fallback_label):
        return {
            "draft_method": (d or {}).get("method", fallback_label),
            "claim_guard": (d or {}).get("guard", {"ok": True, "violations": []}),
            "subject": (d or {}).get("subject", subject_hint or ""),
        }

    option_a = {"steps": [
        {"step_number": 1, "sender": sender, "delay_days": 0,
         "channel_note": "LinkedIn connection + note (warm, if any shared context)",
         "body": _body(d1, local_warm), **_meta(d1, "deterministic:local")},
        {"step_number": 2, "sender": sender, "delay_days": 4,
         "channel_note": "LinkedIn follow-up if no reply",
         "body": _body(d2, (f"Following up briefly — the CrisPRO angle above is specific to "
                            f"{_clip(ctx.get('aacr_topic') or company or 'your program', 120)}. "
                            f"Glad to send a one-pager if easier than a call.\n\n— {sender}")),
         **_meta(d2, "deterministic:local")},
    ]}
    option_b = {"steps": [
        {"step_number": 1, "sender": sender, "delay_days": 0,
         "channel_note": "Direct LinkedIn message (no prior connection)",
         "body": _body(d1b, local_direct), **_meta(d1b, "deterministic:local")},
    ]}
    which_option = [
        {"scenario": "There is a warm intro or shared context (co-author, institution, prior contact)",
         "recommended_option": "Option A — a warm connection note lands better"},
        {"scenario": "No shared context; cold outreach to a KOL/exec",
         "recommended_option": "Option B — a single, specific direct message"},
    ]
    return {"option_a": option_a, "option_b": option_b, "which_option": which_option}


# --------------------------------------------------------------------------- #
# CORE: build a card dict in engagements.json shape
# --------------------------------------------------------------------------- #
def _build_card_for_lead(lead_id: str, enrich: dict, use_enrich: bool) -> dict:
    lead = frappe.get_doc("CRM Lead", lead_id)
    display_name = _first_nonempty(lead.lead_name, lead_id)
    company = _first_nonempty(lead.organization, "—")
    srid = getattr(lead, "source_ref_id", "") or ""

    # (a) AACR Intel GTM narrative (deterministic) if the lead links to intel
    from crm.api.intel_bridge import synthesize_narrative, compute_score
    try:
        from crm.fcrm.doctype.aacr_intel.aacr_intel import get_aacr_intel
        intel = get_aacr_intel(srid) if srid else None
    except Exception:
        # A missing AACR Intel row is normal for non-AACR leads; a real failure here
        # silently strips the card's scientific depth, so it must be visible.
        logger.warning("plan_generator: AACR Intel lookup failed for source_ref_id=%r", srid,
                       exc_info=True)
        intel = None
    narrative = synthesize_narrative(intel) if intel else {}
    scoring = compute_score(intel) if intel else {"lead_score": getattr(lead, "lead_score", 0),
                                                   "tier": getattr(lead, "tier", "Tier 3"),
                                                   "signals": []}

    # (b) matched KOL deep block
    kol = _kol_deep_for_lead(display_name, lead_id)

    # (c) live enrichment signals + fit corroboration
    signals = enrich.get("signals", []) if use_enrich else []
    fit_dims = (enrich.get("fit", {}) or {}).get("dimensions", {}) if use_enrich else {}

    # sharpest hook: KOL hook > top opportunity > narrative current_focus
    sharpest_hook = _first_nonempty(
        (kol or {}).get("hook"),
        narrative.get("current_focus"),
        _clip(narrative.get("pain_points", ""), 200),
    )
    angle = _first_nonempty(
        (kol or {}).get("crispro_angle"),
        (kol or {}).get("brenus_angle"),
    )

    # KOL AACR findings become SOURCED evidence records alongside live signals; only
    # source-bearing items are eligible for safe_to_say / the LLM evidence set.
    kol_evidence = _kol_evidence(kol)
    evidence = list(signals) + kol_evidence

    score_table = _score_table_from_signals(fit_dims, narrative, kol)
    # schema_b vulnerability, when the ingest carries it, sharpens a fit rationale.
    _vulns = [e for e in kol_evidence if e.get("kind") == "aacr_vulnerability"]
    if _vulns and score_table:
        score_table[0] = dict(score_table[0])
        score_table[0]["rationale"] = (
            f"{score_table[0]['rationale']} Stated vulnerability: {_clip(_vulns[0]['text'], 200)}"
        )
    composite = _composite(score_table, kol)

    institution, institution_source = _kol_institution(kol, company)
    subject_hint = _first_nonempty((kol or {}).get("email_subject"))
    open_qs, _oq_trunc = _kol_list(kol, "open_questions")
    trial, phase = _trial_phase_from_sources(intel, narrative, signals)

    # crispro_can / cannot — grounded, honest
    crispro_can = []
    if narrative.get("crispro_fit"):
        crispro_can = [ln.lstrip("• ").strip()
                       for ln in narrative["crispro_fit"].split("\n") if ln.strip()][:3]
    if kol and kol.get("crispro_opportunities"):
        for o in kol["crispro_opportunities"][:3]:
            ang = _first_nonempty(o.get("crispro_angle"), o.get("description"))
            if ang and ang not in crispro_can:
                crispro_can.append(_clip(ang, 200))
    if not crispro_can:
        crispro_can = ["Stratify a biomarker-defined responder subgroup in silico (once a real signal is linked)."]
    crispro_cannot = [
        "Cannot claim a model has been run on their proprietary data (none has).",
        "Cannot promise a clinical endpoint (ORR/PFS/OS) — CrisPRO informs design, not outcomes.",
        "Cannot substitute for their prospective validation.",
    ]

    ctx = {"aacr_topic": narrative.get("aacr_topic"), "organization": company,
           "institution": institution}
    contact_first = display_name.split()[0] if display_name and " " in display_name else display_name
    steps = _steps_from_plan("Lead", lead_id, ctx, sharpest_hook, angle, company, contact_first,
                             evidence=evidence, subject_hint=subject_hint, kol=kol)

    snapshot = _first_nonempty(
        narrative.get("aacr_topic"),
        f"{display_name} — {company}. "
        + (f"AACR focus: {narrative.get('current_focus')}. " if narrative.get("current_focus") else "")
        + (f"{len(signals)} live intel signal(s)." if signals else "Awaiting live enrichment."),
    )

    tier = scoring.get("tier") or getattr(lead, "tier", "Tier 3")
    # Real rank first: the CRM field, then the KOL worklist rank (1-20, a genuine ordering),
    # and only then the coarse tier table — which is a labeled placeholder, not evidence.
    rank = getattr(lead, "priority_rank", None)
    if not rank and isinstance((kol or {}).get("rank"), int):
        rank = kol["rank"]
    if not rank:
        rank = {"Tier 1": 2, "Tier 2": 5, "Tier 3": 8}.get(tier, 8)

    card = {
        "slug": f"lead-{_slugify(display_name)}-{lead_id.split('-')[-1]}",
        "front_matter": {
            "title": f"{display_name} — CrisPRO Engagement (generated)",
            "date": frappe.utils.today(),
            "status": "GENERATED",
            "company": company,
            "lead_drug": _first_nonempty((kol or {}).get("primary_axis"), narrative.get("current_focus"), "—"),
            "target": _first_nonempty((kol or {}).get("primary_axis"), "—"),
            "trial": trial,
            "phase": phase,
            # explicit indication so _seed_one does NOT default a non-CRC lead to
            # "Colorectal Cancer"; honest sentinel when it cannot be derived.
            "cancer_type": _lead_indication(lead),
            "outreach_priority_rank": rank,
            "claim_posture": "conservative (auto-generated; human review required)",
            "evidence_sufficiency": (
                "live-intel + aacr" if (signals and (intel or kol))
                else "live-intel" if signals
                else "kol-target" if kol
                else "aacr-intel" if intel
                else "thin"
            ),
            "primary_contact": display_name,
            "backup_contact": "",
            # Present only when the ingest actually carried it; absent rather than invented.
            **({"stc1010_relevance": _first_nonempty((kol or {}).get("stc1010_relevance"))}
               if _first_nonempty((kol or {}).get("stc1010_relevance")) else {}),
            **({"aacr_talk_title": _first_nonempty((kol or {}).get("schema_a_title"))}
               if _first_nonempty((kol or {}).get("schema_a_title")) else {}),
            "preferred_channel": "LinkedIn",
            "tags": ["generated", tier.replace(" ", "-").lower()] + (["kol"] if kol else []),
            "globs": [],
        },
        "snapshot": _clip(snapshot, 600),
        "fit": {
            "score_table": score_table,
            "composite": composite,
            "sharpest_hook": _clip(sharpest_hook, 300) or "No sharp hook yet — enrich to surface one.",
            "crispro_can": crispro_can,
            "crispro_cannot": crispro_cannot,
        },
        "contacts": {
            "primary": {
                "name": display_name,
                "title": "",
                # KOL institution when the ingest carried it, else the CRM organization.
                # Provenance is recorded so a reader can tell which one they are looking at.
                "institution": institution,
                "institution_source": institution_source,
                "linkedin": f"(search: {display_name} {company})",
                "public_email_verified": "NO",
                "rationale": ("Matched KOL target from AACR 2026." if kol else
                              "AACR-linked lead." if intel else "CRM lead."),
            },
            "backup": {},
            "preferred_channel": "LinkedIn (no verified public email)",
        },
        "message_options": steps,
        "governance": {
            # Built from live signals AND sourced KOL/AACR findings — every entry must
            # carry a source, so unsourced items are dropped rather than softened.
            "safe_to_say": _safe_to_say_from_signals(evidence),
            "not_safe_to_say": list(_STANDING_NOT_SAFE),
            "company_specific_constraints": list(_STANDING_CONSTRAINTS),
        },
        # provenance block (NOT part of curated shape, but harmless + auditable)
        "_generated": {
            "subject_type": "Lead", "subject_key": lead_id,
            "sources_used": {
                "aacr_intel": bool(intel), "kol_target": bool(kol),
                "live_enrichment": bool(signals), "n_signals": len(signals),
                "n_kol_evidence": len(kol_evidence),
                "kol_open_questions": len(open_qs),
                "institution_source": institution_source,
                "subject_hint_used": bool(subject_hint),
                "kol_truncation_flags": _kol_truncation_flags(kol),
            },
            "draft_methods": sorted({
                s.get("draft_method", "")
                for opt in ("option_a", "option_b")
                for s in steps.get(opt, {}).get("steps", [])
            } - {""}),
            "score_backup_tier": tier, "score_backup_lead_score": scoring.get("lead_score"),
        },
    }
    return card


def _build_card_for_company(slug_or_name: str, enrich: dict, use_enrich: bool) -> dict:
    """Company-side card. If slug_or_name matches one of the 10 curated engagements
    we DEFER to that (generation is only for non-curated). Otherwise assemble from
    live enrichment signals."""
    company = slug_or_name
    signals = enrich.get("signals", []) if use_enrich else []
    fit_dims = (enrich.get("fit", {}) or {}).get("dimensions", {}) if use_enrich else {}
    lead_drug = _first_nonempty((enrich.get("fit", {}) or {}).get("lead_drug"), "—")

    score_table = _score_table_from_signals(fit_dims, None, None)
    composite = _composite(score_table, None)
    sharpest = ""
    for s in signals:
        if s.get("kind") in ("trial", "biomarker") and s.get("text"):
            sharpest = s["text"]
            break
    sharpest = sharpest or (signals[0]["text"] if signals else "")

    snapshot = (f"{company} — {len(signals)} live intel signal(s). Lead asset: {lead_drug}."
                if signals else f"{company} — awaiting live enrichment.")
    steps = _steps_from_plan("Company", slug_or_name,
                             {"organization": company, "institution": company},
                             sharpest, "", company, "", evidence=signals)

    card = {
        "slug": f"company-{_slugify(company)}",
        "front_matter": {
            "title": f"{company} — CrisPRO Engagement (generated)",
            "date": frappe.utils.today(), "status": "GENERATED",
            "company": company, "lead_drug": lead_drug, "target": "—",
            "trial": "—", "phase": "—", "cancer_type": _UNSPECIFIED_INDICATION,
            "outreach_priority_rank": 8,
            "claim_posture": "conservative (auto-generated; human review required)",
            "evidence_sufficiency": "live-intel" if signals else "thin",
            "primary_contact": "", "backup_contact": "", "preferred_channel": "LinkedIn",
            "tags": ["generated", "company"], "globs": [],
        },
        "snapshot": _clip(snapshot, 600),
        "fit": {
            "score_table": score_table, "composite": composite,
            "sharpest_hook": _clip(sharpest, 300) or "No sharp hook yet — enrich to surface one.",
            "crispro_can": ["Stratify a biomarker-defined responder subgroup in silico (once a real signal is linked)."],
            "crispro_cannot": [
                "Cannot claim a model has been run on their data (none has).",
                "Cannot promise a clinical endpoint — CrisPRO informs design, not outcomes.",
            ],
        },
        "contacts": {"primary": {}, "backup": {},
                     "preferred_channel": "LinkedIn (no verified public email)"},
        "message_options": steps,
        "governance": {
            "safe_to_say": _safe_to_say_from_signals(signals),
            "not_safe_to_say": list(_STANDING_NOT_SAFE),
            "company_specific_constraints": list(_STANDING_CONSTRAINTS),
        },
        "_generated": {
            "subject_type": "Company", "subject_key": slug_or_name,
            "sources_used": {"live_enrichment": bool(signals), "n_signals": len(signals)},
        },
    }
    return card


# --------------------------------------------------------------------------- #
# ENDPOINTS
# --------------------------------------------------------------------------- #
def _guard():
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
def generate_plan(subject_type: str, subject_key: str, use_enrich: int = 1) -> dict:
    """Assemble an engagements.json-shape card for ANY company or lead.

    subject_type: "Lead"  -> subject_key is a CRM Lead name (CRM-LEAD-...)
                  "Company"-> subject_key is a company slug or name

    use_enrich=1 pulls live enrichment (cache-first; degrades to skipped_no_key
    for unset providers, PubMed/ClinicalTrials keyless). use_enrich=0 builds the
    card from AACR Intel + KOL match only (no external calls).

    WRITES NOTHING. Returns {card, seedable:True}. Call generate_and_seed_plan to
    materialize templates/tasks/drafts.
    """
    _guard()
    use_enrich = int(use_enrich or 0)

    # If a Company slug matches a curated engagement, defer to it (don't regenerate).
    if subject_type == "Company":
        from crm.api.industry import _engagement
        curated = _engagement(subject_key)
        if curated:
            return {"card": curated, "curated": True, "seedable": True,
                    "note": "This company is one of the 10 curated engagements; using the hand-authored card."}

    enrich = {}
    if use_enrich:
        try:
            if subject_type == "Lead":
                from crm.api.enrichment_api import enrich_contact
                enrich = enrich_contact(subject_key, force=0)
            else:
                from crm.api.enrichment_api import enrich_engagement
                enrich = enrich_engagement(subject_key, force=0)
        except Exception as e:  # enrich must never break plan generation
            logger.warning("plan_generator: enrichment failed for %s %s; continuing without it",
                           subject_type, subject_key, exc_info=True)
            enrich = {"status": "error", "error": str(e), "signals": [], "fit": {}}

    if subject_type == "Lead":
        if not frappe.db.exists("CRM Lead", subject_key):
            frappe.throw(_("Lead not found: {0}").format(subject_key), frappe.DoesNotExistError)
        card = _build_card_for_lead(subject_key, enrich, use_enrich=bool(use_enrich))
    else:
        card = _build_card_for_company(subject_key, enrich, use_enrich=bool(use_enrich))

    return {"card": card, "curated": False, "seedable": True,
            "enrich_status": enrich.get("status"),
            "sources_used": card.get("_generated", {}).get("sources_used", {})}


@frappe.whitelist()
def generate_and_seed_plan(subject_type: str, subject_key: str,
                           option: str = "A", use_enrich: int = 1) -> dict:
    """Generate the card, then feed it UNCHANGED into the existing seeder
    (crm.api.industry._seed_one) to materialize Email Templates + Outreach
    Sequence + Prospect + Instance + CRM Tasks + inbox drafts. Human-gated:
    everything is Draft/Todo; nothing sends. Idempotent (upsert)."""
    _guard()
    result = generate_plan(subject_type, subject_key, use_enrich=use_enrich)
    card = result["card"]
    from crm.api.industry import _seed_one
    created = _seed_one(card, option=option)
    frappe.db.commit()
    return {
        "subject_type": subject_type, "subject_key": subject_key,
        "curated": result.get("curated", False),
        "slug": card.get("slug"),
        "seeded": created,
        "counts": {
            "email_templates": len(created.get("email_templates", [])),
            "tasks": len(created.get("tasks", [])),
            "drafts": len(created.get("drafts", [])),
        },
    }
