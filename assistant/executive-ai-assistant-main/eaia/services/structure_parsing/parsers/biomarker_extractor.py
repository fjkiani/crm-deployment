"""
Biomarker extraction from eligibility criteria text
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Embedded Config to avoid external dependency
BIOMARKER_KEYWORDS: Dict[str, List[str]] = {
    "BRCA1/2": ["BRCA", "BRCA1", "BRCA2"],
    "HRD": ["HRD", "homologous recombination deficiency"],
    "TP53": ["TP53", "p53"],
    "KRAS": ["KRAS"],
    "NRAS": ["NRAS"],
    "BRAF": ["BRAF"],
    "HER2": ["HER2", "ERBB2"],
    "PD-L1": ["PD-L1", "PDL1", "CD274"],
    "MSI-H": ["MSI-H", "microsatellite instability high", "dMMR"],
    "TMB-H": ["TMB-H", "tumor mutational burden"],
    "NTRK": ["NTRK", "NTRK1", "NTRK2", "NTRK3"],
    "RET": ["RET"],
    "ALK": ["ALK"],
    "ROS1": ["ROS1"],
    "EGFR": ["EGFR"],
    "MET": ["MET", "HGFR"],
    "PIK3CA": ["PIK3CA"],
    "FGFR": ["FGFR", "FGFR1", "FGFR2", "FGFR3"],
    "CA-125": ["CA-125", "CA125", "MUC16"],
    "Folate Receptor Alpha": ["FOLR1", "folate receptor alpha", "FRalpha"]
}

def extract_biomarkers(eligibility_text: str) -> List[str]:
    """
    Extract biomarker names from eligibility criteria using keyword matching.
    """
    if not eligibility_text:
        return []
    
    biomarkers = []
    text_upper = eligibility_text.upper()
    
    for biomarker, keywords in BIOMARKER_KEYWORDS.items():
        for keyword in keywords:
            if keyword.upper() in text_upper:
                biomarkers.append(biomarker)
                break  # Only add once per biomarker
    
    return list(set(biomarkers))
