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
def autogenerate_mapping(
    profile_name: str,
    source_type: str = "CSV",
    file_url: str | None = None,
    sheet_id: str | None = None,
    filedata: str | None = None,
) -> dict:
    """Create or update a CRM Import Column Map by inferring sensible defaults from headers.

    - Reads headers via `preview` (CSV URL or Google Sheets export CSV)
    - Applies simple heuristics to map common headers to target DocTypes/fields
    - Upserts a `CRM Import Column Map` named `profile_name`

    Returns a summary with created/updated status and the suggested items.
    """
    src = (source_type or "CSV").upper()
    if src not in ("CSV", "GOOGLE_SHEETS"):
        frappe.throw(_(f"Unsupported source_type: {src}"))

    if src == "CSV":
        if not (file_url or filedata):
            frappe.throw(_("Provide file_url or filedata for CSV"))
        if filedata:
            pv = preview(filedata=filedata, max_rows=5)
        else:
            pv = preview(file_url=file_url, max_rows=5)
    else:
        if not sheet_id:
            frappe.throw(_("Provide sheet_id for GOOGLE_SHEETS"))
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        pv = preview(file_url=export_url, max_rows=5)

    headers: list[str] = pv.get("headers") or []
    norm_headers: list[str] = pv.get("normalized_headers") or []

    # Heuristic mapping rules: header → (target_doctype, target_field)
    rules: dict[str, tuple[str, str]] = {
        # Lead
        "email": ("CRM Lead", "email"),
        "email_id": ("CRM Lead", "email"),
        "first_name": ("CRM Lead", "first_name"),
        "lastname": ("CRM Lead", "last_name"),
        "last_name": ("CRM Lead", "last_name"),
        "phone": ("CRM Lead", "phone"),
        "mobile": ("CRM Lead", "mobile_no"),
        "mobile_no": ("CRM Lead", "mobile_no"),
        "status": ("CRM Lead", "status"),
        "source": ("CRM Lead", "lead_source"),
        # Organization
        "organization": ("CRM Organization", "organization_name"),
        "organization_name": ("CRM Organization", "organization_name"),
        "company": ("CRM Organization", "organization_name"),
        "org": ("CRM Organization", "organization_name"),
        "website": ("CRM Organization", "website"),
        # Contact (optional)
        "contact_email": ("Contact", "email_id"),
        "contact_phone": ("Contact", "phone"),
        "contact_first_name": ("Contact", "first_name"),
        "contact_last_name": ("Contact", "last_name"),
    }

    # Build suggestions preserving original header text for readability
    suggestions: list[dict] = []
    for orig, norm in zip(headers, norm_headers):
        key = norm
        # try exact, else try simplified aliases
        target = None
        if key in rules:
            target = rules[key]
        else:
            # soft aliases
            if key.endswith("_email"):
                target = ("CRM Lead", "email")
            elif key in ("name", "full_name"):
                target = ("CRM Lead", "first_name")
            elif key in ("company_name", "employer"):
                target = ("CRM Organization", "organization_name")

        if target:
            suggestions.append(
                {
                    "source_header": orig,
                    "target_doctype": target[0],
                    "target_field": target[1],
                }
            )

    if not suggestions:
        return {
            "created": False,
            "updated": False,
            "message": _("No suggestions found from headers; create mapping manually."),
            "headers": headers,
        }

    # Upsert mapping doc
    created = False
    updated = False
    try:
        doc = frappe.get_doc("CRM Import Column Map", profile_name)
        doc.set("columns", [])
        for s in suggestions:
            doc.append("columns", s)
        doc.save()
        updated = True
    except frappe.DoesNotExistError:
        doc = frappe.get_doc(
            {
                "doctype": "CRM Import Column Map",
                "title": profile_name,
                "columns": suggestions,
            }
        )
        doc.insert()
        created = True

    return {
        "created": created,
        "updated": updated,
        "profile": profile_name,
        "items": suggestions,
    }


def _transform_value(expr: str | None, value: t.Any) -> t.Any:
    """Apply a simple Python expression transform with `value` in scope.
    If expr is empty, return the value as-is. Expressions like `value.title()` are supported.
    Safe-eval with no builtins.
    """
    if not expr:
        return value
    try:
        return eval(expr, {"__builtins__": {}}, {"value": value})
    except Exception:
        # Fallback: best-effort title-case for common text
        try:
            return str(value)
        except Exception:
            return value


@frappe.whitelist(allow_guest=False)
def job_status(job_id: str) -> dict:
    """Return current status for a CRM Import Job."""
    try:
        doc = frappe.get_doc("CRM Import Job", job_id)
        return {
            "job_id": doc.name,
            "status": doc.status,
            "total_rows": doc.get("total_rows"),
            "processed_rows": doc.get("processed_rows"),
            "error_file": doc.get("error_file"),
            "log": doc.get("log"),
        }
    except frappe.DoesNotExistError:
        frappe.throw(_(f"Job not found: {job_id}"))


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

    # If filedata provided, persist as a File and use its file_url
    if data.get("filedata") and not data.get("file_url"):
        try:
            content = data.get("filedata")
            # If base64-encoded data URLs are sent, strip prefix. Otherwise store raw text
            if isinstance(content, str) and content.startswith("data:") and "," in content:
                content = content.split(",", 1)[1]
                import base64

                content = base64.b64decode(content)
            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": (data.get("title") or "import").replace(" ", "_") + ".csv",
                    "content": content,
                    "is_private": 1,
                }
            ).insert()
            data["file_url"] = file_doc.file_url
        except Exception:
            frappe.log_error(message=frappe.get_traceback(), title="ETL Filedata save failed")

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

    # Optionally run synchronously for small uploads / immediate UX
    if bool(data.get("sync")):
        process_job(job.name, options=data)
        return {"accepted": True, "job_id": job.name}

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


def _detect_delimiter(sample: str) -> str:
    """Pick the CSV delimiter robustly for internally-generated ingest CSVs.

    csv.Sniffer().sniff() is content-driven and can mis-detect the delimiter: the
    AACR source uses '::' inside talk_id and ';'-joined multi-value fields, so on
    some batches the sniffer guessed ':' and collapsed the 43-column header into a
    single column, silently zeroing out every field mapping (rows "processed" but
    nothing inserted). The ingest CSV is always produced internally as standard
    comma-delimited RFC-4180, so restrict candidates to real CSV delimiters
    (never ':'), prefer the one whose header row yields the most columns, and
    default to ','.
    """
    first_line = (sample.splitlines() or [""])[0]
    best, best_cols = ",", first_line.count(",") + 1
    for cand in ("\t", ";", "|", ","):
        try:
            cols = len(next(csv.reader(io.StringIO(first_line), delimiter=cand)))
        except Exception:
            cols = 1
        if cols > best_cols:
            best, best_cols = cand, cols
    # A single-column result means the delimiter is wrong; fall back to comma.
    return best if best_cols > 1 else ","


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
            # Try to read from local File doc first; if not found, fallback to HTTP
            text_content = None
            try:
                from frappe.utils.file_manager import get_file

                _fname, _content = get_file(job.file_url)
                if hasattr(_content, "decode"):
                    text_content = _content.decode("utf-8", errors="ignore")
                else:
                    text_content = _content if isinstance(_content, str) else None
            except Exception:
                text_content = None

            if text_content is None:
                import requests

                r = requests.get(job.file_url, timeout=30)
                r.raise_for_status()
                text_content = r.text

            buf = io.StringIO(text_content or "")
            delimiter = _detect_delimiter(buf.read(4096))
            buf.seek(0)
            reader = csv.reader(buf, delimiter=delimiter)
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
                frappe.log_error(message=frappe.get_traceback(), title="ETL Error CSV write failed")
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

    # Build rich maps per doctype: [{field, col_idx, transform}]
    def build_entries(tgt: str) -> list[dict]:
        entries: list[dict] = []
        for mm in mapping:
            if mm["target_doctype"].strip().lower() not in (tgt,):
                continue
            src_norm = _normalize_header(mm["source_header"]) if mm.get("source_header") else None
            if src_norm and src_norm in header_to_idx:
                entries.append({
                    "field": mm["target_field"],
                    "col_idx": header_to_idx[src_norm],
                    "transform": mm.get("transform"),
                })
        return entries

    lead_entries = build_entries("crm lead") + build_entries("lead")
    contact_entries = build_entries("contact")
    org_entries = build_entries("crm organization") + build_entries("organization")
    prospect_entries = build_entries("lead prospect")

    processed = 0
    failures: list[tuple[int, str]] = []
    for idx_row, r in enumerate(rows, start=1):
        try:
            # Build candidate payloads
            lead_data: dict | None = None
            if lead_entries:
                lead_data = {"doctype": "CRM Lead"}
                for e in lead_entries:
                    col_idx = e["col_idx"]
                    if col_idx < len(r):
                        raw_val = r[col_idx]
                        val = _transform_value(e.get("transform"), raw_val)
                        # friendly normalization for common fields
                        if e["field"] in ("status", "lead_source") and isinstance(val, str):
                            val = val.strip().title()
                        lead_data[e["field"]] = val

            # Ensure master values exist for Link fields before upsert
            if lead_data:
                try:
                    if isinstance(lead_data.get("status"), str) and lead_data.get("status"):  # type: ignore[arg-type]
                        _ensure_lead_status_exists(lead_data.get("status"))  # type: ignore[arg-type]
                    if isinstance(lead_data.get("lead_source"), str) and lead_data.get("lead_source"):  # type: ignore[arg-type]
                        _ensure_lead_source_exists(lead_data.get("lead_source"))  # type: ignore[arg-type]
                except Exception:
                    # soft-fail; row handler will catch on insert if still invalid
                    frappe.log_error(message=frappe.get_traceback(), title="ETL Ensure Master Values Failed")

            org_name = None
            if org_entries:
                org_data: dict = {}
                for e in org_entries:
                    col_idx = e["col_idx"]
                    if col_idx < len(r):
                        raw_val = r[col_idx]
                        val = _transform_value(e.get("transform"), raw_val)
                        org_data[e["field"]] = val
                # Only create organization if we have a name
                if org_data and (org_data.get("organization_name") or org_data.get("organization") or org_data.get("name")):
                    org_name = _upsert_org(org_data, dry_run=dry_run)

            if lead_data and org_name and not lead_data.get("organization"):
                lead_data["organization"] = org_name

            if lead_data:
                # Capture unmapped columns into additional_data for audit
                _capture_additional_data(lead_data, headers, r, mapping)
                _upsert_lead(lead_data, dry_run=dry_run)

            # Lead Prospect staging (scientific/clinical datasets, e.g. AACR).
            # Mirrors the lead path but targets the staging doctype and preserves
            # the full source record in `raw` for provenance.
            if prospect_entries:
                prospect_data: dict = {"doctype": "Lead Prospect"}
                for e in prospect_entries:
                    col_idx = e["col_idx"]
                    if col_idx < len(r):
                        raw_val = r[col_idx]
                        prospect_data[e["field"]] = _transform_value(e.get("transform"), raw_val)
                _capture_raw_record(prospect_data, headers, r, mapping)
                _upsert_lead_prospect(prospect_data, dry_run=dry_run)

            if contact_entries:
                contact_data: dict = {"doctype": "Contact"}
                for e in contact_entries:
                    col_idx = e["col_idx"]
                    if col_idx < len(r):
                        raw_val = r[col_idx]
                        val = _transform_value(e.get("transform"), raw_val)
                        contact_data[e["field"]] = val
                if org_name:
                    contact_data["_link_org_name"] = org_name
                _upsert_contact(contact_data, dry_run=dry_run)
            processed += 1
        except Exception as row_err:
            # Row-level failure (e.g. a pre-validation skip for an empty required
            # field). Record it in `failures` so it is surfaced in the job's
            # error_file rather than silently dropped, and continue with the rest
            # of the batch. Use the exception message directly: it is more useful
            # than a traceback here, and avoids frappe.get_traceback(limit=...),
            # whose `limit` kwarg is unsupported on this Frappe build and would
            # turn a caught row error into an unhandled 500.
            frappe.log_error(message=frappe.get_traceback(), title="ETL Row Error")
            failures.append((idx_row, f"{type(row_err).__name__}: {row_err}"))
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


def _valid_select_options(doctype: str, fieldname: str) -> list[str]:
    """Return the allowed options for a Select field, or [] if not a Select."""
    try:
        meta = frappe.get_meta(doctype)
        df = meta.get_field(fieldname)
        if df and df.fieldtype == "Select" and df.options:
            return [o.strip() for o in df.options.split("\n") if o.strip()]
    except Exception:
        pass
    return []


def _clause_aware_truncate(text: str, limit: int) -> str:
    """Truncate `text` to <= `limit` chars on the last clause/word boundary.

    Preference: last ';' or ',' clause separator within the budget -> last word
    boundary -> hard cut. A boundary is only used if it retains >= 50% of the
    budget, so we never collapse to a tiny fragment. Always returns <= limit.
    """
    if text is None:
        return text
    s = str(text)
    if len(s) <= limit:
        return s
    head = s[:limit]
    floor = int(limit * 0.5)
    clause = max(head.rfind(";"), head.rfind(","))
    if clause >= floor:
        return head[:clause].rstrip(" ,;")
    space = head.rfind(" ")
    if space >= floor:
        return head[:space].rstrip(" ,;")
    return head.rstrip(" ,;")


def _truncate_text_fields(doctype: str, data: dict):
    """Trim Data/Small Text fields that exceed the field's max length.

    Frappe raises CharacterLengthExceededError on insert when a value is longer
    than the column (Data defaults to 140 when meta length is 0). Source affiliation
    strings can exceed this, so truncate on a clause boundary so the row still
    imports rather than failing the whole batch. Truncation runs before the dedup
    lookup so re-runs match on the same stored value.
    """
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return
    for field, val in list(data.items()):
        if field in ("doctype",) or val in (None, ""):
            continue
        df = meta.get_field(field)
        if not df or df.fieldtype not in ("Data", "Small Text"):
            continue
        # Data columns default to VARCHAR(140) when meta length is 0/unset.
        limit = int(df.length) if getattr(df, "length", 0) else (140 if df.fieldtype == "Data" else 0)
        if limit and len(str(val)) > limit:
            data[field] = _clause_aware_truncate(val, limit)


def _sanitize_select_fields(doctype: str, data: dict, defaults: dict | None = None):
    """Coerce Select-field values to a valid option.

    Frappe rejects out-of-list Select values on insert. For an arbitrary source
    dataset (e.g. AACR `source` has no matching option), drop or default invalid
    values so the row still imports. `defaults` supplies a fallback per field.
    """
    defaults = defaults or {}
    for field, val in list(data.items()):
        if field in ("doctype",):
            continue
        opts = _valid_select_options(doctype, field)
        if not opts:
            continue
        sval = (str(val).strip() if val is not None else "")
        if sval in opts:
            continue
        # case-insensitive rescue
        match = next((o for o in opts if o.lower() == sval.lower()), None)
        if match:
            data[field] = match
            continue
        # fall back to a configured default, else clear the field.
        # Use "" rather than omitting the key: Frappe v14 assigns the first Select
        # option when a Select key is missing on insert.
        if field in defaults and defaults[field] in opts:
            data[field] = defaults[field]
        else:
            data[field] = ""

    # Inject configured defaults for missing/blank Select fields (e.g. source).
    for field, default in defaults.items():
        if field in ("doctype",):
            continue
        if (str(data.get(field) or "")).strip():
            continue
        opts = _valid_select_options(doctype, field)
        if opts and default in opts:
            data[field] = default


def _missing_required_fields(doctype: str, data: dict) -> list[str]:
    """Return required (reqd=1) fields that are still empty after sanitize/truncate.

    Frappe raises MandatoryError on insert when a reqd field is blank. A failed
    `doc.insert()` poisons the request-level DB transaction, so the per-row
    try/except in the loop cannot recover it and the final commit rolls back the
    WHOLE batch. Detecting empties BEFORE insert lets us skip+log the offending
    row without ever poisoning the transaction. Rule is meta-driven (no hardcoded
    field list) so it tracks the doctype definition.
    """
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return []
    # Framework-managed standard fields (owner, name, creation, ...) are auto-set
    # by Frappe on insert and never appear in the ETL payload; never flag them.
    try:
        from frappe.model import default_fields as _std_fields
        std = set(_std_fields)
    except Exception:
        std = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "parent", "parentfield", "parenttype"}
    missing: list[str] = []
    for df in meta.fields:
        if not getattr(df, "reqd", 0):
            continue
        if df.fieldname in std:
            continue
        # Skip fields with a meta/server default; Frappe will populate them.
        if getattr(df, "default", None):
            continue
        val = data.get(df.fieldname)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(df.fieldname)
    return missing


def _upsert_lead_prospect(prospect_data: dict, dry_run: bool = False) -> str | None:
    """Idempotent upsert into the Lead Prospect staging doctype.

    Dedup key: `source_ref_id` (e.g. AACR talk_id), falling back to (pi_name +
    institution) when no ref id is present. JSON fields (`raw`, `enriched_data`)
    are serialized. Select fields are sanitized against the doctype meta so an
    arbitrary source value never blocks the insert.
    """
    # Serialize JSON fields.
    for jf in ("raw", "enriched_data"):
        if isinstance(prospect_data.get(jf), (dict, list)):
            prospect_data[jf] = json.dumps(prospect_data[jf], ensure_ascii=False)

    # Sanitize Selects; default `source` to "Manual Entry" for unknown sources.
    _sanitize_select_fields(
        "Lead Prospect",
        prospect_data,
        defaults={"source": "Manual Entry"},
    )

    # Trim over-length Data fields (e.g. long affiliations) so the insert
    # doesn't fail; runs before dedup so re-runs match the stored value.
    _truncate_text_fields("Lead Prospect", prospect_data)

    ref_id = (str(prospect_data.get("source_ref_id") or "")).strip()
    pi_name = (str(prospect_data.get("pi_name") or "")).strip()
    institution = (str(prospect_data.get("institution") or "")).strip()

    existing_name = None
    if ref_id:
        existing_name = frappe.db.get_value("Lead Prospect", {"source_ref_id": ref_id}, "name")
    if not existing_name and pi_name and institution:
        existing_name = frappe.db.get_value(
            "Lead Prospect", {"pi_name": pi_name, "institution": institution}, "name"
        )

    if dry_run:
        return existing_name

    if existing_name:
        updates = {k: v for k, v in prospect_data.items() if k not in ("doctype",) and v}
        if updates:
            frappe.db.set_value("Lead Prospect", existing_name, updates)
        return existing_name

    # Pre-validate required fields BEFORE insert. A blank reqd field would raise
    # MandatoryError inside doc.insert(), poisoning the request transaction and
    # rolling back the entire batch. Raising here (no insert attempted) keeps the
    # transaction clean; the loop's per-row handler logs it to the error_file so
    # the skipped row is surfaced, never silently dropped.
    missing = _missing_required_fields("Lead Prospect", prospect_data)
    if missing:
        raise frappe.ValidationError(
            "Skipped Lead Prospect row: empty required field(s) "
            f"{missing} (source_ref_id={ref_id or '<none>'})"
        )

    doc = frappe.get_doc(prospect_data)
    doc.insert()
    return doc.name


def _capture_raw_record(prospect_data: dict, headers: list[str], row: list[str], mapping: list[dict]):
    """Preserve the full source record for a Lead Prospect.

    - `raw`: the COMPLETE flattened source row (all columns) for provenance.
    - `enriched_data`: only the columns NOT mapped to a Lead Prospect field
      (everything the structured fields didn't capture), available for later use.
    """
    try:
        full: dict[str, str] = {}
        for idx, h in enumerate(headers):
            if idx < len(row):
                v = row[idx]
                if v not in (None, ""):
                    full[h] = v
        prospect_data["raw"] = full

        mapped_headers = set()
        for m in mapping:
            if (m.get("target_doctype") or "").strip().lower() == "lead prospect":
                src = (m.get("source_header") or "").strip()
                if src:
                    mapped_headers.add(_normalize_header(src))
        leftover = {h: v for h, v in full.items() if _normalize_header(h) not in mapped_headers}
        if leftover:
            prospect_data["enriched_data"] = leftover
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title="ETL Capture raw record failed")


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
        frappe.log_error(message=frappe.get_traceback(), title="Contact link failed")


def _ensure_lead_status_exists(status: str):
    """Create a CRM Lead Status on-the-fly if missing."""
    val = (status or "").strip()
    if not val:
        return
    name = frappe.db.exists("CRM Lead Status", val)
    if name:
        return
    doc = frappe.get_doc({
        "doctype": "CRM Lead Status",
        "lead_status": val,
        "color": "gray",
        "position": 0,
    })
    doc.insert(ignore_permissions=True)


def _ensure_lead_source_exists(source: str):
    """Create a CRM Lead Source on-the-fly if missing."""
    val = (source or "").strip()
    if not val:
        return
    name = frappe.db.exists("CRM Lead Source", val)
    if name:
        return
    doc = frappe.get_doc({
        "doctype": "CRM Lead Source",
        "source_name": val,
    })
    doc.insert(ignore_permissions=True)


def _capture_additional_data(lead_data: dict, headers: list[str], row: list[str], mapping: list[dict]):
    """Store unmapped CSV columns into lead_data['additional_data'] as JSON.

    - mapping: list of {source_header, target_doctype, target_field}
    Only captures columns that were not mapped to any target field for the lead.
    """
    try:
        mapped_headers = set()
        for m in mapping:
            if (m.get("target_doctype") or "").strip().lower() in ("crm lead", "lead"):
                src = (m.get("source_header") or "").strip()
                if src:
                    mapped_headers.add(_normalize_header(src))

        additional: dict[str, str] = {}
        for idx, h in enumerate(headers):
            norm = _normalize_header(h)
            if norm in mapped_headers:
                continue
            if idx < len(row):
                v = row[idx]
                if v not in (None, ""):
                    additional[h] = v

        if additional:
            existing = {}
            try:
                if isinstance(lead_data.get("additional_data"), str):
                    existing = json.loads(lead_data.get("additional_data"))  # type: ignore[arg-type]
                elif isinstance(lead_data.get("additional_data"), dict):
                    existing = lead_data.get("additional_data")  # type: ignore[assignment]
            except Exception:
                existing = {}
            existing.update(additional)
            lead_data["additional_data"] = existing
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title="ETL Capture additional_data failed")


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


