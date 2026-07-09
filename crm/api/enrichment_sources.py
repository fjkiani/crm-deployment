"""
crm/api/enrichment_sources.py — Multi-source live intel transport for CrisPRO.

Ported + hardened from the sibling EAIA LangGraph app
(assistant/executive-ai-assistant-main/eaia/pipeline/enrichment/*), rebuilt for the
ONCOLOGY / KOL domain (drug pipelines, trials, biomarkers, publications) instead of the
VC/hedge-fund (AUM / SEC 13F) domain it originally targeted.

Sources (uniform envelope: {source, status, data, sources[], fetched_at}):
  Tavily              → recent news, corporate/clinical events, strategy mentions
  Apollo (person)     → email, title, LinkedIn URL, seniority
  Apollo (org)        → firmographics (headcount, industry, founded, website)
  BrightData LinkedIn → headline, summary, positions, recent posts
  BrightData strategy → company pipeline / clinical-strategy page content
  BrightData compete  → competitor drugs / programs
  Diffbot org         → structured firmographics (KG Enhance)
  Diffbot person      → structured person profile (KG Enhance)
  PubMed              → KOL publications (PMID, title, journal, year, DOI) [direct E-utilities]
  ClinicalTrials.gov  → trial involvement (NCT, phase, status, conditions) [direct v2 REST]

Key resolution: every source uses the shared `_get_key()` seam
(crm.api.enrichment._get_key) which checks os.environ[UPPER] then frappe.conf[lower].
No credential is ever hardcoded here. Absent key => status "skipped_no_key" (never crash,
never fabricate).

This module is TRANSPORT ONLY — it fetches and normalizes. Signal distillation and
CrisPRO-fit scoring live in nyx synthesis (see enrichment_api endpoints).
"""

import re
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

import frappe
from frappe.utils import now_datetime

from crm.api.enrichment import _get_key  # shared env + frappe.conf key seam

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 15


# ---------------------------------------------------------------------------
# envelope helper
# ---------------------------------------------------------------------------
def _env(source, status, data=None, sources=None):
	"""Uniform source envelope. status ∈ ok | skipped_no_key | empty | error."""
	return {
		"source": source,
		"status": status,
		"data": data if data is not None else {},
		"sources": sources or [],
		"fetched_at": str(now_datetime()),
	}


# ---------------------------------------------------------------------------
# S1 — Tavily web search (domain-neutral transport; oncology query templates)
# ---------------------------------------------------------------------------
def tavily_search(query: str, max_results: int = 5) -> dict:
	key = _get_key("tavily_api_key")
	if not key:
		return _env("tavily", "skipped_no_key")
	try:
		r = requests.post(
			"https://api.tavily.com/search",
			json={
				"api_key": key,
				"query": query,
				"search_depth": "advanced",
				"max_results": max_results,
				"include_answer": True,
			},
			timeout=_HTTP_TIMEOUT,
		)
		r.raise_for_status()
		d = r.json()
		items, urls = [], []
		if d.get("answer"):
			items.append({"url": "tavily_answer", "content": d["answer"]})
		for res in d.get("results", []):
			u = res.get("url")
			items.append({
				"url": u,
				"content": res.get("content", ""),
				"published_date": res.get("published_date"),
			})
			if u:
				urls.append(u)
		return _env("tavily", "ok" if items else "empty", {"results": items}, urls)
	except Exception as e:
		logger.warning(f"tavily_search failed: {e}")
		return _env("tavily", "error", {"error": str(e)})


def tavily_oncology_multi(company: str, name: str = "") -> dict:
	"""Oncology-framed multi-query scout (replaces the finance/AUM query set)."""
	queries = [
		f"{company} clinical trial pipeline drug development news 2025 2026",
		f"{company} lead drug mechanism target indication oncology",
		f"{company} biomarker strategy patient enrichment trial design",
	]
	if name:
		queries.append(f"{name} {company} publication congress presentation oncology 2025 2026")
	merged, urls = [], []
	status = "skipped_no_key"
	for q in queries:
		res = tavily_search(q, max_results=3)
		if res["status"] == "skipped_no_key":
			return _env("tavily", "skipped_no_key")
		if res["status"] == "ok":
			status = "ok"
			for it in res["data"].get("results", []):
				it = dict(it)
				it["query"] = q
				merged.append(it)
			urls.extend(res.get("sources", []))
	return _env("tavily", status if merged else "empty", {"results": merged}, urls)


# ---------------------------------------------------------------------------
# S2 — Apollo person match
# ---------------------------------------------------------------------------
def apollo_match(name: str, org: str) -> dict:
	key = _get_key("apollo_api_key")
	if not key:
		return _env("apollo_person", "skipped_no_key")
	try:
		r = requests.post(
			"https://api.apollo.io/v1/people/match",
			headers={"Content-Type": "application/json", "X-Api-Key": key},
			json={"name": name, "organization_name": org, "reveal_personal_emails": True},
			timeout=_HTTP_TIMEOUT,
		)
		if r.status_code == 429:
			return _env("apollo_person", "error", {"error": "rate_limited"})
		if r.status_code != 200:
			return _env("apollo_person", "error", {"error": f"http_{r.status_code}"})
		person = r.json().get("person") or {}
		if not person:
			return _env("apollo_person", "empty")
		data = {
			"email": person.get("email"),
			"title": person.get("title"),
			"linkedin_url": person.get("linkedin_url"),
			"organization": (person.get("organization") or {}).get("name"),
			"city": person.get("city"),
			"headline": person.get("headline"),
			"seniority": person.get("seniority"),
			"departments": person.get("departments", []),
		}
		data = {k: v for k, v in data.items() if v}
		return _env("apollo_person", "ok" if data else "empty", data)
	except Exception as e:
		logger.warning(f"apollo_match failed: {e}")
		return _env("apollo_person", "error", {"error": str(e)})


# ---------------------------------------------------------------------------
# S2b — Apollo org enrich (firmographics; real /organizations/enrich call)
# ---------------------------------------------------------------------------
def apollo_org_enrich(domain: str = "", name: str = "") -> dict:
	key = _get_key("apollo_api_key")
	if not key:
		return _env("apollo_org", "skipped_no_key")
	if not domain and not name:
		return _env("apollo_org", "empty")
	try:
		params = {}
		if domain:
			params["domain"] = domain
		r = requests.get(
			"https://api.apollo.io/v1/organizations/enrich",
			headers={"Content-Type": "application/json", "X-Api-Key": key},
			params=params or {"q_organization_name": name},
			timeout=_HTTP_TIMEOUT,
		)
		if r.status_code != 200:
			return _env("apollo_org", "error", {"error": f"http_{r.status_code}"})
		org = r.json().get("organization") or {}
		if not org:
			return _env("apollo_org", "empty")
		data = {
			"name": org.get("name"),
			"website_url": org.get("website_url"),
			"industry": org.get("industry"),
			"estimated_num_employees": org.get("estimated_num_employees"),
			"founded_year": org.get("founded_year"),
			"linkedin_url": org.get("linkedin_url"),
			"short_description": org.get("short_description"),
			"city": org.get("city"),
			"country": org.get("country"),
		}
		data = {k: v for k, v in data.items() if v}
		return _env("apollo_org", "ok" if data else "empty", data)
	except Exception as e:
		logger.warning(f"apollo_org_enrich failed: {e}")
		return _env("apollo_org", "error", {"error": str(e)})


# ---------------------------------------------------------------------------
# S3/S5/S6 — BrightData Web Unlocker (LinkedIn + oncology strategy + competitors)
# ---------------------------------------------------------------------------
def _brightdata_get(url: str, timeout: int = 20) -> str:
	key = _get_key("brightdata_api_key")
	if not key:
		return ""
	# Zone name is account-specific. Configurable via `brightdata_zone`; default matches
	# BrightData's common Web Unlocker zone. If the account uses a different zone name the
	# API returns HTTP 400 "zone not found" — we log and degrade (never fabricate).
	zone = _get_key("brightdata_zone") or "web_unlocker1"
	try:
		r = requests.post(
			"https://api.brightdata.com/request",
			headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
			json={"zone": zone, "url": url, "format": "raw"},
			timeout=timeout,
		)
		if r.status_code == 200:
			return r.text[:8000]
		logger.debug(f"brightdata http {r.status_code} zone={zone}: {r.text[:120]}")
	except Exception as e:
		logger.debug(f"brightdata error ({url[:60]}): {e}")
	return ""


def linkedin_profile(linkedin_url: str) -> dict:
	if not _get_key("brightdata_api_key"):
		return _env("brightdata_linkedin", "skipped_no_key")
	if not linkedin_url:
		return _env("brightdata_linkedin", "empty")
	raw = _brightdata_get(linkedin_url)
	if not raw:
		return _env("brightdata_linkedin", "empty", sources=[linkedin_url])
	try:
		headline_m = re.search(r'"headline":"([^"]{5,200})"', raw)
		summary_m = re.search(r'"summary":"([^"]{20,600})"', raw)
		positions = re.findall(r'"title":"([^"]{5,100})"', raw)
		posts = re.findall(r'"commentary":\{"text":"([^"]{20,300})"', raw)
		data = {
			"headline": headline_m.group(1) if headline_m else "",
			"summary": summary_m.group(1) if summary_m else "",
			"positions": positions[:5],
			"recent_activity": posts[:3],
		}
		data = {k: v for k, v in data.items() if v}
		return _env("brightdata_linkedin", "ok" if data else "empty", data, [linkedin_url])
	except Exception as e:
		return _env("brightdata_linkedin", "error", {"error": str(e)}, [linkedin_url])


def company_clinical_strategy(company: str, website: str = "") -> dict:
	"""Oncology rewrite of company_strategy: pipeline / clinical-focus signal."""
	if not _get_key("brightdata_api_key") and not _get_key("tavily_api_key"):
		return _env("brightdata_strategy", "skipped_no_key")
	# Try website pages first (BrightData) if we have a URL + key
	if website and _get_key("brightdata_api_key"):
		for path in ["/pipeline", "/science", "/our-science", "/programs", "/clinical-trials", "/about"]:
			raw = _brightdata_get(f"{website.rstrip('/')}{path}")
			if raw and len(raw) > 300:
				sentences = re.findall(r"[A-Z][^.!?]{30,220}[.!?]", raw)
				keep = [
					s for s in sentences
					if any(kw in s.lower() for kw in [
						"trial", "phase", "patient", "tumor", "cancer", "oncology",
						"biomarker", "antibody", "therapy", "clinical", "indication",
						"combination", "checkpoint", "mechanism", "target", "efficacy",
					])
				]
				if keep:
					return _env(
						"brightdata_strategy", "ok",
						{"strategy": " ".join(keep[:4])},
						[f"{website.rstrip('/')}{path}"],
					)
	# Fallback: Tavily
	res = tavily_search(
		f"{company} clinical pipeline lead program trial strategy oncology", max_results=3
	)
	if res["status"] == "ok":
		snips = res["data"].get("results", [])
		return _env(
			"brightdata_strategy", "ok",
			{"strategy": " | ".join([s.get("content", "")[:300] for s in snips[:2]])},
			res.get("sources", []),
		)
	return _env("brightdata_strategy", res["status"])


def competitor_programs(company: str) -> dict:
	"""Oncology rewrite of competitor_intel: rival drugs/programs in the same space."""
	res = tavily_search(
		f"{company} competitor drugs programs same target indication oncology 2025 2026",
		max_results=3,
	)
	if res["status"] == "skipped_no_key":
		return _env("competitors", "skipped_no_key")
	if res["status"] == "ok":
		snips = res["data"].get("results", [])
		return _env(
			"competitors", "ok",
			{"competitors": " ".join([s.get("content", "")[:200] for s in snips[:2]])},
			res.get("sources", []),
		)
	return _env("competitors", res["status"])


# ---------------------------------------------------------------------------
# S-new — Diffbot KG Enhance (structured firmographics + person)
# ---------------------------------------------------------------------------
def _diffbot_enhance(entity_type: str, **fields) -> dict:
	token = _get_key("diffbot_token")
	label = "diffbot_org" if entity_type == "Organization" else "diffbot_person"
	if not token:
		return _env(label, "skipped_no_key")
	params = {"type": entity_type, "token": token}
	params.update({k: v for k, v in fields.items() if v})
	try:
		r = requests.get("https://kg.diffbot.com/kg/v3/enhance", params=params, timeout=_HTTP_TIMEOUT)
		if r.status_code != 200:
			return _env(label, "error", {"error": f"http_{r.status_code}"})
		data = r.json()
		matches = (data.get("data") or [])
		if not matches:
			return _env(label, "empty")
		entity = (matches[0].get("entity") or {})
		return _env(label, "ok", {"entity": entity})
	except Exception as e:
		logger.warning(f"diffbot_enhance failed: {e}")
		return _env(label, "error", {"error": str(e)})


def diffbot_org(name: str, url: str = "", location: str = "") -> dict:
	# NOTE: Diffbot org matching is URL-dependent. A bare company name can match the
	# wrong entity (e.g. "Agenus" -> a health-analytics firm on agenus.com rather than
	# the biotech on agenusbio.com). When a URL is supplied the match is reliable; when
	# not, we tag `match_confidence` low so the distill layer / UI can flag it.
	raw = _diffbot_enhance("Organization", name=name, url=url, location=location)
	if raw["status"] != "ok":
		return raw
	e = raw["data"]["entity"]
	data = {
		"name": e.get("name"),
		"description": e.get("description"),
		"nbEmployees": e.get("nbEmployees"),
		"foundingDate": (e.get("foundingDate") or {}).get("str"),
		"homepageUri": e.get("homepageUri"),
		"industries": e.get("industries"),
		"totalInvestment": (e.get("totalInvestment") or {}).get("value"),
		"ceo": (e.get("ceo") or {}).get("name"),
		"nbActiveEmployeeEdges": e.get("nbActiveEmployeeEdges"),
		"match_confidence": "high" if url else "low",
	}
	data = {k: v for k, v in data.items() if v}
	return _env("diffbot_org", "ok" if data else "empty", data)


def diffbot_person(name: str, employer: str = "", title: str = "") -> dict:
	raw = _diffbot_enhance("Person", name=name, employer=employer, title=title)
	if raw["status"] != "ok":
		return raw
	e = raw["data"]["entity"]
	empl = ""
	for emp in (e.get("employments") or []):
		if (emp.get("employer") or {}).get("name"):
			empl = emp["employer"]["name"]
			break
	data = {
		"name": e.get("name"),
		"description": e.get("description"),
		"currentTitle": (e.get("employments") or [{}])[0].get("title") if e.get("employments") else None,
		"employer": empl,
		"linkedin": next((u for u in (e.get("allUris") or []) if "linkedin.com" in u), None),
	}
	data = {k: v for k, v in data.items() if v}
	return _env("diffbot_person", "ok" if data else "empty", data)


# ---------------------------------------------------------------------------
# S7/S8 — PubMed (direct NCBI E-utilities; no Bio.Entrez dependency)
# ---------------------------------------------------------------------------
_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _ncbi_common():
	p = {}
	k = _get_key("ncbi_api_key")
	e = _get_key("ncbi_email", "ncbi_user_email")
	if k:
		p["api_key"] = k
	if e:
		p["email"] = e
		p["tool"] = "crispro-crm"
	return p


def pubmed_search(query: str, retmax: int = 8) -> dict:
	"""Search PubMed and fetch article summaries. Works without a key (lower rate)."""
	try:
		params = {"db": "pubmed", "term": query, "retmax": str(retmax), "retmode": "json"}
		params.update(_ncbi_common())
		r = requests.get(f"{_EUTILS}/esearch.fcgi", params=params, timeout=_HTTP_TIMEOUT)
		r.raise_for_status()
		ids = (r.json().get("esearchresult") or {}).get("idlist") or []
		if not ids:
			return _env("pubmed", "empty", {"articles": []})
		sp = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
		sp.update(_ncbi_common())
		s = requests.get(f"{_EUTILS}/esummary.fcgi", params=sp, timeout=_HTTP_TIMEOUT)
		s.raise_for_status()
		res = s.json().get("result") or {}
		articles, urls = [], []
		for pmid in ids:
			it = res.get(pmid) or {}
			if not it:
				continue
			doi = ""
			for aid in (it.get("articleids") or []):
				if aid.get("idtype") == "doi":
					doi = aid.get("value")
			authors = [a.get("name") for a in (it.get("authors") or [])][:6]
			url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
			articles.append({
				"pmid": pmid,
				"title": it.get("title"),
				"journal": it.get("fulljournalname") or it.get("source"),
				"pubdate": it.get("pubdate"),
				"authors": authors,
				"doi": doi,
				"url": url,
			})
			urls.append(url)
		return _env("pubmed", "ok" if articles else "empty", {"articles": articles}, urls)
	except Exception as e:
		logger.warning(f"pubmed_search failed: {e}")
		return _env("pubmed", "error", {"error": str(e)})


# ---------------------------------------------------------------------------
# S9/S10 — ClinicalTrials.gov v2 REST (direct; no pytrials dependency)
# ---------------------------------------------------------------------------
_CT_V2 = "https://clinicaltrials.gov/api/v2/studies"


def clinicaltrials_search(expr: str, max_studies: int = 8) -> dict:
	"""Search ClinicalTrials.gov v2. No key required."""
	try:
		params = {
			"query.term": expr,
			"pageSize": str(max_studies),
			"fields": "NCTId,BriefTitle,Phase,OverallStatus,Condition,LeadSponsorName,StartDate",
		}
		r = requests.get(_CT_V2, params=params, timeout=_HTTP_TIMEOUT)
		r.raise_for_status()
		studies, urls = [], []
		for st in (r.json().get("studies") or []):
			ps = st.get("protocolSection") or {}
			idm = ps.get("identificationModule") or {}
			stm = ps.get("statusModule") or {}
			dm = ps.get("designModule") or {}
			cm = ps.get("conditionsModule") or {}
			spm = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
			nct = idm.get("nctId")
			url = f"https://clinicaltrials.gov/study/{nct}" if nct else None
			studies.append({
				"nct_id": nct,
				"title": idm.get("briefTitle"),
				"phases": dm.get("phases", []),
				"status": stm.get("overallStatus"),
				"conditions": (cm.get("conditions") or [])[:6],
				"sponsor": spm.get("name"),
				"start_date": (stm.get("startDateStruct") or {}).get("date"),
				"url": url,
			})
			if url:
				urls.append(url)
		return _env("clinicaltrials", "ok" if studies else "empty", {"trials": studies}, urls)
	except Exception as e:
		logger.warning(f"clinicaltrials_search failed: {e}")
		return _env("clinicaltrials", "error", {"error": str(e)})


# ---------------------------------------------------------------------------
# Parallel fan-out orchestrators (used by enrichment_api endpoints)
# ---------------------------------------------------------------------------
def _resolve_company_website(company: str) -> str:
	"""Best-effort resolve a company's canonical website via Tavily.

	Diffbot/Apollo org matching is only reliable with the correct domain (a bare
	company name can match the wrong entity squatting a similar domain). We do one
	cheap Tavily lookup and take the first non-aggregator URL. Returns "" on failure
	(callers degrade gracefully — never fabricated).
	"""
	if not _get_key("tavily_api_key"):
		return ""
	try:
		env = tavily_search(f"{company} official website oncology company", max_results=5)
		if env.get("status") != "ok":
			return ""
		_SKIP = ("linkedin.com", "wikipedia.org", "bloomberg.com", "crunchbase.com",
			"twitter.com", "facebook.com", "sec.gov", "clinicaltrials.gov", "pubmed")
		for u in env.get("sources") or []:
			dom = _domain_from_url(u).lower()
			if dom and not any(s in dom for s in _SKIP):
				return dom
	except Exception as e:
		logger.debug(f"website resolution failed for {company}: {e}")
	return ""


def gather_company_intel(company: str, website: str = "", trial: str = "") -> dict:
	"""Fire all company-level sources in parallel. Returns dict of envelopes keyed by source.

	If no website is supplied we resolve one first (synchronously) so Diffbot/Apollo
	org matching keys off the correct domain rather than the bare name.
	"""
	if not website:
		website = _resolve_company_website(company)
	domain = _domain_from_url(website)
	jobs = {
		"tavily": lambda: tavily_oncology_multi(company),
		"apollo_org": lambda: apollo_org_enrich(domain=domain, name=company),
		"diffbot_org": lambda: diffbot_org(company, url=website),
		"strategy": lambda: company_clinical_strategy(company, website),
		"competitors": lambda: competitor_programs(company),
	}
	# Trials keyed off the company + the specific trial name if provided
	ct_expr = trial or company
	jobs["clinicaltrials"] = lambda: clinicaltrials_search(ct_expr)
	out = _run_parallel(jobs)
	out["_resolved_website"] = website
	return out


def gather_person_intel(name: str, org: str = "", linkedin_url: str = "", title: str = "") -> dict:
	"""Fire all person-level sources in parallel."""
	jobs = {
		"apollo_person": lambda: apollo_match(name, org),
		"diffbot_person": lambda: diffbot_person(name, employer=org, title=title),
		"pubmed": lambda: pubmed_search(f"{name}[Author]" + (f" AND {org}" if org else "")),
	}
	if linkedin_url:
		jobs["linkedin"] = lambda: linkedin_profile(linkedin_url)
	return _run_parallel(jobs)


def _run_parallel(jobs: dict) -> dict:
	out = {}
	with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as ex:
		fut = {ex.submit(fn): key for key, fn in jobs.items()}
		for f in as_completed(fut):
			key = fut[f]
			try:
				out[key] = f.result()
			except Exception as e:
				out[key] = _env(key, "error", {"error": str(e)})
	return out


def _domain_from_url(url: str) -> str:
	if not url:
		return ""
	m = re.search(r"https?://(?:www\.)?([^/]+)", url)
	return m.group(1) if m else url.replace("www.", "").strip("/")
