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

        # Fetch data
        total_rows = 0
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
            for i, _ in enumerate(reader):
                if i == 0:
                    continue  # header
                total_rows += 1
        elif job.source_type == "GOOGLE_SHEETS" and job.sheet_id:
            # Placeholder: Sheets connector to be implemented
            # For now, mark unknown rowcount
            total_rows = 0
        else:
            pass

        job.db_set("total_rows", total_rows)
        job.db_set("processed_rows", 0)
        job.db_set("status", "Completed")
    except Exception as e:
        job.db_set("status", "Failed")
        job.db_set("log", f"{type(e).__name__}: {e}")
        frappe.log_error(message=frappe.get_traceback(), title=f"ETL Job Failed: {job.name}")
        raise


