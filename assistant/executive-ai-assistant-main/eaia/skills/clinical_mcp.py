"""
Clinical Trials tool wrappers for LangChain integration
Transplanted from BioMed-MCP (Oncology Backend)
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Import pytrials client
try:
    from pytrials.client import ClinicalTrials
except ImportError:
    # Fallback or error warning
    print("⚠️ pytrials not installed. Run `pip install pytrials`.")
    ClinicalTrials = None

def get_clinical_trials_client():
    """Initialize Clinical Trials client"""
    if not ClinicalTrials:
        raise ImportError("pytrials library is missing.")
    return ClinicalTrials()

def format_clinical_results(results_data: List, max_chars: int = 5000) -> str:
    """Format clinical trials results for agent consumption"""
    if not results_data or len(results_data) <= 1:
        return "No clinical trials found"
    
    # Convert to DataFrame
    df = pd.DataFrame.from_records(results_data[1:], columns=results_data[0])
    
    if df.empty:
        return "No clinical trials found"
    
    # Create formatted summary
    summary = f"Found {len(df)} clinical trials:\n\n"
    
    for i, row in df.iterrows():
        trial_info = f"{i+1}. {row.get('Study Title', 'Untitled Study')}\n"
        trial_info += f"   NCT ID: {row.get('NCT Number', 'N/A')}\n"
        
        conditions = row.get('Conditions', 'N/A')
        if isinstance(conditions, str) and len(conditions) > 100:
            conditions = conditions[:100] + "..."
        trial_info += f"   Conditions: {conditions}\n"
        
        brief_summary = row.get('Brief Summary', '')
        if isinstance(brief_summary, str) and len(brief_summary) > 200:
            brief_summary = brief_summary[:200] + "..."
        if brief_summary:
            trial_info += f"   Summary: {brief_summary}\n"
        
        trial_info += "\n"
        summary += trial_info
        
        # Check character limit
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n\n[Results truncated for length...]"
            break
    
    return summary

class ClinicalTrialsSearchInput(BaseModel):
    """Input schema for clinical trials search"""
    search_expr: str = Field(description="Search expression or condition name")
    max_studies: int = Field(default=10, description="Maximum number of studies to return")

class ClinicalTrialDetailsInput(BaseModel):
    """Input schema for clinical trial details"""
    nct_id: str = Field(description="NCT ID of the clinical trial (e.g., NCT04280705)")

@tool("search_clinical_trials", args_schema=ClinicalTrialsSearchInput)
def search_clinical_trials(search_expr: str, max_studies: int = 10) -> str:
    """
    Search ClinicalTrials.gov for clinical trials by condition or keywords.
    Returns formatted list of trials with NCT IDs, titles, conditions, and summaries.
    """
    try:
        max_studies = min(max(1, max_studies), 50)
        ct = get_clinical_trials_client()
        
        fields = ["NCT Number", "Conditions", "Study Title", "Brief Summary"]
        results = ct.get_study_fields(
            search_expr=search_expr,
            fields=fields,
            max_studies=max_studies
        )
        
        formatted_results = format_clinical_results(results)
        if formatted_results == "No clinical trials found":
            return f"No clinical trials found for search: {search_expr}"
        
        return f"Clinical trials search results for '{search_expr}':\n\n{formatted_results}"
        
    except Exception as e:
        return f"Error searching clinical trials: {str(e)}"

@tool("get_clinical_trial_details", args_schema=ClinicalTrialDetailsInput)
def get_clinical_trial_details(nct_id: str) -> str:
    """
    Get detailed information about a specific clinical trial using its NCT ID.
    Returns comprehensive trial information including outcomes and eligibility.
    """
    try:
        ct = get_clinical_trials_client()
        study = ct.get_full_studies(search_expr=f"NCT Number={nct_id}", max_studies=1)
        
        if not study or len(study) <= 1:
            return f"Clinical trial with NCT ID {nct_id} not found"
        
        df = pd.DataFrame.from_records(study[1:], columns=study[0])
        if df.empty:
            return f"Clinical trial with NCT ID {nct_id} not found"
        
        trial = df.iloc[0]
        
        details = f"Clinical Trial Details for {nct_id}:\n\n"
        details += f"Title: {trial.get('Study Title', 'N/A')}\n"
        details += f"Status: {trial.get('Study Status', 'N/A')}\n"
        details += f"Phase: {trial.get('Study Phase', 'N/A')}\n"
        details += f"Conditions: {trial.get('Conditions', 'N/A')}\n"
        
        brief_summary = trial.get('Brief Summary', '')
        if brief_summary:
            details += f"\nSummary:\n{brief_summary}\n"
            
        eligibility = trial.get('Eligibility Criteria', '')
        if eligibility:
             # Clean up eligibility text slightly
            if len(eligibility) > 1000:
                eligibility = eligibility[:1000] + "..."
            details += f"\nEligibility Criteria:\n{eligibility}\n"
            
        return details
        
    except Exception as e:
        return f"Error retrieving details for NCT ID {nct_id}: {str(e)}"
