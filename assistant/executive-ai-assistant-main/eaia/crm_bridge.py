"""
EAIA -> CRM bridge
==================
Posts inbound-email drafts into the Frappe CRM (Human Inbox) and triggers sends,
all via the whitelisted crm.api.agent.run command router.

Hardened for a stateless Railway deployment:
  * Idempotency is DURABLE — the CRM (Communication.provider_message_id) is the
    source of truth, queried via email.find_by_provider_id. The local
    processed_ids.json is kept only as a best-effort fast-path cache and no
    longer the authority (Railway's filesystem is ephemeral across restarts).
  * Reference resolution is SMART — the sender email + in_reply_to are resolved
    server-side via email.resolve_reference (thread -> contact -> deal -> lead ->
    org -> optional auto-create), instead of a hardcoded contact name. The env
    default (CRM_REF_DOCTYPE/CRM_REF_NAME) is only a last-resort fallback.
  * Failures are LOGGED, not silently swallowed.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
import httpx

logger = logging.getLogger("eaia.crm_bridge")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
def _crm_conf():
    site = os.getenv("CRM_SITE")
    key = os.getenv("CRM_KEY")
    secret = os.getenv("CRM_SECRET")
    return site, key, secret


def _headers(key: str, secret: str) -> dict:
    return {
        "Authorization": f"token {key}:{secret}",
        "Content-Type": "application/json",
    }


async def _agent_run(command: str, params: dict) -> Optional[dict]:
    """Call crm.api.agent.run with a command + params. Returns parsed JSON or None."""
    site, key, secret = _crm_conf()
    if not (site and key and secret):
        logger.warning("CRM bridge not configured (CRM_SITE/CRM_KEY/CRM_SECRET missing)")
        return None
    payload = {"command": command, "params": params}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{site}/api/method/crm.api.agent.run", json=payload, headers=_headers(key, secret)
        )
        r.raise_for_status()
        return r.json()


def _unwrap(data: Optional[dict]):
    """agent.run wraps the return in {'message': ...}."""
    if not isinstance(data, dict):
        return data
    return data.get("message", data)


# ---------------------------------------------------------------------------
# local fast-path cache (NON-authoritative; ephemeral on Railway)
# ---------------------------------------------------------------------------
def _cache_path() -> Path:
    d = Path(__file__).resolve().parent / ".secrets"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug("cache dir unavailable: %s", e)
    return d / "processed_ids.json"


def _load_cache() -> dict:
    p = _cache_path()
    if not p.exists():
        return {"message_ids": set(), "thread_ids": set(), "mapping": {}}
    try:
        data = json.loads(p.read_text() or "{}")
        return {
            "message_ids": set(data.get("message_ids", [])),
            "thread_ids": set(data.get("thread_ids", [])),
            "mapping": data.get("mapping", {}),
        }
    except Exception as e:
        logger.debug("cache read failed: %s", e)
        return {"message_ids": set(), "thread_ids": set(), "mapping": {}}


def _save_cache(store: dict) -> None:
    try:
        _cache_path().write_text(
            json.dumps(
                {
                    "message_ids": sorted(store.get("message_ids", [])),
                    "thread_ids": sorted(store.get("thread_ids", [])),
                    "mapping": store.get("mapping", {}),
                }
            )
        )
    except Exception as e:
        logger.debug("cache write failed (expected on ephemeral FS): %s", e)


def _cache_mark(message_id: Optional[str], thread_id: Optional[str], comm_name: Optional[str]) -> None:
    store = _load_cache()
    if message_id:
        store["message_ids"].add(message_id)
    if thread_id:
        store["thread_ids"].add(thread_id)
    if comm_name:
        if message_id:
            store["mapping"][f"mid:{message_id}"] = comm_name
        if thread_id:
            store["mapping"][f"tid:{thread_id}"] = comm_name
    _save_cache(store)


def _cache_hit(message_id: Optional[str], thread_id: Optional[str]) -> bool:
    store = _load_cache()
    return bool(
        (message_id and message_id in store["message_ids"])
        or (thread_id and thread_id in store["thread_ids"])
    )


# ---------------------------------------------------------------------------
# durable idempotency (CRM is source of truth)
# ---------------------------------------------------------------------------
async def find_existing_communication(message_id: Optional[str], thread_id: Optional[str]) -> Optional[dict]:
    """Ask the CRM whether a draft already exists for these provider ids.

    Durable across restarts. Returns the Communication dict (name/reference/
    status) or None.
    """
    if not (message_id or thread_id):
        return None
    try:
        data = await _agent_run(
            "email.find_by_provider_id",
            {"provider_message_id": message_id, "provider_thread_id": thread_id},
        )
        return _unwrap(data)
    except Exception as e:
        logger.warning("provider-id lookup failed, falling back to local cache: %s", e)
        return None


async def get_communication_for_ids(message_id: Optional[str], thread_id: Optional[str]) -> Optional[str]:
    """Return the Communication name for these ids (server first, cache fallback)."""
    existing = await find_existing_communication(message_id, thread_id)
    if existing and existing.get("name"):
        return existing["name"]
    store = _load_cache()
    mapping = store.get("mapping", {})
    if message_id and (cm := mapping.get(f"mid:{message_id}")):
        return cm
    if thread_id and (cm := mapping.get(f"tid:{thread_id}")):
        return cm
    return None


# ---------------------------------------------------------------------------
# reference resolution (smart, server-side)
# ---------------------------------------------------------------------------
async def resolve_reference(from_email: str, in_reply_to: Optional[str] = None):
    """Resolve the CRM doc a draft should attach to, from the sender email.

    Returns (doctype, name). Falls back to env CRM_REF_DOCTYPE/CRM_REF_NAME
    only if the server cannot resolve anything.
    """
    try:
        data = await _agent_run(
            "email.resolve_reference",
            {"emails": [from_email] if from_email else [], "in_reply_to": in_reply_to},
        )
        res = _unwrap(data)
        if isinstance(res, dict) and res.get("doctype") and res.get("name"):
            return res["doctype"], res["name"]
    except Exception as e:
        logger.warning("resolve_reference failed, using env default: %s", e)
    # last-resort fallback
    return os.getenv("CRM_REF_DOCTYPE", "CRM Lead"), os.getenv("CRM_REF_NAME") or None


# ---------------------------------------------------------------------------
# public API (called by human_inbox.py / graph.py)
# ---------------------------------------------------------------------------
async def post_draft_with_provider(
    email: dict,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
):
    """Post an inbound-reply draft into the CRM Human Inbox.

    Idempotent (durable): if a Communication already exists for this provider
    message/thread id, returns it instead of creating a duplicate.
    """
    site, key, secret = _crm_conf()
    if not (site and key and secret):
        logger.warning("post_draft_with_provider: CRM bridge not configured")
        return None

    subject = email.get("subject") or "(no subject)"
    from_email = email.get("from_email") or ""
    page_content = email.get("html") or email.get("page_content") or ""
    provider_message_id = email.get("id") or ""
    provider_thread_id = email.get("thread_id") or ""
    in_reply_to = email.get("in_reply_to") or email.get("message_id") or None

    # 1) Durable idempotency — server first, cache as fast-path
    existing = await find_existing_communication(provider_message_id, provider_thread_id)
    if existing and existing.get("name"):
        _cache_mark(provider_message_id, provider_thread_id, existing["name"])
        return {"status": "skipped", "reason": "already processed", "communication_name": existing["name"]}
    if _cache_hit(provider_message_id, provider_thread_id):
        return {"status": "skipped", "reason": "already processed (cache)"}

    # 2) Smart reference resolution (unless caller pinned one)
    if reference_doctype and reference_name:
        doct, docn = reference_doctype, reference_name
    else:
        doct, docn = await resolve_reference(from_email, in_reply_to)
    if not docn:
        logger.error("post_draft_with_provider: could not resolve a CRM reference for %s", from_email)
        return {"status": "error", "reason": "unresolved_reference", "from_email": from_email}

    # 3) Create the draft
    params = {
        "reference_doctype": doct,
        "reference_name": docn,
        "to": from_email,
        "subject": f"Re: {subject}",
        "html": page_content,
        "provider": "gmail",
        "provider_message_id": provider_message_id,
        "provider_thread_id": provider_thread_id,
    }
    data = await _agent_run("email.draft_with_provider", params)
    msg = _unwrap(data)
    comm_name = None
    if isinstance(msg, str):
        comm_name = msg
    elif isinstance(msg, dict):
        comm_name = msg.get("communication_name") or msg.get("name")
    if comm_name:
        _cache_mark(provider_message_id, provider_thread_id, comm_name)
    else:
        logger.warning("draft created but no communication name returned: %r", data)
    return data


async def send_communication(communication_name: str):
    """Trigger send for a Communication in CRM via the send gate."""
    data = await _agent_run("email.send", {"communication_name": communication_name})
    return data
