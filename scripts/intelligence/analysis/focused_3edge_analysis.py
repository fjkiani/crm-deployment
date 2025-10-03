#!/usr/bin/env python3
"""
Focused Intelligence Analysis for 3EDGE Asset Management
Gathers comprehensive business intelligence for targeted outreach
"""

import os
import requests
import re
import json
from typing import List, Dict, Tuple
from datetime import datetime
import time

class Focused3EDGEAnalyzer:
    """Specialized analyzer for 3EDGE Asset Management"""

    def __init__(self, tavily_api_key: str):
        self.tavily_api_key = tavily_api_key
        self.company = "3EDGE Asset Management"
        self.findings = {
            "investment_preferences": [],
            "investment_history": [],
            "activity_level": [],
            "contact_information": [],
            "company_overview": {},
            "recent_news": [],
            "partnerships": [],
            "data_sources": set()
        }

    def search_tavily(self, query: str, max_results: int = 8) -> Dict:
        """Search Tavily API with enhanced parameters"""
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": True,
                    "search_depth": "advanced"
                },
                timeout=20
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error: {response.status_code}")
                return {"error": f"API error {response.status_code}"}

        except Exception as e:
            print(f"❌ Search error: {e}")
            return {"error": str(e)}

    def analyze_investment_preferences(self) -> None:
        """Analyze what 3EDGE likes to invest in"""
        print("💼 ANALYZING INVESTMENT PREFERENCES...")

        investment_queries = [
            f'"{self.company}" investment strategy focus sectors industries',
            f'"{self.company}" investment philosophy asset allocation',
            f'"{self.company}" portfolio composition holdings',
            f'"{self.company}" investment approach risk management',
            f'"{self.company}" target investments sectors markets'
        ]

        for query in investment_queries:
            print(f"   🔍 {query}")
            results = self.search_tavily(query, 6)

            if "error" not in results:
                for result in results.get("results", []):
                    content = result.get("content", "")
                    title = result.get("title", "")
                    url = result.get("url", "")

                    # Extract investment preferences
                    preferences = self.extract_investment_preferences(content, title)
                    if preferences:
                        for pref in preferences:
                            self.findings["investment_preferences"].append({
                                "preference": pref,
                                "context": content[:200],
                                "source": title,
                                "url": url
                            })

                    # Track data sources
                    if url:
                        self.findings["data_sources"].add(url)

            time.sleep(1.5)

    def analyze_investment_history(self) -> None:
        """Analyze what 3EDGE has invested in"""
        print("📈 ANALYZING INVESTMENT HISTORY...")

        history_queries = [
            f'"{self.company}" investments portfolio companies acquisitions',
            f'"{self.company}" deals transactions announcements',
            f'"{self.company}" investment partners collaborators',
            f'"{self.company}" portfolio holdings companies',
            f'"{self.company}" investment track record performance'
        ]

        for query in history_queries:
            print(f"   🔍 {query}")
            results = self.search_tavily(query, 6)

            if "error" not in results:
                for result in results.get("results", []):
                    content = result.get("content", "")
                    title = result.get("title", "")
                    url = result.get("url", "")

                    # Extract investment history
                    investments = self.extract_investment_history(content, title)
                    if investments:
                        for inv in investments:
                            self.findings["investment_history"].append({
                                "investment": inv,
                                "context": content[:200],
                                "source": title,
                                "url": url
                            })

                    if url:
                        self.findings["data_sources"].add(url)

            time.sleep(1.5)

    def analyze_activity_level(self) -> None:
        """Analyze how active 3EDGE is"""
        print("⚡ ANALYZING ACTIVITY LEVEL...")

        activity_queries = [
            f'"{self.company}" recent deals news announcements',
            f'"{self.company}" press releases updates developments',
            f'"{self.company}" market activity investment frequency',
            f'"{self.company}" growth expansion plans',
            f'"{self.company}" industry presence engagement'
        ]

        recent_deals = 0
        press_releases = 0

        for query in activity_queries:
            print(f"   🔍 {query}")
            results = self.search_tavily(query, 5)

            if "error" not in results:
                for result in results.get("results", []):
                    content = result.get("content", "")
                    title = result.get("title", "")
                    url = result.get("url", "")

                    # Count activity indicators
                    if any(word in title.lower() for word in ['announces', 'launches', 'acquires', 'partners']):
                        recent_deals += 1

                    if any(word in title.lower() for word in ['press release', 'announcement', 'news']):
                        press_releases += 1

                    # Extract activity indicators
                    activity = self.extract_activity_indicators(content, title)
                    if activity:
                        self.findings["activity_level"].append({
                            "activity": activity,
                            "context": content[:200],
                            "source": title,
                            "url": url
                        })

                    if url:
                        self.findings["data_sources"].add(url)

            time.sleep(1.5)

        # Summarize activity level
        self.findings["activity_level"].insert(0, {
            "summary": {
                "recent_deals": recent_deals,
                "press_releases": press_releases,
                "activity_level": "High" if recent_deals > 3 else "Medium" if recent_deals > 1 else "Low"
            }
        })

    def gather_contact_information(self) -> None:
        """Gather contact information and points of contact"""
        print("📞 GATHERING CONTACT INFORMATION...")

        contact_queries = [
            f'"{self.company}" contact information email phone',
            f'"{self.company}" executive contacts leadership team',
            f'"{self.company}" press contact media relations',
            f'"{self.company}" investor relations contact',
            f'"{self.company}" business development contact'
        ]

        for query in contact_queries:
            print(f"   🔍 {query}")
            results = self.search_tavily(query, 5)

            if "error" not in results:
                for result in results.get("results", []):
                    content = result.get("content", "")
                    title = result.get("title", "")
                    url = result.get("url", "")

                    # Extract contact information
                    contacts = self.extract_contact_information(content, title)
                    if contacts:
                        for contact in contacts:
                            self.findings["contact_information"].append({
                                "contact": contact,
                                "context": content[:200],
                                "source": title,
                                "url": url
                            })

                    if url:
                        self.findings["data_sources"].add(url)

            time.sleep(1.5)

    def gather_company_overview(self) -> None:
        """Gather comprehensive company overview"""
        print("🏢 GATHERING COMPANY OVERVIEW...")

        overview_query = f'"{self.company}" company overview background history leadership'
        results = self.search_tavily(overview_query, 5)

        if "error" not in results:
            all_content = ""
            for result in results.get("results", []):
                all_content += result.get("content", "") + " "

            self.findings["company_overview"] = {
                "name": self.company,
                "description": all_content[:500],
                "key_points": self.extract_key_company_points(all_content),
                "last_updated": datetime.now().isoformat()
            }

    def extract_investment_preferences(self, content: str, title: str) -> List[str]:
        """Extract investment preferences from content"""
        preferences = []

        # Look for investment focus areas
        investment_focus = [
            "multi-asset", "equity", "fixed income", "alternative investments",
            "private equity", "venture capital", "real estate", "hedge funds",
            "ETF", "mutual funds", "institutional", "retail investors",
            "active management", "passive management", "quantitative",
            "fundamental analysis", "growth investing", "value investing"
        ]

        content_lower = content.lower()
        title_lower = title.lower()

        for focus in investment_focus:
            if focus in content_lower or focus in title_lower:
                preferences.append(focus.title())

        # Look for specific sectors mentioned
        sectors = [
            "technology", "healthcare", "financial services", "consumer",
            "industrial", "energy", "materials", "communication services",
            "utilities", "real estate", "emerging markets", "developed markets"
        ]

        for sector in sectors:
            if sector in content_lower:
                preferences.append(f"Sector: {sector.title()}")

        return list(set(preferences))  # Remove duplicates

    def extract_investment_history(self, content: str, title: str) -> List[str]:
        """Extract investment history from content"""
        investments = []

        # Look for investment indicators
        investment_indicators = [
            "invested in", "acquired", "partnered with", "backed",
            "portfolio company", "investment in", "funded"
        ]

        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in investment_indicators):
                # Extract company names (capitalized words)
                words = sentence.split()
                for i, word in enumerate(words):
                    if (word and len(word) > 2 and word[0].isupper() and
                        word.lower() not in ['the', 'and', 'for', 'with', 'this', 'that', 'has', 'have']):
                        company_name = word
                        if i + 1 < len(words) and words[i+1][0].isupper():
                            company_name += f" {words[i+1]}"

                        if company_name != self.company and len(company_name) > 3:
                            investments.append(f"Invested in {company_name}")

        return list(set(investments))

    def extract_activity_indicators(self, content: str, title: str) -> str:
        """Extract activity level indicators"""
        activity_signals = {
            "high": ["announces", "launches", "expands", "acquires", "partners", "raises", "grows"],
            "medium": ["updates", "continues", "maintains", "develops"],
            "low": ["maintains", "stable", "consistent"]
        }

        content_lower = content.lower()
        title_lower = title.lower()

        for level, signals in activity_signals.items():
            if any(signal in content_lower or signal in title_lower for signal in signals):
                return f"{level.title()} Activity: {', '.join([s for s in signals if s in content_lower or s in title_lower])}"

        return "General activity detected"

    def extract_contact_information(self, content: str, title: str) -> List[Dict]:
        """Extract contact information from content"""
        contacts = []

        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        for email in emails:
            if not any('@' in c.get('email', '') for c in contacts):
                contacts.append({
                    "type": "email",
                    "email": email,
                    "context": "Found in content"
                })

        # Phone pattern (US format)
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, content)
        for phone in phones:
            if not any(phone in c.get('phone', '') for c in contacts):
                contacts.append({
                    "type": "phone",
                    "phone": phone,
                    "context": "Found in content"
                })

        # Look for executive names with contact context
        executive_indicators = ['CEO', 'President', 'Director', 'Managing', 'Partner', 'Chief']
        content_lower = content.lower()

        for indicator in executive_indicators:
            if indicator.lower() in content_lower:
                sentences = content.split('.')
                for sentence in sentences:
                    if indicator.lower() in sentence.lower():
                        words = sentence.split()
                        for i, word in enumerate(words):
                            if (word and len(word) > 1 and word[0].isupper() and
                                word.lower() not in ['the', 'and', 'for', 'with']):
                                name = word
                                if i + 1 < len(words) and words[i+1][0].isupper():
                                    name += f" {words[i+1]}"

                                if len(name) > 3 and name != self.company:
                                    contacts.append({
                                        "type": "executive",
                                        "name": name,
                                        "title": indicator,
                                        "context": sentence.strip()[:100]
                                    })

        return contacts

    def extract_key_company_points(self, content: str) -> List[str]:
        """Extract key company points"""
        points = []

        # Look for key company information
        key_indicators = [
            "founded", "headquartered", "assets under management", "AUM",
            "employees", "offices", "specializes", "focuses", "manages",
            "serves", "provides", "offers"
        ]

        sentences = content.split('.')
        for sentence in sentences[:10]:  # First 10 sentences
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in key_indicators):
                points.append(sentence.strip())

        return points[:5]  # Top 5 points

    def run_comprehensive_analysis(self) -> Dict:
        """Run complete analysis"""
        print("🚀 STARTING COMPREHENSIVE ANALYSIS FOR 3EDGE ASSET MANAGEMENT")
        print("=" * 80)

        # Run all analysis phases
        self.gather_company_overview()
        self.analyze_investment_preferences()
        self.analyze_investment_history()
        self.analyze_activity_level()
        self.gather_contact_information()

        print("\n" + "=" * 80)
        print("🎉 ANALYSIS COMPLETE!")
        print("=" * 80)

        return self.findings

    def generate_outreach_email(self) -> str:
        """Generate personalized cold outreach email"""
        # Gather key information for personalization
        company_info = self.findings.get("company_overview", {})
        investment_prefs = [p.get("preference", "") for p in self.findings.get("investment_preferences", [])]
        investment_history = [h.get("investment", "") for h in self.findings.get("investment_history", [])]
        contacts = self.findings.get("contact_information", [])
        activity_level = self.findings.get("activity_level", [])

        # Find primary contact
        primary_contact = None
        for contact in contacts:
            if contact.get("type") == "executive" and "CEO" in contact.get("title", ""):
                primary_contact = contact
                break
        if not primary_contact:
            primary_contact = contacts[0] if contacts else {"name": "Valued Partner"}

        # Extract key investment themes
        investment_themes = []
        for pref in investment_prefs[:3]:  # Top 3 preferences
            if "multi-asset" in pref.lower():
                investment_themes.append("multi-asset investment strategies")
            elif "equity" in pref.lower():
                investment_themes.append("equity investments")
            elif "fixed income" in pref.lower():
                investment_themes.append("fixed income solutions")
            elif "etf" in pref.lower():
                investment_themes.append("ETF strategies")

        # Activity level summary
        activity_summary = "actively engaged in the market"
        if activity_level and activity_level[0].get("summary"):
            summary = activity_level[0]["summary"]
            if summary.get("activity_level") == "High":
                activity_summary = "highly active with recent market developments"
            elif summary.get("activity_level") == "Medium":
                activity_summary = "steadily active in the investment space"

        # Generate personalized email
        email_template = f"""Subject: Strategic Partnership Opportunity in Multi-Asset Investment Solutions

Dear {primary_contact.get('name', 'Valued Partner')},

I hope this email finds you well. My name is [Your Name], and I'm reaching out from [Your Company] where we specialize in helping sophisticated investment firms like 3EDGE Asset Management optimize their multi-asset investment strategies.

I've been following 3EDGE's impressive work in the investment management space, particularly your focus on {' and '.join(investment_themes[:2]) if investment_themes else 'innovative investment solutions'}. Your recent developments and {activity_summary} demonstrate the kind of forward-thinking approach that aligns perfectly with our partnership objectives.

At [Your Company], we help firms like yours:
• Enhance portfolio diversification across multiple asset classes
• Streamline investment processes and risk management
• Access cutting-edge analytical tools and market insights
• Scale operations efficiently while maintaining quality

I'd love to explore how we might collaborate to support your continued growth in the multi-asset investment space. Would you be available for a brief 15-minute conversation next week to discuss potential synergies?

Looking forward to the possibility of working together.

Best regards,
[Your Name]
[Your Title]
[Your Company]
[Your Phone Number]
[Your Email Address]
[Your LinkedIn Profile]

P.S. I noticed your recent work with {' and '.join([inv.replace('Invested in ', '') for inv in investment_history[:2]]) if investment_history else 'various investment initiatives'} - impressive portfolio expansion!

---
[Your Company] | [Your Website] | [Your Address]
Confidentiality Notice: This email contains confidential information and is intended only for the addressee(s)."""

        return email_template

def main():
    """Run the focused analysis"""
    print("🎯 FOCUSED 3EDGE ASSET MANAGEMENT ANALYSIS")
    print("This analysis targets specific business intelligence for outreach")
    print()

    # Check API key
    api_key = os.getenv('TAVILY_API_KEY')
    if not api_key:
        print("❌ TAVILY_API_KEY not set")
        print("Run: export TAVILY_API_KEY='your_key_here'")
        return

    # Initialize analyzer
    analyzer = Focused3EDGEAnalyzer(api_key)

    # Run comprehensive analysis
    findings = analyzer.run_comprehensive_analysis()

    # Display results
    print("\n📊 ANALYSIS RESULTS:")
    print("-" * 50)

    print(f"🏢 Company: {analyzer.company}")
    print(f"💼 Investment Preferences: {len(findings['investment_preferences'])} found")
    print(f"📈 Investment History: {len(findings['investment_history'])} found")
    print(f"⚡ Activity Level: {len(findings['activity_level'])} indicators")
    print(f"📞 Contact Information: {len(findings['contact_information'])} found")
    print(f"🔗 Data Sources: {len(findings['data_sources'])} URLs")

    # Show key findings
    if findings['investment_preferences']:
        print("\n💼 INVESTMENT PREFERENCES:")
        for pref in findings['investment_preferences'][:5]:
            print(f"   • {pref.get('preference', 'N/A')}")

    if findings['investment_history']:
        print("\n📈 INVESTMENT HISTORY:")
        for inv in findings['investment_history'][:5]:
            print(f"   • {inv.get('investment', 'N/A')}")

    if findings['activity_level'] and findings['activity_level'][0].get('summary'):
        summary = findings['activity_level'][0]['summary']
        print("\n⚡ ACTIVITY LEVEL:")
        print(f"   • Recent Deals: {summary.get('recent_deals', 0)}")
        print(f"   • Press Releases: {summary.get('press_releases', 0)}")
        print(f"   • Overall Activity: {summary.get('activity_level', 'Unknown')}")

    if findings['contact_information']:
        print("\n📞 CONTACT INFORMATION:")
        for contact in findings['contact_information'][:5]:
            contact_type = contact.get('type', 'unknown')
            if contact_type == 'email':
                print(f"   • Email: {contact.get('email', 'N/A')}")
            elif contact_type == 'phone':
                print(f"   • Phone: {contact.get('phone', 'N/A')}")
            elif contact_type == 'executive':
                print(f"   • Executive: {contact.get('name', 'N/A')} - {contact.get('title', 'N/A')}")

    # Generate outreach email
    print("\n📧 GENERATING PERSONALIZED OUTREACH EMAIL...")
    print("-" * 50)

    outreach_email = analyzer.generate_outreach_email()
    print("\n" + "=" * 80)
    print("📧 PERSONALIZED COLD OUTREACH EMAIL DRAFT:")
    print("=" * 80)
    print(outreach_email)

    # Save results to file
    output_file = "3edge_focused_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(findings, f, indent=2, default=str)

    print(f"\n💾 Full analysis saved to: {output_file}")

    print("\n" + "=" * 80)
    print("🎯 ANALYSIS COMPLETE!")
    print("Use this intelligence for targeted, personalized outreach to 3EDGE Asset Management")
    print("=" * 80)

if __name__ == "__main__":
    main()
