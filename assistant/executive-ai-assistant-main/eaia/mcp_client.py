"""
MCP Client — EAIA ↔ Frappe CRM Bridge via MCP Protocol
=======================================================
Calls any of the 22 Frappe MCP tools from the EAIA agent via Streamable HTTP.

Protocol: JSON-RPC 2.0
Endpoint: {FRAPPE_URL}/api/method/crm.api.mcp_server.handle_mcp
Auth:     token {API_KEY}:{API_SECRET}

Usage:
    from eaia.mcp_client import FrappeMCPClient
    client = FrappeMCPClient()
    dossier = await client.get_lead_dossier("LT-1772401234")
"""

import json
import logging
import os
import httpx

from eaia.config import NyxConfig

logger = logging.getLogger(__name__)


class FrappeMCPClient:
    """Async HTTP client for calling Frappe MCP tools."""

    def __init__(self):
        frappe_url = NyxConfig.FRAPPE_URL.rstrip("/")
        # DNS fix: crm.localhost doesn't resolve in Python — same as zo.py
        parsed = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(frappe_url)
        if parsed.hostname == "crm.localhost":
            base = parsed._replace(
                netloc=f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1"
            ).geturl().rstrip("/")
        else:
            base = frappe_url
        self.endpoint = f"{base}/api/method/crm.api.mcp_server.handle_mcp"

        api_key = os.getenv("FRAPPE_API_KEY", "")
        api_secret = os.getenv("FRAPPE_API_SECRET", "")
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
        }
        self._request_id = 0

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a Frappe MCP tool via JSON-RPC 2.0 over Streamable HTTP.

        Args:
            tool_name: Name of the registered MCP tool (e.g. 'get_lead_dossier')
            arguments: Dict of tool arguments

        Returns:
            Tool result dict (or error dict on failure)
        """
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": self._request_id,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint, json=payload, headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    logger.error(f"MCP tool '{tool_name}' error: {data['error']}")
                    return {"error": data["error"]}

                return data.get("result", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"MCP HTTP error calling '{tool_name}': {e.response.status_code}")
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Frappe MCP at {self.endpoint}")
            return {"error": f"Connection refused: {self.endpoint}"}
        except Exception as e:
            logger.error(f"MCP call_tool '{tool_name}' failed: {e}")
            return {"error": str(e)}

    # ══════════════════════════════════════════════════════════════════════════
    # Convenience wrappers — one per Frappe MCP tool category
    # ══════════════════════════════════════════════════════════════════════════

    # ── Lead Management ──────────────────────────────────────────────────────

    async def get_lead_dossier(self, lead_name: str) -> dict:
        """Fetch full lead intelligence dossier."""
        return await self.call_tool("get_lead_dossier", {"lead_name": lead_name})

    async def update_lead_context(self, lead_name: str, context: dict) -> dict:
        """Write enrichment data to CRM Lead's additional_data JSON."""
        return await self.call_tool("update_lead_context", {
            "lead_name": lead_name,
            "context_json": json.dumps(context) if isinstance(context, dict) else context,
        })

    async def search_leads(self, query: str, status: str = "", limit: int = 20) -> dict:
        """Search CRM for leads by name, company, or status."""
        return await self.call_tool("search_leads", {
            "query": query, "status": status, "limit": limit,
        })

    async def create_lead(self, data: dict) -> dict:
        """Create a new CRM Lead."""
        return await self.call_tool("create_lead", data)

    async def cleanup_leads(self, older_than_days: int = 90) -> dict:
        """Remove stale/dead leads older than N days."""
        return await self.call_tool("cleanup_leads", {"older_than_days": older_than_days})

    # ── Intelligence ─────────────────────────────────────────────────────────

    async def get_portfolio_links(self, organization: str, email_domain: str = None) -> dict:
        """Find other CRM Leads connected to the same organization or email domain."""
        return await self.call_tool("get_portfolio_links", {
            "organization": organization,
            "email_domain": email_domain
        })

    # ── Analytics ────────────────────────────────────────────────────────────

    async def get_pipeline_analytics(self) -> dict:
        """Fetch pipeline health and A/B test framework metrics."""
        return await self.call_tool("get_pipeline_analytics", {})

    async def create_note(self, lead_name: str, title: str, content: str) -> dict:
        """Create an FCRM Note on a CRM Lead (appears in timeline)."""
        return await self.call_tool("create_note", {
            "lead_name": lead_name, "title": title, "content": content,
        })

    async def update_lead_score(self, lead_name: str, score: int, reasoning: str = "") -> dict:
        """Update lead_score field on CRM Lead."""
        return await self.call_tool("update_lead_score", {
            "lead_name": lead_name, "score": score, "reasoning": reasoning,
        })

    async def get_enrichment_status(self) -> dict:
        """Health check: leads with intel vs. missing."""
        return await self.call_tool("get_enrichment_status", {})

    async def get_communication_history(self, lead_name: str, limit: int = 20) -> dict:
        """Fetch email/call communication history for a lead."""
        return await self.call_tool("get_communication_history", {
            "lead_name": lead_name, "limit": limit,
        })

    # ── Outreach ─────────────────────────────────────────────────────────────

    async def approve_and_send(
        self, lead_name: str, to_email: str, subject: str, body: str
    ) -> dict:
        """Approve and log an email as Communication in CRM."""
        return await self.call_tool("approve_and_send", {
            "lead_name": lead_name, "to_email": to_email,
            "subject": subject, "body": body,
        })

    async def fire_sequence_step(self, lead_name: str, dry_run: bool = True) -> dict:
        """Fire the next sequence step for a lead."""
        return await self.call_tool("fire_sequence_step", {
            "lead_name": lead_name, "dry_run": dry_run,
        })

    async def get_sequence_status(self, lead_name: str) -> dict:
        """Get current sequence state for a lead."""
        return await self.call_tool("get_sequence_status", {"lead_name": lead_name})

    async def pause_sequence(self, lead_name: str, reason: str = "") -> dict:
        """Pause the outreach sequence for a lead."""
        return await self.call_tool("pause_sequence", {
            "lead_name": lead_name, "reason": reason,
        })

    async def classify_and_route_reply(
        self, from_email: str, subject: str, body: str
    ) -> dict:
        """Classify an inbound reply: INTERESTED/NOT_INTERESTED/OOO/UNSUBSCRIBE."""
        return await self.call_tool("classify_and_route_reply", {
            "from_email": from_email, "subject": subject, "body": body,
        })

    # ── Scheduling ───────────────────────────────────────────────────────────

    async def log_call_outcome(
        self, lead_name: str, outcome: str, notes: str = ""
    ) -> dict:
        """Log a voice call outcome to CRM."""
        return await self.call_tool("log_call_outcome", {
            "lead_name": lead_name, "outcome": outcome, "notes": notes,
        })

    async def get_lead_status_snapshot(self, lead_name: str) -> dict:
        """Compact real-time lead status: status, email count, call count."""
        return await self.call_tool("get_lead_status_snapshot", {"lead_name": lead_name})

    # ── Nyx Field Sync (writes to real Frappe custom fields) ─────────────────

    async def sync_nyx_fields(self, lead_name: str, enrichment_result: dict) -> dict:
        """Sync enrichment results to dedicated Frappe custom fields on CRM Lead.

        This writes to REAL Frappe fields (created by add_nyx_custom_fields.py),
        not to the additional_data JSON blob. This enables native Frappe
        filtering, list views, and reporting on Nyx data.

        Args:
            lead_name: CRM Lead ID
            enrichment_result: Dict from run_enrichment() with score, framework, etc.
        """
        from datetime import datetime

        fields = {
            "nyx_enriched": 1,
            "nyx_score": enrichment_result.get("score", 0),
            "nyx_framework": enrichment_result.get("framework", ""),
            "lead_score": enrichment_result.get("score", 0),  # legacy alias
            "email_status": enrichment_result.get("email_status", ""),
            "nyx_signal_gate": "FAIL" if enrichment_result.get("quarantined") else "PASS",
            "nyx_quarantine_reason": enrichment_result.get("quarantine_reason", ""),
            "nyx_last_pipeline_run": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "nyx_sources_used": ",".join(enrichment_result.get("enrichment_sources_used", [])) if isinstance(enrichment_result.get("enrichment_sources_used"), list) else enrichment_result.get("enrichment_sources_used", ""),
            "nyx_detected_context": ",".join(enrichment_result.get("detected_context", [])) if isinstance(enrichment_result.get("detected_context"), list) else enrichment_result.get("detected_context", ""),
        }

        # Store full enrichment JSON
        try:
            fields["nyx_enrichment_json"] = json.dumps(enrichment_result, default=str)[:65535]
        except Exception:
            fields["nyx_enrichment_json"] = ""

        # Write via Frappe REST API (direct field update, not MCP)
        frappe_url = NyxConfig.FRAPPE_URL.rstrip("/")
        parsed = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(frappe_url)
        if parsed.hostname == "crm.localhost":
            base = parsed._replace(
                netloc=f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1"
            ).geturl().rstrip("/")
        else:
            base = frappe_url

        url = f"{base}/api/resource/CRM Lead/{lead_name}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.put(url, json=fields, headers=self.headers)
                if resp.status_code == 200:
                    logger.info(f"✅ Nyx fields synced for {lead_name}: score={fields['nyx_score']}, gate={fields['nyx_signal_gate']}")
                    return {"synced": True, "fields": list(fields.keys())}
                else:
                    logger.error(f"Nyx field sync failed for {lead_name}: {resp.status_code} {resp.text[:200]}")
                    return {"synced": False, "error": resp.text[:200]}
        except Exception as e:
            logger.error(f"Nyx field sync error for {lead_name}: {e}")
            return {"synced": False, "error": str(e)}

