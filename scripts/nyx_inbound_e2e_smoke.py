#!/usr/bin/env python3
"""NYX inbound E2E smoke test against a live Frappe site.

Usage:
  export FRAPPE_SITE=https://alpha-crm.v.frappe.cloud
  export FRAPPE_TOKEN="api_key:api_secret"
  python3 scripts/nyx_inbound_e2e_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

SITE = os.environ.get("FRAPPE_SITE", "https://alpha-crm.v.frappe.cloud").rstrip("/")
TOKEN = os.environ.get("FRAPPE_TOKEN", "")
LEAD = os.environ.get("NYX_TEST_LEAD", "CRM-LEAD-2026-00908")
SENDER = os.environ.get("NYX_TEST_SENDER", "robinkim1@gmail.com")

if not TOKEN:
    print("Set FRAPPE_TOKEN=api_key:api_secret", file=sys.stderr)
    sys.exit(1)

H = {"Authorization": f"token {TOKEN}", "Content-Type": "application/json"}


def call(method: str, data: dict | None = None, timeout: int = 180):
    req = urllib.request.Request(
        f"{SITE}/api/method/{method}",
        json.dumps(data or {}).encode(),
        headers=H,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.load(r)
        if body.get("exc"):
            raise RuntimeError(body["exc"][:1200])
        return body.get("message")


def main() -> int:
    tag = uuid.uuid4().hex[:8]
    print(f"=== NYX inbound E2E smoke ({tag}) ===")

    inbound = call("crm.api.nyx_inbound.get_inbound_status")
    brain = call("crm.api.nyx_email_brain.brain_status")
    print("inbound:", json.dumps(inbound, indent=2))
    print("brain:", json.dumps(brain, indent=2))

    if not inbound.get("autopilot"):
        print("FAIL: nyx_inbound_autopilot is off")
        return 1
    if not inbound.get("incoming_configured"):
        print("FAIL: no incoming Email Account")
        return 1
    if not brain.get("ok"):
        print("FAIL: brain not ready")
        return 1

    incoming_subject = f"NYX E2E inbound {tag}"
    incoming_body = (
        f"Hi — we're evaluating genomic stratification for our Phase 3 trial. "
        f"Can we schedule a call next week? [{tag}]"
    )
    comm_doc = {
        "doctype": "Communication",
        "communication_type": "Communication",
        "communication_medium": "Email",
        "sent_or_received": "Received",
        "subject": incoming_subject,
        "sender": SENDER,
        "recipients": "fahad@crispro.ai",
        "content": incoming_body,
        "reference_doctype": "CRM Lead",
        "reference_name": LEAD,
        "status": "Linked",
    }
    inserted = call("frappe.client.insert", {"doc": comm_doc})
    comm_name = inserted.get("name")
    print(f"inserted inbound Communication: {comm_name}")

    # Hook runs async via enqueue; also call triage directly for deterministic smoke.
    incoming = f"Subject: {incoming_subject}\n\n{incoming_body}"
    triage = call(
        "crm.api.nyx_email_brain.triage_and_draft",
        {"lead_name": LEAD, "incoming": incoming, "force": 1},
    )
    print("triage:", json.dumps(triage, indent=2))
    if triage.get("decision") != "drafted":
        print(f"FAIL: expected drafted, got {triage.get('decision')}")
        return 1

    draft_name = triage.get("communication")
    filters = json.dumps([
        ["reference_doctype", "=", "CRM Lead"],
        ["reference_name", "=", LEAD],
        ["name", "=", draft_name],
    ])
    fields = json.dumps(["name", "subject", "status", "sent_or_received", "recipients"])
    url = SITE + "/api/resource/Communication?" + urllib.parse.urlencode(
        {"filters": filters, "fields": fields, "limit_page_length": 1}
    )
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}"}), timeout=30) as r:
        rows = json.load(r).get("data", [])
    print("draft row:", json.dumps(rows, indent=2))
    if not rows:
        print("FAIL: draft Communication not found")
        return 1

    print("PASS: inbound -> triage -> draft verified")
    print(f"Human Inbox: {SITE}/human_inbox?doctype=CRM%20Lead&docname={LEAD}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        print("HTTP error:", e.read().decode()[:1500], file=sys.stderr)
        raise SystemExit(1)
