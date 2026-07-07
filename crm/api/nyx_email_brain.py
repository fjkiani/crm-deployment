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


def _get_conf(*names, default=None):
    """Resolve a config value from site_config, env, or CRM Global Settings.

    Site config wins over env so Frappe Cloud Site Config edits take effect even
    when the bench carries a stale OPENROUTER_API_KEY (or similar) in env.
    """
    for n in names:
        v = frappe.conf.get(n.lower())
        if v:
            return v
    for n in names:
        v = os.getenv(n.upper())
        if v:
            return v
    # CRM Global Settings single doctype (native, editable from /app)
    try:
        if frappe.db.exists("DocType", "CRM Global Settings"):
            gs = frappe.get_single("CRM Global Settings")
            for n in names:
                if hasattr(gs, n.lower()) and getattr(gs, n.lower()):
                    return getattr(gs, n.lower())
    except Exception:
        pass
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
        pass
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
        pass
    if incoming:
        parts.append(f"\nINBOUND MESSAGE:\n{incoming}")
    return "\n".join(parts)


# ────────────────────────────────────────────────────────────────────────────
# LLM provider resolution (extends the etl_json seam; adds OpenRouter)
# ────────────────────────────────────────────────────────────────────────────

def _active_llm_provider() -> str:
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
        pass


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
