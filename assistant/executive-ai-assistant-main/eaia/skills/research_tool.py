"""
Research Intelligence Tool
Transplanted from: enhanced_pi_intelligence_extractor.py
Extracts PI publication history from PubMed to personalize outreach.
"""
import requests
import time
from langchain_core.tools import tool

class ResearchIntelligence:
    """Wrapper for PubMed Intelligence Logic"""
    
    @staticmethod
    def get_pi_publications(pi_name: str, limit: int = 5) -> dict:
        """
        Fetches recent publications for a PI from PubMed.
        Logic adapted from 'enhanced_pi_intelligence_extractor.py'
        Returns dict with keys: 'publications', 'research_focus'
        """
        publications = []
        try:
            # 1. Construct Broad Search Query
            if ',' in pi_name:
                parts = pi_name.split(',')
                last = parts[0].strip()
                initial = parts[1].strip()[0] if len(parts) > 1 and parts[1].strip() else ''
                term = f"{last} {initial}[Author]"
            else:
                parts = pi_name.split()
                last = parts[-1]
                initial = parts[0][0] if parts else ''
                term = f"{last} {initial}[Author]"

            # E-Utils Search
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retmax={limit}&retmode=json"
            
            # Retry Loop for Search
            data = None
            for attempt in range(3):
                try:
                    resp = requests.get(search_url, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        break
                except requests.RequestException as e:
                    print(f"PubMed Search Retry {attempt+1}: {e}")
                    time.sleep(2)
            
            if not data:
                return {"publications": [], "research_focus": []}

            ids = data.get('esearchresult', {}).get('idlist', [])
            
            if not ids:
                return {"publications": [], "research_focus": []}
                
            # 2. Fetch Details
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
            
            # Retry Loop for Details
            summary_data = None
            for attempt in range(3):
                try:
                    resp = requests.get(fetch_url, timeout=30)
                    if resp.status_code == 200:
                        summary_data = resp.json().get('result', {})
                        break
                except requests.RequestException as e:
                    print(f"PubMed Summary Retry {attempt+1}: {e}")
                    time.sleep(2)

            if not summary_data:
                return {"publications": [], "research_focus": []}
            
            for pmid in ids:
                if pmid in summary_data:
                    doc = summary_data[pmid]
                    title = doc.get("title", "")
                    publications.append({
                        "pmid": pmid,
                        "title": title,
                        "journal": doc.get("source", ""),
                        "date": doc.get("pubdate", "")
                    })
            
            # Simple Keyword Extraction (Enhancement)
            all_text = " ".join([p["title"].lower() for p in publications])
            common_terms = ["cancer", "study", "analysis", "patients", "treatment", "clinical", "trial"]
            words = [w.strip(".,;:()") for w in all_text.split() if len(w) > 4 and w not in common_terms]
            
            from collections import Counter
            counts = Counter(words)
            top_keywords = [pair[0] for pair in counts.most_common(5)]
            
            return {
                "publications": publications,
                "research_focus": top_keywords,  # Inferred
                "recent_publications": publications # Alias for compatibility
            }
                    
        except Exception as e:
            print(f"PubMed Critical Error: {e}")
            return {"publications": [], "research_focus": []}
            
        return {"publications": publications, "research_focus": []}

@tool("get_research_profile")
def get_research_profile(pi_name: str) -> str:
    """
    [INTELLIGENCE] Fetches recent research publications for a Principal Investigator (PI).
    Use this to personalize emails or calls with specific references to their work.
    """
    res = ResearchIntelligence.get_pi_publications(pi_name)
    pubs = res.get("publications", [])
    focus = res.get("research_focus", [])
    
    if not pubs:
        return f"No recent publications found for {pi_name}."
        
    summary = f"RESEARCH PROFILE: {pi_name}\n"
    summary += f"Inferred Focus: {', '.join(focus)}\n"
    summary += "Recent Publications:\n"
    for p in pubs:
        summary += f"- {p['title']} ({p['journal']}, {p['date']})\n"
        
    return summary
