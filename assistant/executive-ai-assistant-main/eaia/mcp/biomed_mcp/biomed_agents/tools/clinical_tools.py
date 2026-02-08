"""
Clinical Trials tool wrappers for LangChain integration
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Import existing Clinical Trials client
import sys
import os

try:
    from pytrials.client import ClinicalTrials
except ImportError as e:
    raise ImportError(f"Could not import Clinical Trials client. Ensure pytrials is installed. Error: {e}")


def get_clinical_trials_client():
    """Initialize Clinical Trials client"""
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
    
    Supports searches for:
    - Medical conditions: "diabetes", "cancer", "COVID-19"
    - Treatment types: "gene therapy", "immunotherapy"
    - Combined searches: "diabetes AND metformin"
    
    Returns formatted list of trials with NCT IDs, titles, conditions, and summaries.
    """
    try:
        # Validate max_studies
        max_studies = min(max(1, max_studies), 50)
        
        ct = get_clinical_trials_client()
        
        # Search for clinical trials
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
    
    Returns comprehensive trial information including study design, eligibility criteria,
    outcomes, and contact information.
    """
    try:
        ct = get_clinical_trials_client()
        
        # Get full study details
        study = ct.get_full_studies(search_expr=f"NCT Number={nct_id}", max_studies=1)
        
        if not study or len(study) <= 1:
            return f"Clinical trial with NCT ID {nct_id} not found"
        
        # Convert to DataFrame for easier handling
        df = pd.DataFrame.from_records(study[1:], columns=study[0])
        
        if df.empty:
            return f"Clinical trial with NCT ID {nct_id} not found"
        
        trial = df.iloc[0]
        
        # Format detailed information
        details = f"Clinical Trial Details for {nct_id}:\n\n"
        details += f"Title: {trial.get('Study Title', 'N/A')}\n"
        details += f"NCT Number: {trial.get('NCT Number', 'N/A')}\n"
        details += f"Study Type: {trial.get('Study Type', 'N/A')}\n"
        details += f"Study Phase: {trial.get('Study Phase', 'N/A')}\n"
        details += f"Study Status: {trial.get('Study Status', 'N/A')}\n"
        details += f"Conditions: {trial.get('Conditions', 'N/A')}\n"
        details += f"Interventions: {trial.get('Interventions', 'N/A')}\n"
        
        # Add brief summary
        brief_summary = trial.get('Brief Summary', '')
        if brief_summary:
            details += f"\nBrief Summary:\n{brief_summary}\n"
        
        # Add detailed description if available
        detailed_desc = trial.get('Detailed Description', '')
        if detailed_desc and detailed_desc != brief_summary:
            # Truncate if very long
            if len(detailed_desc) > 2000:
                detailed_desc = detailed_desc[:2000] + "..."
            details += f"\nDetailed Description:\n{detailed_desc}\n"
        
        # Add eligibility criteria
        eligibility = trial.get('Eligibility Criteria', '')
        if eligibility:
            if len(eligibility) > 1000:
                eligibility = eligibility[:1000] + "..."
            details += f"\nEligibility Criteria:\n{eligibility}\n"
        
        # Add outcome measures
        primary_outcome = trial.get('Primary Outcome Measures', '')
        if primary_outcome:
            details += f"\nPrimary Outcome Measures:\n{primary_outcome}\n"
        
        return details
        
    except Exception as e:
        return f"Error retrieving details for NCT ID {nct_id}: {str(e)}"


@tool("analyze_clinical_trials_patterns")
def analyze_clinical_trials_patterns(search_expr: str, max_studies: int = 20) -> str:
    """
    Analyze patterns and trends in clinical trials for a given condition or intervention.
    
    Provides statistical insights including study phases, statuses, and intervention types.
    """
    try:
        ct = get_clinical_trials_client()
        
        # Get trials with additional fields for analysis
        fields = ["NCT Number", "Study Title", "Study Type", "Study Phase", 
                 "Study Status", "Conditions", "Interventions"]
        results = ct.get_study_fields(
            search_expr=search_expr,
            fields=fields,
            max_studies=max_studies
        )
        
        if not results or len(results) <= 1:
            return f"No clinical trials found for analysis: {search_expr}"
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame.from_records(results[1:], columns=results[0])
        
        if df.empty:
            return f"No clinical trials found for analysis: {search_expr}"
        
        # Perform analysis
        analysis = f"Clinical Trials Pattern Analysis for '{search_expr}':\n\n"
        analysis += f"Total Studies Analyzed: {len(df)}\n\n"
        
        # Study Phase Distribution
        if 'Study Phase' in df.columns:
            phase_counts = df['Study Phase'].value_counts()
            analysis += "Study Phase Distribution:\n"
            for phase, count in phase_counts.head(5).items():
                analysis += f"  {phase}: {count}\n"
            analysis += "\n"
        
        # Study Status Distribution
        if 'Study Status' in df.columns:
            status_counts = df['Study Status'].value_counts()
            analysis += "Study Status Distribution:\n"
            for status, count in status_counts.head(5).items():
                analysis += f"  {status}: {count}\n"
            analysis += "\n"
        
        # Study Type Distribution
        if 'Study Type' in df.columns:
            type_counts = df['Study Type'].value_counts()
            analysis += "Study Type Distribution:\n"
            for study_type, count in type_counts.head(5).items():
                analysis += f"  {study_type}: {count}\n"
            analysis += "\n"
        
        # Recent studies (if we have study titles that might contain years)
        analysis += f"Key Insights:\n"
        analysis += f"- Most common phase: {phase_counts.index[0] if 'Study Phase' in df.columns and not phase_counts.empty else 'N/A'}\n"
        analysis += f"- Most common status: {status_counts.index[0] if 'Study Status' in df.columns and not status_counts.empty else 'N/A'}\n"
        analysis += f"- Primary study type: {type_counts.index[0] if 'Study Type' in df.columns and not type_counts.empty else 'N/A'}\n"
        
        return analysis
        
    except Exception as e:
        return f"Error analyzing clinical trials patterns: {str(e)}"


# Export the tools for use in agents
CLINICAL_TOOLS = [search_clinical_trials, get_clinical_trial_details, analyze_clinical_trials_patterns]