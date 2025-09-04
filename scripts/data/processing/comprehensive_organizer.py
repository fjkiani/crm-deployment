#!/usr/bin/env python3
import csv
import json
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

def parse_contact_info(contact_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse contact string to extract name and title"""
    if not contact_str or contact_str.strip() == '':
        return None, None

    # Handle cases like "Name, Title"
    if ',' in contact_str:
        parts = contact_str.split(',', 1)
        name = parts[0].strip()
        title = parts[1].strip()
        return name, title

    # Handle cases with parentheses like "Name (additional info)"
    if '(' in contact_str and ')' in contact_str:
        match = re.match(r'([^()]+)\s*\(([^)]+)\)', contact_str)
        if match:
            name = match.group(1).strip()
            title = match.group(2).strip()
            return name, title

    # If no clear separation, treat whole thing as name
    return contact_str.strip(), None

def categorize_organization(company_name: str) -> str:
    """Categorize organization based on name and keywords"""
    name_lower = company_name.lower()

    # Define categorization rules
    categories = {
        'Single Family Office (SFO)': [
            'family office', 'family trust', 'family advisors', 'family capital',
            'family investments', 'family enterprises', 'family foundation',
            '(sfo)', 'single family office'
        ],
        'Multi Family Office (MFO)': [
            'multi family office', '(mfo)', 'wealth management', 'private wealth',
            'wealth advisors', 'family office association', 'family office network'
        ],
        'Private Equity': [
            'private equity', 'capital partners', 'investment partners',
            'equity partners', 'growth capital', 'venture capital'
        ],
        'Asset Management': [
            'asset management', 'investment management', 'capital management',
            'wealth management', 'investment counsel', 'portfolio management'
        ],
        'Venture Capital': [
            'venture capital', 'vc', 'ventures', 'startup', 'innovation capital',
            'growth equity', 'early stage'
        ],
        'Investment Banking': [
            'investment bank', 'merchant bank', 'corporate finance',
            'm&a', 'mergers and acquisitions'
        ],
        'Hedge Funds': [
            'hedge fund', 'alternative investments', 'absolute return',
            'long/short', 'quantitative'
        ],
        'Real Estate': [
            'real estate', 'property', 'land', 'development', 'reit'
        ],
        'Trust Companies': [
            'trust company', 'trust corporation', 'fiduciary services'
        ],
        'Consulting': [
            'consulting', 'advisory', 'consultants', 'advisors'
        ],
        'Other': []
    }

    for category, keywords in categories.items():
        if category != 'Other':
            if any(keyword in name_lower for keyword in keywords):
                return category

    return 'Other'

def extract_location_indicators(company_name: str) -> List[str]:
    """Extract location or type indicators from company name"""
    indicators = []
    name_lower = company_name.lower()

    # Extract common indicators
    if '(sfo)' in name_lower:
        indicators.append('SFO')
    if '(mfo)' in name_lower:
        indicators.append('MFO')
    if 'llc' in name_lower:
        indicators.append('LLC')
    if 'ltd' in name_lower or 'limited' in name_lower:
        indicators.append('Ltd')
    if 'inc' in name_lower or 'incorporated' in name_lower:
        indicators.append('Inc')
    if 'corp' in name_lower or 'corporation' in name_lower:
        indicators.append('Corp')

    return indicators

def clean_company_name(company_name: str) -> str:
    """Clean and standardize company name"""
    # Remove common suffixes for sorting
    name = company_name.strip()

    # Clean up multi-line names
    name = re.sub(r'\s+', ' ', name)

    # Standardize common patterns
    name = re.sub(r'\s*\([^)]*\)\s*', '', name)  # Remove parenthetical info
    name = re.sub(r'\s*/\s*', ' | ', name)  # Standardize separators

    return name

def parse_emails_and_links(email_str: str, extra_str: str = '') -> Dict[str, List[str]]:
    """Parse emails and links from various fields"""
    emails = []
    links = []

    # Combine all text sources
    all_text = f"{email_str} {extra_str}"

    # Extract emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails.extend(re.findall(email_pattern, all_text))

    # Extract LinkedIn URLs
    linkedin_pattern = r'https?://(?:www\.)?linkedin\.com[^\s,]*'
    linkedin_links = re.findall(linkedin_pattern, all_text)
    links.extend(linkedin_links)

    # Extract other website URLs
    website_pattern = r'https?://(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s,]*'
    other_links = re.findall(website_pattern, all_text)
    # Filter out LinkedIn links already captured
    other_links = [link for link in other_links if 'linkedin.com' not in link]
    links.extend(other_links)

    return {
        'emails': list(set(emails)),  # Remove duplicates
        'links': list(set(links))     # Remove duplicates
    }

def process_leads_file():
    """Process the leads CSV file and organize all data"""
    leads_data = []

    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/leads.csv', 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Skip header row

        for row in reader:
            if len(row) < 4:
                continue

            company = row[0].strip()
            contact = row[1].strip() if len(row) > 1 else ''
            email = row[2].strip() if len(row) > 2 else ''
            extra = row[3].strip() if len(row) > 3 else ''

            if not company:  # Skip empty rows
                continue

            # Parse contact information
            contact_name, contact_title = parse_contact_info(contact)

            # Parse emails and links
            contact_info = parse_emails_and_links(email, extra)

            # Categorize organization
            category = categorize_organization(company)

            # Extract indicators
            indicators = extract_location_indicators(company)

            # Clean company name
            clean_name = clean_company_name(company)

            lead = {
                'original_company': company,
                'clean_company': clean_name,
                'contact_name': contact_name,
                'contact_title': contact_title,
                'primary_emails': contact_info['emails'],
                'links': contact_info['links'],
                'category': category,
                'indicators': indicators,
                'has_contact': bool(contact_name),
                'has_email': bool(contact_info['emails']),
                'has_website': bool([link for link in contact_info['links'] if 'linkedin.com' not in link])
            }

            leads_data.append(lead)

    return leads_data

def generate_statistics(leads_data: List[Dict]) -> Dict:
    """Generate comprehensive statistics"""
    stats = {
        'total_leads': len(leads_data),
        'categories': Counter(lead['category'] for lead in leads_data),
        'indicators': Counter(indicator for lead in leads_data for indicator in lead['indicators']),
        'contact_completeness': {
            'with_contacts': sum(1 for lead in leads_data if lead['has_contact']),
            'with_emails': sum(1 for lead in leads_data if lead['has_email']),
            'with_websites': sum(1 for lead in leads_data if lead['has_website']),
            'complete_records': sum(1 for lead in leads_data if lead['has_contact'] and lead['has_email'])
        },
        'top_domains': Counter(),
        'linkedin_profiles': sum(1 for lead in leads_data if any('linkedin.com' in link for link in lead['links']))
    }

    # Count email domains
    for lead in leads_data:
        for email in lead['primary_emails']:
            if '@' in email:
                domain = email.split('@')[1]
                stats['top_domains'][domain] += 1

    return stats

def create_organized_text_output(leads_data: List[Dict]) -> str:
    """Create a beautifully formatted text directory"""
    output = []

    # Header
    output.append("=" * 100)
    output.append("COMPREHENSIVE FINANCIAL INSTITUTIONS CONTACT DIRECTORY")
    output.append("=" * 100)
    output.append("")

    # Group by category
    categories = defaultdict(list)
    for lead in leads_data:
        categories[lead['category']].append(lead)

    # Sort categories and leads
    for category in sorted(categories.keys()):
        leads = categories[category]
        leads.sort(key=lambda x: x['clean_company'])

        output.append(f"## {category.upper()} ({len(leads)} organizations)")
        output.append("=" * 80)
        output.append("")

        for i, lead in enumerate(leads, 1):
            output.append(f"{i:3d}. {lead['clean_company']}")

            if lead['indicators']:
                output.append(f"     Type: {', '.join(lead['indicators'])}")

            if lead['contact_name']:
                contact_display = lead['contact_name']
                if lead['contact_title']:
                    contact_display += f", {lead['contact_title']}"
                output.append(f"     Contact: {contact_display}")

            if lead['primary_emails']:
                for email in lead['primary_emails']:
                    output.append(f"     Email: {email}")

            if lead['links']:
                for link in lead['links']:
                    if 'linkedin.com' in link:
                        output.append(f"     LinkedIn: {link}")
                    else:
                        output.append(f"     Website: {link}")

            output.append("")

        output.append("")

    return "\n".join(output)

def create_cleaned_csv(leads_data: List[Dict]) -> None:
    """Create a cleaned CSV file"""
    fieldnames = [
        'company_name', 'contact_name', 'contact_title', 'primary_email',
        'secondary_emails', 'websites', 'linkedin_profiles', 'category', 'indicators'
    ]

    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/organized_leads.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for lead in sorted(leads_data, key=lambda x: (x['category'], x['clean_company'])):
            # Separate LinkedIn from other websites
            linkedin_links = [link for link in lead['links'] if 'linkedin.com' in link]
            other_links = [link for link in lead['links'] if 'linkedin.com' not in link]

            row = {
                'company_name': lead['clean_company'],
                'contact_name': lead['contact_name'] or '',
                'contact_title': lead['contact_title'] or '',
                'primary_email': lead['primary_emails'][0] if lead['primary_emails'] else '',
                'secondary_emails': ','.join(lead['primary_emails'][1:]) if len(lead['primary_emails']) > 1 else '',
                'websites': ','.join(other_links),
                'linkedin_profiles': ','.join(linkedin_links),
                'category': lead['category'],
                'indicators': ','.join(lead['indicators'])
            }
            writer.writerow(row)

def create_json_output(leads_data: List[Dict]) -> None:
    """Create a JSON file for programmatic use"""
    # Group by category for easier processing
    json_data = {
        'metadata': {
            'total_records': len(leads_data),
            'generated_date': '2024',
            'categories': list(set(lead['category'] for lead in leads_data))
        },
        'leads_by_category': defaultdict(list),
        'all_leads': []
    }

    for lead in leads_data:
        category_leads = json_data['leads_by_category'][lead['category']]
        category_leads.append({
            'company': lead['clean_company'],
            'original_company': lead['original_company'],
            'contact': {
                'name': lead['contact_name'],
                'title': lead['contact_title']
            },
            'communication': {
                'emails': lead['primary_emails'],
                'websites': [link for link in lead['links'] if 'linkedin.com' not in link],
                'linkedin': [link for link in lead['links'] if 'linkedin.com' in link]
            },
            'metadata': {
                'category': lead['category'],
                'indicators': lead['indicators'],
                'has_contact': lead['has_contact'],
                'has_email': lead['has_email'],
                'has_website': lead['has_website']
            }
        })

        json_data['all_leads'].append(category_leads[-1])

    # Sort within each category
    for category in json_data['leads_by_category']:
        json_data['leads_by_category'][category].sort(key=lambda x: x['company'])

    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/organized_leads.json', 'w') as file:
        json.dump(json_data, file, indent=2)

def create_summary_report(stats: Dict) -> str:
    """Create a summary report"""
    output = []

    output.append("=" * 80)
    output.append("CONTACT DATABASE SUMMARY REPORT")
    output.append("=" * 80)
    output.append("")

    output.append(f"📊 TOTAL RECORDS: {stats['total_leads']}")
    output.append("")

    output.append("📂 RECORDS BY CATEGORY:")
    for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_leads']) * 100
        output.append("25")
    output.append("")

    output.append("🏷️  TYPE INDICATORS:")
    for indicator, count in sorted(stats['indicators'].items(), key=lambda x: x[1], reverse=True):
        output.append("15")
    output.append("")

    output.append("📧 CONTACT COMPLETENESS:")
    completeness = stats['contact_completeness']
    output.append(f"   • Records with contact names: {completeness['with_contacts']} ({completeness['with_contacts']/stats['total_leads']*100:.1f}%)")
    output.append(f"   • Records with email addresses: {completeness['with_emails']} ({completeness['with_emails']/stats['total_leads']*100:.1f}%)")
    output.append(f"   • Records with websites: {completeness['with_websites']} ({completeness['with_websites']/stats['total_leads']*100:.1f}%)")
    output.append(f"   • Complete records (contact + email): {completeness['complete_records']} ({completeness['complete_records']/stats['total_leads']*100:.1f}%)")
    output.append("")

    output.append(f"💼 LINKEDIN PROFILES: {stats['linkedin_profiles']}")
    output.append("")

    output.append("📧 TOP EMAIL DOMAINS:")
    for domain, count in stats['top_domains'].most_common(10):
        output.append("15")

    return "\n".join(output)

def main():
    """Main function to process and organize all leads"""
    print("🔄 Processing comprehensive leads database...")

    # Process the data
    leads_data = process_leads_file()
    print(f"✅ Processed {len(leads_data)} lead records")

    # Generate statistics
    stats = generate_statistics(leads_data)
    print("📊 Generated comprehensive statistics")

    # Create organized text directory
    print("📝 Creating formatted directory...")
    formatted_output = create_organized_text_output(leads_data)
    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/comprehensive_directory.txt', 'w') as file:
        file.write(formatted_output)

    # Create cleaned CSV
    print("📊 Creating cleaned CSV...")
    create_cleaned_csv(leads_data)

    # Create JSON output
    print("💾 Creating JSON export...")
    create_json_output(leads_data)

    # Create summary report
    print("📋 Creating summary report...")
    summary_report = create_summary_report(stats)
    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/database_summary.txt', 'w') as file:
        file.write(summary_report)

    print("\n" + "="*50)
    print("🎉 ORGANIZATION COMPLETE!")
    print("="*50)
    print("\n📁 Generated files:")
    print("   • comprehensive_directory.txt - Formatted contact directory")
    print("   • organized_leads.csv - Cleaned CSV file")
    print("   • organized_leads.json - JSON export for programming")
    print("   • database_summary.txt - Statistical summary")
    print(f"\n📊 Key Statistics:")
    print(f"   • Total organizations: {stats['total_leads']}")
    print(f"   • Categories identified: {len(stats['categories'])}")
    print(f"   • Records with contacts: {stats['contact_completeness']['with_contacts']}")
    print(f"   • Records with emails: {stats['contact_completeness']['with_emails']}")
    print(f"   • Complete records: {stats['contact_completeness']['complete_records']}")

if __name__ == "__main__":
    main()
