"""
Lead Generation Scheduler
Handles automated collection, consolidation, and follow-up jobs
"""

import frappe
from frappe.utils import now, add_days, get_datetime
from typing import Dict, List, Any
import json

def run_daily_collectors():
    """Run daily data collection jobs"""
    
    # Check if any jobs are still running
    running_jobs = frappe.get_all("LeadGen Job", 
        filters={"status": "Running"}, 
        fields=["name", "job_type"]
    )
    
    if running_jobs:
        frappe.log_error("Previous jobs still running, skipping daily collection")
        return
    
    # Run collectors
    collectors = [
        {
            "job_type": "clinicaltrials",
            "params": {
                "priority": "Medium",
                "cancer_type": "cancer OR tumor OR oncology",
                "phase": "PHASE3 OR PHASE2",
                "status": "RECRUITING OR ACTIVE"
            }
        },
        {
            "job_type": "nih",
            "params": {
                "priority": "Medium",
                "activity_code": "R01,R21,R43,R44",
                "search_term": "oncology cancer clinical trial"
            }
        },
        {
            "job_type": "asco",
            "params": {
                "priority": "Medium",
                "year": "2024",
                "category": "Clinical Science"
            }
        }
    ]
    
    for collector in collectors:
        try:
            frappe.enqueue(
                "crm.api.leadgen.run_leadgen_job",
                job_type=collector["job_type"],
                params=collector["params"],
                queue="long"
            )
            frappe.logger("leadgen_scheduler").info(f"Queued {collector['job_type']} collector")
        except Exception as e:
            frappe.log_error(f"Failed to queue {collector['job_type']} collector: {str(e)}")

def run_consolidation():
    """Run daily consolidation job"""
    
    try:
        frappe.enqueue(
            "crm.api.leadgen.run_leadgen_job",
            job_type="consolidate",
            params={"priority": "High"},
            queue="long"
        )
        frappe.logger("leadgen_scheduler").info("Queued consolidation job")
    except Exception as e:
        frappe.log_error(f"Failed to queue consolidation job: {str(e)}")

def send_follow_ups():
    """Send scheduled follow-up emails"""
    
    try:
        frappe.enqueue(
            "crm.leadgen.outreach.follow_up_scheduler.send_scheduled_follow_ups",
            queue="short"
        )
        frappe.logger("leadgen_scheduler").info("Queued follow-up emails")
    except Exception as e:
        frappe.log_error(f"Failed to queue follow-up emails: {str(e)}")

def run_weekly_cleanup():
    """Run weekly cleanup and maintenance"""
    
    try:
        # Clean up old completed jobs (older than 30 days)
        old_jobs = frappe.get_all("LeadGen Job",
            filters={
                "status": "Completed",
                "modified": ["<", add_days(now(), -30)]
            },
            fields=["name"]
        )
        
        for job in old_jobs:
            frappe.delete_doc("LeadGen Job", job.name)
        
        frappe.logger("leadgen_scheduler").info(f"Cleaned up {len(old_jobs)} old jobs")
        
        # Archive old prospects (older than 90 days, not contacted)
        old_prospects = frappe.get_all("Lead Prospect",
            filters={
                "outreach_status": "Not Contacted",
                "modified": ["<", add_days(now(), -90)]
            },
            fields=["name"]
        )
        
        for prospect in old_prospects:
            prospect_doc = frappe.get_doc("Lead Prospect", prospect.name)
            prospect_doc.outreach_status = "Archived"
            prospect_doc.save()
        
        frappe.logger("leadgen_scheduler").info(f"Archived {len(old_prospects)} old prospects")
        
    except Exception as e:
        frappe.log_error(f"Failed to run weekly cleanup: {str(e)}")

def generate_weekly_report():
    """Generate weekly lead generation report"""
    
    try:
        # Get metrics for the week
        week_start = add_days(now(), -7)
        
        # New prospects this week
        new_prospects = frappe.db.count("Lead Prospect", {
            "creation": [">=", week_start]
        })
        
        # Prospects by tier
        tier_counts = frappe.db.sql("""
            SELECT tier, COUNT(*) as count
            FROM `tabLead Prospect`
            WHERE creation >= %s
            GROUP BY tier
        """, (week_start,), as_dict=True)
        
        # Outreach activity
        outreach_activity = frappe.db.sql("""
            SELECT outreach_status, COUNT(*) as count
            FROM `tabLead Prospect`
            WHERE creation >= %s
            GROUP BY outreach_status
        """, (week_start,), as_dict=True)
        
        # Job statistics
        job_stats = frappe.db.sql("""
            SELECT job_type, status, COUNT(*) as count
            FROM `tabLeadGen Job`
            WHERE creation >= %s
            GROUP BY job_type, status
        """, (week_start,), as_dict=True)
        
        # Create report
        report = {
            "period": f"Week ending {now()}",
            "new_prospects": new_prospects,
            "tier_breakdown": {t["tier"]: t["count"] for t in tier_counts},
            "outreach_breakdown": {o["outreach_status"]: o["count"] for o in outreach_activity},
            "job_statistics": job_stats
        }
        
        # Save report
        frappe.get_doc({
            "doctype": "LeadGen Job",
            "job_name": f"Weekly Report - {now()}",
            "job_type": "report",
            "status": "Completed",
            "params": frappe.as_json(report),
            "log": f"Weekly report generated: {new_prospects} new prospects",
            "owner": "Administrator"
        }).insert()
        
        frappe.logger("leadgen_scheduler").info("Generated weekly report")
        
    except Exception as e:
        frappe.log_error(f"Failed to generate weekly report: {str(e)}")

def run_enrichment_job():
    """Run enrichment job for high-tier prospects"""
    
    try:
        # Get Tier 1 prospects that need enrichment
        tier1_prospects = frappe.get_all("Lead Prospect",
            filters={
                "tier": "Tier 1",
                "enriched_data": ["is", "not set"]
            },
            fields=["name"],
            limit=50
        )
        
        if tier1_prospects:
            prospect_names = [p["name"] for p in tier1_prospects]
            
            frappe.enqueue(
                "crm.api.leadgen.run_leadgen_job",
                job_type="enrich",
                params={
                    "priority": "High",
                    "prospect_names": prospect_names
                },
                queue="long"
            )
            
            frappe.logger("leadgen_scheduler").info(f"Queued enrichment for {len(prospect_names)} Tier 1 prospects")
        
    except Exception as e:
        frappe.log_error(f"Failed to run enrichment job: {str(e)}")

def check_job_health():
    """Check health of running jobs and restart if needed"""
    
    try:
        # Find jobs that have been running too long (over 2 hours)
        long_running_jobs = frappe.get_all("LeadGen Job",
            filters={
                "status": "Running",
                "started_at": ["<", add_days(now(), -2/24)]  # 2 hours ago
            },
            fields=["name", "job_type", "started_at"]
        )
        
        for job in long_running_jobs:
            # Mark as failed and log
            job_doc = frappe.get_doc("LeadGen Job", job.name)
            job_doc.status = "Failed"
            job_doc.error_details = "Job timed out after 2 hours"
            job_doc.log = f"Job timed out, started at {job.started_at}"
            job_doc.save()
            
            frappe.log_error(f"Job {job.name} timed out and was marked as failed")
        
        frappe.logger("leadgen_scheduler").info(f"Checked {len(long_running_jobs)} long-running jobs")
        
    except Exception as e:
        frappe.log_error(f"Failed to check job health: {str(e)}")

def get_scheduler_status():
    """Get current scheduler status"""
    
    try:
        # Count jobs by status
        job_counts = frappe.db.sql("""
            SELECT status, COUNT(*) as count
            FROM `tabLeadGen Job`
            WHERE creation >= %s
            GROUP BY status
        """, (add_days(now(), -7),), as_dict=True)
        
        # Count prospects by tier
        prospect_counts = frappe.db.sql("""
            SELECT tier, COUNT(*) as count
            FROM `tabLead Prospect`
            GROUP BY tier
        """, as_dict=True)
        
        # Recent activity
        recent_jobs = frappe.get_all("LeadGen Job",
            fields=["name", "job_type", "status", "created"],
            limit=10,
            order_by="created desc"
        )
        
        return {
            "job_counts": {j["status"]: j["count"] for j in job_counts},
            "prospect_counts": {p["tier"]: p["count"] for p in prospect_counts},
            "recent_jobs": recent_jobs,
            "last_check": now()
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get scheduler status: {str(e)}")
        return {"error": str(e)}


