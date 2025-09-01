#!/usr/bin/env python3
import os
import sys
import json
import time
import requests

SITE = os.getenv("SITE", "https://jedilabs2.v.frappe.cloud")
KEY = os.getenv("KEY", "")
SECRET = os.getenv("SECRET", "")
DOC = os.getenv("DOC", "Contact")
NAME = os.getenv("NAME", "Fahad")
TO = os.getenv("TO", "fjkiani1@gmail.com")

HEADERS = {"Authorization": f"token {KEY}:{SECRET}", "Content-Type": "application/json"}


def call(method, payload):
    url = f"{SITE}/api/method/{method}"
    r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    print("E2E: draft_with_provider → send → verify")
    # 1) Create draft
    payload = {
        "command": "email.draft_with_provider",
        "params": {
            "reference_doctype": DOC,
            "reference_name": NAME,
            "to": TO,
            "subject": "E2E Flow Test",
            "html": "<p>E2E flow body</p>",
            "provider": "gmail",
            "provider_message_id": "e2e_msg",
            "provider_thread_id": "e2e_thread"
        },
    }
    draft = call("crm.api.agent.run", payload)
    comm = (draft.get("message") or {}).get("communication_name") or draft.get("message")
    print("Draft:", comm)
    assert comm, "No communication created"
    # 2) Send
    send = call("crm.api.agent.run", {"command": "email.send", "params": {"communication_name": comm}})
    print("Send:", send)
    assert (send.get("message") or {}).get("ok"), "Send failed"
    print("E2E OK")


if __name__ == "__main__":
    success = False
    try:
        main()
        success = True
    except Exception as e:
        print("E2E failed:", e)
    sys.exit(0 if success else 1)
