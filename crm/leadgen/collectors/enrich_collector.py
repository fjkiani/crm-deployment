import frappe
import json
from crm.api.enrichment import (
    _tavily_scout,
    classify_email,
    _llm_adjudicate,
)

"""
Enrich collector — the missing job backend for run_leadgen_job("enrich").

Was referenced by crm.api.leadgen.run_leadgen_job / scheduler.run_enrichment_job
but the module did not exist, so every "enrich" job crashed at runtime
(ModuleNotFoundError). This implements real prospect enrichment by reusing the
deployed, working two-gate email-discovery primitives in crm.api.enrichment
(Tavily scout -> deterministic gate -> LLM adjudication).

For each Lead Prospect (default: Tier-1 prospects lacking enriched_data):
  1. Tavily scout on (pi_name, institution) for candidate emails + context.
  2. Two-gate adjudication (classify_email + _llm_adjudicate) to accept an email.
  3. Write pi_email (if newly resolved) + a structured enriched_data JSON blob.

Follows the exact collector contract used by nih/asco/clinicaltrials collectors:
run(job_name, params) with LeadGen Job status/progress updates.
"""


def run(job_name: str, params: dict):
    """Run prospect enrichment using the unified LeadGen Job system."""
    job = frappe.get_doc("LeadGen Job", job_name)
    try:
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()
        frappe.db.commit()

        prospect_names = params.get("prospect_names") or _default_prospects(
            limit=int(params.get("limit", 50))
        )
        job.total_records = len(prospect_names)
        job.save()

        enriched = 0
        emails_found = 0
        for i, pname in enumerate(prospect_names):
            try:
                res = enrich_one_prospect(pname)
                if res.get("enriched"):
                    enriched += 1
                if res.get("email"):
                    emails_found += 1
            except Exception as e:
                frappe.log_error(f"enrich_collector: {pname}: {e}", "LeadGen enrich")
            finally:
                job.processed_records = i + 1
                job.progress = int(((i + 1) / job.total_records) * 100) if job.total_records else 100
                if (i + 1) % 5 == 0 or (i + 1) == job.total_records:
                    job.save()
                    frappe.db.commit()

        job.status = "Completed"
        job.ended_at = frappe.utils.now()
        job.log = (f"Enriched {enriched}/{len(prospect_names)} prospects; "
                   f"resolved {emails_found} emails.")
        job.save()
        frappe.db.commit()
        return {"enriched": enriched, "emails_found": emails_found,
                "total": len(prospect_names)}
    except Exception as e:
        job.status = "Failed"
        job.log = f"Error: {str(e)}"
        job.save()
        frappe.log_error(f"LeadGen Job {job_name} failed: {str(e)}", "LeadGen enrich")
        frappe.db.rollback()
        raise


def _default_prospects(limit: int = 50):
    """Tier-1 prospects that still need enrichment (no enriched_data yet)."""
    rows = frappe.get_all(
        "Lead Prospect",
        filters={"tier": "Tier 1", "enriched_data": ["is", "not set"]},
        fields=["name"],
        limit=limit,
    )
    return [r["name"] for r in rows]


def enrich_one_prospect(prospect_name: str) -> dict:
    """Enrich a single Lead Prospect. Reuses the deployed two-gate email logic.

    Never clobbers an existing pi_email. Always writes an enriched_data audit blob.
    """
    p = frappe.get_doc("Lead Prospect", prospect_name)
    name = p.pi_name or ""
    org = p.institution or ""

    scout = _tavily_scout(name, org)
    blob = {
        "enriched_at": frappe.utils.now(),
        "scout_context_len": len(scout.get("context") or ""),
        "candidates": scout.get("emails", []),
        "scout_error": scout.get("error"),
        "email_decision": None,
        "email_selected": None,
        "sources_used": ["tavily"],
    }

    selected = None
    if not scout.get("error") and scout.get("emails"):
        for cand in scout["emails"]:
            det = classify_email(cand, name)
            if det in ("reject", "none"):
                continue
            llm = _llm_adjudicate(name, cand, scout.get("context", ""))
            if det in ("accept", "accept_high", "review") and llm.get("verdict") == "accept":
                selected = cand
                blob["email_decision"] = "accept"
                break
        if not selected:
            blob["email_decision"] = "held"
    else:
        blob["email_decision"] = "no_candidate"

    # write pi_email only if newly resolved and not already present
    wrote_email = False
    if selected and not p.pi_email:
        p.pi_email = selected
        blob["email_selected"] = selected
        wrote_email = True

    p.enriched_data = json.dumps(blob)
    p.save(ignore_permissions=True)
    frappe.db.commit()

    return {"prospect": prospect_name, "enriched": True,
            "email": selected if wrote_email else None,
            "decision": blob["email_decision"]}
