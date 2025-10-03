import os
import json
from pathlib import Path
from typing import Optional, Tuple
import httpx

_LOCK_PATH = None  # simple module-level lock placeholder if needed


def _secrets_dir() -> Path:
    here = Path(__file__).resolve()
    d = here.parent / ".secrets"
    if d.exists():
        return d
    # fallback to repo layout: eaia/.secrets
    return here.parent / "eaia" / ".secrets"


def _processed_store_path() -> Path:
    d = _secrets_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "processed_ids.json"


def _load_processed_ids() -> dict:
    p = _processed_store_path()
    if not p.exists():
        return {"message_ids": set(), "thread_ids": set(), "mapping": {}}
    try:
        data = json.loads(p.read_text() or "{}")
        return {
            "message_ids": set(data.get("message_ids", [])),
            "thread_ids": set(data.get("thread_ids", [])),
            "mapping": data.get("mapping", {}),
        }
    except Exception:
        return {"message_ids": set(), "thread_ids": set(), "mapping": {}}


def _save_processed_ids(store: dict) -> None:
    p = _processed_store_path()
    data = {
        "message_ids": sorted(list(store.get("message_ids", []))),
        "thread_ids": sorted(list(store.get("thread_ids", []))),
        "mapping": store.get("mapping", {}),
    }
    p.write_text(json.dumps(data))


def _is_processed(message_id: Optional[str], thread_id: Optional[str]) -> bool:
    store = _load_processed_ids()
    if message_id and message_id in store["message_ids"]:
        return True
    # optionally skip if thread already processed
    if thread_id and thread_id in store["thread_ids"]:
        return True
    return False


def _mark_processed(message_id: Optional[str], thread_id: Optional[str]) -> None:
    store = _load_processed_ids()
    if message_id:
        store["message_ids"].add(message_id)
    if thread_id:
        store["thread_ids"].add(thread_id)
    _save_processed_ids(store)


def _set_mapping(message_id: Optional[str], thread_id: Optional[str], communication_name: str) -> None:
    store = _load_processed_ids()
    mapping = store.get("mapping", {})
    if message_id:
        mapping[f"mid:{message_id}"] = communication_name
    if thread_id:
        mapping[f"tid:{thread_id}"] = communication_name
    store["mapping"] = mapping
    _save_processed_ids(store)


def get_communication_for_ids(message_id: Optional[str], thread_id: Optional[str]) -> Optional[str]:
    store = _load_processed_ids()
    mapping = store.get("mapping", {})
    if message_id and (cm := mapping.get(f"mid:{message_id}")):
        return cm
    if thread_id and (cm := mapping.get(f"tid:{thread_id}")):
        return cm
    return None


async def post_draft_with_provider(
    email: dict,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
):
    """Post draft to CRM using one-call endpoint based on email payload.

    Env overrides:
      CRM_SITE, CRM_KEY, CRM_SECRET, CRM_REF_DOCTYPE, CRM_REF_NAME
    """
    site = os.getenv("CRM_SITE")
    key = os.getenv("CRM_KEY")
    secret = os.getenv("CRM_SECRET")
    if not (site and key and secret):
        return None

    doct = reference_doctype or os.getenv("CRM_REF_DOCTYPE", "Contact")
    docn = reference_name or os.getenv("CRM_REF_NAME", "Fahad")

    subject = email.get("subject") or "(no subject)"
    from_email = email.get("from_email") or ""
    # Prefer explicit HTML if provided at send-time, else fall back to scraped page_content
    page_content = email.get("html") or email.get("page_content") or ""
    provider_message_id = email.get("id") or ""
    provider_thread_id = email.get("thread_id") or ""

    # Idempotency: skip if already processed
    if _is_processed(provider_message_id, provider_thread_id):
        return {"status": "skipped", "reason": "already processed"}

    payload = {
        "command": "email.draft_with_provider",
        "params": {
            "reference_doctype": doct,
            "reference_name": docn,
            "to": from_email,
            "subject": f"Re: {subject}",
            "html": page_content,
            "provider": "gmail",
            "provider_message_id": provider_message_id,
            "provider_thread_id": provider_thread_id,
        },
    }
    headers = {
        "Authorization": f"token {key}:{secret}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{site}/api/method/crm.api.agent.run", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        # Extract communication name from response
        comm_name = None
        msg = data.get("message") if isinstance(data, dict) else None
        if isinstance(msg, str):
            comm_name = msg
        elif isinstance(msg, dict):
            comm_name = msg.get("name") or msg.get("communication_name")
        if comm_name:
            try:
                _set_mapping(provider_message_id, provider_thread_id, comm_name)
            except Exception:
                pass
        try:
            _mark_processed(provider_message_id, provider_thread_id)
        except Exception:
            pass
        return data


async def send_communication(communication_name: str):
    """Trigger send for a Communication in CRM via agent.run."""
    site = os.getenv("CRM_SITE")
    key = os.getenv("CRM_KEY")
    secret = os.getenv("CRM_SECRET")
    if not (site and key and secret):
        return None
    payload = {
        "command": "email.send",
        "params": {"communication_name": communication_name},
    }
    headers = {
        "Authorization": f"token {key}:{secret}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{site}/api/method/crm.api.agent.run", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


