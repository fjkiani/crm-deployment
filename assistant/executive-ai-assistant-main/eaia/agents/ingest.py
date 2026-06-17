"""
Agent Zi: "The Ingestor"
Mission: Let the agent framework autonomously ingest an arbitrary structured
dataset into the CRM via the app's native, server-side agentic-ingest kernel
(`crm.api.leadgen.run_dataset_ingest`).

Design (locked decisions):
  • Target doctype defaults to **Lead Prospect** (staging), not CRM Lead — AACR-type
    scientific datasets are staged, then promoted deliberately.
  • The mapping **kernel lives in `crm/api`** (deterministic Tier-1 + LLM Tier-2);
    this eaia layer only **invokes** it and supplies the LLM brain.
  • **Propose-and-pause, then auto-reuse**: a never-seen schema stops at
    `stage="mapping_review"` for human approval of the CRM Import Column Map;
    once approved, the saved profile is auto-reused on subsequent ingests.

LLM brain — two honest paths, no hidden coupling:
  1. server-side (default here): we call the whitelisted method with `use_llm=1`,
     so the kernel builds its OWN Gemini callable in the Frappe process. This is
     the path that works without shipping a Python callable across processes.
  2. in-process: `build_llm_complete()` returns the same Gemini callable for a
     same-process caller (e.g. a `bench execute` script) to inject as
     `_llm_complete` — exposed for completeness/testing.

NOTE on transport: like the other eaia agents (see zo.py::CRMClient), this node
reaches Frappe over the REST API using `token {key}:{secret}` auth. On deployments
where that token path is intercepted (the known Frappe Cloud header-stripping
issue), trigger `run_dataset_ingest` server-side instead (UI button / bench /
scheduled job) — the kernel and its `use_llm` brain are identical either way.
"""
from __future__ import annotations
import logging
import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

from eaia.agents.state import AgentState
from eaia.config import NyxConfig

params_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".secrets", ".env"))
load_dotenv(params_path)

logger = logging.getLogger(__name__)

DEFAULT_TARGET_DOCTYPE = "Lead Prospect"


# ── eaia-side LLM brain (in-process injection path) ──────────────────────────
def build_llm_complete(model: str = "gemini-1.5-pro", temperature: float = 0.0):
    """Return an `llm_complete(prompt) -> str` callable backed by Gemini, or None.

    Mirrors the eaia LLM pattern (ChatGoogleGenerativeAI, temperature 0). Used
    when a SAME-PROCESS caller wants to inject the Tier-2 brain directly as
    `_llm_complete`. Returns None if the dependency or API key is unavailable,
    so callers can fall back to the server-side `use_llm=1` path.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        logger.warning("langchain_google_genai not available — Tier-2 LLM disabled in-process")
        return None
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No GOOGLE_API_KEY/GEMINI_API_KEY — Tier-2 LLM disabled in-process")
        return None
    llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)

    def _complete(prompt: str) -> str:
        return llm.invoke(prompt).content

    return _complete


# ── Transport to the server-side kernel ──────────────────────────────────────
class IngestClient:
    """HTTP client for the app's agentic-ingest kernel (whitelisted methods)."""

    def __init__(self):
        frappe_url = NyxConfig.FRAPPE_URL
        parsed = urlparse(frappe_url)
        if parsed.hostname == "crm.localhost":
            self.base_url = parsed._replace(
                netloc=f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1"
            ).geturl()
            self.host = "crm.localhost"
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

    def run_dataset_ingest(
        self,
        target_doctype: str = DEFAULT_TARGET_DOCTYPE,
        file_url: str | None = None,
        records_json: str | None = None,
        profile_name: str | None = None,
        array_policy: str = "join",
        dry_run: int = 1,
        auto_approve_deterministic: int = 0,
        use_llm: int = 1,
    ) -> dict | None:
        """Call `crm.api.leadgen.run_dataset_ingest` (server-side kernel).

        use_llm=1 → the kernel builds its own server-side Gemini callable for
        Tier-2 (no Python callable crosses the wire). Returns the kernel's result
        dict (`stage="mapping_review"` when paused, or `stage="imported"`), or a
        mock when no API keys are configured.
        """
        if not self.api_key:
            logger.warning("mocking ingest (no Frappe API keys)")
            return {"stage": "mock", "target_doctype": target_doctype, "dry_run": bool(dry_run)}

        payload = {
            "target_doctype": target_doctype,
            "array_policy": array_policy,
            "dry_run": int(dry_run),
            "auto_approve_deterministic": int(auto_approve_deterministic),
            "use_llm": int(use_llm),
        }
        if file_url:
            payload["file_url"] = file_url
        if records_json:
            payload["records_json"] = records_json
        if profile_name:
            payload["profile_name"] = profile_name

        url = f"{self.base_url}/api/method/crm.api.leadgen.run_dataset_ingest"
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=600)
            if resp.status_code == 200:
                return resp.json().get("message", resp.json())
            logger.error(f"❌ run_dataset_ingest failed ({resp.status_code}): {resp.text[:400]}")
            return {"stage": "error", "status_code": resp.status_code, "detail": resp.text[:400]}
        except Exception as e:
            logger.error(f"❌ run_dataset_ingest exception: {e}")
            return {"stage": "error", "detail": str(e)}


# ── LangGraph node ───────────────────────────────────────────────────────────
def zi_ingest_agent(state: AgentState) -> AgentState:
    """Zi Node Logic — autonomous dataset ingest into the staging doctype.

    Reads the ingest request from state:
        ingest_file_url        : File URL of the dataset to ingest (JSON or CSV)
        ingest_records_json    : inline JSON array (alternative to file_url)
        ingest_target_doctype  : defaults to "Lead Prospect"
        ingest_dry_run         : defaults to 1 (validate first, never blind-write)
        ingest_profile_name    : optional explicit CRM Import Column Map name

    Returns the kernel result on `state["ingest_result"]` and sets mission_status:
        INGEST_REVIEW   — propose-and-pause: a new schema needs mapping approval
        INGEST_DRY_RUN  — dry-run import completed (no rows persisted)
        INGEST_DONE     — rows committed to the target doctype
        INGEST_NOOP     — nothing to ingest
        INGEST_ERROR    — kernel/transport error
    """
    file_url = state.get("ingest_file_url")
    records_json = state.get("ingest_records_json")
    if not file_url and not records_json:
        logger.info("Zi: no ingest_file_url / ingest_records_json in state — skipping")
        return {
            "mission_status": "INGEST_NOOP",
            "messages": [{"role": "assistant", "content": "Zi: nothing to ingest."}],
        }

    target = state.get("ingest_target_doctype", DEFAULT_TARGET_DOCTYPE)
    dry_run = int(state.get("ingest_dry_run", 1))
    profile_name = state.get("ingest_profile_name")

    logger.info(f"📥 Zi ingesting dataset → {target} (dry_run={dry_run}, LLM Tier-2 server-side)")

    client = IngestClient()
    result = client.run_dataset_ingest(
        target_doctype=target,
        file_url=file_url,
        records_json=records_json,
        profile_name=profile_name,
        dry_run=dry_run,
        use_llm=1,  # kernel uses its own server-side Gemini brain for Tier-2
    ) or {}

    stage = result.get("stage")
    if stage == "mapping_review":
        status, msg = "INGEST_REVIEW", (
            f"Zi: proposed a mapping for a new schema → {target}. "
            f"Approve CRM Import Column Map '{result.get('profile')}' then re-run. "
            f"(Tier-1 hits: {result.get('tier1_count')}, LLM hits: {result.get('tier2_llm_count')})"
        )
    elif stage == "imported" and dry_run:
        status, msg = "INGEST_DRY_RUN", (
            f"Zi: dry-run import OK → {target}. "
            f"{result.get('processed_rows')}/{result.get('total_rows')} rows would upsert."
        )
    elif stage == "imported":
        status, msg = "INGEST_DONE", (
            f"Zi: committed {result.get('processed_rows')}/{result.get('total_rows')} "
            f"rows → {target}."
        )
    elif stage == "mock":
        status, msg = "INGEST_NOOP", "Zi: ingest mocked (no Frappe API keys configured)."
    else:
        status, msg = "INGEST_ERROR", f"Zi: ingest error → {result.get('detail') or result}"

    logger.info(msg)
    return {
        "ingest_result": result,
        "mission_status": status,
        "messages": [{"role": "assistant", "content": msg}],
    }
