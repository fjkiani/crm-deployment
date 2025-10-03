import csv, re, sys, os

SRC = sys.argv[1]
OUT = sys.argv[2]
MAX_ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 50

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://\S+")


def clean_text(x: str) -> str:
    if not x:
        return ""
    x = x.replace("\n", " ").replace("\r", " ")
    x = re.sub(r"\s+", " ", x).strip()
    return x


def normalize_company(name: str) -> str:
    if not name:
        return ""
    name = clean_text(name)
    name = re.sub(r"\s*\((SFO|MFO|Foundation|AKA:[^)]+)\)\s*", "", name, flags=re.I)
    name = re.sub(r"\s*/\s*", " / ", name)
    return name.strip(" -")


def parse_contact(contact: str):
    contact = clean_text(contact)
    if not contact:
        return ("", "")
    # Split on first comma → name, title
    parts = [p.strip() for p in contact.split(",", 1)]
    if len(parts) == 2:
        return parts[0], parts[1]
    return contact, ""


def extract_emails_and_urls(fields):
    emails, urls = [], []
    for f in fields:
        if not f:
            continue
        for e in EMAIL_RE.findall(f):
            emails.append(e.strip().strip(","))
        for u in URL_RE.findall(f):
            urls.append(u.strip().strip(","))
    # de-dup preserving order
    def dedup(seq):
        seen = set(); out = []
        for s in seq:
            k = s.lower()
            if k not in seen:
                seen.add(k); out.append(s)
        return out
    return dedup(emails), dedup(urls)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(SRC, newline="", encoding="utf-8") as f, open(OUT, "w", newline="", encoding="utf-8") as w:
        reader = csv.reader(f)
        header = next(reader, [])
        writer = csv.DictWriter(w, fieldnames=[
            "organization_name",
            "contact_full_name",
            "job_title",
            "primary_email",
            "secondary_emails",
            "websites",
            "notes",
        ])
        writer.writeheader()
        count = 0
        for row in reader:
            if count >= MAX_ROWS:
                break
            # Expect at least: Company, Contact, Email, extra...
            company = row[0] if len(row) > 0 else ""
            contact = row[1] if len(row) > 1 else ""
            email = row[2] if len(row) > 2 else ""
            extras = row[3:]
            org = normalize_company(company)
            name, title = parse_contact(contact)
            emails, urls = extract_emails_and_urls([email] + extras)
            primary_email = emails[0] if emails else ""
            secondary = ";".join(emails[1:]) if len(emails) > 1 else ""
            websites = ";".join(urls)
            notes_bits = []
            if any(extras):
                # add non-url/email extras to notes
                for f in extras:
                    if not f:
                        continue
                    if EMAIL_RE.search(f) or URL_RE.search(f):
                        continue
                    txt = clean_text(f)
                    if txt:
                        notes_bits.append(txt)
            notes = " | ".join(notes_bits)
            writer.writerow({
                "organization_name": org,
                "contact_full_name": name,
                "job_title": title,
                "primary_email": primary_email,
                "secondary_emails": secondary,
                "websites": websites,
                "notes": notes,
            })
            count += 1

if __name__ == "__main__":
    main()
