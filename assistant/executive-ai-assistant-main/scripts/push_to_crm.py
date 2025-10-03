#!/usr/bin/env python3
import os
import json
import argparse
import httpx

CRM_SITE = os.getenv("CRM_SITE", "https://jedilabs2.v.frappe.cloud")
CRM_KEY = os.getenv("CRM_KEY", "")
CRM_SECRET = os.getenv("CRM_SECRET", "")


def create_draft_with_provider(
    reference_doctype: str,
    reference_name: str,
    to: str,
    subject: str,
    html: str,
    provider: str | None = None,
    provider_message_id: str | None = None,
    provider_thread_id: str | None = None,
):
    url = f"{CRM_SITE}/api/method/crm.api.agent.run"
    headers = {
        "Authorization": f"token {CRM_KEY}:{CRM_SECRET}",
        "Content-Type": "application/json",
    }
    payload = {
        "command": "email.draft_with_provider",
        "params": {
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "to": to,
            "subject": subject,
            "html": html,
            "provider": provider,
            "provider_message_id": provider_message_id,
            "provider_thread_id": provider_thread_id,
        },
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doctype", required=True)
    parser.add_argument("--docname", required=True)
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--provider", default="gmail")
    parser.add_argument("--provider_message_id", default=None)
    parser.add_argument("--provider_thread_id", default=None)
    args = parser.parse_args()

    resp = create_draft_with_provider(
        reference_doctype=args.doctype,
        reference_name=args.docname,
        to=args.to,
        subject=args.subject,
        html=args.html,
        provider=args.provider,
        provider_message_id=args.provider_message_id,
        provider_thread_id=args.provider_thread_id,
    )
    print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()

