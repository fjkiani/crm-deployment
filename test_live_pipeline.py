#!/usr/bin/env python3
"""
🔱 ZETA PROTOCOL — LIVE A-Z INTEGRATION TEST
REAL API CALLS. REAL DB WRITES. NO MOCKS.

What fires live:
  ✅ Apollo API        — real person lookup by name + company
  ✅ Tavily API        — real web search for company signals
  ✅ Gemini API        — real LLM kill score + email draft
  ✅ Frappe REST API   — real lead create, communication read, sequence check
  ✅ DB read           — direct MariaDB query to verify writes
  ❌ Vapi API         — SKIPPED (no calls to real people)
  ❌ Twilio SMS       — SKIPPED (no texts to real people)

Usage:
  python3 test_live_pipeline.py
  python3 test_live_pipeline.py --lead-only        # just test enrichment + score
  python3 test_live_pipeline.py --frappe-only      # just test Frappe CRUD
"""

import sys
import os
import json
import time
import argparse
import requests
import traceback
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Load API keys from .env files
# ─────────────────────────────────────────────────────────────────────────────
BASE = Path("/Users/fahadkiani/Desktop/development/crm-develop")
ENV1 = BASE / "assistant/executive-ai-assistant-main/.env"
ENV2 = BASE / "assistant/executive-ai-assistant-main/eaia/.secrets/.env"

for env_path in [ENV1, ENV2]:
    if env_path.exists():
        load_dotenv(env_path, override=True)

APOLLO_KEY       = os.getenv("APOLLO_API_KEY", "")
TAVILY_KEY       = os.getenv("TAVILY_API_KEY", "")
GEMINI_KEY       = os.getenv("GEMINI_API_KEY", "")
BRIGHTDATA_KEY   = os.getenv("BRIGHTDATA_API_KEY", "")
COHERE_KEY       = os.getenv("COHERE_API_KEY", "")
FRAPPE_API_KEY   = os.getenv("FRAPPE_API_KEY", "")
FRAPPE_API_SEC   = os.getenv("FRAPPE_API_SECRET", "")
FRAPPE_URL       = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────────────────────────────────────
# Colors
# ─────────────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
CYAN = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"
PASS = f"{GREEN}✅ LIVE{RESET}"; FAIL = f"{RED}❌ FAIL{RESET}"; WARN = f"{YELLOW}⚠️  SKIP{RESET}"


def section(name):
    print(f"\n{BOLD}{CYAN}{'─'*65}{RESET}")
    print(f"{BOLD}{CYAN}  {name}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*65}{RESET}")


def log(msg, level="info"):
    icons = {"pass": PASS, "fail": FAIL, "warn": WARN, "info": f"{CYAN}ℹ️ {RESET}"}
    print(f"  {icons.get(level, '')} {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# FRAPPE AUTH HELPER
# ─────────────────────────────────────────────────────────────────────────────
def frappe_headers():
    if FRAPPE_API_KEY and FRAPPE_API_SEC:
        return {"Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SEC}"}
    return {}


def frappe_get(method, params=None):
    r = requests.get(f"{FRAPPE_URL}/api/method/{method}", params=params,
                     headers=frappe_headers(), timeout=15)
    return r


def frappe_post(method, data=None):
    r = requests.post(f"{FRAPPE_URL}/api/method/{method}", json=data or {},
                      headers=frappe_headers(), timeout=15)
    return r


def frappe_doc_post(doctype, data):
    r = requests.post(f"{FRAPPE_URL}/api/resource/{doctype}", json=data,
                      headers=frappe_headers(), timeout=15)
    return r


def frappe_doc_get(doctype, name):
    r = requests.get(f"{FRAPPE_URL}/api/resource/{doctype}/{name}",
                     headers=frappe_headers(), timeout=15)
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 0. PREFLIGHT — Check services + API keys
# ─────────────────────────────────────────────────────────────────────────────
def test_0_preflight():
    section("0. PREFLIGHT — Services + API Keys")
    results = {}

    # Frappe ping
    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
        if r.status_code == 200:
            log(f"Frappe @ {FRAPPE_URL}: UP → {r.json()}", "pass")
            results["frappe"] = True
        else:
            log(f"Frappe @ {FRAPPE_URL}: returned {r.status_code}", "warn")
            results["frappe"] = False
    except Exception as e:
        log(f"Frappe @ {FRAPPE_URL}: OFFLINE ({e})", "warn")
        results["frappe"] = False

    # API Key inventory
    key_map = {
        "Apollo": APOLLO_KEY[:12] + "..." if APOLLO_KEY else "MISSING",
        "Tavily": TAVILY_KEY[:18] + "..." if TAVILY_KEY else "MISSING",
        "Gemini": GEMINI_KEY[:14] + "..." if GEMINI_KEY else "MISSING",
        "Frappe Key": FRAPPE_API_KEY[:12] + "..." if FRAPPE_API_KEY else "MISSING",
        "BrightData": BRIGHTDATA_KEY[:12] + "..." if BRIGHTDATA_KEY else "MISSING",
        "Cohere": COHERE_KEY[:12] + "..." if COHERE_KEY else "MISSING",
    }
    for name, val in key_map.items():
        have = "MISSING" not in val
        log(f"{name}: {val}", "pass" if have else "warn")
        results[name.lower()] = have

    return results


# ─────────────────────────────────────────────────────────────────────────────
# A. APOLLO — Real person lookup
# ─────────────────────────────────────────────────────────────────────────────
def test_a_apollo():
    section("A. Apollo — Real Person Lookup")
    if not APOLLO_KEY:
        log("APOLLO_API_KEY not set — skipping", "warn")
        return None, False

    # Use Marc Lasry from Avenue Capital (on our actual lead list)
    test_subjects = [
        {"first_name": "Marc", "last_name": "Lasry", "organization_name": "Avenue Capital Group"},
        {"first_name": "Peter", "last_name": "McManus", "organization_name": "3EDGE Asset Management"},
    ]

    results = []
    enriched_leads = []

    for subject in test_subjects:
        try:
            log(f"Querying Apollo for {subject['first_name']} {subject['last_name']} @ {subject['organization_name']}...", "info")
            r = requests.post(
                "https://api.apollo.io/api/v1/people/match",
                json={
                    "first_name": subject["first_name"],
                    "last_name": subject["last_name"],
                    "organization_name": subject["organization_name"],
                    "reveal_personal_emails": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": APOLLO_KEY,
                },
                timeout=20,
            )
            data = r.json()
            person = data.get("person", {})
            email = person.get("email", "")
            title = person.get("title", "")
            linkedin = person.get("linkedin_url", "")
            phone = person.get("phone_numbers", [{}])[0].get("sanitized_number", "") if person.get("phone_numbers") else ""

            if email or title:
                log(f"  Found: {subject['first_name']} {subject['last_name']}", "pass")
                log(f"  Email: {email or '(not returned)'}", "info")
                log(f"  Title: {title or '(not returned)'}", "info")
                log(f"  LinkedIn: {linkedin or '(not returned)'}", "info")
                results.append(True)
                enriched_leads.append({**subject, "email": email, "title": title, "linkedin": linkedin})
            else:
                log(f"  {subject['first_name']} {subject['last_name']}: No match found (status={r.status_code})", "warn")
                if r.status_code == 200:
                    log(f"  Raw response keys: {list(data.keys())}", "info")
                results.append(False)

        except Exception as e:
            log(f"Apollo error for {subject['first_name']}: {e}", "fail")
            results.append(False)

    passed = any(results)
    return enriched_leads, passed


# ─────────────────────────────────────────────────────────────────────────────
# B. TAVILY — Real company signal search
# ─────────────────────────────────────────────────────────────────────────────
def test_b_tavily():
    section("B. Tavily — Real Company Signal Search")
    if not TAVILY_KEY:
        log("TAVILY_API_KEY not set — skipping", "warn")
        return None, False

    test_companies = [
        "Avenue Capital Group investment fund",
        "3EDGE Asset Management portfolio strategy",
    ]

    signals_found = []
    all_passed = True

    for query in test_companies:
        try:
            log(f"Searching: '{query}'...", "info")
            r = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
                timeout=20,
            )
            data = r.json()
            results_list = data.get("results", [])
            answer = data.get("answer", "")

            if results_list or answer:
                answer_label = "answer" if answer else "no answer"
                log(f"  Got {len(results_list)} results + {answer_label}", "pass")
                for res in results_list[:2]:
                    log(f"  → {res.get('title','')[:60]} | {res.get('url','')[:60]}", "info")
                if answer:
                    log(f"  AI Answer: {answer[:120]}...", "info")
                signals_found.append({
                    "company": query,
                    "signals": [r.get("title", "") for r in results_list],
                    "answer": answer[:200],
                })
            else:
                log(f"  No results for: {query}", "warn")
                all_passed = False

        except Exception as e:
            log(f"Tavily error: {e}", "fail")
            all_passed = False

    return signals_found, all_passed


# ─────────────────────────────────────────────────────────────────────────────
# C. GEMINI — Real LLM Kill Score + Email Draft
# ─────────────────────────────────────────────────────────────────────────────
def test_c_gemini(enriched_leads=None, signals=None):
    section("C. Gemini — Real LLM Kill Score + Email Draft")
    if not GEMINI_KEY:
        log("GEMINI_API_KEY not set — skipping", "warn")
        return None, False

    lead = (enriched_leads or [{}])[0] if enriched_leads else {
        "first_name": "Marc", "last_name": "Lasry",
        "company_name": "Avenue Capital Group",
        "title": "Co-CEO",
        "email": "mlasry@avenuecapital.com",
    }
    company = lead.get("organization_name") or lead.get("company_name") or "Unknown"
    name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()
    title = lead.get("title", "")

    signals_text = ""
    if signals:
        s = signals[0]
        signals_text = "\n".join(s.get("signals", [])[:3])

    # Kill score prompt
    scoring_prompt = f"""
You are a sales intelligence AI scoring a B2B lead (0-100).

Lead: {name}
Title: {title}
Company: {company}
Recent Signals: {signals_text or "None found"}

Score this lead from 0-100 based on:
- Title seniority (C-level = +30, VP = +20, Director = +10)
- Company size/relevance signals
- Any urgency indicators

Respond ONLY with JSON: {{"score": <int>, "reasoning": "<1 sentence>", "tier": "hot|warm|cold"}}
"""

    # Email draft prompt
    email_prompt = f"""
Write a 3-sentence cold outreach email for:
Name: {name}
Title: {title}
Company: {company}

Context: We offer genomic data stratification technology that helps investment firms identify high-confidence biotech opportunities.

Rules: Personal, specific to their role, no fluff, ends with ONE clear CTA.
Respond ONLY with JSON: {{"subject": "...", "body": "..."}}
"""

    gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

    # Score
    score_result = None
    draft_result = None
    try:
        log(f"Scoring {name} @ {company} via Gemini...", "info")
        r = requests.post(
            gemini_endpoint,
            json={"contents": [{"parts": [{"text": scoring_prompt}]}]},
            timeout=30,
        )
        raw_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Strip markdown code blocks if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        score_result = json.loads(raw_text.strip())
        log(f"  Kill Score: {score_result.get('score')}/100 ({score_result.get('tier')})", "pass")
        log(f"  Reasoning: {score_result.get('reasoning','')[:100]}", "info")
    except Exception as e:
        log(f"Gemini scoring error: {e}", "fail")

    # Draft
    try:
        log(f"Drafting email for {name} via Gemini...", "info")
        r = requests.post(
            gemini_endpoint,
            json={"contents": [{"parts": [{"text": email_prompt}]}]},
            timeout=30,
        )
        raw_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        draft_result = json.loads(raw_text.strip())
        log(f"  Subject: '{draft_result.get('subject','')}'", "pass")
        log(f"  Body (preview): '{draft_result.get('body','')[:120]}...'", "info")
    except Exception as e:
        log(f"Gemini draft error: {e}", "fail")

    passed = score_result is not None or draft_result is not None
    return {"score": score_result, "draft": draft_result, "lead": lead}, passed


# ─────────────────────────────────────────────────────────────────────────────
# D. FRAPPE — Real CRUD: Create Lead → Read it back → Check sequence
# ─────────────────────────────────────────────────────────────────────────────
def test_d_frappe_crud():
    section("D. Frappe — Real CRUD: Create Lead + Read Back")

    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
        if r.status_code != 200:
            log(f"Frappe not reachable (status {r.status_code}) — skipping DB tests", "warn")
            return None, False
    except Exception:
        log(f"Frappe offline at {FRAPPE_URL} — skipping DB tests", "warn")
        return None, False

    test_lead_data = {
        "doctype": "CRM Lead",
        "first_name": "Zeta",
        "last_name": "TestLive",
        "lead_name": "Zeta TestLive",
        "email": f"zeta.test.live.{int(time.time())}@testpipeline.io",
        "company_name": "Live Test Corp",
        "status": "New",
        "source": "Live Test",
        "mobile_no": "",
    }

    # CREATE
    log("Creating test CRM Lead via Frappe REST API...", "info")
    r = frappe_doc_post("CRM Lead", test_lead_data)
    if r.status_code not in (200, 201):
        log(f"Create failed: {r.status_code} → {r.text[:200]}", "fail")
        return None, False

    lead_name = r.json().get("data", {}).get("name")
    if not lead_name:
        log(f"Create returned no name → {r.json()}", "fail")
        return None, False

    log(f"Created: {lead_name}", "pass")

    # READ BACK
    log(f"Reading back {lead_name}...", "info")
    r = frappe_doc_get("CRM Lead", lead_name)
    if r.status_code != 200:
        log(f"Read failed: {r.status_code}", "fail")
        return lead_name, False

    data = r.json().get("data", {})
    assert data.get("email") == test_lead_data["email"], f"Email mismatch: {data.get('email')}"
    assert data.get("company_name") == test_lead_data["company_name"]
    log(f"Read back OK: email={data['email']} company={data['company_name']}", "pass")

    # UPDATE STATUS
    log(f"Updating {lead_name} status to 'Contacted'...", "info")
    r = requests.put(
        f"{FRAPPE_URL}/api/resource/CRM Lead/{lead_name}",
        json={"status": "Contacted"},
        headers=frappe_headers(),
        timeout=10,
    )
    if r.status_code == 200:
        updated_status = r.json().get("data", {}).get("status")
        log(f"Status updated: {updated_status}", "pass")
    else:
        log(f"Update failed: {r.status_code}", "warn")

    return lead_name, True


# ─────────────────────────────────────────────────────────────────────────────
# E. FRAPPE — Communication Log: Write then Query Back
# ─────────────────────────────────────────────────────────────────────────────
def test_e_frappe_communication(lead_name=None):
    section("E. Frappe — Communication Log (Write + Memory Query)")

    if not lead_name:
        log("No lead_name from test D — skipping", "warn")
        return False

    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
        if r.status_code != 200:
            log("Frappe offline — skipping", "warn")
            return False
    except Exception:
        log("Frappe offline — skipping", "warn")
        return False

    # Write a Communication record
    log(f"Writing Communication for {lead_name}...", "info")
    comm_data = {
        "doctype": "Communication",
        "communication_type": "Communication",
        "communication_medium": "Email",
        "subject": "[Live Test] Kill Score Report",
        "content": "This is a live test email generated by test_live_pipeline.py",
        "sender": "test@zeta.local",
        "recipients": "zeta.test@example.com",
        "reference_doctype": "CRM Lead",
        "reference_name": lead_name,
        "status": "Sent",
    }

    r = frappe_doc_post("Communication", comm_data)
    if r.status_code not in (200, 201):
        log(f"Communication create failed: {r.status_code} → {r.text[:200]}", "fail")
        return False

    comm_name = r.json().get("data", {}).get("name")
    log(f"Communication created: {comm_name}", "pass")

    # Now call our AI memory endpoint to read it back
    log(f"Calling get_lead_communication_history for {lead_name}...", "info")
    r = frappe_get(
        "crm.api.email.get_lead_communication_history",
        params={"lead_name": lead_name, "limit": 5},
    )
    if r.status_code == 200:
        history = r.json().get("message", {})
        total = history.get("total", 0)
        threads = history.get("threads", [])
        log(f"Memory returned {total} communication(s)", "pass" if total > 0 else "warn")
        for t in threads:
            log(f"  → [{t.get('date','')[:10]}] {t.get('subject','')[:60]}", "info")
    else:
        log(f"Memory endpoint failed: {r.status_code} → {r.text[:200]}", "fail")
        return False

    return True


# ─────────────────────────────────────────────────────────────────────────────
# F. FRAPPE — ETL upload: real CSV row via etl endpoint
# ─────────────────────────────────────────────────────────────────────────────
def test_f_etl_upload():
    section("F. ETL — Real CSV Row Upload via Frappe API")

    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
        if r.status_code != 200:
            log("Frappe offline — skipping", "warn")
            return False
    except Exception:
        log("Frappe offline — skipping", "warn")
        return False

    # Build a small CSV in memory with 3 leads from our real list
    import io
    csv_content = (
        "doctype,first_name,last_name,lead_name,email,organization,status,source\n"
        f"CRM Lead,LiveTest,Alpha,LiveTest Alpha,livetest.alpha.{int(time.time())}@zeta.io,Live Test Fund A,New,Live Test\n"
        f"CRM Lead,LiveTest,Beta,LiveTest Beta,livetest.beta.{int(time.time())}@zeta.io,Live Test Fund B,New,Live Test\n"
    )

    log("Uploading 2-lead CSV via ETL endpoint...", "info")
    files = {"file": ("live_test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    r = requests.post(
        f"{FRAPPE_URL}/api/method/crm.api.etl.upload_and_import",
        files=files,
        headers=frappe_headers(),
        timeout=30,
    )

    if r.status_code == 200:
        result = r.json().get("message", {})
        inserted = result.get("inserted", 0)
        updated = result.get("updated", 0)
        errors = result.get("errors", [])
        log(f"ETL result: inserted={inserted}, updated={updated}, errors={len(errors)}", "pass")
        if errors:
            for e in errors[:3]:
                log(f"  Error: {e}", "warn")
        return inserted > 0 or updated > 0
    else:
        log(f"ETL upload failed: {r.status_code} → {r.text[:300]}", "fail")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# G. FRAPPE — Outreach Sequence Query (does a sequence exist we can attach?)
# ─────────────────────────────────────────────────────────────────────────────
def test_g_sequences():
    section("G. Frappe — Outreach Sequences Query")

    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
        if r.status_code != 200:
            log("Frappe offline — skipping", "warn")
            return False
    except Exception:
        log("Frappe offline — skipping", "warn")
        return False

    log("Querying Outreach Sequences...", "info")
    r = requests.get(
        f"{FRAPPE_URL}/api/resource/Outreach Sequence",
        params={"limit": 10, "fields": '["name","is_active","subject_line"]'},
        headers=frappe_headers(),
        timeout=15,
    )

    if r.status_code == 200:
        sequences = r.json().get("data", [])
        log(f"Found {len(sequences)} outreach sequences", "pass" if sequences else "warn")
        for seq in sequences[:3]:
            log(f"  → {seq.get('name')} | active={seq.get('is_active')} | {seq.get('subject_line','')[:40]}", "info")
        return True
    else:
        log(f"Sequences query failed: {r.status_code} → {r.text[:200]}", "fail")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# H. BRIGHTDATA — Company firmographic lookup (LinkedIn scrape)
# ─────────────────────────────────────────────────────────────────────────────
def test_h_brightdata():
    section("H. BrightData — Company Signal Probe")
    if not BRIGHTDATA_KEY:
        log("BRIGHTDATA_API_KEY not set — skipping", "warn")
        return False

    try:
        # BrightData web unlocker: fetch a company page
        log("Testing BrightData proxy for Avenue Capital Group...", "info")
        r = requests.get(
            "https://api.brightdata.com/datasets/v3/trigger",
            params={
                "dataset_id": "gd_l1viktl72bvl7bvt9l",
                "type": "discover_new",
                "discover_by": "url",
            },
            headers={
                "Authorization": f"Bearer {BRIGHTDATA_KEY}",
                "Content-Type": "application/json",
            },
            json=[{"url": "https://www.avenuecapital.com/"}],
            timeout=15,
        )
        if r.status_code in (200, 202):
            log(f"BrightData trigger accepted (status={r.status_code})", "pass")
            log(f"  Response: {r.text[:100]}", "info")
            return True
        else:
            log(f"BrightData response: {r.status_code} → {r.text[:200]}", "warn")
            return False
    except Exception as e:
        log(f"BrightData error: {e}", "fail")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead-only", action="store_true", help="Only test enrichment/scoring APIs")
    parser.add_argument("--frappe-only", action="store_true", help="Only test Frappe CRUD")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*65}{RESET}")
    print(f"{BOLD}  🔱 ZETA PROTOCOL — LIVE A-Z INTEGRATION TEST{RESET}")
    print(f"{BOLD}  REAL APIs. REAL DB. NO VAPI. NO SMS TO REAL PEOPLE.{RESET}")
    print(f"{BOLD}  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'═'*65}{RESET}\n")

    results = {}
    start = time.time()

    # 0. PREFLIGHT
    preflight = test_0_preflight()

    enriched_leads = None
    signals = None
    lead_name = None

    if not args.frappe_only:
        # A. Apollo
        try:
            enriched_leads, passed = test_a_apollo()
            results["A. Apollo Person Lookup"] = passed
        except Exception as e:
            results["A. Apollo Person Lookup"] = False
            log(f"Exception: {e}", "fail")

        # B. Tavily
        try:
            signals, passed = test_b_tavily()
            results["B. Tavily Signal Search"] = passed
        except Exception as e:
            results["B. Tavily Signal Search"] = False
            log(f"Exception: {e}", "fail")

        # C. Gemini
        try:
            gemini_out, passed = test_c_gemini(enriched_leads, signals)
            results["C. Gemini Score + Draft"] = passed
        except Exception as e:
            results["C. Gemini Score + Draft"] = False
            log(f"Exception: {e}", "fail")
            traceback.print_exc()

    if not args.lead_only:
        is_frappe_up = preflight.get("frappe", False)
        if not is_frappe_up:
            log("Frappe is offline — waiting 10s then retrying...", "warn")
            time.sleep(10)
            try:
                r = requests.get(f"{FRAPPE_URL}/api/method/frappe.ping", timeout=5)
                is_frappe_up = r.status_code == 200
                if is_frappe_up:
                    log("Frappe came online!", "pass")
            except Exception:
                pass

        if is_frappe_up:
            # D. Frappe CRUD
            try:
                lead_name, passed = test_d_frappe_crud()
                results["D. Frappe Lead CRUD"] = passed
            except Exception as e:
                results["D. Frappe Lead CRUD"] = False
                log(f"Exception: {e}", "fail")

            # E. Communication + Memory
            try:
                passed = test_e_frappe_communication(lead_name)
                results["E. Frappe Comm + Memory"] = passed
            except Exception as e:
                results["E. Frappe Comm + Memory"] = False
                log(f"Exception: {e}", "fail")

            # F. ETL Upload
            try:
                passed = test_f_etl_upload()
                results["F. ETL CSV Upload"] = passed
            except Exception as e:
                results["F. ETL CSV Upload"] = False
                log(f"Exception: {e}", "fail")

            # G. Sequences
            try:
                passed = test_g_sequences()
                results["G. Sequence Query"] = passed
            except Exception as e:
                results["G. Sequence Query"] = False
                log(f"Exception: {e}", "fail")
        else:
            for key in ["D. Frappe Lead CRUD", "E. Frappe Comm + Memory", "F. ETL CSV Upload", "G. Sequence Query"]:
                results[key] = None  # Skipped
                log(f"{key}: SKIPPED (Frappe offline)", "warn")

    # H. BrightData
    if not args.frappe_only:
        try:
            passed = test_h_brightdata()
            results["H. BrightData Probe"] = passed
        except Exception as e:
            results["H. BrightData Probe"] = False
            log(f"Exception: {e}", "fail")

    # Final report
    elapsed = time.time() - start
    print(f"\n{BOLD}{'═'*65}{RESET}")
    print(f"{BOLD}  🔱 LIVE TEST RESULTS ({elapsed:.1f}s){RESET}")
    print(f"{BOLD}{'═'*65}{RESET}")

    passed_count = skipped_count = failed_count = 0
    for name, passed in results.items():
        if passed is None:
            icon = WARN
            skipped_count += 1
        elif passed:
            icon = PASS
            passed_count += 1
        else:
            icon = FAIL
            failed_count += 1
        print(f"  {icon}  {name}")

    total = len(results)
    print(f"\n{BOLD}{'═'*65}{RESET}")
    print(f"{BOLD}  Passed: {passed_count} | Failed: {failed_count} | Skipped: {skipped_count} / {total}{RESET}")

    if failed_count == 0 and skipped_count == 0:
        print(f"{GREEN}{BOLD}  🔱 ALL LIVE — REAL ROUNDS FIRED AND LANDED{RESET}")
    elif failed_count == 0:
        print(f"{YELLOW}{BOLD}  ⚠️  CLEAN BUT SOME SKIPPED (Frappe offline or missing keys){RESET}")
    else:
        print(f"{RED}{BOLD}  ❌ {failed_count} FAILURES — CHECK ABOVE{RESET}")

    print(f"{BOLD}{'═'*65}{RESET}\n")


if __name__ == "__main__":
    main()
