#!/usr/bin/env python3
import csv
import re
from collections import defaultdict

def clean_data():
    """Parse and organize the CSV contact data into a neat format"""

    # Read the CSV file
    contacts = []
    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/preview_top50.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Skip empty rows
            if not row['organization_name'].strip():
                continue

            # Clean up the data
            contact = {
                'organization': row['organization_name'].strip(),
                'contact_name': row['contact_full_name'].strip() if row['contact_full_name'].strip() else None,
                'job_title': row['job_title'].strip() if row['job_title'].strip() else None,
                'primary_email': row['primary_email'].strip() if row['primary_email'].strip() else None,
                'secondary_emails': [email.strip() for email in row['secondary_emails'].split(',') if email.strip()],
                'websites': [site.strip() for site in row['websites'].split(',') if site.strip()],
                'notes': row['notes'].strip() if row['notes'].strip() else None
            }

            # Clean up organization names (handle multiple names separated by /)
            if '/' in contact['organization']:
                contact['organization'] = contact['organization'].replace('/', ' | ')

            contacts.append(contact)

    return contacts

def categorize_contacts(contacts):
    """Categorize contacts by organization type"""
    categories = defaultdict(list)

    # Keywords for categorization
    category_keywords = {
        'Asset Management': ['asset management', 'asset', 'management'],
        'Private Equity': ['private equity', 'capital', 'partners'],
        'Family Office': ['family office', 'family', 'advisors'],
        'Investment Banking': ['investment', 'bank', 'wealth management'],
        'Venture Capital': ['venture capital', 'ventures', 'vc'],
        'Trust Company': ['trust', 'trust company'],
        'Other': []
    }

    for contact in contacts:
        org_name = contact['organization'].lower()
        categorized = False

        for category, keywords in category_keywords.items():
            if category != 'Other':
                if any(keyword in org_name for keyword in keywords):
                    categories[category].append(contact)
                    categorized = True
                    break

        if not categorized:
            categories['Other'].append(contact)

    return categories

def create_formatted_output(contacts):
    """Create a nicely formatted text output"""
    output = []

    # Header
    output.append("=" * 80)
    output.append("FINANCIAL INSTITUTIONS CONTACT DIRECTORY")
    output.append("=" * 80)
    output.append("")

    # Sort contacts alphabetically by organization
    sorted_contacts = sorted(contacts, key=lambda x: x['organization'].lower())

    for i, contact in enumerate(sorted_contacts, 1):
        output.append(f"{i:2d}. {contact['organization']}")
        output.append("-" * len(f"{i:2d}. {contact['organization']}"))

        if contact['contact_name']:
            output.append(f"   Contact: {contact['contact_name']}")

        if contact['job_title']:
            output.append(f"   Title:   {contact['job_title']}")

        if contact['primary_email']:
            output.append(f"   Email:   {contact['primary_email']}")

        if contact['secondary_emails']:
            for email in contact['secondary_emails']:
                output.append(f"           {email}")

        if contact['websites']:
            for website in contact['websites']:
                output.append(f"   Website: {website}")

        if contact['notes']:
            output.append(f"   Notes:   {contact['notes']}")

        output.append("")  # Empty line between entries

    return "\n".join(output)

def create_cleaned_csv(contacts):
    """Create a cleaned CSV file"""
    fieldnames = ['organization_name', 'contact_full_name', 'job_title', 'primary_email', 'secondary_emails', 'websites', 'notes']

    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/organized_contacts.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for contact in sorted(contacts, key=lambda x: x['organization'].lower()):
            # Convert back to original format
            row = {
                'organization_name': contact['organization'],
                'contact_full_name': contact['contact_name'] or '',
                'job_title': contact['job_title'] or '',
                'primary_email': contact['primary_email'] or '',
                'secondary_emails': ','.join(contact['secondary_emails']) if contact['secondary_emails'] else '',
                'websites': ','.join(contact['websites']) if contact['websites'] else '',
                'notes': contact['notes'] or ''
            }
            writer.writerow(row)

def main():
    """Main function to process and organize the contact data"""
    print("Processing contact data...")

    # Clean and organize the data
    contacts = clean_data()

    print(f"Found {len(contacts)} contacts")

    # Create formatted text output
    formatted_output = create_formatted_output(contacts)

    # Write to file
    with open('/Users/fahadkiani/Desktop/development/crm-deployment/scripts/organized_contacts.txt', 'w') as file:
        file.write(formatted_output)

    # Create cleaned CSV
    create_cleaned_csv(contacts)

    print("Created files:")
    print("- organized_contacts.txt (formatted directory)")
    print("- organized_contacts.csv (cleaned CSV)")

    # Show categorization summary
    categories = categorize_contacts(contacts)
    print("\nContact Summary by Category:")
    for category, contacts_list in categories.items():
        print(f"- {category}: {len(contacts_list)} contacts")

if __name__ == "__main__":
    main()
