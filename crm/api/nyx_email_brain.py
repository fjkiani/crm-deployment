# crm/api/nyx_email_brain.py
"""
NYX Email Brain — runtime-swappable orchestrator for the outreach HITL loop.

Ask #1 (Human Inbox) implemented "within frappe" but kept SWAPPABLE:

    triage -> draft -> human-approve (Human Inbox) -> send

Two interchangeable backends behind ONE public API, selected by config key
`nyx_email_brain` (site_config.json or CRM Global Settings):

  * "frappe"  (default) — pure Frappe server-side. Reuses the already-deployed
                primitives: LLM via crm.api.etl_json._default_llm_complete /
                _openrouter_complete, drafts via crm.api.email.save_draft_with_provider,
                send via crm.api.email.send (frappe.sendmail). No external service.
  * "eaia"    — proxy to the standalone LangGraph EAIA service at $EAIA_URL
                (the container defined by Dockerfile.eaia / eaia/main/graph.py).
                Lets the same logic lift back out to Railway/Render unchanged.

The public whitelisted functions never change signature, so the front-end and
schedulers are runtime-agnostic. Switching backend is a one-key config change.
"""

from __future__ import annotations

import json
import os
import frappe
from frappe import _


# ────────────────────────────────────────────────────────────────────────────
# Backend selection
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_BACKEND = "frappe"


# Password-type fields on Nyx Brain Settings that must be read via get_password()
# (stored encrypted). Any other field is read as a plain attribute.
_NBS_PASSWORD_FIELDS = {"openrouter_api_key", "google_api_key"}


def _nyx_brain_settings_value(name: str):
    """Read a single value from the Nyx Brain Settings single doctype, or None.

    This is the highest-priority config source so a change made from the CRM UI
    (crm.api.nyx_email_brain.set_brain_settings) wins over stale env / site_config
    and persists in the DB across Frappe Cloud redeploys.
    """
    try:
        if not frappe.db.exists("DocType", "Nyx Brain Settings"):
            return None
        doc = frappe.get_single("Nyx Brain Settings")
        if not hasattr(doc, name):
            return None
        if name in _NBS_PASSWORD_FIELDS:
            # get_password decrypts; returns None/"" when unset.
            try:
                v = doc.get_password(name, raise_exception=False)
            except Exception:
                v = None
            return v or None
        v = getattr(doc, name)
        return v or None
    except Exception:
        return None


def _get_conf(*names, default=None):
    """Resolve a config value from Nyx Brain Settings, site_config, env, or CRM
    Global Settings — in that priority order.

    Nyx Brain Settings (DB, UI-editable) wins so provider/model/key changes made
    in the CRM take effect immediately and survive redeploys. Site config then
    wins over env so Frappe Cloud Site Config edits take effect even when the
    bench carries a stale OPENROUTER_API_KEY (or similar) in env.
    """
    # 1) Nyx Brain Settings single doctype (UI-editable, DB-persisted).
    for n in names:
        v = _nyx_brain_settings_value(n.lower())
        if v:
            return v
    # 2) site_config.json
    for n in names:
        v = frappe.conf.get(n.lower())
        if v:
            return v
    # 3) environment
    for n in names:
        v = os.getenv(n.upper())
        if v:
            return v
    # 4) CRM Global Settings single doctype (native, editable from /app)
    try:
        if frappe.db.exists("DocType", "CRM Global Settings"):
            gs = frappe.get_single("CRM Global Settings")
            for n in names:
                if hasattr(gs, n.lower()) and getattr(gs, n.lower()):
                    return getattr(gs, n.lower())
    except Exception:
        logger.debug("nyx_email_brain._get_conf: CRM Global Settings lookup failed for %s", names, exc_info=True)
    return default


def get_backend() -> str:
    """Which email-brain backend is active. 'frappe' (default) or 'eaia'."""
    b = (_get_conf("nyx_email_brain", default=DEFAULT_BACKEND) or DEFAULT_BACKEND).strip().lower()
    return b if b in ("frappe", "eaia") else DEFAULT_BACKEND


# ────────────────────────────────────────────────────────────────────────────
# Public API (runtime-agnostic) — whitelisted
# ────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def brain_status() -> dict:
    """Report active backend + reachability so the UI can show a truthful state."""
    backend = get_backend()
    out = {"backend": backend, "ok": False, "detail": ""}
    if backend == "eaia":
        url = _get_conf("eaia_url", default="")
        out["eaia_url"] = url
        if not url:
            out["detail"] = "EAIA backend selected but EAIA_URL is not set."
            return out
        out["ok"], out["detail"] = _eaia_healthcheck(url)
        return out
    # frappe backend — check LLM availability
    llm = _resolve_llm()
    out["ok"] = llm is not None
    out["detail"] = "Frappe-native brain ready." if llm else \
        "No LLM provider configured (set openrouter_api_key or google_api_key)."
    out["llm_provider"] = _active_llm_provider()
    return out


# ────────────────────────────────────────────────────────────────────────────
# LLM provider/model settings (UI-editable, DB-persisted via Nyx Brain Settings)
# ────────────────────────────────────────────────────────────────────────────

# Static catalog surfaced to the settings UI. OpenRouter ids are free-text too,
# but these are the vetted defaults. gemma-3-27b-it is the reliable default;
# gpt-oss-20b:free hits the free-model daily rate limit (429) on shared keys.
_PROVIDER_CATALOG = {
    "openrouter": {
        "label": "OpenRouter",
        "key_field": "openrouter_api_key",
        "key_hint": "sk-or-...",
        "models": [
            {"id": "google/gemma-3-27b-it", "label": "Gemma 3 27B (recommended, reliable)"},
            {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "label": "Nemotron 70B (NVIDIA)"},
            {"id": "openai/gpt-oss-20b", "label": "GPT-OSS 20B"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "label": "Llama 3.3 70B"},
        ],
    },
    "gemini": {
        "label": "Google Gemini",
        "key_field": "google_api_key",
        "key_hint": "AIza...",
        "models": [
            {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
        ],
    },
}
# NOTE: only providers with a real backend completion path appear above.
# _active_llm_provider() dispatches on this catalog, so an entry here without a
# working seam would advertise a capability the server cannot honour. Add a new
# provider only together with its completion function and _ALLOWED_WRITE_PROVIDERS entry.

_ALLOWED_WRITE_PROVIDERS = {"openrouter", "gemini"}


def _require_brain_settings_perm():
    """Only managers may read/write LLM provider settings (keys are sensitive)."""
    roles = set(frappe.get_roles())
    if not ({"System Manager", "Sales Manager"} & roles):
        frappe.throw(
            _("You do not have permission to view or change Nyx model settings."),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_brain_settings() -> dict:
    """Return the current provider/model + whether keys are set (never the keys
    themselves) plus the provider catalog for the settings UI. Manager-gated."""
    _require_brain_settings_perm()
    provider = _active_llm_provider()  # what will actually run right now
    configured_provider = (_get_conf("llm_provider", default="") or "").strip().lower()
    model = _get_conf("openrouter_enrichment_model", "openrouter_model",
                      default="google/gemma-3-27b-it")
    return {
        "ok": True,
        "active_provider": provider,               # resolved (by key presence)
        "configured_provider": configured_provider,  # explicit setting, if any
        "openrouter_model": model,
        "has_openrouter_key": bool(_get_conf("openrouter_api_key")),
        "has_google_key": bool(_get_conf("google_api_key", "gemini_api_key")),
        "eaia_url": _get_conf("eaia_url", default="") or "",
        "backend": get_backend(),
        "provider_catalog": _PROVIDER_CATALOG,
    }


@frappe.whitelist()
def set_brain_settings(llm_provider: str | None = None,
                       openrouter_model: str | None = None,
                       openrouter_api_key: str | None = None,
                       google_api_key: str | None = None,
                       eaia_url: str | None = None) -> dict:
    """Write LLM provider settings into the Nyx Brain Settings single doctype.

    Blank/omitted values are LEFT UNCHANGED (so editing only the model does not
    wipe an existing key). Keys are stored encrypted (Password fieldtype) and are
    never echoed back. Manager-gated. Returns the same shape as get_brain_settings.
    """
    _require_brain_settings_perm()

    doc = frappe.get_single("Nyx Brain Settings")

    if llm_provider is not None:
        p = (llm_provider or "").strip().lower()
        if p and p not in _ALLOWED_WRITE_PROVIDERS:
            frappe.throw(_("Unsupported provider: {0}").format(p))
        if p:
            doc.llm_provider = p

    # Plain (non-secret) fields: empty string means "clear", None means "leave".
    if openrouter_model is not None and openrouter_model.strip():
        doc.openrouter_model = openrouter_model.strip()
    if eaia_url is not None:
        doc.eaia_url = eaia_url.strip()

    # Secret fields: only overwrite when a non-empty value is provided.
    if openrouter_api_key is not None and openrouter_api_key.strip():
        doc.openrouter_api_key = openrouter_api_key.strip()
    if google_api_key is not None and google_api_key.strip():
        doc.google_api_key = google_api_key.strip()

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Return fresh status (also re-reads via _get_conf so caller sees the effect).
    out = get_brain_settings()
    out["saved"] = True
    return out


@frappe.whitelist()
def triage_and_draft(lead_name: str, incoming: str | None = None, force: bool = False) -> dict:
    """Triage an inbound context for a CRM Lead and, if warranted, create a draft
    reply that lands in the Human Inbox for approval.

    Backend-agnostic. Returns {decision, communication, backend, ...}.
    """
    backend = get_backend()
    if backend == "eaia":
        return _eaia_triage_and_draft(lead_name, incoming, force)
    return _frappe_triage_and_draft(lead_name, incoming, force)


@frappe.whitelist()
def approve_and_send(communication_name: str) -> dict:
    """Human-approve a queued draft and actually send it (the send gate).

    Always routes through the deployed crm.api.email.send (frappe.sendmail),
    regardless of which backend produced the draft — the send authority lives
    in Frappe so it is auditable and consistent.
    """
    if not communication_name:
        frappe.throw(_("communication_name is required"))
    # Optional: mark reviewed metadata before sending
    res = frappe.call("crm.api.email.send", communication_name=communication_name)
    try:
        _record_brain_event(communication_name, "sent", {"backend": get_backend()})
    except Exception:
        # The send already succeeded; a telemetry failure must not fail the call,
        # but it must be visible in the log rather than swallowed.
        logger.warning("nyx_email_brain: failed to record 'sent' brain event for %s", communication_name, exc_info=True)
    return {"ok": True, "communication": communication_name, "backend": get_backend(), "send": res}


@frappe.whitelist()
def batch_triage_and_draft(limit: int = 10, only_with_email: int = 1) -> dict:
    """Batch entry point for the Human Inbox 'Draft for top leads' action.

    Bounded, opt-in proactive drafting: pick up to `limit` high-signal CRM Leads
    that do NOT already have a pending draft, and enqueue triage+draft for each.
    Enqueued (not inline) because each lead is an LLM round-trip. Returns the set
    of leads queued so the UI can report honestly.

    This is the ONLY proactive/scheduled-style trigger in Frappe. Inbound-reply
    drafting is owned by the EAIA Gmail cron loop (cron_graph.fetch_group_emails),
    not duplicated here.
    """
    limit = max(1, min(int(limit or 10), 50))
    only_with_email = int(only_with_email or 0)

    # Candidate leads: highest score first, skip anything already sitting as a draft.
    lead_filters = {"status": ["not in", ["Converted", "Do Not Contact", "Lost", "Junk"]]}
    if only_with_email:
        lead_filters["email"] = ["is", "set"]

    candidates = frappe.get_all(
        "CRM Lead",
        filters=lead_filters,
        fields=["name", "lead_name", "email"],
        order_by="modified desc",
        limit=limit * 3,  # over-fetch; we filter out ones that already have drafts
    )

    queued, skipped = [], []
    for c in candidates:
        if len(queued) >= limit:
            break
        if _has_pending_draft("CRM Lead", c["name"]):
            skipped.append(c["name"])
            continue
        frappe.enqueue(
            "crm.api.nyx_email_brain.triage_and_draft",
            queue="long",
            lead_name=c["name"],
            force=True,
        )
        queued.append(c["name"])

    return {
        "ok": True,
        "backend": get_backend(),
        "queued_count": len(queued),
        "queued": queued,
        "skipped_existing_draft": len(skipped),
    }


def _has_pending_draft(reference_doctype: str, reference_name: str) -> bool:
    """True if an outbound draft is already awaiting human review on this doc."""
    return bool(frappe.db.exists(
        "Communication",
        {
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "communication_type": "Communication",
            "communication_medium": "Email",
            "sent_or_received": "Sent",
            "status": ["in", ["Draft", "Open"]],
        },
    ))


# ────────────────────────────────────────────────────────────────────────────
# Frappe-native backend
# ────────────────────────────────────────────────────────────────────────────

TRIAGE_SYSTEM = (
    "You are NYX, an outreach SDR assistant for a life-sciences CRM. "
    "Given a lead and any inbound message, decide one of: RESPOND (draft a reply), "
    "NOTIFY (needs human attention, no draft), or IGNORE (no action). "
    "Return STRICT JSON: {\"action\":\"RESPOND|NOTIFY|IGNORE\",\"reason\":\"...\"}."
)

DRAFT_SYSTEM = (
    "You are NYX writing a concise, specific, non-generic outreach email for a "
    "life-sciences CRM. Ground the message in the lead's context. Keep it under "
    "160 words, one clear ask, no fluff. Return STRICT JSON: "
    "{\"subject\":\"...\",\"html\":\"<p>...</p>\"}."
)


def _frappe_triage_and_draft(lead_name: str, incoming: str | None, force: bool) -> dict:
    lead = frappe.get_doc("CRM Lead", lead_name)
    ctx = _lead_context(lead, incoming)

    complete = _resolve_llm()
    if complete is None:
        return {"decision": "no_llm", "backend": "frappe",
                "error": "No LLM provider configured."}

    # 1) triage
    triage_raw = complete(f"{TRIAGE_SYSTEM}\n\nLEAD CONTEXT:\n{ctx}")
    triage = _safe_json(triage_raw, {"action": "NOTIFY", "reason": "unparseable triage"})
    action = (triage.get("action") or "NOTIFY").upper()
    if action == "IGNORE" and not force:
        return {"decision": "ignore", "backend": "frappe", "reason": triage.get("reason")}
    if action == "NOTIFY" and not force:
        return {"decision": "notify", "backend": "frappe", "reason": triage.get("reason")}

    # 2) draft
    draft_raw = complete(f"{DRAFT_SYSTEM}\n\nLEAD CONTEXT:\n{ctx}")
    draft = _safe_json(draft_raw, {})
    subject = (draft.get("subject") or f"Following up — {lead.lead_name or ''}").strip()
    html = (draft.get("html") or "").strip()
    if not html:
        return {"decision": "draft_failed", "backend": "frappe",
                "error": "LLM did not return draft html", "raw": draft_raw[:500]}

    to = lead.email or ""
    # 3) write draft as a Communication (lands in Human Inbox), never auto-send
    comm_name = frappe.call(
        "crm.api.email.save_draft",
        reference_doctype="CRM Lead",
        reference_name=lead_name,
        to=to,
        subject=subject,
        html=html,
    )
    _record_brain_event(comm_name, "drafted",
                        {"backend": "frappe", "triage": action, "lead": lead_name})
    return {"decision": "drafted", "backend": "frappe", "communication": comm_name,
            "subject": subject, "to": to, "triage": action}


def _norm_name(s: str) -> str:
    """Normalize a person name for fuzzy matching (lower, strip titles/punct)."""
    import re
    s = (s or "").lower().strip()
    s = re.sub(r"^(dr|prof|professor|mr|ms|mrs)\.?\s+", "", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_KOL_INDEX_CACHE = None


def _kol_index() -> dict:
    """Load kol_targets.json (bundled in crm/aacr_data) indexed by normalized name.

    Each value carries the human-authored angle: hook, crispro_angle,
    open_questions, primary_axis, email_subject. Returns {} if unavailable.
    """
    global _KOL_INDEX_CACHE
    if _KOL_INDEX_CACHE is not None:
        return _KOL_INDEX_CACHE
    idx = {}
    try:
        import os as _os
        path = _os.path.join(frappe.get_app_path("crm"), "aacr_data", "kol_targets.json")
        with open(path, "r") as fh:
            for t in (json.load(fh) or []):
                nm = _norm_name(t.get("name", ""))
                if nm:
                    idx[nm] = t
    except Exception:
        idx = {}
    _KOL_INDEX_CACHE = idx
    return idx


def _aacr_talk_for_lead(lead, ad: dict):
    """Resolve the AACR Talk linked to an AACR-sourced lead.

    Two link paths (either may be present):
      * AACR Talk.crm_lead == lead.name         (forward link)
      * lead.additional_data.nyx_facets.source_ref_id == AACR Talk.name  (facet)
    Returns the AACR Talk doc or None.
    """
    talk_name = None
    facets = ad.get("nyx_facets") or {}
    if isinstance(facets, dict):
        talk_name = facets.get("source_ref_id")
    try:
        if talk_name and frappe.db.exists("AACR Talk", talk_name):
            return frappe.get_doc("AACR Talk", talk_name)
        # fall back to reverse link
        rev = frappe.get_all("AACR Talk", filters={"crm_lead": lead.name},
                             pluck="name", limit=1)
        if rev:
            return frappe.get_doc("AACR Talk", rev[0])
    except Exception:
        return None
    return None


def _aacr_scientific_context(lead, ad: dict) -> list[str]:
    """Build the AACR-specific scientific context block for an outreach draft.

    Pulls the linked AACR Talk's MOA / targets / stage / novelty, and — when the
    speaker matches a curated KOL target — the human-authored hook + CrisPRO angle.
    Returns a list of context lines (possibly empty for non-AACR leads).
    """
    lines: list[str] = []
    talk = _aacr_talk_for_lead(lead, ad)
    if talk:
        lines.append("\n--- AACR 2026 SCIENTIFIC CONTEXT (source of this lead) ---")
        if talk.get("talk_title"):
            lines.append(f"Talk: {talk.talk_title}")
        if talk.get("session_title"):
            lines.append(f"Session: {talk.session_title}")
        meta = []
        if talk.get("clinical_stage"):
            meta.append(f"stage={talk.clinical_stage}")
        if talk.get("novelty_flag"):
            meta.append(f"novelty={talk.novelty_flag}")
        if meta:
            lines.append("Classification: " + ", ".join(meta))
        if talk.get("moa_summary"):
            lines.append(f"Mechanism / finding: {talk.moa_summary}")
        # top targets (gene + modality/alteration)
        tgts = []
        for t in (talk.get("targets") or [])[:6]:
            g = (t.get("gene_or_protein") or "").strip()
            if not g:
                continue
            extra = t.get("alteration") or t.get("modality") or t.get("pathway")
            tgts.append(f"{g} ({extra})" if extra else g)
        if tgts:
            lines.append("Targets: " + ", ".join(tgts))
        # biomarker names — skip opaque row-hash tokens (e.g. "f4965toj69") that
        # some live child rows carry instead of a human-readable name.
        import re as _re
        def _real_bm(n):
            n = (n or "").strip()
            if not n:
                return False
            return not (bool(_re.fullmatch(r"[a-z0-9]{6,12}", n)) and any(c.isdigit() for c in n))
        bms = [b.get("name") for b in (talk.get("biomarkers") or []) if _real_bm(b.get("name"))]
        if bms:
            lines.append("Biomarkers: " + ", ".join(bms[:6]))

    # curated KOL angle (human-authored hook + CrisPRO positioning)
    kol = _kol_index().get(_norm_name(lead.lead_name or ""))
    if kol:
        lines.append("\n--- CURATED OUTREACH ANGLE (use this framing) ---")
        if kol.get("primary_axis"):
            lines.append(f"Primary axis: {kol.get('primary_axis')}")
        if kol.get("opportunity_type"):
            lines.append(f"Opportunity type: {kol.get('opportunity_type')}")
        if kol.get("hook"):
            lines.append(f"Hook (their own words): {kol.get('hook')}")
        if kol.get("crispro_angle"):
            lines.append(f"CrisPRO angle: {kol.get('crispro_angle')}")
        oq = kol.get("open_questions") or []
        if oq:
            lines.append("Open questions to raise: " + "; ".join(oq[:3]))
    return lines


def _lead_context(lead, incoming: str | None) -> str:
    ad = {}
    try:
        ad = json.loads(lead.additional_data or "{}")
    except Exception:
        ad = {}
    parts = [
        f"Name: {lead.lead_name or ''}",
        f"Organization: {lead.organization or ''}",
        f"Email: {lead.email or '(none)'}",
        f"Status: {lead.status or ''}",
        f"Lead score: {ad.get('score', 'n/a')}",
        f"Detected context: {', '.join(ad.get('detected_context', []) or []) or 'n/a'}",
    ]
    sig = ad.get("distilled_signals") or {}
    if sig:
        parts.append("Signals: " + json.dumps({k: sig.get(k) for k in
                     ("specific_number", "recent_event", "strategic_detail") if sig.get(k)}))
    # AACR-sourced leads: enrich with the linked talk's science + curated angle.
    # Backward-compatible — yields nothing for non-AACR leads.
    try:
        parts.extend(_aacr_scientific_context(lead, ad))
    except Exception:
        # Non-AACR leads legitimately yield nothing; a real failure here silently
        # degrades draft quality, so surface it.
        logger.warning("nyx_email_brain: AACR scientific context failed for lead %s", getattr(lead, "name", "?"), exc_info=True)
    if incoming:
        parts.append(f"\nINBOUND MESSAGE:\n{incoming}")
    return "\n".join(parts)


# ────────────────────────────────────────────────────────────────────────────
# LLM provider resolution (extends the etl_json seam; adds OpenRouter)
# ────────────────────────────────────────────────────────────────────────────

def _active_llm_provider() -> str:
    # An explicit UI setting wins IF its key is actually present (so the user's
    # provider choice is authoritative even when both keys exist).
    explicit = (_get_conf("llm_provider", default="") or "").strip().lower()
    if explicit == "openrouter" and _get_conf("openrouter_api_key"):
        return "openrouter"
    if explicit == "gemini" and _get_conf("google_api_key", "gemini_api_key"):
        return "gemini"
    # Backward-compatible fallback: resolve by key presence (no explicit setting).
    if _get_conf("openrouter_api_key"):
        return "openrouter"
    if _get_conf("google_api_key", "gemini_api_key"):
        return "gemini"
    return "none"


def _resolve_llm():
    """Return a Callable[[str], str] or None. Prefers OpenRouter (free models),
    falls back to the existing Gemini seam in etl_json."""
    provider = _active_llm_provider()
    if provider == "openrouter":
        return _openrouter_complete
    if provider == "gemini":
        try:
            from crm.api.etl_json import _default_llm_complete
            return _default_llm_complete()
        except Exception:
            return None
    return None


def _openrouter_complete(prompt: str) -> str:
    """OpenAI-compatible OpenRouter call.

    Model resolution matches the DEPLOYED enrichment path (crm.api.enrichment):
    config key `openrouter_enrichment_model`, else `google/gemma-3-27b-it`.
    We intentionally do NOT default to `openai/gpt-oss-20b:free` — that free model
    is already hitting the free-models-per-day rate limit (429) on the live key,
    whereas gemma-3-27b-it responds reliably (verified live 2026-07-03).
    """
    import requests
    key = _get_conf("openrouter_api_key")
    model = _get_conf("openrouter_enrichment_model", "openrouter_model",
                      default="google/gemma-3-27b-it")
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""


# ────────────────────────────────────────────────────────────────────────────
# EAIA-proxy backend (swap target — the standalone LangGraph service)
# ────────────────────────────────────────────────────────────────────────────

def _eaia_healthcheck(url: str):
    import requests
    try:
        r = requests.get(url.rstrip("/") + "/health", timeout=10)
        return (r.status_code == 200), f"HTTP {r.status_code} from {url}/health"
    except Exception as e:
        return False, f"EAIA unreachable: {e}"


def _eaia_triage_and_draft(lead_name: str, incoming: str | None, force: bool) -> dict:
    """Delegate to the EAIA service; it drafts back into CRM via crm_bridge
    (post_draft_with_provider -> crm.api.agent.run). We just kick it and report."""
    import requests
    url = _get_conf("eaia_url", default="")
    if not url:
        return {"decision": "eaia_unconfigured", "backend": "eaia",
                "error": "EAIA_URL not set."}
    try:
        r = requests.post(url.rstrip("/") + "/triage",
                          json={"lead_name": lead_name, "incoming": incoming, "force": force},
                          timeout=60)
        r.raise_for_status()
        out = r.json()
        out.setdefault("backend", "eaia")
        return out
    except Exception as e:
        return {"decision": "eaia_error", "backend": "eaia", "error": str(e)}


# ────────────────────────────────────────────────────────────────────────────
# Lightweight brain-event log (guarded; no-op if doctype absent)
# ────────────────────────────────────────────────────────────────────────────

def _record_brain_event(communication_name, event, meta: dict):
    if not frappe.db.exists("DocType", "NYX Brain Event"):
        return
    try:
        frappe.get_doc({
            "doctype": "NYX Brain Event",
            "communication": communication_name,
            "event": event,
            "meta": json.dumps(meta or {}),
        }).insert(ignore_permissions=True)
    except Exception:
        logger.warning("nyx_email_brain._record_brain_event: insert failed (event=%s)", event, exc_info=True)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _safe_json(raw: str, default: dict) -> dict:
    if not raw:
        return dict(default)
    s = raw.strip()
    # strip markdown fences if present
    if s.startswith("```"):
        s = s.split("```", 2)[1] if "```" in s[3:] else s.strip("`")
        s = s.lstrip("json").strip()
    try:
        return json.loads(s)
    except Exception:
        # try to locate the first {...} block
        import re
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return dict(default)
        return dict(default)


# ────────────────────────────────────────────────────────────────────────────
# REUSABLE GUARDED DRAFTING SEAM  (consumed by crm.api.plan_generator)
# ────────────────────────────────────────────────────────────────────────────
#
# Frozen contract:
#   draft_outreach_body(ctx, evidence, subject_hint="") -> {subject, html, method, guard}
#
# The LLM writes PROSE ONLY and can never introduce a citable claim, because:
#   1. the prompt receives ONLY sourced evidence (every item carries a source), and
#   2. the output is scanned by _claim_guard() for any number, trial id, or drug
#      name absent from that evidence; on violation the LLM text is DISCARDED and
#      the deterministic body is used instead (and labelled as such).
#
# That two-part construction is what makes LLM-written outreach safe to put in
# front of a clinical audience: the model controls tone and ordering, never facts.

import logging as _logging  # noqa: E402
import re as _re  # noqa: E402  (module tail import; header left untouched)

logger = _logging.getLogger(__name__)

# drug-like tokens (INN stems). Used to catch invented compound names.
# CASE-INSENSITIVE on purpose: generic drug names are lowercase in prose
# ("zanubrutinib"), so an upper-case-only pattern misses almost every real
# fabrication. Suffixes that collide with ordinary English ("-cel" in "cancel",
# "-stat" in "thermostat", "-tide" in "peptide") are deliberately EXCLUDED from
# the bare-word branch; hyphenated cell-therapy products (cilta-cel, ide-cel)
# get their own branch where the hyphen makes the match unambiguous.
# USAN/INN stems for drug classes a model could plausibly invent. Chosen so that
# the anchor indication's own vocabulary is covered: MSS colorectal cancer on an
# mFOLFOX6 +/- bevacizumab backbone means fluoro-pyrimidines (-uracil, -itabine),
# platinums (-platin), topoisomerase-I (-tecan, incl. FOLFIRI), anti-VEGF/EGFR
# (-mab, -bercept) and the KRAS G12C comparator class (-rasib) are all live terms
# an unguarded draft could fabricate. Empirically validated: 58/58 hits on a
# CRC/IO reference drug list, 0 false positives across 717 KB of this repo's own
# prose (curated engagement cards, governance constants, deterministic bodies)
# and an ordinary-English sweep of look-alike endings (concept/accept/consensus/
# stimulus/pecan/toucan/citation/volcanic/...).
# Deliberately NOT included: bare -cel, -stat, -tide, -cept, -fur (each collides
# with ordinary English or with words this codebase already ships).
_DRUG_SUFFIX = _re.compile(
    r"\b[A-Za-z][a-z]{2,}(?:mab|nib|tinib|ciclib|parib|zumab|ximab|umab|limab"
    r"|mycin|platin|rubicin|taxel|sertib|degib|lisib|rafenib"
    # added after integration testing found the shipped list missed 21/58 of the
    # drugs that matter for this program (whole KRAS G12C class, the FOLFOX/FOLFIRI
    # backbone, mTOR and proteasome inhibitors):
    r"|rasib|tecan|itabine|itidine|uracil|limus|zomib|bercept|leucel)\b"
    r"|\b[a-z]{3,}-cel\b",
    _re.I)
_NCT_RE = _re.compile(r"\bNCT\d{6,}\b", _re.I)
# numbers that read as CLINICAL RESULTS — deliberately narrow so ordinary prose
# ("step 2", "in 4 days") does not trip the guard.
_CLINICAL_NUM = _re.compile(
    r"\d+(?:\.\d+)?\s?%"
    r"|(?:ORR|PFS|OS|DFS|HR|median|survival|response rate)[^.\n]{0,24}?\d+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?[^.\n]{0,24}?(?:ORR|PFS|OS|DFS|median|survival|response rate)"
    r"|\bp\s*[<=]\s*0?\.\d+"
    r"|\bHR\s*[=:]\s*\d"
    r"|\bn\s*=\s*\d+",
    _re.I)
_NUMERAL = _re.compile(r"\d+(?:\.\d+)?")

_DRAFT_SYS = (
    "You are drafting a short, specific outreach message from a computational "
    "oncology team (CrisPRO / Brenus Pharma) to a named cancer researcher.\n"
    "HARD RULES — violating any of these makes the draft unusable:\n"
    "  1. Use ONLY the facts in EVIDENCE below. Invent nothing.\n"
    "  2. Never state a number, percentage, trial identifier (NCT...), or drug "
    "name that is not present verbatim in EVIDENCE.\n"
    "  3. Never claim a model has been run on their data, never promise a "
    "clinical outcome (ORR/PFS/OS), never imply an existing partnership.\n"
    "  4. If EVIDENCE is thin, write a short scientific-interest note and ask "
    "one question. Do NOT pad with invented specifics.\n"
    "  5. 120 words maximum. Plain, peer-to-peer tone. No marketing language.\n"
    "Return ONLY the message body as simple HTML <p> paragraphs. No subject line, "
    "no preamble, no code fences."
)


def _fence_strip(txt: str) -> str:
    """Local fence stripper. Defined here (not imported from nyx_agent) because
    nyx_agent imports THIS module — importing back would be circular."""
    t = (txt or "").strip()
    if t.startswith("```"):
        t = _re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = _re.sub(r"\s*```$", "", t)
    return t.strip()


def _evidence_blob(evidence) -> str:
    parts = []
    for e in evidence or []:
        if isinstance(e, dict):
            parts.append(str(e.get("text", "")))
            parts.append(str(e.get("source", "")))
        else:
            parts.append(str(e))
    return " \n".join(parts)


def _claim_guard(text: str, evidence_blob: str) -> dict:
    """Reject prose that introduces facts absent from the sourced evidence.

    Returns {"ok": bool, "violations": [str]}. Conservative by construction: a
    claim is a violation unless its literal token appears in the evidence blob.
    """
    violations = []
    body = text or ""
    blob = evidence_blob or ""
    blob_l = blob.lower()

    for nct in set(_NCT_RE.findall(body)):
        if nct.lower() not in blob_l:
            violations.append(f"unsourced trial id: {nct}")

    for drug in set(_DRUG_SUFFIX.findall(body)):
        if drug.lower() not in blob_l:
            violations.append(f"unsourced drug name: {drug}")

    for m in set(_CLINICAL_NUM.findall(body)):
        frag = m if isinstance(m, str) else " ".join(x for x in m if x)
        for num in _NUMERAL.findall(frag):
            if num not in blob:
                violations.append(f"unsourced clinical number: {frag.strip()[:60]}")
                break

    return {"ok": not violations, "violations": violations}


def _deterministic_body(ctx: dict, evidence) -> str:
    """Data-derived fallback. Dynamic (built from real ctx/evidence) but not
    LLM-written. Never asserts anything not already in ctx/evidence."""
    name = (ctx or {}).get("display_name") or "there"
    first = name.split()[0] if " " in name else name
    hook = (ctx or {}).get("hook") or ""
    angle = (ctx or {}).get("crispro_angle") or ""
    oq = (ctx or {}).get("open_questions") or ""
    if isinstance(oq, (list, tuple)):
        oq = oq[0] if oq else ""
    topic = (ctx or {}).get("aacr_topic") or (ctx or {}).get("company") or "your program"

    ps = [f"Hi {first},"]
    if hook:
        ps.append(f"Your work on {str(hook)[:220]} is directly relevant to what we build.")
    else:
        ps.append(f"I follow work in {str(topic)[:120]} and wanted to make a brief, "
                  f"specific introduction.")
    if angle:
        ps.append(f"Where we may be useful: {str(angle)[:220]}")
    if oq:
        ps.append(f"The open question I would most like your read on: {str(oq)[:200]}")
    ps.append("No ask beyond a short scientific conversation. Worth 20 minutes?")
    sender = (ctx or {}).get("sender") or "CrisPRO / Brenus Pharma"
    ps.append(f"— {sender}")
    return "".join(f"<p>{p}</p>" for p in ps)


def _fallback_subject(ctx: dict) -> str:
    topic = (ctx or {}).get("aacr_topic") or (ctx or {}).get("hook") or ""
    topic = str(topic).strip()
    if topic:
        return f"Question about {topic[:60]}"
    company = (ctx or {}).get("company") or "your program"
    return f"Brief scientific question — {str(company)[:50]}"


def draft_outreach_body(ctx: dict, evidence=None, subject_hint: str = "") -> dict:
    """Draft one outreach message body. NEVER raises; always returns a usable body.

    ctx      : {display_name, company, institution, aacr_topic, hook,
                crispro_angle, open_questions, step_number, sender}
    evidence : ONLY sourced signals -> [{text, source, kind}, ...]
    returns  : {subject, html, method, guard}
                 method: 'llm:<provider>' | 'deterministic' | 'deterministic:guard_violation'
                 guard : {'ok': bool, 'violations': [...]}
    """
    ctx = ctx or {}
    evidence = evidence or []
    blob = _evidence_blob(evidence)
    subject = (subject_hint or "").strip() or _fallback_subject(ctx)
    guard = {"ok": True, "violations": []}

    llm = None
    try:
        llm = _resolve_llm()
    except Exception:
        logger.warning("draft_outreach_body: LLM resolution failed", exc_info=True)
        llm = None

    if llm:
        try:
            ev_lines = "\n".join(
                f"- {e.get('text','')} [source: {e.get('source','')}]"
                for e in evidence if isinstance(e, dict) and e.get("text")
            ) or "(no sourced evidence available — keep it general and ask a question)"
            prompt = (
                f"{_DRAFT_SYS}\n\n"
                f"RECIPIENT: {ctx.get('display_name','')}"
                f"{' — ' + str(ctx.get('institution')) if ctx.get('institution') else ''}\n"
                f"THEIR FOCUS: {ctx.get('aacr_topic') or ctx.get('hook') or 'unknown'}\n"
                f"WHERE WE MAY HELP: {ctx.get('crispro_angle') or 'general trial-design support'}\n"
                f"OPEN QUESTION TO RAISE: {ctx.get('open_questions') or '(none supplied)'}\n"
                f"SENDER: {ctx.get('sender') or 'CrisPRO / Brenus Pharma'}\n"
                f"STEP: {ctx.get('step_number', 1)} of a 2-step sequence\n\n"
                f"EVIDENCE (the ONLY facts you may use):\n{ev_lines}\n"
            )
            raw = _fence_strip(llm(prompt) or "")
            if raw:
                guard = _claim_guard(raw, blob)
                if guard["ok"]:
                    return {"subject": subject, "html": raw,
                            "method": f"llm:{_active_llm_provider()}", "guard": guard}
                logger.warning(
                    "draft_outreach_body: claim guard rejected LLM draft: %s",
                    guard["violations"])
                return {"subject": subject, "html": _deterministic_body(ctx, evidence),
                        "method": "deterministic:guard_violation", "guard": guard}
        except Exception:
            logger.warning("draft_outreach_body: LLM draft failed, using deterministic",
                           exc_info=True)

    return {"subject": subject, "html": _deterministic_body(ctx, evidence),
            "method": "deterministic", "guard": guard}
