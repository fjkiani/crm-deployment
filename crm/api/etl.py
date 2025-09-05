import io
import csv
import json
import typing as t

import frappe
from frappe import _


def _infer_type(values: list[str]) -> str:
    sample = [v for v in values if v not in (None, "", "null", "None")][:25]
    if not sample:
        return "Data"
    # very light heuristics
    lowers = [v.lower() for v in sample if isinstance(v, str)]
    if all("@" in v and "." in v for v in lowers):
        return "Data"  # Email
    digits = sum(1 for v in sample if str(v).replace("+", "").replace("-", "").replace(" ", "").isdigit())
    if digits >= max(3, len(sample) // 2):
        return "Data"  # Numeric / Phone
    return "Data"


def _normalize_header(h: str) -> str:
    return (h or "").strip().replace(" ", "_").replace("/", "_").replace("-", "_").lower()


@frappe.whitelist(allow_guest=False)
def preview(file_url: str | None = None, filedata: str | None = None, delimiter: str | None = None, max_rows: int = 50) -> dict:
    """Preview a CSV/XLSX-like payload (CSV expected for now).

    Args:
      - file_url: public URL to a CSV
      - filedata: raw CSV content (string)
      - delimiter: optional delimiter override
      - max_rows: sample rows to return
    Returns:
      { headers: [...], sample: [[...], ...], inferred: {header: fieldtype} }
    """
    if not file_url and not filedata:
        frappe.throw(_("Provide file_url or filedata"))

    content = ""
    if filedata:
        content = filedata
    else:
        import requests

        r = requests.get(file_url, timeout=15)
        r.raise_for_status()
        content = r.text

    # Parse CSV
    buf = io.StringIO(content)
    sniff = None
    if not delimiter:
        try:
            sniff = csv.Sniffer().sniff(buf.read(2048))
            buf.seek(0)
        except Exception:
            buf.seek(0)
    reader = csv.reader(buf, delimiter=delimiter or (sniff.delimiter if sniff else ","))
    rows: list[list[str]] = []
    for i, row in enumerate(reader):
        if i == 0:
            headers = [str(c) for c in row]
            continue
        rows.append([str(c) for c in row])
        if len(rows) >= max_rows:
            break

    headers = [h for h in locals().get("headers", [])]
    norm_headers = [_normalize_header(h) for h in headers]

    # columnwise values for inference
    cols: dict[str, list[str]] = {h: [] for h in norm_headers}
    for r in rows:
        for idx, h in enumerate(norm_headers):
            if idx < len(r):
                cols[h].append(r[idx])

    inferred = {h: _infer_type(vs) for h, vs in cols.items()}
    return {
        "headers": headers,
        "normalized_headers": norm_headers,
        "sample": rows,
        "inferred": inferred,
    }


@frappe.whitelist(allow_guest=False)
def job_status(job_id: str) -> dict:
    """Placeholder ETL job status (to be backed by DocType in next step)."""
    return {"job_id": job_id, "status": "not_implemented"}


@frappe.whitelist(allow_guest=False)
def import_rows(payload: str) -> dict:
    """Placeholder import endpoint. Accepts JSON string and returns stub.
    Will enqueue background job in next iteration.
    """
    try:
        data = json.loads(payload or "{}")
    except Exception:
        frappe.throw(_("Invalid JSON payload"))

    source_type = (data.get("source_type") or "CSV").upper()
    if source_type not in ("CSV", "GOOGLE_SHEETS"):
        frappe.throw(_(f"Unsupported source_type: {source_type}"))

    # Create Import Job Doc
    job = frappe.get_doc(
        {
            "doctype": "CRM Import Job",
            "title": data.get("title") or _(f"Import {source_type}"),
            "source_type": source_type,
            "file_url": data.get("file_url"),
            "sheet_id": data.get("sheet_id"),
            "sheet_range": data.get("sheet_range"),
            "mapping_profile": data.get("mapping_profile"),
            "dedupe": 1 if data.get("dedupe", True) else 0,
            "create_custom_fields": 1 if data.get("create_custom_fields") else 0,
            "link_organization": 1 if data.get("link_organization", True) else 0,
            "status": "Queued",
        }
    )
    job.insert()

    kwargs = {"job_name": job.name, "options": data}
    frappe.enqueue(
        method="crm.api.etl.process_job",
        queue="long",
        job_name=f"etl_import_{job.name}",
        timeout=60 * 30,
        now=frappe.flags.in_test,  # run synchronously during tests
        **{"kwargs": kwargs},
    )

    return {"accepted": True, "job_id": job.name}


@frappe.whitelist(allow_guest=False)
def process_job(job_name: str, options: dict | None = None):
    """Background worker entrypoint.

    Reads job doc, fetches data (CSV or Sheets), performs basic counting, and marks status.
    The real import logic (validation, mapping, upsert) will be added in next iterations.
    """
    job = frappe.get_doc("CRM Import Job", job_name)
    try:
        job.db_set("status", "Running")

        dry_run = False
        if isinstance(options, dict):
            dry_run = bool(options.get("dry_run"))

        # Fetch data & optionally import
        total_rows = 0
        headers: list[str] = []
        data_rows: list[list[str]] = []
        if job.source_type == "CSV" and job.file_url:
            import requests

            r = requests.get(job.file_url, timeout=30)
            r.raise_for_status()
            buf = io.StringIO(r.text)
            sniff = None
            try:
                sniff = csv.Sniffer().sniff(buf.read(2048))
                buf.seek(0)
            except Exception:
                buf.seek(0)
            reader = csv.reader(buf, delimiter=(sniff.delimiter if sniff else ","))
            for i, row in enumerate(reader):
                if i == 0:
                    headers = [str(c) for c in row]
                    continue
                data_rows.append([str(c) for c in row])
            total_rows = len(data_rows)
        elif job.source_type == "GOOGLE_SHEETS" and job.sheet_id:
            # Basic Sheets connector via CSV export (first sheet if no gid)
            export_url = f"https://docs.google.com/spreadsheets/d/{job.sheet_id}/export?format=csv"
            # Note: range-based export via A1 requires Google API; unsupported here without credentials
            import requests

            r = requests.get(export_url, timeout=30)
            r.raise_for_status()
            buf = io.StringIO(r.text)
            reader = csv.reader(buf, delimiter=",")
            for i, row in enumerate(reader):
                if i == 0:
                    headers = [str(c) for c in row]
                    continue
                data_rows.append([str(c) for c in row])
            total_rows = len(data_rows)
        else:
            pass

        job.db_set("total_rows", total_rows)

        # Apply mapping and upsert (minimal CRM Lead support)
        processed = 0
        failures: list[tuple[int, str]] = []
        if total_rows and job.mapping_profile:
            try:
                processed, failures = _apply_mapping_and_upsert(job, headers, data_rows, dry_run=dry_run)
            except Exception as imp_e:
                job.db_set("status", "Failed")
                job.db_set("log", f"Import error: {type(imp_e).__name__}: {imp_e}")
                frappe.log_error(message=frappe.get_traceback(), title=f"ETL Import Failed: {job.name}")
                raise

        job.db_set("processed_rows", processed)
        # Write error CSV if failures exist
        if failures:
            try:
                err_csv = io.StringIO()
                w = csv.writer(err_csv)
                w.writerow(["row_index", "error"])
                for idx, msg in failures:
                    w.writerow([idx, msg])
                file_doc = frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_name": f"etl_errors_{job.name}.csv",
                        "content": err_csv.getvalue(),
                        "is_private": 1,
                        "attached_to_doctype": job.doctype,
                        "attached_to_name": job.name,
                    }
                ).insert()
                job.db_set("error_file", file_doc.file_url)
            except Exception:
                frappe.log_error(frappe.get_traceback(), title="ETL Error CSV write failed")
        if job.status != "Failed":
            job.db_set("status", "Completed" if not dry_run else "Completed (Dry Run)")
    except Exception as e:
        job.db_set("status", "Failed")
        job.db_set("log", f"{type(e).__name__}: {e}")
        frappe.log_error(message=frappe.get_traceback(), title=f"ETL Job Failed: {job.name}")
        raise


def _load_mapping(profile_name: str) -> list[dict]:
    doc = frappe.get_doc("CRM Import Column Map", profile_name)
    items = []
    for row in doc.get("columns") or []:
        items.append(
            {
                "source_header": (row.get("source_header") or "").strip(),
                "target_doctype": (row.get("target_doctype") or "").strip(),
                "target_field": (row.get("target_field") or "").strip(),
                "transform": row.get("transform") or None,
            }
        )
    return items


def _apply_mapping_and_upsert(job, headers: list[str], rows: list[list[str]], dry_run: bool = False) -> tuple[int, list[tuple[int, str]]]:
    header_to_idx = {h: i for i, h in enumerate([_normalize_header(h) for h in headers])}
    mapping = _load_mapping(job.mapping_profile)
    # Split mapping by target doctype
    lead_maps = [m for m in mapping if m["target_doctype"].strip().lower() in ("crm lead", "lead")]
    contact_maps = [m for m in mapping if m["target_doctype"].strip().lower() == "contact"]
    org_maps = [m for m in mapping if m["target_doctype"].strip().lower() in ("crm organization", "organization")] 

    # Build per-doctype field index maps
    def build_index(maps: list[dict]) -> dict[str, int]:
        idx_map: dict[str, int] = {}
        for mm in maps:
            src = _normalize_header(mm["source_header"])
            if src in header_to_idx:
                idx_map[mm["target_field"]] = header_to_idx[src]
        return idx_map

    lead_idx = build_index(lead_maps)
    contact_idx = build_index(contact_maps)
    org_idx = build_index(org_maps)

    processed = 0
    failures: list[tuple[int, str]] = []
    for idx_row, r in enumerate(rows, start=1):
        try:
            # Build candidate payloads
            lead_data: dict | None = None
            if lead_idx:
                lead_data = {"doctype": "CRM Lead"}
                for target_field, col_idx in lead_idx.items():
                    if col_idx < len(r):
                        lead_data[target_field] = r[col_idx]

            org_name = None
            if org_idx:
                org_data: dict = {}
                for target_field, col_idx in org_idx.items():
                    if col_idx < len(r):
                        org_data[target_field] = r[col_idx]
                if org_data:
                    org_name = _upsert_org(org_data, dry_run=dry_run)

            if lead_data and org_name and not lead_data.get("organization"):
                lead_data["organization"] = org_name

            if lead_data:
                _upsert_lead(lead_data, dry_run=dry_run)

            if contact_idx:
                contact_data: dict = {"doctype": "Contact"}
                for target_field, col_idx in contact_idx.items():
                    if col_idx < len(r):
                        contact_data[target_field] = r[col_idx]
                if org_name:
                    contact_data["_link_org_name"] = org_name
                _upsert_contact(contact_data, dry_run=dry_run)
            processed += 1
        except Exception:
            # Collecting row-level errors can be added (write error_file)
            frappe.log_error(frappe.get_traceback(), title="ETL Row Error")
            failures.append((idx_row, str(frappe.get_traceback(limit=1))))
            continue
    return processed, failures


def _upsert_lead(lead_data: dict, dry_run: bool = False) -> str | None:
    email = (lead_data.get("email") or "").strip()
    phone = (lead_data.get("phone") or lead_data.get("mobile_no") or "").strip()
    existing_name = None
    if email:
        existing_name = frappe.db.get_value("CRM Lead", {"email": email}, "name")
    if not existing_name and phone:
        existing_name = frappe.db.get_value("CRM Lead", {"phone": phone}, "name")
    if dry_run:
        return existing_name
    if existing_name:
        frappe.db.set_value("CRM Lead", existing_name, {k: v for k, v in lead_data.items() if k not in ("doctype",) and v})
        return existing_name
    doc = frappe.get_doc(lead_data)
    doc.insert()
    return doc.name


def _upsert_org(org_data: dict, dry_run: bool = False) -> str | None:
    name = (org_data.get("organization") or org_data.get("name") or "").strip()
    website = (org_data.get("website") or "").strip()
    existing_name = None
    if website:
        existing_name = frappe.db.get_value("CRM Organization", {"website": website}, "name")
    if not existing_name and name:
        existing_name = frappe.db.get_value("CRM Organization", {"organization_name": name}, "name")
    if dry_run:
        return existing_name or name or None
    if existing_name:
        # update basic fields
        updates = {k: v for k, v in org_data.items() if v}
        if updates:
            frappe.db.set_value("CRM Organization", existing_name, updates)
        return existing_name
    # Insert with minimum required fields
    payload = {"doctype": "CRM Organization"}
    if name:
        payload["organization_name"] = name
    payload.update({k: v for k, v in org_data.items() if k not in ("doctype",) and v})
    doc = frappe.get_doc(payload)
    doc.insert()
    return doc.name


def _upsert_contact(contact_data: dict, dry_run: bool = False) -> str | None:
    # Contact core fields
    email = (contact_data.get("email_id") or contact_data.get("email") or "").strip()
    phone = (contact_data.get("phone") or contact_data.get("mobile_no") or "").strip()
    first_name = contact_data.get("first_name") or ""
    last_name = contact_data.get("last_name") or ""
    existing_name = None
    if email:
        existing_name = frappe.db.get_value("Contact", {"email_id": email}, "name")
    if not existing_name and phone:
        existing_name = frappe.db.get_value("Contact", {"phone": phone}, "name")

    if dry_run:
        return existing_name

    if existing_name:
        updates = {k: v for k, v in {
            "first_name": first_name,
            "last_name": last_name,
            "email_id": email or None,
            "phone": phone or None,
            "mobile_no": contact_data.get("mobile_no") or None,
        }.items() if v}
        if updates:
            frappe.db.set_value("Contact", existing_name, updates)
        # Link to organization if provided
        org_name = contact_data.get("_link_org_name")
        if org_name:
            _ensure_contact_link(existing_name, "CRM Organization", org_name)
        return existing_name

    payload = {
        "doctype": "Contact",
        "first_name": first_name,
        "last_name": last_name,
        "email_id": email or None,
        "phone": phone or None,
        "mobile_no": contact_data.get("mobile_no") or None,
    }
    doc = frappe.get_doc(payload)
    doc.insert()
    org_name = contact_data.get("_link_org_name")
    if org_name:
        _ensure_contact_link(doc.name, "CRM Organization", org_name)
    return doc.name


def _ensure_contact_link(contact_name: str, link_doctype: str, link_name: str):
    # Contact has child table 'links' (Dynamic Link)
    try:
        links = frappe.get_all(
            "Dynamic Link",
            filters={
                "parenttype": "Contact",
                "parent": contact_name,
                "link_doctype": link_doctype,
                "link_name": link_name,
            },
            limit=1,
        )
        if links:
            return
        contact = frappe.get_doc("Contact", contact_name)
        contact.append("links", {"link_doctype": link_doctype, "link_name": link_name})
        contact.save()
    except Exception:
        frappe.log_error(frappe.get_traceback(), title="Contact link failed")


@frappe.whitelist()
def run_scheduled_imports():
    """Find CRM Import Jobs marked scheduled and run them if interval elapsed."""
    now = frappe.utils.now_datetime()
    jobs = frappe.get_all(
        "CRM Import Job",
        filters={"scheduled": 1},
        fields=["name", "interval_minutes", "last_run"],
    )
    for j in jobs:
        interval = int(j.interval_minutes or 60)
        last = j.last_run
        should_run = False
        if not last:
            should_run = True
        else:
            delta = now - frappe.utils.get_datetime(last)
            if delta.total_seconds() >= interval * 60:
                should_run = True
        if should_run:
            frappe.enqueue(
                method="crm.api.etl.process_job",
                queue="long",
                job_name=f"etl_sched_{j.name}",
                timeout=60 * 30,
                now=frappe.flags.in_test,
                kwargs={"job_name": j.name, "options": {}},
            )
            frappe.db.set_value("CRM Import Job", j.name, "last_run", now)


