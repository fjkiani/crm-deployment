# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt
"""
GTM <-> Schema B bridge.

Reads the competitive-intel record already assembled by
`crm.fcrm.doctype.aacr_intel.aacr_intel.get_aacr_intel` for a lead's
`source_ref_id` (canonical talk UID) and:

  1. Synthesizes the 5 GTM narrative fields (deterministic templating).
  2. Recomputes lead_score / tier / priority_rank from the v2 scoring formula.
  3. Snapshots the pre-existing score/tier into additional_data.nyx_score_backup
     (reversible) and stamps provenance + intel_synced_at.

The v2 scoring formula is TUNABLE and is NOT the governance-locked production
ranker. It is documented here as the single source of truth for the bridge.

No LLM is used (per GTM_SCHEMA_B_BRIDGE.md: LLM polish is optional).
"""

import json
from datetime import datetime, timezone

import frappe
from crm.fcrm.doctype.aacr_intel.aacr_intel import get_aacr_intel

try:
	from crm.fcrm.doctype.aacr_talk.aacr_talk import get_aacr_talk
except Exception:  # AACR Talk API optional; synthesis works from Schema B alone
	get_aacr_talk = None


# --------------------------------------------------------------------------- #
# scoring formula (v2, tunable; NOT the locked production ranker)
# --------------------------------------------------------------------------- #
# v2 rebalance (approved 2026-07-02): keeps the GTM_SCHEMA_B_BRIDGE.md tier bands
# (>=8 Tier 1, >=6 Tier 2) but re-weights signals so a strong beatable-competitor
# lead can actually reach Tier 1. v1 capped at ~6.5 (Tier 1 unreachable); v2 was
# calibrated against the live 743-lead intel population so Tier 1 stays elite
# (~1.5%: only clinical-trial readouts with >=3 opportunities, >=2 explicit failure
# admissions, and trial-dilution risk). Reversible via additional_data.nyx_score_backup.
#
#   opportunities:  >=4 -> +3.0 | >=3 -> +2.0 | >=1 -> +1.0
#   explicit_admission vulnerabilities: +2.0 each, capped +4.0
#   trial-dilution risks:               +0.5 each, capped +1.5   (new signal)
#   presentation_type == clinical_trial_readout: +1.0
#   data_maturity contains "mature":              +0.5
SCORING_FORMULA_VERSION = "v2"
# Tier cut-offs, recorded alongside every score so a historical row can be
# re-derived even after the bands are retuned.
TIER_BANDS = {"Tier 1": 8.0, "Tier 2": 6.0}


def compute_score(intel: dict) -> dict:
	"""Return {'lead_score', 'tier', 'signals'} from a Schema B intel record."""
	counts = (intel or {}).get("counts", {}) or {}
	n_opps = counts.get("opportunities", 0)
	n_risk = counts.get("trial_risks", 0)
	vulns = (intel or {}).get("vulnerability_identified", []) or []
	pres = ((intel or {}).get("presentation_type") or "").lower()
	maturity = ((intel or {}).get("data_maturity") or "").lower()

	score = 0.0
	signals = []

	if n_opps >= 4:
		score += 3.0
		signals.append(f"n_opportunities>=4 (+3.0) [{n_opps}]")
	elif n_opps >= 3:
		score += 2.0
		signals.append(f"n_opportunities>=3 (+2.0) [{n_opps}]")
	elif n_opps >= 1:
		score += 1.0
		signals.append(f"n_opportunities>=1 (+1.0) [{n_opps}]")

	explicit = sum(1 for v in vulns if (v.get("evidence_strength") or "") == "explicit_admission")
	if explicit:
		bump = min(2.0 * explicit, 4.0)
		score += bump
		signals.append(f"explicit_admission vulnerabilities x{explicit} (+{bump})")

	if n_risk >= 1:
		bump = min(0.5 * n_risk, 1.5)
		score += bump
		signals.append(f"trial_dilution_risks x{n_risk} (+{bump})")

	if pres == "clinical_trial_readout":
		score += 1.0
		signals.append("presentation_type=clinical_trial_readout (+1.0)")

	if "mature" in maturity:
		score += 0.5
		signals.append(f"data_maturity~mature (+0.5) [{maturity}]")

	tier = ("Tier 1" if score >= TIER_BANDS["Tier 1"]
	        else ("Tier 2" if score >= TIER_BANDS["Tier 2"] else "Tier 3"))
	return {"lead_score": round(score, 2), "tier": tier, "signals": signals,
	        "formula_version": SCORING_FORMULA_VERSION}


# --------------------------------------------------------------------------- #
# Deterministic GTM narrative templating (Schema B -> 5 GTM fields)
# --------------------------------------------------------------------------- #
def _fmt_vuln(v: dict) -> str:
	bits = []
	if v.get("failure_type"):
		bits.append(v["failure_type"].replace("_", " "))
	if v.get("failing_compound_or_target"):
		bits.append(f"({v['failing_compound_or_target']})")
	if v.get("mechanistic_blindspot"):
		bits.append(f"— {v['mechanistic_blindspot']}")
	return " ".join(bits).strip()


def synthesize_narrative(intel: dict) -> dict:
	"""Return the 5 GTM narrative fields templated deterministically."""
	opps = (intel or {}).get("crispro_opportunity", []) or []
	vulns = (intel or {}).get("vulnerability_identified", []) or []
	maturity = (intel or {}).get("data_maturity") or ""

	# aacr_topic: talk title (Schema B parent)
	aacr_topic = (intel or {}).get("talk_title") or ""

	# current_focus: top opportunity type + first vulnerability target
	focus_bits = []
	if opps:
		focus_bits.append((opps[0].get("opportunity_type") or "").replace("_", " "))
	if vulns and vulns[0].get("failing_compound_or_target"):
		focus_bits.append(vulns[0]["failing_compound_or_target"])
	current_focus = " / ".join([b for b in focus_bits if b]).strip()

	# pain_points: summarize vulnerability rows
	pain_points = "; ".join([_fmt_vuln(v) for v in vulns if _fmt_vuln(v)])

	# crispro_fit: top 1-3 opportunity descriptions + angle
	fit_lines = []
	for o in opps[:3]:
		desc = o.get("description") or ""
		angle = o.get("crispro_angle") or ""
		line = desc + ((" — " + angle) if angle else "")
		if line.strip():
			fit_lines.append(f"• {line.strip()}")
	crispro_fit = "\n".join(fit_lines)

	# fit_rationale: evidence quality summary
	n_opps = len(opps)
	explicit = sum(1 for v in vulns if (v.get("evidence_strength") or "") == "explicit_admission")
	rat_bits = []
	if explicit:
		rat_bits.append(f"{explicit} explicit resistance/failure admission(s)")
	if n_opps:
		rat_bits.append(f"{n_opps} CrisPRO angle(s)")
	if maturity:
		rat_bits.append(f"data maturity: {maturity}")
	fit_rationale = "; ".join(rat_bits)

	return {
		"aacr_topic": aacr_topic,
		"current_focus": current_focus,
		"pain_points": pain_points,
		"crispro_fit": crispro_fit,
		"fit_rationale": fit_rationale,
	}


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def synthesize_gtm_from_intel(lead_name: str, commit: bool = True) -> dict:
	"""Read Schema A+B for a lead's source_ref_id, write synthesized GTM narrative
	+ recomputed score/tier back to the CRM Lead. Idempotent. Reversible (snapshots
	the prior score/tier into additional_data.nyx_score_backup)."""
	lead = frappe.get_doc("CRM Lead", lead_name)
	srid = lead.source_ref_id
	if not srid:
		return {"lead": lead_name, "status": "skipped", "reason": "no source_ref_id"}

	intel = get_aacr_intel(srid)
	if not intel:
		return {"lead": lead_name, "status": "skipped", "reason": "no intel for source_ref_id"}

	narrative = synthesize_narrative(intel)
	scoring = compute_score(intel)

	# merge additional_data (preserve existing keys, e.g. enrichment)
	try:
		ad = json.loads(lead.additional_data) if lead.additional_data else {}
	except Exception:
		ad = {}
	if "nyx_score_backup" not in ad:  # snapshot only once, don't clobber on re-run
		ad["nyx_score_backup"] = {
			"lead_score": lead.lead_score,
			"tier": lead.tier,
			"priority_rank": lead.priority_rank,
			"snapped_at": datetime.now(timezone.utc).isoformat(),
		}
	# Provenance MUST name the formula that actually ran. This previously read a
	# hardcoded "v1_tunable" while compute_score implemented v2, so every lead the
	# bridge touched carried a false formula label. Derive it from the constant.
	ad["nyx_gtm"] = {
		"source": "synthesized",
		"formula": f"{SCORING_FORMULA_VERSION}_tunable",
		"formula_version": SCORING_FORMULA_VERSION,
		"tier_bands": TIER_BANDS,
		"signals": scoring["signals"],
		"intel_synced_at": datetime.now(timezone.utc).isoformat(),
	}

	# apply
	for k, v in narrative.items():
		setattr(lead, k, v)
	lead.lead_score = scoring["lead_score"]
	lead.tier = scoring["tier"]
	lead.additional_data = json.dumps(ad)

	if commit:
		lead.save(ignore_permissions=True)
		frappe.db.commit()

	return {
		"lead": lead_name,
		"status": "synthesized",
		"lead_score": scoring["lead_score"],
		"tier": scoring["tier"],
		"signals": scoring["signals"],
		"narrative_filled": {k: bool(v) for k, v in narrative.items()},
	}


@frappe.whitelist()
def backfill_gtm(only_resolvable: bool = True, limit: int = 0) -> dict:
	"""Batch synthesize all leads with a resolvable canonical source_ref_id, then
	assign priority_rank within each tier by score desc."""
	filters = [["source_ref_id", "like", "%::%"]] if only_resolvable else [["source_ref_id", "is", "set"]]
	names = frappe.get_all("CRM Lead", filters=filters, pluck="name", limit_page_length=limit or 0)

	results = {"synthesized": 0, "skipped": 0, "errors": 0, "by_tier": {}}
	scored = []
	for n in names:
		try:
			r = synthesize_gtm_from_intel(n, commit=True)
			if r["status"] == "synthesized":
				results["synthesized"] += 1
				results["by_tier"][r["tier"]] = results["by_tier"].get(r["tier"], 0) + 1
				scored.append((n, r["tier"], r["lead_score"]))
			else:
				results["skipped"] += 1
		except Exception as e:
			results["errors"] += 1
			frappe.log_error(f"backfill_gtm {n}: {e}")

	# priority_rank within tier
	for tier in set(t for _, t, _ in scored):
		group = sorted([(n, s) for n, t, s in scored if t == tier], key=lambda x: -x[1])
		for rank, (n, _) in enumerate(group, 1):
			frappe.db.set_value("CRM Lead", n, "priority_rank", rank, update_modified=False)
	frappe.db.commit()
	return results
