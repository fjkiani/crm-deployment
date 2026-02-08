import frappe
import requests
import time
from datetime import datetime, timedelta
import json

def run(job_name: str, params: dict):
    """Run NIH RePORTER collector using unified job system"""
    job = frappe.get_doc("LeadGen Job", job_name)
    try:
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()

        query = params.get("query", "oncology")
        max_results = params.get("max_results", 100)
        rate_limit_per_minute = params.get("rate_limit_per_minute", 20)  # NIH allows higher rate
        delay_between_requests = 60 / rate_limit_per_minute

        grants = collect_grants_with_bookmark(query, max_results, job.bookmark, delay_between_requests, job)
        job.total_records = len(grants)
        job.save()

        prospects_created = process_and_save_grants(grants, job)

        job.bookmark = str(int(job.bookmark or 0) + max_results)  # Simple offset-based bookmark
        job.status = "Completed"
        job.ended_at = frappe.utils.now()
        job.log = f"Collected {len(grants)} grants, created {prospects_created} prospects"
        job.save()
    except Exception as e:
        job.status = "Failed"
        job.log = f"Error: {str(e)}"
        job.save()
        frappe.log_error(f"LeadGen Job {job_name} failed: {str(e)}")
        frappe.db.rollback()

def collect_grants_with_bookmark(query: str, max_results: int, bookmark: str = None, delay: float = 0, job=None):
    """Collect grants with bookmark pagination for resumability"""
    base_url = "https://api.reporter.nih.gov/v2/projects/search"
    grants = []
    offset = int(bookmark) if bookmark and bookmark.isdigit() else 0
    
    while len(grants) < max_results:
        try:
            # NIH RePORTER API payload
            payload = {
                "criteria": {
                    "advanced_text_search": {
                        "search_text": query,
                        "operator": "AND"
                    },
                    "fiscal_years": [2023, 2024],  # Recent grants
                    "activity_codes": ["R01", "R21", "R37", "P01", "P50"],  # Research grants
                    "org_cities": [],  # All cities
                    "org_states": [],  # All states
                    "org_countries": ["United States"]  # US only
                },
                "offset": offset,
                "limit": min(500, max_results - len(grants)),  # NIH max is 500 per request
                "sort_field": "project_start_date",
                "sort_order": "desc"
            }

            frappe.logger("nih_collector").info(f"Fetching NIH RePORTER grants with offset {offset}")
            response = requests.post(base_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                frappe.logger("nih_collector").info(f"No more grants found at offset {offset}")
                break
            
            grants.extend(results)
            offset += len(results)
            
            if job:
                job.bookmark = str(offset)
                job.processed_records = len(grants)
                job.progress = int((len(grants) / max_results) * 100)
                job.save(ignore_permissions=True)

            time.sleep(delay)  # Respect rate limit

        except requests.exceptions.RequestException as e:
            frappe.log_error(f"NIH RePORTER API request failed at offset {offset}: {str(e)}")
            break
        except json.JSONDecodeError as e:
            frappe.log_error(f"NIH RePORTER API response JSON decode error at offset {offset}: {str(e)}")
            break
        except Exception as e:
            frappe.log_error(f"Unexpected error in NIH RePORTER collector at offset {offset}: {str(e)}")
            break

    return grants[:max_results]  # Ensure we don't exceed max_results

def process_and_save_grants(grants: list, job=None):
    """Process raw grant data and save as Lead Prospects"""
    prospects_created = 0
    for grant in grants:
        try:
            # Extract relevant data from NIH RePORTER structure
            project_number = grant.get("project_number", "")
            project_title = grant.get("project_title", "")
            principal_investigators = grant.get("principal_investigators", [])
            organization = grant.get("organization", {})
            project_start_date = grant.get("project_start_date", "")
            project_end_date = grant.get("project_end_date", "")
            abstract_text = grant.get("abstract_text", "")
            
            # Get PI information
            if principal_investigators:
                pi = principal_investigators[0]  # Primary PI
                pi_name = pi.get("first_name", "") + " " + pi.get("last_name", "")
                pi_email = pi.get("email", "")
            else:
                pi_name = "N/A"
                pi_email = ""

            # Get organization info
            org_name = organization.get("org_name", "N/A")
            org_city = organization.get("org_city", "")
            org_state = organization.get("org_state", "")
            org_country = organization.get("org_country", "")

            # Extract cancer-related keywords from abstract
            cancer_keywords = extract_cancer_keywords(abstract_text)
            cancer_type = ", ".join(cancer_keywords) if cancer_keywords else "Oncology Research"

            # Basic deduplication check
            existing_prospect = frappe.get_all(
                "Lead Prospect",
                filters={"source_ref_id": project_number, "source": "NIH RePORTER"},
                limit=1
            )

            if not existing_prospect and pi_name != "N/A":
                prospect = frappe.get_doc({
                    "doctype": "Lead Prospect",
                    "pi_name": pi_name.strip(),
                    "pi_email": pi_email,
                    "institution": f"{org_name}, {org_city}, {org_state}".strip(", "),
                    "cancer_type": cancer_type,
                    "lead_score": calculate_nih_lead_score(grant),
                    "tier": assign_nih_tier(grant),
                    "source": "NIH RePORTER",
                    "source_ref_id": project_number,
                    "raw_data": json.dumps(grant),
                    "status": "New",
                    "notes": f"Grant: {project_title}\nPeriod: {project_start_date} - {project_end_date}"
                })
                prospect.insert(ignore_permissions=True)
                prospects_created += 1
                
                if job:
                    job.processed_records += 1
                    job.progress = int((job.processed_records / job.total_records) * 100) if job.total_records else 0
                    job.save(ignore_permissions=True)
            else:
                frappe.logger("nih_collector").info(f"Prospect with Project Number {project_number} already exists or no PI name. Skipping.")

        except Exception as e:
            frappe.log_error(f"Error processing grant {grant.get('project_number', 'unknown')}: {str(e)}")
    
    return prospects_created

def extract_cancer_keywords(abstract_text: str) -> list:
    """Extract cancer-related keywords from abstract text"""
    cancer_types = [
        "breast cancer", "lung cancer", "prostate cancer", "colorectal cancer",
        "pancreatic cancer", "ovarian cancer", "cervical cancer", "melanoma",
        "leukemia", "lymphoma", "brain tumor", "glioblastoma", "sarcoma",
        "hepatocellular carcinoma", "gastric cancer", "esophageal cancer",
        "bladder cancer", "kidney cancer", "thyroid cancer", "head and neck cancer",
        "pediatric cancer", "metastatic", "immunotherapy", "targeted therapy",
        "chemotherapy", "radiation therapy", "precision medicine", "biomarker"
    ]
    
    abstract_lower = abstract_text.lower()
    found_keywords = []
    
    for cancer_type in cancer_types:
        if cancer_type in abstract_lower:
            found_keywords.append(cancer_type.title())
    
    return list(set(found_keywords))  # Remove duplicates

def calculate_nih_lead_score(grant: dict) -> float:
    """Calculate lead score based on NIH grant characteristics"""
    score = 0.0
    
    # Base score for having a grant
    score += 0.3
    
    # Activity code scoring (higher for research grants)
    activity_codes = grant.get("activity_codes", [])
    for code in activity_codes:
        if code.get("code") in ["R01", "P01", "P50"]:  # High-value grants
            score += 0.3
        elif code.get("code") in ["R21", "R37"]:  # Medium-value grants
            score += 0.2
        else:
            score += 0.1
    
    # Abstract relevance scoring
    abstract_text = grant.get("abstract_text", "").lower()
    cancer_keywords = [
        "cancer", "oncology", "tumor", "carcinoma", "metastasis", 
        "immunotherapy", "biomarker", "precision medicine"
    ]
    
    keyword_count = sum(1 for keyword in cancer_keywords if keyword in abstract_text)
    score += min(0.3, keyword_count * 0.05)  # Max 0.3 for keywords
    
    # Recent grant scoring
    project_start_date = grant.get("project_start_date", "")
    if project_start_date:
        try:
            start_date = datetime.strptime(project_start_date, "%Y-%m-%d")
            if start_date >= datetime.now() - timedelta(days=365):  # Within last year
                score += 0.2
        except ValueError:
            pass
    
    # Organization prestige scoring (simplified)
    organization = grant.get("organization", {})
    org_name = organization.get("org_name", "").lower()
    prestigious_orgs = [
        "harvard", "stanford", "mit", "johns hopkins", "mayo clinic",
        "md anderson", "memorial sloan kettering", "dana farber"
    ]
    
    if any(prestigious in org_name for prestigious in prestigious_orgs):
        score += 0.2
    
    return min(1.0, score)  # Cap at 1.0

def assign_nih_tier(grant: dict) -> str:
    """Assign tier based on NIH grant characteristics"""
    score = calculate_nih_lead_score(grant)
    
    if score >= 0.8:
        return "Tier 1"
    elif score >= 0.6:
        return "Tier 2"
    elif score >= 0.4:
        return "Tier 3"
    else:
        return "Unassigned"
