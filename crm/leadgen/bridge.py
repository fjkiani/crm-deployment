import frappe
import csv
import io
import json
from crm.leadgen.collectors import asco_collector
# Import other collectors as needed

def run_ingest(job_name: str, params: dict):
    """
    Hybrid Ingestion Job:
    1. Runs the specific collector (ASCO, NIH, etc.)
    2. Generates a Standard Schema CSV
    3. Triggers Core ETL (crm.api.etl)
    """
    job = frappe.get_doc("LeadGen Job", job_name)
    try:
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()

        source = params.get("source", "ASCO Abstracts")
        
        # 1. Collect & Extract
        data = []
        if source == "ASCO Abstracts":
            abstracts = asco_collector.collect_abstracts_with_bookmark(
                params.get("year", 2024),
                params.get("keyword", "immunotherapy"),
                params.get("max_results", 100),
                job.bookmark,
                0, # delay handled in collector or passed here? collector takes delay.
                job
            )
            data = asco_collector.extract_prospect_data(abstracts)
        else:
            raise NotImplementedError(f"Source {source} not supported in Bridge yet.")

        if not data:
            job.log = "No data collected."
            job.status = "Completed"
            job.save()
            return

        # 2. Convert to CSV
        csv_file = generate_csv(data)

        # 3. Create File Doc
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{source.replace(' ', '_')}_{job_name}.csv",
            "content": csv_file,
            "is_private": 1
        }).insert(ignore_permissions=True)

        # 4. Create CRM Import Job (ETL)
        import_job = frappe.get_doc({
            "doctype": "CRM Import Job",
            "title": f"Bridge Import: {source} ({job_name})",
            "source_type": "CSV",
            "file_url": file_doc.file_url,
            "mapping_profile": "LeadGen Standard", # We need to ensure this mapping exists!
            "dedupe": 1,
            "link_organization": 1,
            "status": "Queued"
        }).insert(ignore_permissions=True)

        job.log = f"Bridge successful. Triggered ETL Job: {import_job.name}"
        job.status = "Completed" # The LeadGen Job is done, the ETL job is separate.
        job.save()

        # Trigger ETL
        frappe.enqueue(
            "crm.api.etl.process_job",
            queue="long",
            job_name=import_job.name
        )

    except Exception as e:
        job.status = "Failed"
        job.log = f"Bridge Error: {str(e)}"
        job.save()
        frappe.log_error(f"Bridge Job {job_name} failed: {str(e)}")

def generate_csv(data_list: list[dict]) -> str:
    """
    Convert List[Dict] to CSV string.
    Ensures columns match 'LeadGen Standard' schema.
    """
    # Define Standard Header
    headers = [
        "email", "first_name", "last_name", "job_title", 
        "organization_name", "mobile_no", "website", 
        "source", "tier", "lead_score", "cancer_type", 
        "source_ref_id" # Mapped to specific fields
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()

    for item in data_list:
        # Map Item keys to Header keys
        row = {
            "email": item.get("pi_email"),
            "first_name": item.get("first_name"),
            "last_name": item.get("last_name"),
            "job_title": item.get("job_title"),
            "organization_name": item.get("institution"),
            "mobile_no": "", # ASCO usually doesn't have phone
            "website": "",
            "source": item.get("source"),
            "tier": item.get("tier"),
            "lead_score": item.get("lead_score"),
            "cancer_type": item.get("cancer_type"),
            "source_ref_id": item.get("source_ref_id")
        }
        writer.writerow(row)
    
    return output.getvalue()
