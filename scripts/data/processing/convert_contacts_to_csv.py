#!/usr/bin/env python3
"""
Convert organized_contacts.txt to Frappe CRM CSV format
"""

import csv
import re
from typing import Dict, List, Optional


def parse_contact_name(name: str) -> tuple[str, str]:
    """Split full name into first and last name"""
    if not name:
        return "", ""

    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        # For names with middle names, take first as first name, last as last name
        return parts[0], parts[-1]


def parse_contacts_file(file_path: str) -> List[Dict]:
    """Parse the organized_contacts.txt file and extract contact data"""
    contacts = []

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Split by numbered entries (1., 2., etc.)
    entries = re.split(r'\n\s*\d+\.\s+', content)

    for entry in entries:
        if not entry.strip():
            continue

        lines = entry.strip().split('\n')
        if not lines:
            continue

        # Extract organization name (first line, remove dashes and clean up)
        org_line = lines[0].strip()
        # Skip header entries
        if 'FINANCIAL INSTITUTIONS CONTACT DIRECTORY' in org_line or '=' in org_line:
            continue

        if '|' in org_line:
            # Handle multiple organizations separated by |
            organizations = [org.strip() for org in org_line.split('|')]
            organization = organizations[0]  # Use first one as primary
        else:
            organization = org_line

        contact_data = {
            'Organization': organization,
            'First Name': '',
            'Last Name': '',
            'Job Title': '',
            'Email': '',
            'Website': '',
            'Industry': 'Financial Services',
            'Status': 'Open',
            'Source': 'Research'
        }

        # Parse remaining lines for contact details
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Contact:'):
                contact_name = line.replace('Contact:', '').strip()
                first_name, last_name = parse_contact_name(contact_name)
                contact_data['First Name'] = first_name
                contact_data['Last Name'] = last_name

            elif line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
                # Clean up common title abbreviations (word boundaries and specific patterns)
                title = re.sub(r'\bMP\b', 'Managing Partner', title)
                title = re.sub(r'\bMD\b', 'Managing Director', title)
                title = re.sub(r'\bCEO/CIO\b', 'CEO and CIO', title)
                title = re.sub(r'\bCIO/Chairman\b', 'CIO and Chairman', title)
                title = re.sub(r'\bPM\b', 'Portfolio Manager', title)
                title = re.sub(r'\bCCO\b', 'Chief Commercial Officer', title)
                title = re.sub(r'\bCOO\b', 'Chief Operating Officer', title)
                title = re.sub(r'\bCFO\b', 'Chief Financial Officer', title)
                title = re.sub(r'\bP\b(?!\w)', 'Partner', title)  # P followed by word boundary

                contact_data['Job Title'] = title

            elif line.startswith('Email:'):
                email_text = line.replace('Email:', '').strip()
                # Handle multiple emails (take first one)
                emails = [e.strip() for e in email_text.split() if '@' in e]
                if emails:
                    contact_data['Email'] = emails[0]

            elif line.startswith('Website:'):
                website = line.replace('Website:', '').strip()
                contact_data['Website'] = website

        # Only add contacts that have at least an organization or email
        if contact_data['Organization'] or contact_data['Email']:
            contacts.append(contact_data)

    return contacts


def create_crm_csv(contacts: List[Dict], template_path: str, output_path: str):
    """Create CSV file in Frappe CRM format using template structure"""

    # Read template to get column headers
    with open(template_path, 'r', encoding='utf-8') as template_file:
        template_content = template_file.read()
        # Extract headers from first line
        first_line = template_content.split('\n')[0]
        # Remove quotes and split by comma
        headers = [col.strip('"') for col in first_line.split(',')]

    # Write CSV with contacts data
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow({col: col for col in headers})

        # Write contact data
        for i, contact in enumerate(contacts, 1):
            row = {}

            # Map our contact data to CSV columns
            for header in headers:
                if header == 'ID':
                    row[header] = str(i)
                elif header == 'First Name':
                    row[header] = contact.get('First Name', '')
                elif header == 'Last Name':
                    row[header] = contact.get('Last Name', '')
                elif header == 'Organization':
                    row[header] = contact.get('Organization', '')
                elif header == 'Job Title':
                    row[header] = contact.get('Job Title', '')
                elif header == 'Email':
                    row[header] = contact.get('Email', '')
                elif header == 'Website':
                    row[header] = contact.get('Website', '')
                elif header == 'Industry':
                    row[header] = contact.get('Industry', '')
                elif header == 'Status':
                    row[header] = contact.get('Status', 'Open')
                elif header == 'Source':
                    row[header] = contact.get('Source', 'Research')
                elif header == 'Full Name':
                    first = contact.get('First Name', '')
                    last = contact.get('Last Name', '')
                    row[header] = f"{first} {last}".strip()
                else:
                    # Set default empty values for other columns
                    row[header] = ''

            writer.writerow(row)


def main():
    input_file = '/Users/fahadkiani/Desktop/development/crm-deployment/scripts/organized_contacts.txt'
    template_file = '/Users/fahadkiani/Desktop/development/crm-deployment/scripts/template.csv'
    output_file = '/Users/fahadkiani/Desktop/development/crm-deployment/scripts/contacts_frm_formatted.csv'

    print("Parsing contacts from organized_contacts.txt...")
    contacts = parse_contacts_file(input_file)

    print(f"Found {len(contacts)} contacts")
    print("Creating Frappe CRM formatted CSV...")

    create_crm_csv(contacts, template_file, output_file)

    print(f"✅ CSV file created: {output_file}")
    print("\nPreview of first few contacts:")
    for i, contact in enumerate(contacts[:3], 1):
        print(f"{i}. {contact['Organization']} - {contact['First Name']} {contact['Last Name']} ({contact['Email']})")


if __name__ == "__main__":
    main()
