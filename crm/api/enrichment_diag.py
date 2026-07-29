"""
crm/api/enrichment_diag.py — TEMPORARY read-only diagnostic for the enrich 500.

Re-runs the enrich_contact internals step-by-step, each wrapped in try/except, and
returns a JSON report of which step throws + the traceback. Writes NOTHING to the
cache (the _cache_write step is simulated: builds the doc dict and validates it can
be constructed, but does NOT insert). Safe to call on the live site.

Remove after the 500 is root-caused.
"""
from __future__ import annotations

import json
import traceback

import frappe
from frappe import _


def _cap(obj, n=1500):
    try:
        return json.dumps(obj, default=str)[:n]
    except Exception:
        return str(obj)[:n]


@frappe.whitelist()
def diag_enrich_contact(lead_name: str) -> dict:
    """Step-through of enrich_contact with per-step error capture. Read-only."""
    report = {"lead_name": lead_name, "steps": []}

    def step(name, fn):
        rec = {"step": name}
        try:
            rec["ok"] = True
            rec["result_preview"] = _cap(fn())
        except Exception as e:
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["traceback"] = traceback.format_exc()
        report["steps"].append(rec)
        return rec

    # env facts
    report["env"] = {
        "user": frappe.session.user,
        "frappe_version": frappe.__version__,
        "site": frappe.local.site,
        "doctype_exists_meta": frappe.db.exists("DocType", "CrisPRO Enrichment"),
        "table_exists": _table_exists("CrisPRO Enrichment"),
        "action_log_doctype": frappe.db.exists("DocType", "Nyx Action Log"),
        "action_log_table": _table_exists("Nyx Action Log"),
    }

    # 0. lead exists + fields
    holder = {}

    def s_lead():
        if not frappe.db.exists("CRM Lead", lead_name):
            raise frappe.DoesNotExistError(f"Lead not found: {lead_name}")
        lead = frappe.get_doc("CRM Lead", lead_name)
        holder["name"] = lead.lead_name or ""
        holder["org"] = lead.organization or ""
        return {"lead_name": holder["name"], "organization": holder["org"],
                "source_ref_id": getattr(lead, "source_ref_id", None), "tier": getattr(lead, "tier", None)}

    step("load_lead", s_lead)

    # 1. cache get
    def s_cacheget():
        from crm.api.enrichment_api import _cache_get
        c = _cache_get("Person", lead_name)
        return {"cached_row": bool(c), "name": getattr(c, "name", None) if c else None}

    step("cache_get", s_cacheget)

    # 2. gather person intel
    def s_gather():
        from crm.api import enrichment_sources as ES
        intel = ES.gather_person_intel(holder.get("name", ""), org=holder.get("org", ""),
                                       linkedin_url="", title="")
        holder["intel"] = intel
        return {k: (v.get("status") if isinstance(v, dict) else type(v).__name__)
                for k, v in intel.items()}

    step("gather_person_intel", s_gather)

    # 3. distill
    def s_distill():
        from crm.api.enrichment_api import _distill_oncology
        sig = _distill_oncology(holder.get("intel", {}))
        holder["signals"] = sig
        return {"method": sig.get("method"), "gate": sig.get("signal_gate"),
                "n_signals": len(sig.get("signals", []))}

    step("distill_oncology", s_distill)

    # 4. map fit
    def s_fit():
        from crm.api.enrichment_api import _map_fit
        f = _map_fit(holder.get("signals", {}), None)
        holder["fit"] = f
        return {"dims": list(f.get("dimensions", {}).keys())}

    step("map_fit", s_fit)

    # 5. collect sources
    def s_sources():
        from crm.api.enrichment_api import _collect_sources
        src = _collect_sources(holder.get("intel", {}))
        holder["sources"] = src
        return {"n_sources": len(src)}

    step("collect_sources", s_sources)

    # 6. SIMULATE cache write (build doc dict + validate construct, do NOT insert)
    def s_write_sim():
        from frappe.utils import now_datetime, add_to_date
        from crm.api.enrichment_api import _cost_note, _DOCTYPE, _TTL_DAYS
        intel = holder.get("intel", {})
        signals = holder.get("signals", {})
        fit = holder.get("fit", {})
        sources = holder.get("sources", [])
        status = "ok"
        # try to actually construct the doc object (this triggers meta/field validation)
        doc = frappe.get_doc({
            "doctype": _DOCTYPE,
            "subject_type": "Person",
            "subject_key": lead_name,
            "company": holder.get("org", ""),
            "person_name": holder.get("name", ""),
            "status": status,
            "fetched_at": now_datetime(),
            "expires_at": add_to_date(now_datetime(), days=_TTL_DAYS),
            "cost_note": _cost_note(intel),
            "signals_json": json.dumps(signals),
            "fit_json": json.dumps(fit),
            "sources_json": json.dumps(sources),
            "payload": json.dumps(intel),
        })
        # run_method validate WITHOUT insert
        doc.set_new_name()  # would raise if naming broken
        return {"constructed": True, "proposed_name": getattr(doc, "name", None),
                "cost_note": doc.cost_note}

    step("cache_write_SIMULATED", s_write_sim)

    report["summary_first_failure"] = next(
        (s["step"] for s in report["steps"] if not s.get("ok")), None)
    return report


def _table_exists(doctype: str) -> bool:
    try:
        tbl = "tab" + doctype
        return bool(frappe.db.sql(
            "SELECT 1 FROM information_schema.tables WHERE table_name=%s LIMIT 1", (tbl,)))
    except Exception:
        return False
