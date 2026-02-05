"""
Lead Generation API Endpoints
Provides unified job orchestration and prospect management
"""

import frappe
from frappe import _
from frappe.utils import now, cint, flt
from typing import Dict, List, Any, Optional
import json

@frappe.whitelist()
def run_leadgen_job(job_type: str, params: dict = None) -> Dict[str, Any]:
    """Run lead generation job using unified job system"""
    
    if not frappe.has_permission("LeadGen Job", "create"):
        frappe.throw(_("Insufficient permissions to create jobs"))
    
    # Validate job type
    valid_types = ["clinicaltrials", "nih", "asco", "consolidate", "enrich", "outreach"]
    if job_type not in valid_types:
        frappe.throw(_(f"Invalid job type. Must be one of: {', '.join(valid_types)}"))
    
    # Create job record
    job = frappe.get_doc({
        "doctype": "LeadGen Job",
        "job_name": f"{job_type.title()} Job - {now()}",
        "job_type": job_type,
        "params": frappe.as_json(params or {}),
        "status": "Queued",
        "owner": frappe.session.user,
        "priority": params.get("priority", "Medium") if params else "Medium"
    })
    job.insert()
    
    # Enqueue job using existing Frappe queue system
    frappe.enqueue(
        f"crm.leadgen.collectors.{job_type}_collector.run",
        job_name=job.name,
        params=params or {},
        queue="long",
        timeout=3600
    )
    
    return {
        "job_name": job.name,
        "status": "Queued",
        "message": f"{job_type.title()} job queued successfully"
    }

@frappe.whitelist()
def job_status(job_name: str) -> Dict[str, Any]:
    """Get job status and progress"""
    
    if not frappe.has_permission("LeadGen Job", "read"):
        frappe.throw(_("Insufficient permissions"))
    
    # Check if user can access this job
    if frappe.has_role("Sales User") and not frappe.has_role("Sales Manager"):
        job = frappe.get_doc("LeadGen Job", job_name)
        if job.owner != frappe.session.user:
            frappe.throw(_("You can only view your own jobs"))
    
    try:
        job = frappe.get_doc("LeadGen Job", job_name)
        
        return {
            "job_name": job.name,
            "status": job.status,
            "progress": flt(job.progress),
            "records_processed": cint(job.records_processed),
            "started_at": job.started_at,
            "ended_at": job.ended_at,
            "log": job.log,
            "error_details": job.error_details
        }
    except frappe.DoesNotExistError:
        frappe.throw(_("Job not found"))

@frappe.whitelist()
def get_prospects(filters: dict = None, limit: int = 20, include_raw: bool = False) -> List[Dict[str, Any]]:
    """Get prospects with PII protection"""
    
    if not frappe.has_permission("Lead Prospect", "read"):
        frappe.throw(_("Insufficient permissions"))
    
    # Apply owner filter for Sales Users
    if frappe.has_role("Sales User") and not frappe.has_role("Sales Manager"):
        filters = filters or {}
        filters["owner"] = frappe.session.user
    
    # Define fields based on permissions
    fields = [
        "name", "pi_name", "institution", "cancer_type", 
        "tier", "lead_score", "source", "source_ref_id",
        "outreach_status", "last_contacted", "response_rate"
    ]
    
    # Add PII fields only for managers
    if include_raw and frappe.has_role("Sales Manager"):
        fields.extend(["raw", "pi_email", "enriched_data"])
    
    prospects = frappe.get_list(
        "Lead Prospect",
        fields=fields,
        filters=filters or {},
        limit=limit,
        order_by="lead_score desc, tier asc"
    )
    
    return prospects

@frappe.whitelist()
def promote_prospects(prospect_names: List[str], lead_owner: str = None) -> Dict[str, Any]:
    """Promote prospects to CRM leads"""
    
    if not frappe.has_permission("Lead Prospect", "read"):
        frappe.throw(_("Insufficient permissions"))
    
    if not frappe.has_permission("CRM Lead", "create"):
        frappe.throw(_("Insufficient permissions to create leads"))
    
    promoted_count = 0
    errors = []
    
    for prospect_name in prospect_names:
        try:
            prospect = frappe.get_doc("Lead Prospect", prospect_name)
            
            # Check if already promoted
            if prospect.promoted_to_lead:
                errors.append(f"Prospect {prospect_name} already promoted to {prospect.promoted_to_lead}")
                continue
            
            # Create CRM Lead
            lead = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": prospect.pi_name.split()[0] if prospect.pi_name else "Unknown",
                "last_name": " ".join(prospect.pi_name.split()[1:]) if prospect.pi_name and len(prospect.pi_name.split()) > 1 else "",
                "lead_name": prospect.pi_name,
                "email": prospect.pi_email,
                "organization": prospect.institution,
                "source": "Lead Generation",
                "lead_owner": lead_owner or frappe.session.user,
                "tier": prospect.tier,
                "lead_score": prospect.lead_score,
                "prospect_ref": prospect.name
            })
            lead.insert()
            
            # Update prospect
            prospect.promoted_to_lead = lead.name
            prospect.save()
            
            promoted_count += 1
            
        except Exception as e:
            errors.append(f"Error promoting {prospect_name}: {str(e)}")
    
    return {
        "promoted_count": promoted_count,
        "errors": errors,
        "message": f"Successfully promoted {promoted_count} prospects to leads"
    }

@frappe.whitelist()
def start_outreach_sequence(prospect_names: List[str], sequence_name: str) -> Dict[str, Any]:
    """Start outreach sequence for prospects"""
    
    if not frappe.has_permission("Outreach Sequence", "read"):
        frappe.throw(_("Insufficient permissions"))
    
    if not frappe.has_permission("Outreach Sequence Instance", "create"):
        frappe.throw(_("Insufficient permissions to create outreach instances"))
    
    # Get sequence
    try:
        sequence = frappe.get_doc("Outreach Sequence", sequence_name)
    except frappe.DoesNotExistError:
        frappe.throw(_("Outreach sequence not found"))
    
    if not sequence.active:
        frappe.throw(_("Outreach sequence is not active"))
    
    started_count = 0
    errors = []
    
    for prospect_name in prospect_names:
        try:
            prospect = frappe.get_doc("Lead Prospect", prospect_name)
            
            # Check if sequence already started
            existing = frappe.get_all(
                "Outreach Sequence Instance",
                filters={
                    "prospect": prospect_name,
                    "outreach_sequence": sequence_name
                }
            )
            
            if existing:
                errors.append(f"Sequence already started for prospect {prospect_name}")
                continue
            
            # Create sequence instance
            instance = frappe.get_doc({
                "doctype": "Outreach Sequence Instance",
                "prospect": prospect_name,
                "outreach_sequence": sequence_name,
                "status": "Not Started",
                "total_steps": sequence.max_follow_ups,
                "owner": frappe.session.user
            })
            instance.insert()
            
            started_count += 1
            
        except Exception as e:
            errors.append(f"Error starting sequence for {prospect_name}: {str(e)}")
    
    return {
        "started_count": started_count,
        "errors": errors,
        "message": f"Successfully started outreach for {started_count} prospects"
    }

@frappe.whitelist()
def get_dashboard_metrics() -> Dict[str, Any]:
    """Get dashboard metrics for lead generation"""
    
    if not frappe.has_permission("Lead Prospect", "read"):
        frappe.throw(_("Insufficient permissions"))
    
    # Apply owner filter for Sales Users
    filters = {}
    if frappe.has_role("Sales User") and not frappe.has_role("Sales Manager"):
        filters["owner"] = frappe.session.user
    
    # Total prospects
    total_prospects = frappe.db.count("Lead Prospect", filters)
    
    # Prospects by tier
    tier_counts = frappe.db.sql("""
        SELECT tier, COUNT(*) as count
        FROM `tabLead Prospect`
        WHERE 1=1 {owner_filter}
        GROUP BY tier
    """.format(
        owner_filter="AND owner = %(owner)s" if filters else ""
    ), filters, as_dict=True)
    
    # Prospects by outreach status
    status_counts = frappe.db.sql("""
        SELECT outreach_status, COUNT(*) as count
        FROM `tabLead Prospect`
        WHERE 1=1 {owner_filter}
        GROUP BY outreach_status
    """.format(
        owner_filter="AND owner = %(owner)s" if filters else ""
    ), filters, as_dict=True)
    
    # Recent jobs
    job_filters = {}
    if frappe.has_role("Sales User") and not frappe.has_role("Sales Manager"):
        job_filters["owner"] = frappe.session.user
    
    recent_jobs = frappe.get_all(
        "LeadGen Job",
        fields=["name", "job_type", "status", "created", "records_processed"],
        filters=job_filters,
        limit=10,
        order_by="created desc"
    )
    
    return {
        "total_prospects": total_prospects,
        "tier_counts": {t["tier"]: t["count"] for t in tier_counts},
        "status_counts": {s["outreach_status"]: s["count"] for s in status_counts},
        "recent_jobs": recent_jobs
    }

@frappe.whitelist()
def consolidate_prospects() -> Dict[str, Any]:
    """Run consolidation job to deduplicate prospects"""
    
    if not frappe.has_permission("LeadGen Job", "create"):
        frappe.throw(_("Insufficient permissions"))
    
    return run_leadgen_job("consolidate", {"priority": "High"})

@frappe.whitelist()
def enrich_prospects(prospect_names: List[str] = None) -> Dict[str, Any]:
    """Run enrichment job for prospects"""
    
    if not frappe.has_permission("LeadGen Job", "create"):
        frappe.throw(_("Insufficient permissions"))
    
    params = {"priority": "Medium"}
    if prospect_names:
        params["prospect_names"] = prospect_names
    
    return run_leadgen_job("enrich", params)

@frappe.whitelist()
def unsubscribe(prospect_name: str):
    """Handle unsubscribe request from email link"""
    try:
        prospect = frappe.get_doc("Lead Prospect", prospect_name)
        
        # Update prospect status
        prospect.status = "Unsubscribed"
        prospect.notes = f"Unsubscribed on {frappe.utils.now()}"
        prospect.save(ignore_permissions=True)
        
        # Update any active outreach sequences
        active_instances = frappe.get_all(
            "Outreach Sequence Instance",
            filters={
                "lead_prospect": prospect_name,
                "status": "Active"
            }
        )
        
        for instance_data in active_instances:
            instance = frappe.get_doc("Outreach Sequence Instance", instance_data.name)
            instance.status = "Unsubscribed"
            instance.save(ignore_permissions=True)
        
        return {"status": "success", "message": "You have been unsubscribed from future communications."}
        
    except Exception as e:
        frappe.log_error(f"Error processing unsubscribe for prospect {prospect_name}: {str(e)}")
        return {"status": "error", "message": "An error occurred while processing your unsubscribe request."}
