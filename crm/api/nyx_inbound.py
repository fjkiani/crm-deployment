# crm/api/nyx_inbound.py
"""
NYX Inbound — reusable, multi-tenant inbound-email capability, Frappe-native.

Design intent (per product direction):
  * DON'T DRIFT from Frappe. The inbound loop runs entirely inside the managed
    Frappe runtime — NO standalone Railway/Render service is required. Inbound
    mail is pulled by Frappe's built-in `Email Account` (IMAP), which lands a
    `Communication` per message; this module reacts to those Communications.
  * REUSABLE / MULTI-TENANT. Nothing here is hardcoded to a single mailbox or
    tenant. Per-tenant credentials live on a per-tenant `Email Account` (Frappe's
    native, inherently multi-account primitive). Behaviour is gated by config
    that resolves per site/tenant (env -> site_config -> CRM Global Settings),
    so a fresh tenant that has configured nothing is a safe NO-OP (stubbed).
  * SWAPPABLE BRAIN. Routing hands off to crm.api.nyx_email_brain.triage_and_draft,
    which is itself backend-agnostic ("frappe" default, or "eaia" proxy). This
    module never calls an LLM directly.

Flow:
    Gmail (per-tenant app password)
      -> Frappe "Email Account" (IMAP poll; built-in scheduler)      [per tenant]
      -> creates Communication (sent_or_received = "Received")
      -> Communication.after_insert hook:
             1) crm.api.email.auto_link_communication  (resolve -> Lead/Deal/Contact)
             2) crm.api.nyx_inbound.route_inbound_communication  (THIS module)
      -> if autopilot enabled + linked + no pending draft:
             enqueue crm.api.nyx_email_brain.triage_and_draft (LLM round-trip)
      -> draft parked in the Human Inbox for approval  ->  approve_and_send

Everything is best-effort: a failure here NEVER interrupts inbound mail ingestion.
"""

from __future__ import annotations

import frappe
from frappe import _

# Reuse the brain's config resolver + pending-draft guard so behaviour is
# consistent with the rest of the NYX stack (single source of truth).
from crm.api.nyx_email_brain import _get_conf, get_backend, _has_pending_draft


# ────────────────────────────────────────────────────────────────────────────
# Per-tenant configuration (all safe-defaulted; unconfigured tenant == no-op)
# ────────────────────────────────────────────────────────────────────────────

def _autopilot_enabled() -> bool:
    """Master switch for inbound auto-triage, resolved per tenant.

    Off by default: a tenant must explicitly opt in via any of
      env NYX_INBOUND_AUTOPILOT=1 | site_config nyx_inbound_autopilot |
      CRM Global Settings.nyx_inbound_autopilot
    This is what makes a freshly-provisioned tenant a safe stub.
    """
    val = _get_conf("nyx_inbound_autopilot", default="")
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _reference_allowlist() -> set[str]:
    """Which linked reference doctypes are eligible for auto-triage.

    Default: CRM Lead + CRM Deal. Overridable per tenant via
    `nyx_inbound_reference_doctypes` (comma-separated).
    """
    raw = _get_conf("nyx_inbound_reference_doctypes", default="") or ""
    parsed = {p.strip() for p in str(raw).split(",") if p.strip()}
    return parsed or {"CRM Lead", "CRM Deal"}


def _account_allowlist() -> set[str]:
    """Optional per-tenant restriction to specific Email Accounts.

    Empty => every inbound Email Account is eligible. Set
    `nyx_inbound_email_accounts` (comma-separated Email Account names) to scope.
    """
    raw = _get_conf("nyx_inbound_email_accounts", default="") or ""
    return {p.strip() for p in str(raw).split(",") if p.strip()}


# ────────────────────────────────────────────────────────────────────────────
# The reusable router — wired to Communication.after_insert
# ────────────────────────────────────────────────────────────────────────────

def route_inbound_communication(doc, method: str | None = None) -> None:
    """Hook: react to a newly-created inbound email Communication.

    Multi-tenant + stub-safe: does nothing unless the tenant opted in and the
    message is a linkable inbound email. Never raises into the ingest pipeline.
    """
    try:
        if not _autopilot_enabled():
            return  # stubbed for tenants that have not opted in

        # Only inbound emails (Frappe sets these on IMAP-pulled mail).
        if (doc.get("communication_type") or "Communication") != "Communication":
            return
        if (doc.get("communication_medium") or "Email") != "Email":
            return
        if (doc.get("sent_or_received") or "") != "Received":
            return

        # Optional per-tenant Email Account scoping.
        allow_accounts = _account_allowlist()
        if allow_accounts and (doc.get("email_account") or "") not in allow_accounts:
            return

        # Must already be linked to an eligible reference. auto_link_communication
        # runs first (same after_insert hook, earlier in the list) and persists
        # reference_doctype/reference_name via resolve_reference().
        ref_dt = doc.get("reference_doctype")
        ref_dn = doc.get("reference_name")
        if not (ref_dt and ref_dn):
            return
        if ref_dt not in _reference_allowlist():
            return

        # For CRM Deal, triage against the originating lead when present; the
        # brain's public API is lead-centric. Fall back to skipping deals that
        # have no lead rather than guessing.
        lead_name = _lead_for_reference(ref_dt, ref_dn)
        if not lead_name:
            return

        # Idempotency: don't stack drafts on a reference already awaiting review.
        if _has_pending_draft(ref_dt, ref_dn):
            return

        # Hand the incoming context to the (swappable) brain, off the web worker.
        incoming = _incoming_text(doc)
        frappe.enqueue(
            "crm.api.nyx_email_brain.triage_and_draft",
            queue="long",
            job_name=f"nyx_inbound_triage::{doc.get('name')}",
            lead_name=lead_name,
            incoming=incoming,
            force=False,
        )
        frappe.logger("nyx_inbound").info(
            f"queued triage for {ref_dt} {ref_dn} from Communication {doc.get('name')} "
            f"(backend={get_backend()})"
        )
    except Exception:
        # Best-effort; inbound ingestion must never be interrupted.
        frappe.log_error(
            title="nyx_inbound.route_inbound_communication failed",
            message=frappe.get_traceback(),
        )


def _lead_for_reference(ref_dt: str, ref_dn: str) -> str | None:
    """Resolve a CRM Lead name for the linked reference (brain API is lead-centric)."""
    if ref_dt == "CRM Lead":
        return ref_dn
    if ref_dt == "CRM Deal":
        # CRM Deal stores the originating lead on `lead` (set by convert_to_deal).
        try:
            lead = frappe.db.get_value("CRM Deal", ref_dn, "lead")
            return lead or None
        except Exception:
            return None
    return None


def _incoming_text(doc) -> str:
    """Best available plain text of the inbound message for triage context."""
    txt = doc.get("content") or doc.get("text_content") or ""
    subject = doc.get("subject") or ""
    if subject and txt:
        return f"Subject: {subject}\n\n{txt}"
    return txt or subject or ""


# ────────────────────────────────────────────────────────────────────────────
# Provisioning helper — reusable, per-tenant (NOT hardcoded to one mailbox)
# ────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def provision_gmail_email_account(
    email_id: str | None = None,
    app_password: str | None = None,
    account_name: str | None = None,
    enable_incoming: int = 1,
    enable_outgoing: int = 1,
    imap_folder: str = "INBOX",
) -> dict:
    """Create/update a Frappe `Email Account` for a Gmail mailbox using an app
    password (SMTP send + IMAP poll). Reusable across tenants: each tenant calls
    this with ITS OWN mailbox + app password. Nothing is hardcoded.

    Credentials fall back to per-tenant config keys so an operator can seed them
    via site_config/env without exposing them in an API call:
      GMAIL_USER / gmail_user         -> email_id
      GMAIL_APP_PASSWORD / gmail_app_password -> app_password

    Gmail SMTP/IMAP endpoints are standard (smtp.gmail.com:587 STARTTLS,
    imap.gmail.com:993 SSL).
    """
    email_id = email_id or _get_conf("gmail_user", default="")
    app_password = app_password or _get_conf("gmail_app_password", default="")
    if not email_id or not app_password:
        frappe.throw(_("email_id and app_password (Gmail app password) are required. "
                       "Provide them directly or via GMAIL_USER / GMAIL_APP_PASSWORD config."))

    account_name = account_name or f"NYX Gmail ({email_id})"

    existing = frappe.db.get_value("Email Account", {"email_id": email_id}, "name")
    doc = frappe.get_doc("Email Account", existing) if existing else frappe.new_doc("Email Account")

    doc.update({
        "email_account_name": account_name,
        "email_id": email_id,
        "service": "GMail",
        # Outgoing (SMTP)
        "enable_outgoing": int(enable_outgoing),
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": 1,
        # Incoming (IMAP)
        "enable_incoming": int(enable_incoming),
        "use_imap": 1,
        "email_server": "imap.gmail.com",
        "incoming_port": 993,
        "use_ssl": 1,
        # Where inbound lands + how it is attributed
        "imap_folder": imap_folder,
        "append_to": "CRM Lead",
        "default_incoming": 1 if int(enable_incoming) else 0,
        "create_contact": 0,
    })
    # App password is the auth secret for both SMTP and IMAP with Gmail.
    doc.password = app_password

    doc.flags.ignore_mandatory = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "ok": True,
        "email_account": doc.name,
        "email_id": email_id,
        "enable_incoming": int(enable_incoming),
        "enable_outgoing": int(enable_outgoing),
        "note": "Set nyx_inbound_autopilot=1 (per tenant) to enable auto-triage of inbound mail.",
    }


# ────────────────────────────────────────────────────────────────────────────
# Truthful status for the UI
# ────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_inbound_status() -> dict:
    """Report inbound capability state so the UI never lies about it."""
    out = {
        "autopilot": _autopilot_enabled(),
        "backend": get_backend(),
        "reference_doctypes": sorted(_reference_allowlist()),
        "email_accounts": [],
        "incoming_configured": False,
    }
    try:
        accts = frappe.get_all(
            "Email Account",
            filters={"enable_incoming": 1},
            fields=["name", "email_id", "service", "email_server", "imap_folder"],
        )
        out["email_accounts"] = accts
        out["incoming_configured"] = len(accts) > 0
    except Exception:
        # Email Account is a core doctype; if this fails, report honestly.
        out["detail"] = "Could not read Email Account list."
    return out
