"""
crm/api/enrichment_api.py — On-demand, cached, oncology-domain intel endpoints.

Cache-first: reads the CrisPRO Enrichment doctype; if a fresh (< 7-day TTL) row exists
returns it with cached=True and makes ZERO external calls. Otherwise fires the
enrichment_sources fan-out in parallel, distills oncology signals, maps them to CrisPRO
fit dimensions, persists, and returns.

Distillation + scoring are ONCOLOGY-domain (drug pipelines, trials, biomarkers,
publications) — the VC/AUM rubric from the EAIA source is intentionally NOT ported.
LLM steps use the shared _resolve_llm() seam and degrade to labeled deterministic
fallbacks when no LLM provider is configured (no fabricated intel).
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime, add_to_date

from crm.api import enrichment_sources as ES
from crm.api.industry import _engagement, _company_for_slug
from crm.api.nyx_email_brain import _resolve_llm, _active_llm_provider

logger = logging.getLogger(__name__)

_TTL_DAYS = 7
_DOCTYPE = "CrisPRO Enrichment"


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------
def _guard():
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


# ---------------------------------------------------------------------------
# cache read / write
# ---------------------------------------------------------------------------
def _cache_get(subject_type: str, subject_key: str):
	rows = frappe.get_all(
		_DOCTYPE,
		filters={"subject_type": subject_type, "subject_key": subject_key},
		fields=["name", "expires_at", "status"],
		order_by="fetched_at desc",
		limit_page_length=1,
	)
	if not rows:
		return None
	row = rows[0]
	if row.expires_at and get_datetime(row.expires_at) < now_datetime():
		return None  # expired
	doc = frappe.get_doc(_DOCTYPE, row.name)
	return doc


def _cache_write(subject_type, subject_key, company, person_name, status,
                 signals, fit, sources, payload):
	# supersede prior rows for the same subject (keep latest only)
	for old in frappe.get_all(_DOCTYPE, filters={"subject_type": subject_type,
	                                              "subject_key": subject_key}, pluck="name"):
		frappe.delete_doc(_DOCTYPE, old, ignore_permissions=True, force=True)
	doc = frappe.get_doc({
		"doctype": _DOCTYPE,
		"subject_type": subject_type,
		"subject_key": subject_key,
		"company": company or "",
		"person_name": person_name or "",
		"status": status,
		"fetched_at": now_datetime(),
		"expires_at": add_to_date(now_datetime(), days=_TTL_DAYS),
		"cost_note": _cost_note(payload),
		"signals_json": json.dumps(signals),
		"fit_json": json.dumps(fit),
		"sources_json": json.dumps(sources),
		"payload": json.dumps(payload),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc


def _cost_note(payload: dict) -> str:
	paid = {"tavily", "apollo_person", "apollo_org", "brightdata_linkedin",
	        "brightdata_strategy", "diffbot_org", "diffbot_person"}
	fired = [k for k, v in payload.items()
	         if isinstance(v, dict) and v.get("status") == "ok" and k in paid]
	return f"{len(fired)} paid source(s) called" if fired else "no paid calls"


def _serialize(doc) -> dict:
	return {
		"subject_type": doc.subject_type,
		"subject_key": doc.subject_key,
		"company": doc.company,
		"person_name": doc.person_name,
		"status": doc.status,
		"fetched_at": str(doc.fetched_at),
		"expires_at": str(doc.expires_at),
		"cost_note": doc.cost_note,
		"signals": json.loads(doc.signals_json or "[]"),
		"fit": json.loads(doc.fit_json or "{}"),
		"sources": json.loads(doc.sources_json or "[]"),
		"payload": json.loads(doc.payload or "{}"),
	}


# ---------------------------------------------------------------------------
# oncology distillation
# ---------------------------------------------------------------------------
_DISTILL_SYS = """You are an oncology business-development intelligence analyst for CrisPRO \
(Brenus Pharma's in-silico trial-simulation and patient-stratification platform).

Below is raw multi-source intel on a biotech/oncology company (and optionally a KOL). \
Extract EXACTLY 3-6 citable signals that matter for a scientific outreach conversation. \
Only include facts with a specific number, name, date, trial ID, drug, target, or biomarker \
-- no generic descriptions. Each signal must be usable as a talking point.

Return ONLY valid JSON:
{
  "signals": [
    {"kind": "trial|biomarker|publication|pipeline|event|competitor",
     "text": "one specific, citable fact",
     "source": "which source it came from"}
  ],
  "lead_drug": "primary drug/asset if identifiable, else ''",
  "primary_indication": "if identifiable, else ''",
  "signal_gate": "ok if >=2 real signals, else quarantine"
}"""


def _flatten_for_distill(payload: dict) -> str:
	parts = []
	for key, env in payload.items():
		if not isinstance(env, dict) or env.get("status") != "ok":
			continue
		data = env.get("data") or {}
		if key == "tavily":
			for r in data.get("results", [])[:6]:
				parts.append(f"[news] {r.get('content','')[:400]}")
		elif key == "clinicaltrials":
			for t in data.get("trials", [])[:6]:
				parts.append(f"[trial] {t.get('nct_id')} {t.get('phases')} {t.get('status')} — "
				             f"{t.get('title','')} (conditions: {', '.join(t.get('conditions',[])[:3])})")
		elif key == "pubmed":
			for a in data.get("articles", [])[:6]:
				parts.append(f"[pub] {a.get('pubdate')} — {a.get('title','')} ({a.get('journal','')})")
		elif key == "diffbot_org":
			parts.append(f"[firmographics] {json.dumps(data)[:400]}")
		elif key == "apollo_org":
			parts.append(f"[firmographics] {json.dumps(data)[:400]}")
		elif key == "strategy":
			parts.append(f"[strategy] {data.get('strategy','')[:400]}")
		elif key == "competitors":
			parts.append(f"[competitors] {data.get('competitors','')[:300]}")
		elif key in ("diffbot_person", "apollo_person", "linkedin"):
			parts.append(f"[person] {json.dumps(data)[:300]}")
	return "\n".join(parts)


def _distill_oncology(payload: dict) -> dict:
	raw = _flatten_for_distill(payload)
	if not raw.strip():
		return {"signals": [], "signal_gate": "quarantine", "lead_drug": "",
		        "primary_indication": "", "method": "no_data"}
	llm = _resolve_llm()
	if llm:
		try:
			out = llm(_DISTILL_SYS + "\n\nRAW INTEL:\n" + raw[:6000])
			out = _strip_fence(out)
			data = json.loads(out)
			data["method"] = f"llm:{_active_llm_provider()}"
			# enforce the gate
			real = [s for s in data.get("signals", []) if len((s.get("text") or "")) > 10]
			data["signals"] = real
			data["signal_gate"] = "ok" if len(real) >= 2 else "quarantine"
			return data
		except Exception as e:
			logger.warning(f"distill llm failed, falling back: {e}")
	return _distill_deterministic(payload)


def _distill_deterministic(payload: dict) -> dict:
	"""Deterministic fallback — extract structured signals directly, no LLM. Labeled."""
	signals = []
	ct = (payload.get("clinicaltrials") or {}).get("data", {}).get("trials", [])
	for t in ct[:3]:
		if t.get("nct_id"):
			signals.append({
				"kind": "trial",
				"text": f"{t.get('nct_id')} — {', '.join(t.get('phases',[])) or 'Phase n/a'}, "
				        f"{t.get('status','')} ({t.get('title','')[:80]})",
				"source": "ClinicalTrials.gov",
			})
	pm = (payload.get("pubmed") or {}).get("data", {}).get("articles", [])
	for a in pm[:2]:
		if a.get("title"):
			signals.append({
				"kind": "publication",
				"text": f"{a.get('pubdate','')} — {a.get('title','')[:100]} ({a.get('journal','')})",
				"source": "PubMed",
			})
	org = (payload.get("diffbot_org") or {}).get("data") or \
	      (payload.get("apollo_org") or {}).get("data") or {}
	if org.get("nbEmployees") or org.get("estimated_num_employees"):
		hc = org.get("nbEmployees") or org.get("estimated_num_employees")
		signals.append({"kind": "pipeline", "text": f"Company headcount ~{hc}",
		                "source": "firmographics"})
	return {
		"signals": signals,
		"signal_gate": "ok" if len(signals) >= 2 else "quarantine",
		"lead_drug": "",
		"primary_indication": "",
		"method": "deterministic",
	}


def _strip_fence(txt: str) -> str:
	import re
	txt = re.sub(r"^```(?:json)?\s*", "", (txt or "").strip())
	txt = re.sub(r"\s*```$", "", txt)
	return txt.strip()


# ---------------------------------------------------------------------------
# CrisPRO fit mapping (aligns to the fit dimensions already in engagement JSON)
# ---------------------------------------------------------------------------
_FIT_DIMS = [
	("BG", "Biomarker Gap", ["biomarker", "enrichment", "stratif", "subgroup", "retrospective"]),
	("CN", "Comparator Need", ["control arm", "comparator", "benchmark", "historical", "sparse"]),
	("PC", "Population Complexity", ["population", "co-mutation", "stratif", "liver", "subgroup", "mss"]),
	("TI", "Translational Interpretability", ["interpretab", "prospective", "validation", "itt", "endpoint"]),
]


def _map_fit(signals: dict, engagement: dict | None) -> dict:
	"""Map distilled signals to the 4 CrisPRO dimensions. If the engagement JSON already
	carries a fit table, we surface it and annotate which dims the live intel corroborates."""
	txt = " ".join([(s.get("text") or "").lower() for s in signals.get("signals", [])])
	corroborated = {}
	for code, label, kws in _FIT_DIMS:
		hits = [k for k in kws if k in txt]
		corroborated[code] = {"label": label, "live_evidence": bool(hits), "matched": hits}
	base_table = (engagement or {}).get("fit", {}).get("score_table", [])
	return {
		"dimensions": corroborated,
		"engagement_fit_table": base_table,
		"signal_gate": signals.get("signal_gate"),
		"lead_drug": signals.get("lead_drug", ""),
	}


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------
@frappe.whitelist()
def enrich_engagement(slug: str, force: int = 0) -> dict:
	"""Company + primary/backup contacts intel for an industry engagement. Cache-first."""
	_guard()
	force = int(force or 0)
	eng = _engagement(slug)
	if not eng:
		frappe.throw(_("Engagement not found: {0}").format(slug), frappe.DoesNotExistError)
	fm = eng.get("front_matter", {})
	company = fm.get("company") or _company_for_slug(slug)

	if not force:
		cached = _cache_get("Company", slug)
		if cached:
			out = _serialize(cached)
			out["cached"] = True
			return out

	website = ""  # engagement JSON has no canonical website; Diffbot/Tavily resolve by name
	trial = fm.get("trial") or ""
	company_intel = ES.gather_company_intel(company, website=website, trial=_trial_expr(trial, company))

	signals = _distill_oncology(company_intel)
	fit = _map_fit(signals, eng)
	sources = _collect_sources(company_intel)
	status = "quarantine" if signals.get("signal_gate") == "quarantine" else \
	         ("ok" if any(isinstance(v, dict) and v.get("status") == "ok" for v in company_intel.values()) else "error")

	doc = _cache_write("Company", slug, company, "", status, signals, fit, sources, company_intel)
	out = _serialize(doc)
	out["cached"] = False
	return out


@frappe.whitelist()
def enrich_contact(lead_name: str, force: int = 0) -> dict:
	"""Person-level intel for a CRM Lead. Cache-first."""
	_guard()
	force = int(force or 0)
	if not frappe.db.exists("CRM Lead", lead_name):
		frappe.throw(_("Lead not found: {0}").format(lead_name), frappe.DoesNotExistError)
	lead = frappe.get_doc("CRM Lead", lead_name)
	name = lead.lead_name or ""
	org = lead.organization or ""

	if not force:
		cached = _cache_get("Person", lead_name)
		if cached:
			out = _serialize(cached)
			out["cached"] = True
			return out

	person_intel = ES.gather_person_intel(name, org=org, linkedin_url="", title="")
	signals = _distill_oncology(person_intel)
	fit = _map_fit(signals, None)
	sources = _collect_sources(person_intel)
	status = "ok" if any(isinstance(v, dict) and v.get("status") == "ok" for v in person_intel.values()) else "error"

	doc = _cache_write("Person", lead_name, org, name, status, signals, fit, sources, person_intel)
	out = _serialize(doc)
	out["cached"] = False
	return out


@frappe.whitelist()
def get_enrichment(subject_type: str, subject_key: str) -> dict:
	"""Read cache only. Never fires external calls. Returns {status:'empty'} if none."""
	_guard()
	cached = _cache_get(subject_type, subject_key)
	if not cached:
		return {"status": "empty", "subject_type": subject_type, "subject_key": subject_key}
	out = _serialize(cached)
	out["cached"] = True
	return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _collect_sources(intel: dict) -> list:
	urls = []
	for env in intel.values():
		if isinstance(env, dict):
			for u in env.get("sources", []):
				if u and u not in urls and u not in ("#", "tavily_answer"):
					urls.append(u)
	return urls


def _trial_expr(trial: str, company: str) -> str:
	"""Extract a searchable expression for ClinicalTrials from the trial front-matter string."""
	import re
	# prefer an NCT id if present
	m = re.search(r"NCT\d{8}", trial or "")
	if m:
		return m.group(0)
	# else use the drug/company
	return company
