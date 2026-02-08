import frappe
import requests
import time
from datetime import datetime
import json
import re

def run(job_name: str, params: dict):
    """Run ASCO Abstracts collector using unified job system"""
    job = frappe.get_doc("LeadGen Job", job_name)
    try:
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()

        year = params.get("year", 2024)
        keyword = params.get("keyword", "immunotherapy")
        max_results = params.get("max_results", 100)
        rate_limit_per_minute = params.get("rate_limit_per_minute", 15)  # Conservative rate
        delay_between_requests = 60 / rate_limit_per_minute

        # 1. Collect
        abstracts = collect_abstracts_with_bookmark(year, keyword, max_results, job.bookmark, delay_between_requests, job)
        job.total_records = len(abstracts)
        job.save()

        # 2. Extract
        prospect_data_list = extract_prospect_data(abstracts)

        # 3. Load (Direct Insert - Legacy)
        # Check if we should use Hybrid Ingestion (Bridge) or Direct
        # For now, maintain backward compatibility
        prospects_created = save_prospects(prospect_data_list, job)

        job.bookmark = str(int(job.bookmark or 0) + max_results)  # Simple offset-based bookmark
        job.status = "Completed"
        job.ended_at = frappe.utils.now()
        job.log = f"Collected {len(abstracts)} abstracts, extracted {len(prospect_data_list)}, created {prospects_created} prospects"
        job.save()
    except Exception as e:
        job.status = "Failed"
        job.log = f"Error: {str(e)}"
        job.save()
        frappe.log_error(f"LeadGen Job {job_name} failed: {str(e)}")
        frappe.db.rollback()

# ... collect_abstracts_with_bookmark remains same ...

def extract_prospect_data(abstracts: list) -> list[dict]:
    """Pure transformation of ASCO structure to Lead Prospect dicts"""
    results = []
    for abstract in abstracts:
        try:
            # Extract relevant data from ASCO abstract structure
            abstract_id = abstract.get("id", "")
            title = abstract.get("title", "")
            authors = abstract.get("authors", [])
            institution = abstract.get("institution", "")
            abstract_text = abstract.get("abstract", "")
            presentation_type = abstract.get("presentation_type", "")
            session_title = abstract.get("session_title", "")
            
            # Get primary author (usually the presenting author)
            primary_author = None
            if authors:
                # Look for presenting author or first author
                for author in authors:
                    if author.get("is_presenting", False) or author.get("is_corresponding", False):
                        primary_author = author
                        break
                if not primary_author:
                    primary_author = authors[0]  # Fallback to first author
            
            if not primary_author:
                continue  # Skip if no author info

            pi_name = f"{primary_author.get('first_name', '')} {primary_author.get('last_name', '')}".strip()
            pi_email = primary_author.get("email", "")
            
            # Extract cancer type from abstract content
            cancer_type = extract_cancer_type_from_abstract(abstract_text, title)

            if pi_name:
                results.append({
                    "doctype": "Lead Prospect",
                    "pi_name": pi_name,
                    "pi_email": pi_email,
                    "institution": institution,
                    "cancer_type": cancer_type,
                    "lead_score": calculate_asco_lead_score(abstract),
                    "tier": assign_asco_tier(abstract),
                    "source": "ASCO Abstracts",
                    "source_ref_id": abstract_id,
                    "raw_data": json.dumps(abstract),
                    "status": "New",
                    "notes": f"ASCO {abstract.get('year', 'N/A')} Abstract\nTitle: {title}\nSession: {session_title}\nType: {presentation_type}",
                    "first_name": primary_author.get('first_name', ''),
                    "last_name": primary_author.get('last_name', ''),
                    "job_title": "Principal Investigator" # Default
                })
        except Exception as e:
            frappe.log_error(f"Error extracting abstract {abstract.get('id', 'unknown')}: {str(e)}")
    return results

def save_prospects(prospect_data_list: list[dict], job=None) -> int:
    """Save extracted data to Lead Prospect doctype (Legacy Path)"""
    prospects_created = 0
    for data in prospect_data_list:
        try:
            # Basic deduplication check
            existing_prospect = frappe.get_all(
                "Lead Prospect",
                filters={"source_ref_id": data["source_ref_id"], "source": "ASCO Abstracts"},
                limit=1
            )

            if not existing_prospect:
                # Remove extra fields not in Lead Prospect if any (e.g. first_name helper)
                # But Lead Prospect is dynamic or loose? No, strict.
                # 'first_name', 'last_name', 'job_title' are NOT in Lead Prospect standard probably.
                # We need to clean dict before insertion.
                clean_data = data.copy()
                clean_data.pop('first_name', None)
                clean_data.pop('last_name', None)
                clean_data.pop('job_title', None)
                
                prospect = frappe.get_doc(clean_data)
                prospect.insert(ignore_permissions=True)
                prospects_created += 1
                
                if job:
                    job.processed_records += 1
                    job.progress = int((job.processed_records / job.total_records) * 100) if job.total_records else 0
                    job.save(ignore_permissions=True)
            else:
                frappe.logger("asco_collector").info(f"Prospect with Abstract ID {data['source_ref_id']} already exists. Skipping.")

        except Exception as e:
            frappe.log_error(f"Error saving prospect {data.get('source_ref_id', 'unknown')}: {str(e)}")
    
    return prospects_created

def extract_cancer_type_from_abstract(abstract_text: str, title: str) -> str:
    """Extract cancer type from abstract text and title"""
    text_to_search = f"{title} {abstract_text}".lower()
    
    # Cancer type patterns
    cancer_patterns = {
        "breast cancer": ["breast", "mammary"],
        "lung cancer": ["lung", "pulmonary", "nsclc", "sclc"],
        "prostate cancer": ["prostate"],
        "colorectal cancer": ["colorectal", "colon", "rectal"],
        "pancreatic cancer": ["pancreatic", "pancreas"],
        "ovarian cancer": ["ovarian", "ovary"],
        "cervical cancer": ["cervical", "cervix"],
        "melanoma": ["melanoma"],
        "leukemia": ["leukemia", "leukaemia"],
        "lymphoma": ["lymphoma"],
        "brain tumor": ["brain", "cerebral", "glioma", "glioblastoma"],
        "sarcoma": ["sarcoma"],
        "hepatocellular carcinoma": ["hepatocellular", "liver"],
        "gastric cancer": ["gastric", "stomach"],
        "esophageal cancer": ["esophageal", "esophagus"],
        "bladder cancer": ["bladder"],
        "kidney cancer": ["kidney", "renal"],
        "thyroid cancer": ["thyroid"],
        "head and neck cancer": ["head and neck", "hnscc"],
        "pediatric cancer": ["pediatric", "childhood"]
    }
    
    found_types = []
    for cancer_type, patterns in cancer_patterns.items():
        for pattern in patterns:
            if pattern in text_to_search:
                found_types.append(cancer_type)
                break
    
    # Also check for general oncology terms
    oncology_terms = ["immunotherapy", "targeted therapy", "precision medicine", "biomarker", "metastatic"]
    has_oncology_focus = any(term in text_to_search for term in oncology_terms)
    
    if found_types:
        return ", ".join(found_types[:3])  # Limit to top 3 cancer types
    elif has_oncology_focus:
        return "Oncology Research"
    else:
        return "Cancer Research"

def calculate_asco_lead_score(abstract: dict) -> float:
    """Calculate lead score based on ASCO abstract characteristics"""
    score = 0.0
    
    # Base score for having an ASCO abstract
    score += 0.4
    
    # Presentation type scoring
    presentation_type = abstract.get("presentation_type", "").lower()
    if "oral" in presentation_type:
        score += 0.3  # Oral presentations are high value
    elif "poster" in presentation_type:
        score += 0.2  # Poster presentations are medium value
    else:
        score += 0.1
    
    # Abstract content scoring
    abstract_text = abstract.get("abstract", "").lower()
    title = abstract.get("title", "").lower()
    combined_text = f"{title} {abstract_text}"
    
    # High-value keywords
    high_value_keywords = [
        "immunotherapy", "car-t", "checkpoint inhibitor", "pd-1", "pd-l1",
        "precision medicine", "biomarker", "targeted therapy", "clinical trial",
        "phase ii", "phase iii", "randomized", "multicenter"
    ]
    
    keyword_count = sum(1 for keyword in high_value_keywords if keyword in combined_text)
    score += min(0.3, keyword_count * 0.05)  # Max 0.3 for keywords
    
    # Institution prestige scoring
    institution = abstract.get("institution", "").lower()
    prestigious_orgs = [
        "harvard", "stanford", "mit", "johns hopkins", "mayo clinic",
        "md anderson", "memorial sloan kettering", "dana farber",
        "university of california", "duke", "yale", "columbia"
    ]
    
    if any(prestigious in institution for prestigious in prestigious_orgs):
        score += 0.2
    
    # Session importance scoring
    session_title = abstract.get("session_title", "").lower()
    important_sessions = [
        "plenary", "keynote", "presidential", "late-breaking",
        "clinical science symposium", "education session"
    ]
    
    if any(important in session_title for important in important_sessions):
        score += 0.1
    
    return min(1.0, score)  # Cap at 1.0

def assign_asco_tier(abstract: dict) -> str:
    """Assign tier based on ASCO abstract characteristics"""
    score = calculate_asco_lead_score(abstract)
    
    if score >= 0.8:
        return "Tier 1"
    elif score >= 0.6:
        return "Tier 2"
    elif score >= 0.4:
        return "Tier 3"
    else:
        return "Unassigned"


