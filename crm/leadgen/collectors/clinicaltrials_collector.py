"""
ClinicalTrials.gov Collector
Implements rate-limited data collection from ClinicalTrials.gov API
"""

import frappe
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

class ClinicalTrialsCollector:
    """Collector for ClinicalTrials.gov data"""
    
    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        self.rate_limit = 100  # requests per minute
        self.time_window = 60  # seconds
        self.calls = []
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        # If at rate limit, wait
        if len(self.calls) >= self.rate_limit:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Record this call
        self.calls.append(now)
    
    def make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make rate-limited request to ClinicalTrials API"""
        self.wait_if_needed()
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"ClinicalTrials API request failed: {str(e)}")
            raise
    
    def collect_trials(self, params: Dict[str, Any], bookmark: str = None) -> List[Dict[str, Any]]:
        """Collect trials with bookmark pagination"""
        trials = []
        page = 1
        
        if bookmark and bookmark.isdigit():
            page = int(bookmark)
        
        while True:
            try:
                # Add pagination parameters
                request_params = params.copy()
                request_params.update({
                    "pageSize": 100,
                    "pageToken": str(page)
                })
                
                # Make API request
                response = self.make_request(request_params)
                
                if not response.get("studies"):
                    break
                
                # Process trials
                page_trials = self.process_trials(response["studies"])
                trials.extend(page_trials)
                
                # Check if we have more pages
                if len(response["studies"]) < 100:
                    break
                
                page += 1
                
                # Safety limit
                if page > 1000:  # Max 100k trials
                    break
                    
            except Exception as e:
                frappe.log_error(f"Error collecting trials page {page}: {str(e)}")
                break
        
        return trials
    
    def process_trials(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process raw trial data into structured format"""
        processed_trials = []
        
        for study in studies:
            try:
                # Extract basic trial info
                trial = {
                    "nct_id": study.get("protocolSection", {}).get("identificationModule", {}).get("nctId"),
                    "title": study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle"),
                    "status": study.get("protocolSection", {}).get("statusModule", {}).get("overallStatus"),
                    "phase": self.extract_phase(study),
                    "conditions": self.extract_conditions(study),
                    "locations": self.extract_locations(study),
                    "contacts": self.extract_contacts(study),
                    "raw_data": study
                }
                
                # Only include oncology trials
                if self.is_oncology_trial(trial):
                    processed_trials.append(trial)
                    
            except Exception as e:
                frappe.log_error(f"Error processing trial: {str(e)}")
                continue
        
        return processed_trials
    
    def extract_phase(self, study: Dict[str, Any]) -> str:
        """Extract trial phase"""
        phases = study.get("protocolSection", {}).get("designModule", {}).get("phases", [])
        if phases:
            return phases[0]
        return "Unknown"
    
    def extract_conditions(self, study: Dict[str, Any]) -> List[str]:
        """Extract trial conditions"""
        conditions = study.get("protocolSection", {}).get("conditionsModule", {}).get("conditions", [])
        return conditions
    
    def extract_locations(self, study: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trial locations"""
        locations = study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("locations", [])
        processed_locations = []
        
        for location in locations:
            processed_locations.append({
                "name": location.get("name"),
                "city": location.get("city"),
                "state": location.get("state"),
                "country": location.get("country")
            })
        
        return processed_locations
    
    def extract_contacts(self, study: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trial contacts"""
        contacts = study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("contacts", [])
        processed_contacts = []
        
        for contact in contacts:
            processed_contacts.append({
                "name": contact.get("name"),
                "title": contact.get("title"),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "role": contact.get("role")
            })
        
        return processed_contacts
    
    def is_oncology_trial(self, trial: Dict[str, Any]) -> bool:
        """Check if trial is oncology-related"""
        oncology_keywords = [
            "cancer", "tumor", "oncology", "carcinoma", "sarcoma", 
            "lymphoma", "leukemia", "melanoma", "metastatic"
        ]
        
        conditions = trial.get("conditions", [])
        title = trial.get("title", "").lower()
        
        # Check conditions
        for condition in conditions:
            if any(keyword in condition.lower() for keyword in oncology_keywords):
                return True
        
        # Check title
        if any(keyword in title for keyword in oncology_keywords):
            return True
        
        return False
    
    def create_prospects(self, trials: List[Dict[str, Any]], job_name: str) -> int:
        """Create Lead Prospect records from trials"""
        created_count = 0
        
        for trial in trials:
            try:
                # Extract PI information
                contacts = trial.get("contacts", [])
                pi_contact = None
                
                # Find Principal Investigator
                for contact in contacts:
                    if contact.get("role", "").lower() in ["principal investigator", "pi", "lead investigator"]:
                        pi_contact = contact
                        break
                
                # If no PI found, use first contact
                if not pi_contact and contacts:
                    pi_contact = contacts[0]
                
                if not pi_contact:
                    continue
                
                # Calculate lead score
                lead_score = self.calculate_lead_score(trial, pi_contact)
                
                # Determine tier
                tier = self.determine_tier(lead_score)
                
                # Create prospect
                prospect = frappe.get_doc({
                    "doctype": "Lead Prospect",
                    "pi_name": pi_contact.get("name"),
                    "pi_email": pi_contact.get("email"),
                    "institution": self.extract_institution(trial),
                    "cancer_type": self.extract_primary_cancer_type(trial),
                    "trial_phase": trial.get("phase"),
                    "tier": tier,
                    "lead_score": lead_score,
                    "source": "ClinicalTrials.gov",
                    "source_ref_id": trial.get("nct_id"),
                    "raw": frappe.as_json(trial.get("raw_data")),
                    "created_by_job": job_name,
                    "owner": frappe.session.user
                })
                
                # Check for duplicates
                existing = frappe.get_all(
                    "Lead Prospect",
                    filters={
                        "pi_email": pi_contact.get("email"),
                        "source_ref_id": trial.get("nct_id")
                    }
                )
                
                if not existing:
                    prospect.insert()
                    created_count += 1
                
            except Exception as e:
                frappe.log_error(f"Error creating prospect for trial {trial.get('nct_id')}: {str(e)}")
                continue
        
        return created_count
    
    def calculate_lead_score(self, trial: Dict[str, Any], pi_contact: Dict[str, Any]) -> float:
        """Calculate lead score based on trial and PI characteristics"""
        score = 0.0
        
        # Phase scoring (Phase 3 = highest)
        phase = trial.get("phase", "").lower()
        if "phase 3" in phase:
            score += 30
        elif "phase 2" in phase:
            score += 20
        elif "phase 1" in phase:
            score += 10
        
        # Status scoring (Active = highest)
        status = trial.get("status", "").lower()
        if "recruiting" in status:
            score += 25
        elif "active" in status:
            score += 20
        elif "completed" in status:
            score += 10
        
        # Contact completeness
        if pi_contact.get("email"):
            score += 15
        if pi_contact.get("phone"):
            score += 10
        if pi_contact.get("title"):
            score += 5
        
        # Institution scoring (major institutions get higher scores)
        institution = self.extract_institution(trial)
        if institution:
            major_institutions = ["university", "medical center", "cancer center", "hospital"]
            if any(inst in institution.lower() for inst in major_institutions):
                score += 10
        
        return min(score, 100.0)  # Cap at 100
    
    def determine_tier(self, lead_score: float) -> str:
        """Determine tier based on lead score"""
        if lead_score >= 70:
            return "Tier 1"
        elif lead_score >= 50:
            return "Tier 2"
        else:
            return "Tier 3"
    
    def extract_institution(self, trial: Dict[str, Any]) -> str:
        """Extract primary institution from trial"""
        locations = trial.get("locations", [])
        if locations:
            return locations[0].get("name", "")
        return ""
    
    def extract_primary_cancer_type(self, trial: Dict[str, Any]) -> str:
        """Extract primary cancer type from trial"""
        conditions = trial.get("conditions", [])
        if conditions:
            # Map common conditions to cancer types
            condition = conditions[0].lower()
            if "breast" in condition:
                return "Breast Cancer"
            elif "lung" in condition:
                return "Lung Cancer"
            elif "colorectal" in condition or "colon" in condition:
                return "Colorectal Cancer"
            elif "prostate" in condition:
                return "Prostate Cancer"
            elif "pancreatic" in condition:
                return "Pancreatic Cancer"
            elif "ovarian" in condition:
                return "Ovarian Cancer"
            elif "leukemia" in condition:
                return "Leukemia"
            elif "lymphoma" in condition:
                return "Lymphoma"
            elif "melanoma" in condition:
                return "Melanoma"
            else:
                return "Other"
        return "Unknown"

def run(job_name: str, params: Dict[str, Any]):
    """Run ClinicalTrials collector using unified job system"""
    
    job = frappe.get_doc("LeadGen Job", job_name)
    
    try:
        # Update job status
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()
        
        # Initialize collector
        collector = ClinicalTrialsCollector()
        
        # Set up collection parameters
        collection_params = {
            "query.cond": "cancer OR tumor OR oncology",
            "query.phase": "PHASE3 OR PHASE2",
            "query.status": "RECRUITING OR ACTIVE"
        }
        
        # Add custom parameters
        if params.get("cancer_type"):
            collection_params["query.cond"] = params["cancer_type"]
        if params.get("phase"):
            collection_params["query.phase"] = params["phase"]
        if params.get("status"):
            collection_params["query.status"] = params["status"]
        
        # Collect trials
        frappe.publish_realtime("leadgen_progress", {
            "job_name": job_name,
            "message": "Collecting trials from ClinicalTrials.gov...",
            "progress": 10
        })
        
        trials = collector.collect_trials(collection_params, job.bookmark)
        
        # Update progress
        frappe.publish_realtime("leadgen_progress", {
            "job_name": job_name,
            "message": f"Found {len(trials)} oncology trials",
            "progress": 50
        })
        
        # Create prospects
        created_count = collector.create_prospects(trials, job_name)
        
        # Update job completion
        job.status = "Completed"
        job.ended_at = frappe.utils.now()
        job.records_processed = len(trials)
        job.progress = 100
        job.log = f"Collected {len(trials)} trials, created {created_count} prospects"
        job.save()
        
        frappe.publish_realtime("leadgen_progress", {
            "job_name": job_name,
            "message": f"Completed: {created_count} prospects created",
            "progress": 100
        })
        
    except Exception as e:
        # Update job failure
        job.status = "Failed"
        job.ended_at = frappe.utils.now()
        job.error_details = str(e)
        job.log = f"Error: {str(e)}"
        job.save()
        
        frappe.log_error(f"LeadGen Job {job_name} failed: {str(e)}")
        
        frappe.publish_realtime("leadgen_progress", {
            "job_name": job_name,
            "message": f"Failed: {str(e)}",
            "progress": 0
        })

def collect_trials_dry_run(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Dry run collector with limited results"""
    collector = ClinicalTrialsCollector()
    
    # Limit parameters for dry run
    dry_run_params = params.copy()
    dry_run_params["pageSize"] = 10  # Limit to 10 trials
    
    trials = collector.collect_trials(dry_run_params)
    return trials[:5]  # Return max 5 trials for dry run
