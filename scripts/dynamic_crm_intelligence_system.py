#!/usr/bin/env python3
"""
Dynamic CRM Intelligence System - Single Comprehensive Script
All functionality consolidated with dynamic configuration and no hard-coded values
"""

import os
import json
import csv
import re
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import argparse

@dataclass
class SystemConfig:
    """Dynamic system configuration - no hard-coded values"""

    # API Configuration
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com/search"
    tavily_timeout: int = 30
    tavily_max_retries: int = 3

    # File Paths (dynamically determined)
    base_dir: Path = Path.cwd()
    input_dir: Path = None
    output_dir: Path = None
    config_dir: Path = None

    # Processing Configuration
    max_companies_per_batch: int = 5
    search_results_per_query: int = 5
    rate_limit_delay: float = 1.0
    max_processing_time: int = 300  # 5 minutes

    # Company Configuration (dynamic)
    target_company: str = ""
    target_company_config: Dict[str, Any] = None

    # Email Configuration (dynamic)
    sender_company: str = ""
    sender_name: str = ""
    sender_title: str = ""
    sender_email: str = ""

    def __post_init__(self):
        """Initialize dynamic paths"""
        self.input_dir = self.base_dir / "data" / "input"
        self.output_dir = self.base_dir / "data" / "output"
        self.config_dir = self.base_dir / "config"

        # Load API key from environment
        self.tavily_api_key = os.getenv('TAVILY_API_KEY', '')

    def load_company_config(self, company_name: str) -> Dict[str, Any]:
        """Load company-specific configuration dynamically"""
        config_file = self.config_dir / f"{company_name.lower().replace(' ', '_')}_config.json"

        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)

        # Default company configuration
        return {
            "name": company_name,
            "industry": "Financial Services",
            "focus_areas": ["Investment Management", "Asset Management"],
            "decision_makers": {},
            "pain_points": ["Operational Efficiency", "Data Analysis", "Risk Management"],
            "recent_news": [],
            "partnerships": []
        }

    def save_company_config(self, company_name: str, config: Dict[str, Any]):
        """Save company-specific configuration"""
        self.config_dir.mkdir(exist_ok=True)
        config_file = self.config_dir / f"{company_name.lower().replace(' ', '_')}_config.json"

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def get_input_file(self, filename: str) -> Path:
        """Get dynamic input file path"""
        return self.input_dir / filename

    def get_output_file(self, filename: str) -> Path:
        """Get dynamic output file path"""
        return self.output_dir / filename

class DynamicCRMIntelligenceSystem:
    """Unified system with all functionality - no hard-coded values"""

    def __init__(self, config: SystemConfig):
        self.config = config
        self.session = requests.Session()
        self.logger = self._setup_logger()

        # Initialize data structures
        self.findings = {
            "company_overview": {},
            "executive_intelligence": {},
            "investment_intelligence": {},
            "partnership_intelligence": {},
            "news_intelligence": {},
            "digital_presence": {},
            "contact_intelligence": {},
            "data_sources": set()
        }

    def _setup_logger(self):
        """Setup dynamic logging"""
        import logging

        # Create output directory if it doesn't exist
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging with dynamic file path
        log_file = self.config.get_output_file("crm_intelligence_system.log")

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        return logging.getLogger("CRMIntelligenceSystem")

    def run_complete_workflow(self, company_name: str = None) -> Dict[str, Any]:
        """Complete intelligence gathering workflow"""

        company_name = company_name or self.config.target_company
        if not company_name:
            raise ValueError("Company name must be provided")

        self.logger.info(f"🚀 Starting complete workflow for: {company_name}")

        # Load company configuration dynamically
        company_config = self.config.load_company_config(company_name)
        self.config.target_company_config = company_config

        # Execute intelligence gathering phases
        results = {
            "company": company_name,
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "summary": {}
        }

        try:
            # Phase 1: Company Overview
            self.logger.info("📊 Phase 1: Gathering company overview")
            results["phases"]["overview"] = self._gather_company_overview(company_name)

            # Phase 2: Executive Intelligence
            self.logger.info("👥 Phase 2: Gathering executive intelligence")
            results["phases"]["executives"] = self._gather_executive_intelligence(company_name)

            # Phase 3: Investment Intelligence
            self.logger.info("💼 Phase 3: Gathering investment intelligence")
            results["phases"]["investments"] = self._gather_investment_intelligence(company_name)

            # Phase 4: Partnership Intelligence
            self.logger.info("🤝 Phase 4: Gathering partnership intelligence")
            results["phases"]["partnerships"] = self._gather_partnership_intelligence(company_name)

            # Phase 5: News Intelligence
            self.logger.info("📰 Phase 5: Gathering news intelligence")
            results["phases"]["news"] = self._gather_news_intelligence(company_name)

            # Phase 6: Digital Presence
            self.logger.info("🌐 Phase 6: Gathering digital presence")
            results["phases"]["digital"] = self._gather_digital_presence(company_name)

            # Phase 7: Generate Outreach
            self.logger.info("📧 Phase 7: Generating personalized outreach")
            results["phases"]["outreach"] = self._generate_personalized_outreach(results)

            # Create summary
            results["summary"] = self._create_workflow_summary(results)

            # Save results
            self._save_results(results)

            self.logger.info("✅ Complete workflow finished successfully")
            return results

        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {e}")
            results["error"] = str(e)
            return results

    def _gather_company_overview(self, company_name: str) -> Dict[str, Any]:
        """Gather comprehensive company overview"""

        queries = [
            f'"{company_name}" company overview background history',
            f'"{company_name}" business model products services',
            f'"{company_name}" market position industry standing',
            f'"{company_name}" leadership team executives'
        ]

        overview_data = {
            "basic_info": {},
            "leadership": [],
            "business_model": {},
            "market_position": {},
            "data_sources": []
        }

        for query in queries:
            results = self._search_api(query, max_results=3)
            for result in results.get("results", []):
                overview_data["data_sources"].append(result.get("url", ""))

                # Extract relevant information
                content = result.get("content", "")
                title = result.get("title", "")

                # Categorize information
                if "leadership" in query.lower() or "executive" in query.lower():
                    overview_data["leadership"].append({
                        "title": title,
                        "snippet": content[:200],
                        "url": result.get("url", "")
                    })
                elif "business model" in query.lower() or "products" in query.lower():
                    overview_data["business_model"]["description"] = content[:500]
                elif "market position" in query.lower():
                    overview_data["market_position"]["description"] = content[:500]

        return overview_data

    def _gather_executive_intelligence(self, company_name: str) -> Dict[str, Any]:
        """Gather executive and leadership intelligence"""

        queries = [
            f'"{company_name}" leadership team executives management board',
            f'"{company_name}" CEO founder chief executive officer',
            f'"{company_name}" key personnel senior management'
        ]

        executive_data = {
            "executives": [],
            "leadership_structure": {},
            "backgrounds": [],
            "decision_makers": []
        }

        for query in queries:
            results = self._search_api(query, max_results=4)
            for result in results.get("results", []):
                content = result.get("content", "")
                executives = self._extract_executive_info(content, result.get("title", ""))

                for exec_info in executives:
                    if not any(e["name"] == exec_info["name"] for e in executive_data["executives"]):
                        executive_data["executives"].append(exec_info)

        # Identify decision makers
        executive_data["decision_makers"] = [
            exec for exec in executive_data["executives"]
            if any(title in exec.get("title", "").lower()
                  for title in ["ceo", "founder", "chief", "president", "managing"])
        ]

        return executive_data

    def _gather_investment_intelligence(self, company_name: str) -> Dict[str, Any]:
        """Gather investment portfolio and strategy intelligence"""

        queries = [
            f'"{company_name}" investments portfolio companies',
            f'"{company_name}" investment strategy focus areas',
            f'"{company_name}" sectors industries specialization'
        ]

        investment_data = {
            "portfolio_companies": [],
            "investment_strategy": {},
            "sector_focus": [],
            "geographic_focus": []
        }

        for query in queries:
            results = self._search_api(query, max_results=4)
            for result in results.get("results", []):
                content = result.get("content", "")
                investments = self._extract_investment_info(content)

                investment_data["portfolio_companies"].extend(investments)

        # Remove duplicates
        seen = set()
        unique_investments = []
        for inv in investment_data["portfolio_companies"]:
            key = inv.get("company", "").lower()
            if key and key not in seen:
                seen.add(key)
                unique_investments.append(inv)

        investment_data["portfolio_companies"] = unique_investments

        return investment_data

    def _gather_partnership_intelligence(self, company_name: str) -> Dict[str, Any]:
        """Gather partnership and network intelligence"""

        queries = [
            f'"{company_name}" partnerships collaborations alliances',
            f'"{company_name}" strategic partners joint ventures',
            f'"{company_name}" industry associations memberships'
        ]

        partnership_data = {
            "strategic_partners": [],
            "industry_associations": [],
            "collaborations": []
        }

        for query in queries:
            results = self._search_api(query, max_results=3)
            for result in results.get("results", []):
                content = result.get("content", "")
                partnerships = self._extract_partnership_info(content)

                for partnership in partnerships:
                    if partnership.get("type") == "strategic_partner":
                        partnership_data["strategic_partners"].append(partnership)
                    elif partnership.get("type") == "association":
                        partnership_data["industry_associations"].append(partnership)
                    else:
                        partnership_data["collaborations"].append(partnership)

        return partnership_data

    def _gather_news_intelligence(self, company_name: str) -> Dict[str, Any]:
        """Gather news and developments intelligence"""

        queries = [
            f'"{company_name}" news updates press release',
            f'"{company_name}" company announcements developments',
            f'"{company_name}" milestones achievements awards'
        ]

        news_data = {
            "recent_news": [],
            "press_releases": [],
            "milestones": []
        }

        for query in queries:
            results = self._search_api(query, search_type="news", max_results=5)
            for result in results.get("results", []):
                news_item = self._process_news_item(result)

                if news_item:
                    if news_item.get("type") == "press_release":
                        news_data["press_releases"].append(news_item)
                    elif news_item.get("type") == "milestone":
                        news_data["milestones"].append(news_item)
                    else:
                        news_data["recent_news"].append(news_item)

        return news_data

    def _gather_digital_presence(self, company_name: str) -> Dict[str, Any]:
        """Gather digital presence and online intelligence"""

        queries = [
            f'"{company_name}" website homepage about us',
            f'site:linkedin.com/company "{company_name}"',
            f'"{company_name}" social media presence'
        ]

        digital_data = {
            "website_info": {},
            "social_media": {},
            "online_mentions": []
        }

        for query in queries:
            results = self._search_api(query, max_results=3)
            for result in results.get("results", []):
                url = result.get("url", "")
                content = result.get("content", "")

                if "linkedin.com" in url:
                    digital_data["social_media"]["linkedin"] = {
                        "url": url,
                        "content": content[:200]
                    }
                elif any(domain in url for domain in [".com", ".org", ".net"]):
                    digital_data["website_info"]["main_site"] = url

        return digital_data

    def _generate_personalized_outreach(self, intelligence_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized outreach based on gathered intelligence"""

        company_config = self.config.target_company_config or {}
        executives = intelligence_results.get("phases", {}).get("executives", {}).get("executives", [])

        outreach_campaign = {
            "company": intelligence_results.get("company", ""),
            "emails_generated": 0,
            "personalized_emails": [],
            "campaign_timestamp": datetime.now().isoformat()
        }

        for executive in executives[:3]:  # Limit to top 3 executives
            email = self._create_personalized_email(executive, intelligence_results)
            if email:
                outreach_campaign["personalized_emails"].append(email)
                outreach_campaign["emails_generated"] += 1

        return outreach_campaign

    def _create_personalized_email(self, executive: Dict[str, Any], intelligence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a personalized email for an executive"""

        if not executive.get("name") or not executive.get("title"):
            return None

        # Get company configuration
        company_config = self.config.target_company_config or {}

        # Dynamic email content based on role and company intelligence
        email_content = self._generate_email_content(executive, intelligence)

        return {
            "recipient": executive["name"],
            "title": executive["title"],
            "subject": email_content["subject"],
            "body": email_content["body"],
            "personalization_score": self._calculate_personalization_score(executive, intelligence),
            "generated_at": datetime.now().isoformat()
        }

    def _generate_email_content(self, executive: Dict[str, Any], intelligence: Dict[str, Any]) -> Dict[str, str]:
        """Generate dynamic email content based on executive role and intelligence"""

        name = executive.get("name", "").split()[0]
        title = executive.get("title", "").lower()
        company = intelligence.get("company", "")

        # Dynamic subject line based on role
        if "ceo" in title or "chief" in title:
            subject = f"AI-Powered Intelligence: Solving {company}'s Strategic Challenges"
        elif "president" in title:
            subject = f"Scaling {company}: AI-Driven Growth Solutions"
        else:
            subject = f"Operational Excellence: How AI Can Transform {company}"

        # Dynamic pain points based on role
        pain_points_map = {
            "ceo": ["Portfolio optimization", "Market prediction", "Risk management"],
            "president": ["Client acquisition", "Operational scaling", "Business growth"],
            "cio": ["Data analysis", "Technology integration", "Innovation"],
            "director": ["Team management", "Process optimization", "Strategic planning"]
        }

        role_key = "director"  # default
        for key in pain_points_map:
            if key in title:
                role_key = key
                break

        pain_points = pain_points_map[role_key]

        # Generate email body
        body = f"""Dear {name},

As {executive.get('title', 'Executive')} at {company}, you're navigating complex challenges in today's market.

Our AI-powered solutions directly address your key challenges:
• {pain_points[0]}
• {pain_points[1]}
• {pain_points[2]}

Would you be available for a brief conversation to explore how we're helping organizations like yours achieve breakthrough results?

Best regards,
{self.config.sender_name or '[Your Name]'}
{self.config.sender_title or '[Your Title]'}
{self.config.sender_company or '[Your Company]'}
{self.config.sender_email or '[your.email@company.com]'}"""

        return {
            "subject": subject,
            "body": body
        }

    def _calculate_personalization_score(self, executive: Dict[str, Any], intelligence: Dict[str, Any]) -> float:
        """Calculate personalization effectiveness score"""
        score = 0.5  # Base score

        # Name personalization
        if executive.get("name") and len(executive["name"].split()) > 1:
            score += 0.2

        # Role-specific content
        if executive.get("title"):
            score += 0.15

        # Company-specific references
        company = intelligence.get("company", "")
        if company:
            score += 0.15

        return min(score, 1.0)

    def _search_api(self, query: str, search_type: str = "general", max_results: int = 5) -> Dict[str, Any]:
        """Unified API search method"""

        if not self.config.tavily_api_key:
            self.logger.error("No API key configured")
            return {"results": []}

        # Rate limiting
        time.sleep(self.config.rate_limit_delay)

        try:
            response = self.session.post(
                self.config.tavily_base_url,
                json={
                    "api_key": self.config.tavily_api_key,
                    "query": query,
                    "search_type": search_type,
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": True
                },
                timeout=self.config.tavily_timeout
            )

            if response.status_code == 200:
                result = response.json()
                # Track data sources
                for item in result.get("results", []):
                    if item.get("url"):
                        self.findings["data_sources"].add(item["url"])
                return result
            else:
                self.logger.error(f"API error: {response.status_code}")
                return {"results": []}

        except Exception as e:
            self.logger.error(f"Search failed for '{query}': {e}")
            return {"results": []}

    def _extract_executive_info(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Extract executive information from content"""
        executives = []

        executive_titles = [
            'CEO', 'Chief Executive Officer', 'President', 'Founder', 'Co-founder',
            'Managing Partner', 'Partner', 'Managing Director', 'Director'
        ]

        content_lower = content.lower()
        title_lower = title.lower()

        for exec_title in executive_titles:
            if exec_title.lower() in content_lower or exec_title.lower() in title_lower:
                sentences = content.split('.')
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    if exec_title.lower() in sentence_lower:
                        words = sentence.split()
                        for i, word in enumerate(words):
                            if (word and len(word) > 1 and word[0].isupper() and
                                word.lower() not in ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'been']):
                                name = word
                                if i + 1 < len(words) and words[i+1][0].isupper():
                                    name += f" {words[i+1]}"

                                if not any(e["name"] == name for e in executives):
                                    executives.append({
                                        "name": name,
                                        "title": exec_title,
                                        "source_content": sentence.strip()[:100],
                                        "confidence": 0.7
                                    })
                                if len(executives) >= 3:
                                    break

        return executives

    def _extract_investment_info(self, content: str) -> List[Dict[str, Any]]:
        """Extract investment information from content"""
        investments = []

        investment_indicators = [
            "invested in", "investment in", "portfolio company", "acquired",
            "merged with", "partnered with", "backed by", "funded"
        ]

        sentences = content.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in investment_indicators):
                words = sentence.split()
                for i, word in enumerate(words):
                    if word[0].isupper() and len(word) > 3:
                        investments.append({
                            "company": word,
                            "context": sentence.strip(),
                            "type": "portfolio_company"
                        })
                        break

        return investments

    def _extract_partnership_info(self, content: str) -> List[Dict[str, Any]]:
        """Extract partnership information from content"""
        partnerships = []

        partnership_indicators = {
            "strategic_partner": ["strategic partner", "alliance", "partnership"],
            "association": ["member of", "affiliated with", "part of"],
            "board": ["board member", "board director", "advisory board"],
            "collaboration": ["collaborated with", "joint venture", "cooperation"]
        }

        for partnership_type, indicators in partnership_indicators.items():
            for indicator in indicators:
                if indicator in content.lower():
                    partnerships.append({
                        "type": partnership_type,
                        "context": content[:200],
                        "indicator": indicator
                    })

        return partnerships

    def _process_news_item(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and categorize news items"""
        content = result.get("content", "")
        title = result.get("title", "")

        if "press release" in title.lower() or "announces" in title.lower():
            news_type = "press_release"
        elif "interview" in title.lower() or "said" in content.lower():
            news_type = "executive_quote"
        elif any(word in content.lower() for word in ["milestone", "achievement", "award", "expansion"]):
            news_type = "milestone"
        else:
            news_type = "general_news"

        return {
            "type": news_type,
            "title": title,
            "content": content[:300],
            "url": result.get("url", ""),
            "published_date": result.get("published_date", "")
        }

    def _create_workflow_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive workflow summary"""

        phases = results.get("phases", {})

        summary = {
            "total_phases_completed": len(phases),
            "intelligence_categories": {},
            "data_quality_metrics": {},
            "key_findings": [],
            "recommendations": []
        }

        # Count intelligence categories
        for phase_name, phase_data in phases.items():
            if isinstance(phase_data, dict):
                for category, items in phase_data.items():
                    if isinstance(items, list):
                        summary["intelligence_categories"][f"{phase_name}_{category}"] = len(items)

        # Calculate data quality
        total_data_sources = len(self.findings["data_sources"])
        summary["data_quality_metrics"] = {
            "total_data_sources": total_data_sources,
            "data_source_quality": min(total_data_sources / 10, 1.0),
            "intelligence_completeness": len(phases) / 7  # 7 phases total
        }

        # Generate key findings
        if phases.get("executives", {}).get("executives"):
            exec_count = len(phases["executives"]["executives"])
            summary["key_findings"].append(f"Identified {exec_count} key executives")

        if phases.get("investments", {}).get("portfolio_companies"):
            portfolio_count = len(phases["investments"]["portfolio_companies"])
            summary["key_findings"].append(f"Discovered {portfolio_count} portfolio companies")

        if phases.get("outreach", {}).get("emails_generated", 0) > 0:
            email_count = phases["outreach"]["emails_generated"]
            summary["key_findings"].append(f"Generated {email_count} personalized outreach emails")

        # Generate recommendations
        if summary["data_quality_metrics"]["intelligence_completeness"] < 0.8:
            summary["recommendations"].append("Consider expanding search queries for more comprehensive intelligence")

        if total_data_sources < 5:
            summary["recommendations"].append("Limited data sources found - consider broader search scope")

        return summary

    def _save_results(self, results: Dict[str, Any]):
        """Save workflow results to files"""

        company_name = results.get("company", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save complete results
        output_file = self.config.get_output_file(f"{company_name.lower().replace(' ', '_')}_intelligence_{timestamp}.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Save outreach campaign separately
        outreach_data = results.get("phases", {}).get("outreach", {})
        if outreach_data.get("personalized_emails"):
            campaign_dir = self.config.output_dir / f"{company_name.lower().replace(' ', '_')}_outreach_{timestamp}"
            campaign_dir.mkdir(exist_ok=True)

            # Save campaign summary
            summary_file = campaign_dir / "campaign_summary.md"
            with open(summary_file, 'w') as f:
                f.write(f"# Outreach Campaign for {company_name}\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Emails Generated: {outreach_data.get('emails_generated', 0)}\n\n")

                for i, email in enumerate(outreach_data.get("personalized_emails", []), 1):
                    f.write(f"## Email {i}: {email['recipient']}\n")
                    f.write(f"**Title:** {email['title']}\n")
                    f.write(f"**Subject:** {email['subject']}\n\n")

            # Save individual emails
            for email in outreach_data.get("personalized_emails", []):
                safe_name = email["recipient"].lower().replace(" ", "_").replace(",", "")
                email_file = campaign_dir / f"{safe_name}_{email['title'].lower().replace(' ', '_')}.txt"

                with open(email_file, 'w') as f:
                    f.write(f"To: {email['recipient']}\n")
                    f.write(f"Subject: {email['subject']}\n\n")
                    f.write(email['body'])

        self.logger.info(f"Results saved to: {output_file}")

    def process_data_file(self, input_filename: str) -> Dict[str, Any]:
        """Process and organize data from input file"""

        input_file = self.config.get_input_file(input_filename)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        self.logger.info(f"Processing data file: {input_filename}")

        # Read and process data
        leads_data = []
        with open(input_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('organization_name', '').strip():
                    processed_lead = self._process_lead_record(row)
                    leads_data.append(processed_lead)

        # Generate outputs
        results = {
            "input_file": input_filename,
            "total_records": len(leads_data),
            "processed_at": datetime.now().isoformat(),
            "outputs": {}
        }

        # Create JSON output
        json_output = self.config.get_output_file("organized_leads.json")
        with open(json_output, 'w') as f:
            json.dump({"leads": leads_data}, f, indent=2)
        results["outputs"]["json"] = str(json_output)

        # Create CSV output
        csv_output = self.config.get_output_file("organized_leads.csv")
        if leads_data:
            fieldnames = leads_data[0].keys()
            with open(csv_output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(leads_data)
        results["outputs"]["csv"] = str(csv_output)

        # Create text summary
        text_output = self.config.get_output_file("data_summary.txt")
        with open(text_output, 'w') as f:
            f.write(f"Data Processing Summary\n")
            f.write(f"======================\n\n")
            f.write(f"Input File: {input_filename}\n")
            f.write(f"Total Records: {len(leads_data)}\n")
            f.write(f"Processed At: {datetime.now().isoformat()}\n\n")

            # Category breakdown
            categories = {}
            for lead in leads_data:
                cat = lead.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

            f.write("Records by Category:\n")
            for cat, count in sorted(categories.items()):
                f.write(f"  {cat}: {count}\n")

        results["outputs"]["summary"] = str(text_output)

        self.logger.info(f"Data processing complete. Processed {len(leads_data)} records.")
        return results

    def _process_lead_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual lead record"""

        processed = {
            "company": row.get('organization_name', '').strip(),
            "category": self._determine_category(row.get('organization_name', '')),
            "contact": {},
            "communication": {},
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "csv_import"
            }
        }

        # Process contact information
        contact_str = row.get('contact_info', '')
        if contact_str:
            name, title = self._parse_contact_info(contact_str)
            processed["contact"] = {
                "name": name,
                "title": title
            }

        # Process communication information
        processed["communication"] = {
            "emails": self._extract_emails(row),
            "phones": self._extract_phones(row),
            "websites": self._extract_websites(row),
            "linkedin": row.get('linkedin_url', ''),
            "twitter": row.get('twitter_handle', '')
        }

        return processed

    def _determine_category(self, company_name: str) -> str:
        """Determine company category based on name"""

        name_lower = company_name.lower()

        # Define category patterns
        categories = {
            "Private Equity": ["private equity", "pe firm", "equity firm"],
            "Venture Capital": ["venture capital", "vc firm", "venture"],
            "Asset Management": ["asset management", "asset mgr", "wealth management"],
            "Investment Banking": ["investment bank", "banking", "ib"],
            "Hedge Fund": ["hedge fund", "hedge"],
            "Family Office": ["family office", "sfo", "mfo"],
            "Financial Services": ["financial", "finance", "capital"]
        }

        for category, patterns in categories.items():
            if any(pattern in name_lower for pattern in patterns):
                return category

        return "Financial Services"  # Default category

    def _parse_contact_info(self, contact_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse contact string to extract name and title"""

        if not contact_str or contact_str.strip() == '':
            return None, None

        # Handle "Name, Title" format
        if ',' in contact_str:
            parts = contact_str.split(',', 1)
            return parts[0].strip(), parts[1].strip()

        # Handle parentheses format
        if '(' in contact_str and ')' in contact_str:
            match = re.match(r'([^()]+)\s*\(([^)]+)\)', contact_str)
            if match:
                return match.group(1).strip(), match.group(2).strip()

        # Return as name if no clear separation
        return contact_str.strip(), None

    def _extract_emails(self, row: Dict[str, Any]) -> List[str]:
        """Extract email addresses from row"""
        emails = []
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        for value in row.values():
            if isinstance(value, str):
                matches = re.findall(email_pattern, value)
                emails.extend(matches)

        return list(set(emails))  # Remove duplicates

    def _extract_phones(self, row: Dict[str, Any]) -> List[str]:
        """Extract phone numbers from row"""
        phones = []
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

        for value in row.values():
            if isinstance(value, str):
                matches = re.findall(phone_pattern, value)
                phones.extend(matches)

        return list(set(phones))  # Remove duplicates

    def _extract_websites(self, row: Dict[str, Any]) -> List[str]:
        """Extract website URLs from row"""
        websites = []
        website_pattern = r'https?://[^\s,]+'

        for value in row.values():
            if isinstance(value, str):
                matches = re.findall(website_pattern, value)
                websites.extend(matches)

        return list(set(websites))  # Remove duplicates


def main():
    """Main entry point with dynamic configuration"""

    parser = argparse.ArgumentParser(
        description="Dynamic CRM Intelligence System - Single Comprehensive Script"
    )

    parser.add_argument(
        '--company',
        help='Target company name for intelligence gathering'
    )

    parser.add_argument(
        '--input-file',
        help='Input data file to process (CSV format)'
    )

    parser.add_argument(
        '--config-file',
        help='JSON configuration file path'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory path'
    )

    args = parser.parse_args()

    # Initialize dynamic configuration
    config = SystemConfig()

    # Override configuration from arguments
    if args.company:
        config.target_company = args.company

    if args.output_dir:
        config.output_dir = Path(args.output_dir)

    # Load configuration file if provided
    if args.config_file and Path(args.config_file).exists():
        with open(args.config_file, 'r') as f:
            file_config = json.load(f)

        # Update config with file values
        for key, value in file_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # Initialize the system
    system = DynamicCRMIntelligenceSystem(config)

    print("🚀 Dynamic CRM Intelligence System")
    print("=" * 50)
    print(f"Company: {config.target_company or 'Not specified'}")
    print(f"API Key: {'Configured' if config.tavily_api_key else 'Missing'}")
    print(f"Output Dir: {config.output_dir}")
    print()

    try:
        if args.input_file:
            # Process data file
            print(f"📊 Processing data file: {args.input_file}")
            results = system.process_data_file(args.input_file)
            print("✅ Data processing complete!")
            print(f"   Processed {results['total_records']} records")
            print("   Generated files:")
            for output_type, filepath in results['outputs'].items():
                print(f"     • {output_type.upper()}: {filepath}")

        elif config.target_company:
            # Run intelligence workflow
            print(f"🧠 Running intelligence workflow for: {config.target_company}")
            results = system.run_complete_workflow(config.target_company)
            print("✅ Intelligence workflow complete!")
            print(f"   Phases completed: {len(results.get('phases', {}))}")
            print(f"   Data sources found: {len(system.findings['data_sources'])}")

            if 'error' in results:
                print(f"❌ Error: {results['error']}")
            else:
                print("   Generated personalized outreach campaign")

        else:
            print("❌ No action specified. Use --company for intelligence or --input-file for data processing")
            parser.print_help()

    except Exception as e:
        print(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
