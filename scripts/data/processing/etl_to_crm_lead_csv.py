import csv, sys, os

SRC = sys.argv[1]
OUT = sys.argv[2]

os.makedirs(os.path.dirname(OUT), exist_ok=True)

def split_name(full: str):
    full = (full or '').strip()
    if not full:
        return ('','')
    parts = full.split()
    if len(parts) == 1:
        return (parts[0], '')
    return (' '.join(parts[:-1]), parts[-1])

with open(SRC, newline='', encoding='utf-8') as f, open(OUT, 'w', newline='', encoding='utf-8') as w:
    r = csv.DictReader(f)
    fieldnames = [
        'doctype',
        'first_name',
        'last_name',
        'lead_name',
        'email',
        'organization',
        'status',
        'source',
        'website',
        'notes'
    ]
    wr = csv.DictWriter(w, fieldnames=fieldnames)
    wr.writeheader()
    for row in r:
        first, last = split_name(row.get('contact_full_name',''))
        wr.writerow({
            'doctype': 'CRM Lead',
            'first_name': first,
            'last_name': last,
            'lead_name': row.get('contact_full_name') or row.get('organization_name') or 'Lead',
            'email': row.get('primary_email',''),
            'organization': row.get('organization_name',''),
            'status': 'New',
            'source': 'CSV Import',
            'website': (row.get('websites') or '').split(';')[0] if row.get('websites') else '',
            'notes': row.get('notes','')
        })
