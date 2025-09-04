"""
Data Management Layer
Handles input/output and data persistence
"""

from typing import Dict, List, Any, Optional
import json
import csv
from pathlib import Path
from datetime import datetime

class DataManager:
    """Manages data input/output and persistence"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_path = Path(config.get('data_path', 'data'))

        # Create data directories
        self.input_path = self.base_path / 'input'
        self.output_path = self.base_path / 'output'
        self.cache_path = self.base_path / 'cache'

        for path in [self.input_path, self.output_path, self.cache_path]:
            path.mkdir(parents=True, exist_ok=True)

    def load_companies_from_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Load company data from CSV"""
        filepath = self.input_path / filename

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        companies = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append(row)

        return companies

    def save_intelligence_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save intelligence results to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intelligence_results_{timestamp}.json"

        filepath = self.output_path / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        return str(filepath)

    def save_outreach_campaign(self, campaign: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save outreach campaign results"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company = campaign.get('company', 'unknown').replace(' ', '_')
            filename = f"outreach_campaign_{company}_{timestamp}.json"

        filepath = self.output_path / filename

        with open(filepath, 'w') as f:
            json.dump(campaign, f, indent=2, default=str)

        return str(filepath)

    def cache_intelligence(self, company_name: str, intelligence: Dict[str, Any]) -> None:
        """Cache intelligence results"""
        cache_file = self.cache_path / f"{company_name.replace(' ', '_')}.json"

        cache_data = {
            "company": company_name,
            "intelligence": intelligence,
            "cached_at": datetime.now().isoformat()
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)

    def get_cached_intelligence(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Get cached intelligence if available"""
        cache_file = self.cache_path / f"{company_name.replace(' ', '_')}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is still valid (24 hours)
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            if (datetime.now() - cached_at).total_seconds() < 86400:  # 24 hours
                return cache_data['intelligence']

        return None

    def export_to_csv(self, data: List[Dict[str, Any]], filename: str, fields: List[str] = None) -> str:
        """Export data to CSV format"""
        filepath = self.output_path / filename

        if not fields and data:
            fields = list(data[0].keys())

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)

        return str(filepath)
