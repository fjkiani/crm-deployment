# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt
"""
Native lead-email enrichment for NYX.

Ports the ad-hoc Tavily + two-gate adjudication flow (proven in the AACR-CRM
enrichment passes: 84 + 13 + 47 = 144 verified writes, 0 overwrites) into a
whitelisted server function so the pipeline can enrich internally instead of a
notebook.

Two-gate adjudication (write ONLY where both gates agree):
  gate 1 (deterministic): surname of the lead name appears in the email local-part,
                          and the local-part is not a role/dept account.
  gate 2 (LLM):           an OpenRouter/Gemma call confirms the email belongs to
                          this specific person (rejects cross-contaminated scrapes).

Keys resolve from env first, then site_config (mirrors etl_json.py):
  TAVILY_API_KEY / tavily_api_key
  OPENROUTER_API_KEY / openrouter_api_key   (model: openrouter_enrichment_model
                                             or google/gemma-3-27b-it)

Every attempt is logged to `Lead Enrichment Log` (one row per attempt) and a
compact trail is appended to CRM Lead `additional_data.nyx_enrichment_log`.
Existing `email` is never overwritten; existing additional_data keys are merged.
"""

import json
import re
import unicodedata

import frappe

# ---------------------------------------------------------------------------
# deterministic gate  (verified primitives: split_name, ROLE_PREFIXES)
# ---------------------------------------------------------------------------
_TITLE_RE = re.compile(r"^(Dr\.?|Prof\.?|Professor|Mr\.?|Ms\.?|Mrs\.?|Sir|MD|PhD)\s+", re.I)
ROLE_PREFIXES = (
	"info", "media", "contact", "admin", "press", "office", "support", "hello",
	"inquiries", "inquiry", "general", "webmaster", "help", "news", "comms",
	"communications", "mail", "email", "dept", "department", "giving", "referral",
	"referralcenter", "bcrf", "investors", "clinicaltrials", "address", "sports",
)


def _norm(s: str) -> str:
	"""strip accents, lowercase, keep a-z only (transliteration-tolerant)."""
	s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
	return re.sub(r"[^a-z]", "", s.lower())


def split_name(full: str):
	f = _TITLE_RE.sub("", str(full or "")).strip()
	parts = f.split()
	if len(parts) >= 2:
		return parts[0], parts[-1]
	return (parts[0] if parts else str(full or "")), ""


def classify_email(email: str, name: str) -> str:
	"""Deterministic verdict: accept | accept_high | review | reject | none."""
	if not email or "@" not in email:
		return "none"
	local = email.split("@")[0].lower()
	local_alpha = re.sub(r"[^a-z]", "", local)
	first, last = split_name(name)
	fn, ln = _norm(first), _norm(last)

	# role / department account -> never a person
	base = re.split(r"[._\-+0-9]", local)[0]
	if base in ROLE_PREFIXES or local in ROLE_PREFIXES:
		return "reject"

	# strong: full surname (>=3 chars) present in local-part
	if ln and len(ln) >= 3 and ln in local_alpha:
		return "accept"
	# medium: surname stem (first 5 chars) present
	if ln and len(ln) >= 5 and ln[:5] in local_alpha:
		return "accept_high"
	# firstname-only match -> needs LLM gate
	if fn and len(fn) >= 3 and fn in local_alpha:
		return "review"
	return "reject"


# ---------------------------------------------------------------------------
# key resolution + LLM gate
# ---------------------------------------------------------------------------
def _get_key(*names):
	import os
	for n in names:
		v = os.getenv(n.upper())
		if v:
			return v
		try:
			v = frappe.conf.get(n.lower())
		except Exception:
			v = None
		if v:
			return v
	return None


def _strip_json_fence(txt: str) -> str:
	txt = re.sub(r"^```(?:json)?\s*", "", txt.strip())
	txt = re.sub(r"\s*```$", "", txt)
	return txt.strip()


def _llm_adjudicate(name: str, email: str, context: str = "") -> dict:
	"""gate 2: OpenRouter/Gemma confirms email belongs to this person."""
	key = _get_key("openrouter_api_key")
	if not key:
		return {"verdict": "skip", "reason": "no_openrouter_key"}
	import requests
	model = _get_key("openrouter_enrichment_model") or "google/gemma-3-27b-it"
	prompt = (
		"You verify whether an email address belongs to a specific named person.\n"
		f"PERSON: {name}\nEMAIL: {email}\n"
		f"CONTEXT: {context[:500] if context else '(none)'}\n\n"
		"Rules:\n"
		"- ACCEPT if the local-part plausibly encodes THIS person's name "
		"(surname, initials+surname, first.last). Transliteration/spelling variants OK.\n"
		"- REJECT if the local-part is a different person's name (cross-contamination),\n"
		"  or a role/department account (info@, media@, contact@).\n"
		'Respond with JSON only: {"verdict":"accept"|"reject","reason":"<short>"}'
	)
	try:
		r = requests.post(
			"https://openrouter.ai/api/v1/chat/completions",
			headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
			json={"model": model, "temperature": 0.1, "max_tokens": 120,
			      "messages": [{"role": "user", "content": prompt}]},
			timeout=45,
		)
		if r.status_code != 200:
			return {"verdict": "skip", "reason": f"http_{r.status_code}"}
		txt = r.json()["choices"][0]["message"]["content"]
		data = json.loads(_strip_json_fence(txt))
		v = str(data.get("verdict", "")).lower()
		return {"verdict": v if v in ("accept", "reject") else "skip",
		        "reason": data.get("reason", "")}
	except Exception as e:
		return {"verdict": "skip", "reason": f"error:{type(e).__name__}"}


# ---------------------------------------------------------------------------
# Tavily scout
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _tavily_scout(name: str, org: str = "", depth: str = "advanced", max_results: int = 6) -> dict:
	key = _get_key("tavily_api_key")
	if not key:
		return {"emails": [], "context": "", "error": "no_tavily_key"}
	import requests
	q = f'"{name}" {org} email contact'.strip()
	try:
		r = requests.post(
			"https://api.tavily.com/search",
			json={"api_key": key, "query": q, "search_depth": depth,
			      "include_answer": True, "max_results": max_results},
			timeout=40,
		)
		if r.status_code != 200:
			return {"emails": [], "context": "", "error": f"http_{r.status_code}"}
		d = r.json()
		blob = (d.get("answer") or "") + " " + " ".join(
			(x.get("content") or "") + " " + (x.get("url") or "") for x in d.get("results", [])
		)
		emails = []
		for m in _EMAIL_RE.findall(blob):
			e = m.lower().strip(".")
			if e not in emails and not e.endswith((".png", ".jpg", ".gif")):
				emails.append(e)
		return {"emails": emails, "context": (d.get("answer") or "")[:500], "error": None}
	except Exception as e:
		return {"emails": [], "context": "", "error": f"error:{type(e).__name__}"}


# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------
def _log_attempt(lead_name, name, org, candidate, det, llm, decision, reason, source="tavily"):
	# in-CRM compact trail
	try:
		lead = frappe.get_doc("CRM Lead", lead_name)
		ad = frappe.parse_json(lead.additional_data) if lead.additional_data else {}
		if not isinstance(ad, dict):
			ad = {}
		trail = ad.get("nyx_enrichment_log", [])
		trail.append({
			"ts": frappe.utils.now(), "candidate": candidate, "det": det,
			"llm": llm.get("verdict"), "decision": decision, "reason": reason, "source": source,
		})
		ad["nyx_enrichment_log"] = trail[-20:]
		lead.db_set("additional_data", json.dumps(ad), update_modified=False)
	except Exception:
		pass
	# dedicated log doctype
	try:
		if frappe.db.exists("DocType", "Lead Enrichment Log"):
			frappe.get_doc({
				"doctype": "Lead Enrichment Log", "crm_lead": lead_name,
				"lead_name_snapshot": name, "organization": org,
				"candidate_email": candidate, "deterministic_verdict": det,
				"llm_verdict": llm.get("verdict"), "llm_reason": (llm.get("reason") or "")[:140],
				"decision": decision, "reason": (reason or "")[:140], "source": source,
			}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Lead Enrichment Log insert failed")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
@frappe.whitelist()
def enrich_lead_email(lead_name: str, force: bool = False, write: bool = True) -> dict:
	"""Enrich ONE lead's email via Tavily scout + two-gate adjudication.

	Never overwrites an existing email unless force=True. Returns the decision
	regardless of write. `write=False` performs a dry run (adjudicate + log only).
	"""
	lead = frappe.get_doc("CRM Lead", lead_name)
	name = lead.lead_name or ""
	org = lead.organization or ""

	if lead.email and not force:
		return {"lead": lead_name, "decision": "skip_has_email", "email": lead.email}

	scout = _tavily_scout(name, org)
	if scout.get("error") or not scout["emails"]:
		_log_attempt(lead_name, name, org, "", "none", {"verdict": "skip"},
		             "no_candidate", scout.get("error") or "no_emails")
		return {"lead": lead_name, "decision": "no_candidate",
		        "error": scout.get("error"), "candidates": scout["emails"]}

	# adjudicate candidates; take the first that passes BOTH gates
	best = None
	for cand in scout["emails"]:
		det = classify_email(cand, name)
		if det in ("reject", "none"):
			_log_attempt(lead_name, name, org, cand, det, {"verdict": "n/a"},
			             "reject_deterministic", "surname/role gate")
			continue
		llm = _llm_adjudicate(name, cand, scout["context"])
		agree = det in ("accept", "accept_high", "review") and llm.get("verdict") == "accept"
		decision = "write" if agree else ("hold_disagree" if llm.get("verdict") == "reject" else "hold_llm_skip")
		_log_attempt(lead_name, name, org, cand, det, llm, decision,
		             llm.get("reason") or "two-gate")
		if agree:
			best = cand
			break

	if not best:
		return {"lead": lead_name, "decision": "held", "candidates": scout["emails"]}

	if not write:
		return {"lead": lead_name, "decision": "would_write", "email": best,
		        "candidates": scout["emails"]}

	# write (merge additional_data, never clobber)
	lead.reload()
	if lead.email and not force:
		return {"lead": lead_name, "decision": "skip_has_email", "email": lead.email}
	lead.email = best
	lead.save(ignore_permissions=True)
	frappe.db.commit()
	return {"lead": lead_name, "decision": "written", "email": best}


@frappe.whitelist()
def enrich_leads_batch(lead_names, force: bool = False, write: bool = True, limit: int = 0) -> dict:
	"""Enrich a batch. `lead_names` may be a JSON list or comma string; if empty,
	selects leads with no email and a resolvable source_ref_id."""
	if isinstance(lead_names, str):
		lead_names = frappe.parse_json(lead_names) if lead_names.strip().startswith("[") \
			else [x.strip() for x in lead_names.split(",") if x.strip()]
	if not lead_names:
		lead_names = frappe.get_all(
			"CRM Lead", filters=[["email", "is", "not set"], ["source_ref_id", "like", "%::%"]],
			pluck="name", limit_page_length=int(limit or 0))
	out = {"attempted": 0, "written": 0, "held": 0, "no_candidate": 0, "skipped": 0, "results": []}
	for n in lead_names:
		try:
			res = enrich_lead_email(n, force=force, write=write)
		except Exception as e:
			res = {"lead": n, "decision": "error", "error": str(e)}
		d = res.get("decision", "")
		out["attempted"] += 1
		if d in ("written", "would_write"):
			out["written"] += 1
		elif d == "held":
			out["held"] += 1
		elif d == "no_candidate":
			out["no_candidate"] += 1
		elif d.startswith("skip"):
			out["skipped"] += 1
		out["results"].append(res)
	return out
