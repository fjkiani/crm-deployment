import frappe
import json
from difflib import SequenceMatcher
import re
from typing import List, Dict, Tuple

def run(job_name: str, params: dict):
    """Run consolidation and deduplication job using unified job system"""
    job = frappe.get_doc("LeadGen Job", job_name)
    try:
        job.status = "Running"
        job.started_at = frappe.utils.now()
        job.save()

        match_threshold = params.get("match_threshold", 0.8)
        auto_merge_threshold = params.get("auto_merge_threshold", 0.95)
        dry_run = params.get("dry_run", False)

        # Get all prospects for deduplication
        prospects = frappe.get_all(
            "Lead Prospect",
            fields=["name", "pi_name", "pi_email", "institution", "source", "source_ref_id"],
            filters={"status": ["!=", "Discarded"]}
        )
        
        job.total_records = len(prospects)
        job.save()

        matches_found = find_duplicate_prospects(prospects, match_threshold, job)
        matches_processed = process_matches(matches_found, auto_merge_threshold, dry_run, job)

        job.status = "Completed"
        job.ended_at = frappe.utils.now()
        job.log = f"Found {matches_found} potential matches, processed {matches_processed} matches"
        job.save()
    except Exception as e:
        job.status = "Failed"
        job.log = f"Error: {str(e)}"
        job.save()
        frappe.log_error(f"LeadGen Job {job_name} failed: {str(e)}")
        frappe.db.rollback()

def find_duplicate_prospects(prospects: List[Dict], match_threshold: float, job=None) -> int:
    """Find potential duplicate prospects using multiple matching strategies"""
    matches_found = 0
    processed_pairs = set()
    
    for i, prospect1 in enumerate(prospects):
        for j, prospect2 in enumerate(prospects[i+1:], i+1):
            # Skip if already processed this pair
            pair_key = tuple(sorted([prospect1["name"], prospect2["name"]]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)
            
            # Calculate match score
            match_score, match_reason = calculate_match_score(prospect1, prospect2)
            
            if match_score >= match_threshold:
                # Check if match already exists
                existing_match = frappe.get_all(
                    "Lead Prospect Match",
                    filters={
                        "prospect1": ["in", [prospect1["name"], prospect2["name"]]],
                        "prospect2": ["in", [prospect1["name"], prospect2["name"]]],
                        "status": ["!=", "Dismissed"]
                    },
                    limit=1
                )
                
                if not existing_match:
                    # Create match record
                    match_doc = frappe.get_doc({
                        "doctype": "Lead Prospect Match",
                        "prospect1": prospect1["name"],
                        "prospect2": prospect2["name"],
                        "match_score": match_score,
                        "match_reason": match_reason,
                        "status": "Pending Review"
                    })
                    match_doc.insert(ignore_permissions=True)
                    matches_found += 1
                    
                    if job:
                        job.processed_records += 1
                        job.progress = int((job.processed_records / job.total_records) * 100) if job.total_records else 0
                        job.save(ignore_permissions=True)
    
    return matches_found

def calculate_match_score(prospect1: Dict, prospect2: Dict) -> Tuple[float, str]:
    """Calculate match score between two prospects using multiple criteria"""
    scores = []
    reasons = []
    
    # Name matching
    name_score = calculate_name_similarity(prospect1["pi_name"], prospect2["pi_name"])
    if name_score > 0.8:
        scores.append(name_score)
        reasons.append(f"Name similarity: {name_score:.2f}")
    
    # Email matching (exact match)
    if prospect1["pi_email"] and prospect2["pi_email"]:
        if prospect1["pi_email"].lower() == prospect2["pi_email"].lower():
            scores.append(1.0)
            reasons.append("Exact email match")
    
    # Institution matching
    institution_score = calculate_institution_similarity(prospect1["institution"], prospect2["institution"])
    if institution_score > 0.7:
        scores.append(institution_score)
        reasons.append(f"Institution similarity: {institution_score:.2f}")
    
    # Source combination bonus (different sources = higher confidence)
    if prospect1["source"] != prospect2["source"]:
        scores.append(0.1)  # Small bonus for cross-source matches
        reasons.append("Cross-source match")
    
    # Calculate weighted average
    if scores:
        # Weight name and email more heavily
        weighted_score = 0.0
        total_weight = 0.0
        
        for score in scores:
            if score == 1.0:  # Exact email match
                weighted_score += score * 0.4
                total_weight += 0.4
            elif "Name similarity" in str(reasons):
                weighted_score += score * 0.3
                total_weight += 0.3
            elif "Institution similarity" in str(reasons):
                weighted_score += score * 0.2
                total_weight += 0.2
            else:
                weighted_score += score * 0.1
                total_weight += 0.1
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0.0
        reason_text = "; ".join(reasons)
        
        return final_score, reason_text
    
    return 0.0, "No significant matches found"

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names using fuzzy matching"""
    if not name1 or not name2:
        return 0.0
    
    # Normalize names
    name1_norm = normalize_name(name1)
    name2_norm = normalize_name(name2)
    
    # Use SequenceMatcher for fuzzy matching
    similarity = SequenceMatcher(None, name1_norm, name2_norm).ratio()
    
    # Also check for exact match after normalization
    if name1_norm == name2_norm:
        return 1.0
    
    return similarity

def normalize_name(name: str) -> str:
    """Normalize name for comparison"""
    if not name:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = re.sub(r'\s+', ' ', name.lower().strip())
    
    # Remove common titles and suffixes
    titles = ["dr", "prof", "professor", "md", "phd", "jr", "sr", "iii", "ii"]
    for title in titles:
        normalized = re.sub(rf'\b{title}\b', '', normalized)
    
    # Remove extra spaces again
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def calculate_institution_similarity(inst1: str, inst2: str) -> float:
    """Calculate similarity between two institution names"""
    if not inst1 or not inst2:
        return 0.0
    
    # Normalize institution names
    inst1_norm = normalize_institution(inst1)
    inst2_norm = normalize_institution(inst2)
    
    # Use SequenceMatcher for fuzzy matching
    similarity = SequenceMatcher(None, inst1_norm, inst2_norm).ratio()
    
    # Also check for exact match after normalization
    if inst1_norm == inst2_norm:
        return 1.0
    
    return similarity

def normalize_institution(inst: str) -> str:
    """Normalize institution name for comparison"""
    if not inst:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = re.sub(r'\s+', ' ', inst.lower().strip())
    
    # Remove common institution suffixes
    suffixes = ["university", "college", "medical center", "hospital", "institute", "clinic"]
    for suffix in suffixes:
        normalized = re.sub(rf'\b{suffix}\b', '', normalized)
    
    # Remove city/state information (common in institution names)
    normalized = re.sub(r',\s*[a-z\s]+$', '', normalized)  # Remove trailing city/state
    
    # Remove extra spaces again
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def process_matches(matches_found: int, auto_merge_threshold: float, dry_run: bool, job=None) -> int:
    """Process found matches - auto-merge high confidence matches"""
    matches_processed = 0
    
    # Get all pending matches
    pending_matches = frappe.get_all(
        "Lead Prospect Match",
        filters={"status": "Pending Review"},
        fields=["name", "prospect1", "prospect2", "match_score", "match_reason"]
    )
    
    for match in pending_matches:
        try:
            if match["match_score"] >= auto_merge_threshold and not dry_run:
                # Auto-merge high confidence matches
                merge_prospects(match["prospect1"], match["prospect2"], match["name"])
                matches_processed += 1
                
                if job:
                    job.processed_records += 1
                    job.progress = int((job.processed_records / job.total_records) * 100) if job.total_records else 0
                    job.save(ignore_permissions=True)
            else:
                # Leave for manual review
                frappe.logger("consolidator").info(f"Match {match['name']} left for manual review (score: {match['match_score']:.2f})")
                
        except Exception as e:
            frappe.log_error(f"Error processing match {match['name']}: {str(e)}")
    
    return matches_processed

def merge_prospects(prospect1_name: str, prospect2_name: str, match_name: str):
    """Merge two prospects into one, keeping the higher-scored one"""
    prospect1 = frappe.get_doc("Lead Prospect", prospect1_name)
    prospect2 = frappe.get_doc("Lead Prospect", prospect2_name)
    
    # Determine which prospect to keep (higher lead score)
    if prospect1.lead_score >= prospect2.lead_score:
        keep_prospect = prospect1
        merge_prospect = prospect2
    else:
        keep_prospect = prospect2
        merge_prospect = prospect1
    
    # Merge data from both prospects
    merged_data = merge_prospect_data(keep_prospect, merge_prospect)
    
    # Update the kept prospect with merged data
    for field, value in merged_data.items():
        if hasattr(keep_prospect, field) and value:
            setattr(keep_prospect, field, value)
    
    # Add note about the merge
    merge_note = f"Merged with {merge_prospect.name} (source: {merge_prospect.source}) on {frappe.utils.now()}"
    if keep_prospect.notes:
        keep_prospect.notes += f"\n{merge_note}"
    else:
        keep_prospect.notes = merge_note
    
    keep_prospect.save(ignore_permissions=True)
    
    # Mark the other prospect as discarded
    merge_prospect.status = "Discarded"
    merge_prospect.notes = f"Merged into {keep_prospect.name} on {frappe.utils.now()}"
    merge_prospect.save(ignore_permissions=True)
    
    # Update the match record
    match_doc = frappe.get_doc("Lead Prospect Match", match_name)
    match_doc.status = "Merged"
    match_doc.save(ignore_permissions=True)
    
    frappe.logger("consolidator").info(f"Merged {merge_prospect.name} into {keep_prospect.name}")

def merge_prospect_data(keep_prospect, merge_prospect):
    """Merge data from two prospects, preferring non-empty values"""
    merged = {}
    
    # Fields to merge
    fields_to_merge = [
        "pi_email", "phone", "cancer_type", "notes"
    ]
    
    for field in fields_to_merge:
        keep_value = getattr(keep_prospect, field, None)
        merge_value = getattr(merge_prospect, field, None)
        
        # Prefer non-empty values
        if not keep_value and merge_value:
            merged[field] = merge_value
        elif keep_value and merge_value and keep_value != merge_value:
            # Combine values if they're different
            if field == "cancer_type":
                # Combine cancer types
                combined_types = list(set((keep_value + ", " + merge_value).split(", ")))
                merged[field] = ", ".join(combined_types)
            elif field == "notes":
                # Combine notes
                merged[field] = f"{keep_value}\n---\n{merge_value}"
    
    return merged


