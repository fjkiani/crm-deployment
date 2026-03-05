"""
Agent Zo: "The Integrator"
Mission: Sync verified intelligence into Frappe CRM (standard CRM Lead + FCRM Note).
"""
from __future__ import annotations
import logging
import os
import json
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

from eaia.agents.state import AgentState
from eaia.config import NyxConfig

# Load secrets relative to this file
params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".secrets", ".env"))
load_dotenv(params_path)

logger = logging.getLogger(__name__)


class CRMClient:
    """HTTP client for Frappe CRM REST API — targets standard CRM Lead doctype."""

    def __init__(self):
        frappe_url = NyxConfig.FRAPPE_URL
        # For DNS: crm.localhost doesn't resolve in Python, use 127.0.0.1
        # If NyxConfig.FRAPPE_URL is crm.localhost, replace hostname with 127.0.0.1 for internal access.
        parsed = urlparse(frappe_url)
        if parsed.hostname == "crm.localhost":
            self.base_url = parsed._replace(netloc=f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1").geturl()
            self.host = "crm.localhost" # Keep original host for HTTP Host header
        else:
            self.base_url = frappe_url
            self.host = parsed.hostname or "crm.localhost"

        self.api_key = os.getenv("FRAPPE_API_KEY")
        self.api_secret = os.getenv("FRAPPE_API_SECRET")
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Host": f"{self.host}:{parsed.port}" if parsed.port else self.host,
        }

    # ── CRM Lead upsert ──────────────────────────────────────────────────
    def upsert_lead(self, data: dict) -> str | None:
        """
        Creates or updates a standard CRM Lead.
        Uses email as the dedup key.
        Returns the CRM Lead name (e.g. 'LT-1772401234') or None.
        """
        if not self.api_key:
            logger.warning("mocking CRM sync (no keys)")
            return "MOCK_ID"

        try:
            email = data.get("email")
            if not email:
                logger.warning("No email — skipping CRM sync")
                return None

            # Check if lead already exists by email
            filters = json.dumps([["email", "=", email]])
            check_url = f"{self.base_url}/api/resource/CRM Lead?filters={filters}"
            resp = requests.get(check_url, headers=self.headers, timeout=10)
            existing = resp.json().get("data", [])

            if existing:
                doc_name = existing[0]["name"]
                update_url = f"{self.base_url}/api/resource/CRM Lead/{doc_name}"
                requests.put(update_url, headers=self.headers, json=data, timeout=10)
                logger.info(f"🔄 Zo Updated CRM Lead: {email} → {doc_name}")
                return doc_name
            else:
                create_url = f"{self.base_url}/api/resource/CRM Lead"
                # {in Zeta, asked by Alpha} 🔱
                # Purge Link validators.
                create_data = {
                    "lead_name":   data.get("lead_name", ""),
                    "first_name":  data.get("first_name") or (data.get("lead_name", "Unknown").split()[0]),
                    "last_name":   data.get("last_name", ""),
                    "email":       email,
                    "organization": data.get("organization", ""),
                    "mobile_no":   data.get("mobile_no", ""),
                    "job_title":   data.get("job_title", ""),
                    "website":     data.get("website", ""),
                    "status":      "New",
                }
                resp = requests.post(create_url, headers=self.headers, json=create_data, timeout=10)
                if resp.status_code == 200:
                    doc_name = resp.json()["data"]["name"]
                    logger.info(f"✨ Zo Created CRM Lead: {email} → {doc_name}")
                    return doc_name
                else:
                    logger.error(f"❌ Zo Create Failed ({resp.status_code}): {resp.text[:300]}")
                    return None



        except Exception as e:
            logger.error(f"❌ CRM Lead Error: {e}")
            return None

    # ── Legacy: still supported for backward compat ──────────────────────
    def upsert_prospect(self, data: dict) -> str | None:
        """Backward-compatible wrapper — maps Lead Prospect fields to CRM Lead."""
        lead_data = {
            "lead_name": data.get("pi_name", ""),
            "first_name": (data.get("pi_name") or "").split()[0] if data.get("pi_name") else "",
            "last_name": " ".join((data.get("pi_name") or "").split()[1:]) if data.get("pi_name") else "",
            "email": data.get("pi_email", ""),
            "organization": data.get("institution", ""),
            "source": data.get("source", "Nyx Pipeline"),
        }
        # Remove empty strings to avoid overwriting existing data
        lead_data = {k: v for k, v in lead_data.items() if v}
        return self.upsert_lead(lead_data)

    # ── FCRM Note (appears in "Notes" tab of CRM Lead) ──────────────────
    def create_note(self, lead_name: str, title: str, content: str, intel_data: dict = None) -> str | None:
        """
        Creates an FCRM Note linked to a CRM Lead.
        This shows up in the 'Notes' tab of the lead detail page.
        {in Zeta, asked by Alpha} 🔱
        """
        if not self.api_key:
            return "MOCK_NOTE"


        try:
            if intel_data:
                # Embed the raw intel JSON for the Cockpit to sniff.
                intel_block = f"\n<!-- NYX_INTEL_JSON\n{json.dumps(intel_data, indent=2)}\n-->"
                content += intel_block

            note_data = {
                "doctype": "FCRM Note",
                "title": title,
                "content": content,
                "reference_doctype": "CRM Lead",
                "reference_name": lead_name
            }
            url = f"{self.base_url}/api/resource/FCRM Note"
            resp = requests.post(url, headers=self.headers, json=note_data, timeout=10)
            if resp.status_code == 200:
                logger.debug(f"📝 Zo Created Note for {lead_name}")
                return resp.json()["data"]["name"]
            else:
                logger.error(f"❌ Note Error ({resp.status_code}): {resp.text[:300]}")
                return None
        except Exception as e:
            logger.error(f"❌ Note Exception: {e}")
            return None

    # ── Communication (appears in "Emails" tab of CRM Lead) ─────────────
    def create_communication(self, lead_name: str, sender: str, to_email: str,
                              subject: str, body: str) -> str | None:
        """
        Creates a Communication record linked to a CRM Lead.
        This shows up in the 'Emails' tab of the lead detail page.
        """
        if not self.api_key:
            return "MOCK_COMM"

        try:
            comm_data = {
                "doctype": "Communication",
                "communication_type": "Communication",
                "communication_medium": "Email",
                "sent_or_received": "Sent",
                "subject": subject,
                "content": body,
                "sender": sender,
                "recipients": to_email,
                "reference_doctype": "CRM Lead",
                "reference_name": lead_name,
                "status": "Linked",
            }
            url = f"{self.base_url}/api/resource/Communication"
            resp = requests.post(url, headers=self.headers, json=comm_data, timeout=10)
            if resp.status_code == 200:
                comm_id = resp.json()["data"]["name"]
                logger.info(f"📧 Communication logged on {lead_name}: {subject[:50]} → {comm_id}")
                return comm_id
            else:
                logger.warning(f"⚠️ Communication create failed ({resp.status_code}): {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"❌ Communication Error: {e}")
            return None

    # ── Sequence enrollment (still uses Lead Prospect for now) ───────────
    def create_sequence_instance(self, prospect_name: str, sequence_name: str):
        if not self.api_key:
            return
        try:
            data = {
                "prospect": prospect_name,
                "sequence": sequence_name,
                "status": "Active",
                "start_date": "2026-02-06"
            }
            url = f"{self.base_url}/api/resource/Outreach Sequence Instance"
            resp = requests.post(url, headers=self.headers, json=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"🧬 Sequence Started: {sequence_name} -> {prospect_name}")
            else:
                logger.warning(f"⚠️ Sequence Failed: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"❌ Sequence Error: {e}")


def zo_crm_sync(state: AgentState) -> AgentState:
    """
    Zo Node Logic:
    1. Iterate Safe Leads.
    2. Sync to CRM Lead.
    3. Trigger Sequence if applicable.
    """
    leads = state.get("leads", [])
    safe_ids = state.get("safe_lead_ids", [])
    scorecards = state.get("lead_scorecards", {})
    campaign = state.get("campaign", {})

    client = CRMClient()

    synced_count = 0
    safe_lead_objects = [l for l in leads if l["id"] in safe_ids]

    logger.info(f"🧠 Zo Syncing {len(safe_lead_objects)} leads to Frappe CRM...")

    for lead in safe_lead_objects:
        lead_id = lead["id"]
        score_data = scorecards.get(lead_id, {})
        score = score_data.get("total_score", 0)

        lead_data = {
            "lead_name": lead["name"],
            "first_name": lead["name"].split()[0] if lead.get("name") else "",
            "last_name": " ".join(lead["name"].split()[1:]) if lead.get("name") else "",
            "email": lead["email"],
            "organization": lead.get("organization_id", ""),
            # "source": "Nyx Pipeline", # Purged as per instruction
        }

        lead_name = client.upsert_lead(lead_data)

        if lead_name:
            tier = "Tier 1" if score > 75 else "Tier 2" if score > 40 else "Tier 3"
            client.create_note(
                lead_name,
                f"🎯 Kill Score: {score} ({tier})",
                f"**Score:** {score}/100 | **Tier:** {tier}\n\n"
                f"**Role:** {lead.get('role', 'Unknown')}\n\n"
                f"Harvested by EAIA Pipeline.",
                intel_data=lead # Pass the full lead object as intel_data
            )

        synced_count += 1

    return {
        "mission_status": "SYNCED",
        "messages": [{"role": "assistant", "content": f"Zo: Synced {synced_count} leads to CRM."}]
    }
