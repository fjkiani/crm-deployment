#!/usr/bin/env python3
import os
import json
import argparse
import asyncio
import httpx
from eaia.gmail import fetch_group_emails
from eaia.main.config import get_config

CRM_SITE = os.getenv("CRM_SITE", "https://jedilabs2.v.frappe.cloud")
CRM_KEY = os.getenv("CRM_KEY", "")
CRM_SECRET = os.getenv("CRM_SECRET", "")

async def post_draft(doct, docname, to, subject, html, provider, provider_message_id, provider_thread_id):
    url = f"{CRM_SITE}/api/method/crm.api.agent.run"
    headers = {
        "Authorization": f"token {CRM_KEY}:{CRM_SECRET}",
        "Content-Type": "application/json",
    }
    payload = {
        "command": "email.draft_with_provider",
        "params": {
            "reference_doctype": doct,
            "reference_name": docname,
            "to": to,
            "subject": subject,
            "html": html,
            "provider": provider,
            "provider_message_id": provider_message_id,
            "provider_thread_id": provider_thread_id,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()

async def main(minutes_since: int, reference_doctype: str, reference_name: str, provider: str):
    email_address = get_config({"configurable": {}})["email"]
    print(f"Fetching recent emails for {email_address} ({minutes_since}m)...")
    count = 0
    async for email in fetch_group_emails(email_address, minutes_since=minutes_since):
        count += 1
        subject = email.get("subject") or "(no subject)"
        to_addr = email.get("to_email") or email_address
        html = email.get("page_content") or ""
        msg_id = email.get("id") or ""
        thread_id = email.get("thread_id") or ""
        print(f"Posting draft {count}: {subject}")
        try:
            resp = await post_draft(
                reference_doctype, reference_name, to_addr, f"Re: {subject}", html,
                provider, msg_id, thread_id,
            )
            print("  ->", json.dumps(resp))
        except Exception as e:
            print("  !! error:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes-since", type=int, default=60)
    parser.add_argument("--doctype", type=str, default="Contact")
    parser.add_argument("--docname", type=str, default="Fahad")
    parser.add_argument("--provider", type=str, default="gmail")
    args = parser.parse_args()
    asyncio.run(main(args.minutes_since, args.doctype, args.docname, args.provider))

