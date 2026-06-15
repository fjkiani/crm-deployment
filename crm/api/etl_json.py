# Copyright (c) 2026, CrisPRO/Brenus and contributors
# For license information, please see license.txt
"""JSON projection layer for the agentic dataset-ingest capability.

Gap #1 closed here: the existing ETL kernel (crm/api/etl.py) operates on FLAT
CSV/Google-Sheets headers. It cannot read nested/arbitrary JSON records (e.g. an
AACR talk record with `speaker.name` and `tumor_types[]`). This module flattens
arbitrary nested JSON into a flat, tabular field set with the SAME return shape
that `etl.preview()` produces, so everything downstream (autogenerate_mapping,
process_job, _apply_mapping_and_upsert) is reused unchanged.

Two public, whitelisted entrypoints:
  - preview_records(records_json, ...) -> {headers, normalized_headers, sample, inferred}
  - records_to_csv_file(records_json, ...) -> {file_url, headers, row_count}
        materializes the flattened records as a CSV File doc so a JSON dataset can
        be driven through the existing CSV process_job pipeline with zero forking.
"""

import io
import csv
import json
import typing as t

import frappe
from frappe import _

# Reuse the kernel's own helpers so JSON and CSV paths normalize/infer identically.
from crm.api.etl import _normalize_header, _infer_type


# Array reduction policy. Select/Link targets generally want a single scalar;
# free text wants a readable join. Default per-type is decided by the caller,
# but the flattener exposes the raw choice so mapping/transform can override.
ArrayPolicy = str  # one of: "first" | "join" | "last" | "count"

_DEFAULT_ARRAY_POLICY: ArrayPolicy = "join"
_JOIN_SEP = "; "


def _reduce_array(values: list, policy: ArrayPolicy) -> t.Any:
    """Collapse a list value to a scalar per the chosen policy.

    Scalars-in-list are stringified; dicts in a list are JSON-encoded so no
    information is silently dropped (it remains recoverable downstream / in `raw`).
    """
    flat: list[str] = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            flat.append(json.dumps(v, ensure_ascii=False, sort_keys=True))
        else:
            flat.append(str(v))
    if not flat:
        return ""
    if policy == "first":
        return flat[0]
    if policy == "last":
        return flat[-1]
    if policy == "count":
        return str(len(flat))
    # default: join
    return _JOIN_SEP.join(flat)


def flatten_record(
    rec: t.Any,
    array_policy: ArrayPolicy = _DEFAULT_ARRAY_POLICY,
    _prefix: str = "",
) -> dict:
    """Flatten a nested JSON object to dot-path keys.

    - Nested objects -> `parent.child` keys (recursively).
    - Arrays of scalars/objects -> reduced to one value via `array_policy`, with an
      additional `<key>__count` companion key so cardinality is never lost.
    - Scalars -> kept as-is (stringified at CSV time, not here).

    Example: {"speaker": {"name": "X"}, "tumor_types": ["a","b"]}
        -> {"speaker.name": "X", "tumor_types": "a; b", "tumor_types__count": "2"}
    """
    out: dict = {}
    if isinstance(rec, dict):
        for k, v in rec.items():
            key = f"{_prefix}{k}"
            if isinstance(v, dict):
                out.update(flatten_record(v, array_policy, _prefix=f"{key}."))
            elif isinstance(v, list):
                out[key] = _reduce_array(v, array_policy)
                out[f"{key}__count"] = str(len([x for x in v if x is not None]))
            else:
                out[key] = v
    else:
        # Non-dict top-level record (rare) — store under a generic key.
        out[_prefix or "value"] = rec
    return out


def _load_records(records_json: str | None, file_url: str | None) -> list[dict]:
    """Accept either an inline JSON string (array OR {records:[...]}) or a File URL."""
    if not records_json and not file_url:
        frappe.throw(_("Provide records_json or file_url"))
    raw: t.Any
    if records_json:
        try:
            raw = json.loads(records_json)
        except Exception:
            frappe.throw(_("records_json is not valid JSON"))
    else:
        text = None
        try:
            from frappe.utils.file_manager import get_file

            _fn, content = get_file(file_url)
            text = content.decode("utf-8", errors="ignore") if hasattr(content, "decode") else content
        except Exception:
            import requests

            r = requests.get(file_url, timeout=30)
            r.raise_for_status()
            text = r.text
        try:
            raw = json.loads(text or "[]")
        except Exception:
            frappe.throw(_("File content is not valid JSON"))

    # Normalize to a list of records.
    if isinstance(raw, dict):
        # common envelopes: {"records": [...]} / {"data": [...]} / {"items": [...]}
        for key in ("records", "data", "items", "results"):
            if isinstance(raw.get(key), list):
                return raw[key]
        # single record
        return [raw]
    if isinstance(raw, list):
        return raw
    frappe.throw(_("JSON must be an array of records or an object containing one"))


def _flatten_all(records: list[dict], array_policy: ArrayPolicy) -> tuple[list[str], list[dict]]:
    """Flatten every record and compute the UNION of keys (stable, first-seen order)."""
    flattened: list[dict] = [flatten_record(r, array_policy) for r in records]
    seen: dict[str, None] = {}
    for fr in flattened:
        for k in fr.keys():
            if k not in seen:
                seen[k] = None
    headers = list(seen.keys())
    return headers, flattened


@frappe.whitelist(allow_guest=False)
def preview_records(
    records_json: str | None = None,
    file_url: str | None = None,
    array_policy: str = _DEFAULT_ARRAY_POLICY,
    max_rows: int = 50,
) -> dict:
    """Preview an arbitrary JSON dataset as if it were tabular.

    Returns the SAME shape as crm.api.etl.preview so autogenerate_mapping and the
    rest of the kernel consume it unchanged:
        { headers, normalized_headers, sample, inferred, total_records }
    """
    records = _load_records(records_json, file_url)
    total = len(records)
    headers, flattened = _flatten_all(records, array_policy)
    norm_headers = [_normalize_header(h) for h in headers]

    # Build sample rows aligned to `headers`.
    sample: list[list[str]] = []
    for fr in flattened[: int(max_rows)]:
        sample.append(["" if fr.get(h) is None else str(fr.get(h, "")) for h in headers])

    # Column-wise inference reuses the kernel's _infer_type.
    cols: dict[str, list[str]] = {h: [] for h in norm_headers}
    for row in sample:
        for idx, h in enumerate(norm_headers):
            if idx < len(row):
                cols[h].append(row[idx])
    inferred = {h: _infer_type(vs) for h, vs in cols.items()}

    return {
        "headers": headers,
        "normalized_headers": norm_headers,
        "sample": sample,
        "inferred": inferred,
        "total_records": total,
    }


@frappe.whitelist(allow_guest=False)
def records_to_csv_file(
    records_json: str | None = None,
    file_url: str | None = None,
    array_policy: str = _DEFAULT_ARRAY_POLICY,
    title: str = "json_ingest",
    is_private: int = 1,
) -> dict:
    """Materialize a flattened JSON dataset as a CSV File doc.

    This is the bridge that lets a JSON dataset reuse the EXISTING CSV pipeline:
    the returned file_url is fed straight into etl.import_rows(source_type="CSV").
    Returns { file_url, headers, row_count }.
    """
    records = _load_records(records_json, file_url)
    headers, flattened = _flatten_all(records, array_policy)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for fr in flattened:
        writer.writerow(["" if fr.get(h) is None else _stringify(fr.get(h)) for h in headers])

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": (title or "json_ingest").replace(" ", "_") + ".csv",
            "content": buf.getvalue(),
            "is_private": 1 if int(is_private) else 0,
        }
    ).insert()

    return {
        "file_url": file_doc.file_url,
        "headers": headers,
        "row_count": len(flattened),
    }


def _stringify(v: t.Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


# ---------------------------------------------------------------------------
# B2 — Agentic field-mapping kernel (Tier-1 deterministic)
#
# Gap #2 closed here. The legacy crm.api.etl.autogenerate_mapping uses a frozen
# rules dict that only targets CRM Lead / Organization / Contact and cannot point
# at Lead Prospect. This kernel is:
#   - parameterized by ANY target doctype,
#   - driven by the target's LIVE field metadata (frappe.get_meta), not a frozen
#     table, so it adapts as doctypes evolve,
#   - returns confidences + an explicit `unmapped` list that the Tier-2 LLM
#     fallback (next module fn) is asked to resolve.
# It is dataset-agnostic: no AACR-specific field names are hardcoded.
# ---------------------------------------------------------------------------

# System/layout fields that are never mapping targets.
_SKIP_FIELDTYPES = {
    "Section Break", "Column Break", "Tab Break", "HTML", "Heading",
    "Button", "Image", "Fold", "Table", "Table MultiSelect",
}
_SKIP_FIELDNAMES = {
    "naming_series", "amended_from", "owner", "assigned_to",
    "created_by_job", "promoted_to_lead",
}

# Generic semantic aliases keyed by TARGET fieldname tokens. These encode common
# CRM/scientific synonyms that pure name/label matching misses. Keyed on the
# target side (not the source), so they generalize across source datasets.
_SEMANTIC_ALIASES: dict[str, list[str]] = {
    "pi_name": ["speaker", "investigator", "presenter", "author", "contact", "name", "full_name", "pi"],
    "pi_email": ["email", "email_id", "contact_email"],
    "institution": ["affiliation", "organization", "company", "institute", "university", "employer", "site"],
    "cancer_type": ["tumor", "tumor_type", "tumor_types", "indication", "disease", "cancer"],
    "trial_phase": ["phase", "clinical_stage", "stage", "trial_phase"],
    "source_ref_id": ["id", "ref", "ref_id", "external_id", "talk_id", "record_id", "uid"],
    "source": ["source", "origin", "provenance"],
    "notes": ["summary", "moa_summary", "description", "abstract", "key_findings", "comment"],
    "lead_score": ["score", "rank", "priority"],
    "tier": ["tier", "segment", "grade"],
}


def _normish(s: str) -> str:
    return _normalize_header(s or "")


def _tokens(s: str) -> set:
    return {t for t in _normish(s).split("_") if t}


def _ratio(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, _normish(a), _normish(b)).ratio()


def _score_match(src_field: str, tgt_fieldname: str, tgt_label: str) -> float:
    """Deterministic similarity in [0,1] between a source field and a target field.

    Combines: exact normalized-name (1.0), label match, token overlap (Jaccard),
    fuzzy ratio, and the target-keyed semantic-alias table.
    """
    s_norm = _normish(src_field)
    # exact name or label
    if s_norm == _normish(tgt_fieldname) or s_norm == _normish(tgt_label):
        return 1.0
    # leaf of a dot-path: speaker.name -> "name"
    leaf = s_norm.split(".")[-1] if "." in src_field else s_norm
    if leaf == _normish(tgt_fieldname):
        return 0.95

    score = 0.0
    # semantic alias hit (target-keyed)
    aliases = _SEMANTIC_ALIASES.get(tgt_fieldname, [])
    s_tokens = _tokens(src_field) | {leaf}
    if any(_normish(a) in s_tokens or _normish(a) == leaf for a in aliases):
        score = max(score, 0.9)
    # token overlap (Jaccard) against name+label
    tgt_tokens = _tokens(tgt_fieldname) | _tokens(tgt_label)
    if tgt_tokens and s_tokens:
        jacc = len(s_tokens & tgt_tokens) / len(s_tokens | tgt_tokens)
        score = max(score, 0.6 + 0.3 * jacc if jacc > 0 else 0.0)
    # fuzzy fallback
    score = max(score, 0.7 * _ratio(src_field, tgt_fieldname), 0.65 * _ratio(src_field, tgt_label))
    return round(min(score, 0.99), 3)


def _target_field_catalog(doctype: str) -> list[dict]:
    """Live, mappable field catalog for a target doctype (via frappe.get_meta)."""
    meta = frappe.get_meta(doctype)
    out: list[dict] = []
    for df in meta.fields:
        if df.fieldtype in _SKIP_FIELDTYPES:
            continue
        if df.fieldname in _SKIP_FIELDNAMES:
            continue
        if getattr(df, "read_only", 0):
            continue
        out.append({
            "fieldname": df.fieldname,
            "label": df.label or df.fieldname,
            "fieldtype": df.fieldtype,
            "options": df.options or None,
            "reqd": int(getattr(df, "reqd", 0) or 0),
        })
    return out


@frappe.whitelist(allow_guest=False)
def propose_mapping(
    target_doctype: str,
    records_json: str | None = None,
    file_url: str | None = None,
    array_policy: str = _DEFAULT_ARRAY_POLICY,
    profile_name: str | None = None,
    min_confidence: float = 0.6,
    save: int = 0,
) -> dict:
    """Tier-1 deterministic mapping proposal for an arbitrary dataset → target doctype.

    Returns:
      {
        target_doctype, source_fields, target_fields,
        proposals: [{source_header, target_doctype, target_field, confidence, basis}],
        unmapped_source: [...],     # source fields with no confident target (Tier-2 input)
        unmapped_required: [...],   # required target fields no source mapped to (gaps)
        saved_profile: <name|null>
      }
    """
    pv = preview_records(records_json=records_json, file_url=file_url, array_policy=array_policy, max_rows=5)
    source_fields: list[str] = pv["headers"]
    catalog = _target_field_catalog(target_doctype)

    proposals: list[dict] = []
    used_targets: set = set()
    unmapped_source: list[str] = []

    # Greedy best-target per source field; one target field used at most once.
    for src in source_fields:
        # ignore the synthetic __count companions for primary mapping
        if src.endswith("__count"):
            continue
        best = None
        best_score = 0.0
        for tf in catalog:
            if tf["fieldname"] in used_targets:
                continue
            sc = _score_match(src, tf["fieldname"], tf["label"])
            if sc > best_score:
                best_score, best = sc, tf
        if best and best_score >= float(min_confidence):
            proposals.append({
                "source_header": src,
                "target_doctype": target_doctype,
                "target_field": best["fieldname"],
                "confidence": best_score,
                "basis": "deterministic",
                "target_fieldtype": best["fieldtype"],
            })
            used_targets.add(best["fieldname"])
        else:
            unmapped_source.append(src)

    required = [tf["fieldname"] for tf in catalog if tf["reqd"]]
    unmapped_required = [f for f in required if f not in used_targets]

    saved = None
    if int(save) and profile_name:
        saved = _save_mapping_profile(profile_name, target_doctype, proposals)

    return {
        "target_doctype": target_doctype,
        "source_fields": source_fields,
        "target_fields": [tf["fieldname"] for tf in catalog],
        "proposals": proposals,
        "unmapped_source": unmapped_source,
        "unmapped_required": unmapped_required,
        "saved_profile": saved,
    }


def source_signature(source_fields: list[str]) -> str:
    """Stable hash of source field names → used to auto-match a saved profile to
    an incoming dataset of the same shape (propose-and-pause auto-reuse)."""
    import hashlib
    norm = sorted(_normalize_header(f) for f in source_fields if not f.endswith("__count"))
    return hashlib.sha1("|".join(norm).encode("utf-8")).hexdigest()[:16]


def find_reusable_profile(target_doctype: str, source_fields: list[str]) -> str | None:
    """Return an APPROVED profile name whose source_signature matches, else None.

    This is the 'auto-reuse after first approval' half of the propose-and-pause
    policy: once a human approves a profile for a given schema, future imports of
    the same schema skip the LLM/review step entirely.
    """
    sig = source_signature(source_fields)
    rows = frappe.get_all(
        "CRM Import Column Map",
        filters={"target_doctype": target_doctype, "status": "Approved", "source_signature": sig},
        fields=["name"],
        limit=1,
    )
    return rows[0]["name"] if rows else None


def _save_mapping_profile(
    profile_name: str,
    target_doctype: str,
    proposals: list[dict],
    source_fields: list[str] | None = None,
    status: str = "Needs Review",
) -> str:
    """Persist proposals as a CRM Import Column Map (reuses the existing doctype).

    Writes status (propose-and-pause gate) + source_signature (auto-reuse key) +
    per-column confidence/basis so the profile is reviewable in the Frappe UI.
    """
    columns = [
        {
            "source_header": p["source_header"],
            "target_doctype": p["target_doctype"],
            "target_field": p["target_field"],
            "transform": p.get("transform") or None,
            "confidence": p.get("confidence"),
            "basis": p.get("basis") or "deterministic",
        }
        for p in proposals
    ]
    sig = source_signature(source_fields or [p["source_header"] for p in proposals])
    try:
        doc = frappe.get_doc("CRM Import Column Map", profile_name)
        doc.set("columns", [])
        for c in columns:
            doc.append("columns", c)
        doc.target_doctype = target_doctype
        doc.status = status
        doc.source_signature = sig
        doc.save()
    except frappe.DoesNotExistError:
        doc = frappe.get_doc({
            "doctype": "CRM Import Column Map",
            "title": profile_name,
            "target_doctype": target_doctype,
            "status": status,
            "source_signature": sig,
            "columns": columns,
        })
        doc.insert()
    return doc.name


# ---------------------------------------------------------------------------
# B2 Tier-2 — LLM fallback for fields Tier-1 could not confidently map.
#
# Per the locked decision (propose-and-pause, then auto-reuse): on first sight of
# a new schema, LLM-proposed mappings are saved with status "Needs Review" for a
# human to approve; once Approved, find_reusable_profile() auto-reuses them.
#
# Architecture (locked decision: kernel in crm/api, eaia invokes): the LLM client
# lives in the eaia app, NOT here — so this fn accepts an INJECTABLE callable
# `llm_complete(prompt:str)->str`. When eaia calls run_dataset_ingest it passes a
# Gemini-backed callable; a pure-Frappe call with no callable degrades gracefully
# to "return unmapped for review" (which is exactly propose-and-pause).
# ---------------------------------------------------------------------------

def _build_llm_mapping_prompt(unmapped_source: list[str], samples: dict, catalog: list[dict]) -> str:
    avail = [
        f"- {tf['fieldname']} ({tf['fieldtype']}{': ' + tf['options'].replace(chr(10), '/') if tf.get('options') else ''})"
        for tf in catalog
    ]
    src_lines = []
    for s in unmapped_source:
        ex = samples.get(s)
        src_lines.append(f"- {s}" + (f"  e.g. {str(ex)[:80]!r}" if ex else ""))
    return (
        "You map fields from an arbitrary source dataset onto a fixed target DocType.\n"
        "For each UNMAPPED source field, choose the single best target field, or null if none fits.\n"
        "Only use target fields from the AVAILABLE list. Prefer leaving a field unmapped over a weak guess.\n\n"
        f"TARGET DOCTYPE FIELDS (available):\n" + "\n".join(avail) + "\n\n"
        f"UNMAPPED SOURCE FIELDS:\n" + "\n".join(src_lines) + "\n\n"
        'Return ONLY JSON: {"mappings":[{"source_header":"...","target_field":"...|null",'
        '"confidence":0.0-1.0,"reason":"short"}]}'
    )


def _default_llm_complete() -> t.Callable[[str], str] | None:
    """Build a server-side LLM callable from the app's own config.

    Lets the kernel run Tier-2 without a caller-injected callable (e.g. when the
    ingest is triggered over REST by the eaia agent, which cannot pass a Python
    function across the process boundary). Lazy-imports langchain_google_genai so
    the kernel keeps ZERO hard LLM dependency: if the package or an API key is
    absent, returns None and Tier-2 cleanly degrades to "leave unmapped → review".
    Model/key mirror the eaia pattern (Gemini, temperature 0).
    """
    try:
        import os
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        return None
    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
               or frappe.conf.get("google_api_key") or frappe.conf.get("gemini_api_key"))
    if not api_key:
        return None
    model_name = frappe.conf.get("ingest_llm_model") or "gemini-1.5-pro"
    try:
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, google_api_key=api_key)
    except Exception:
        return None

    def _complete(prompt: str) -> str:
        return llm.invoke(prompt).content

    return _complete


def llm_complete_unmapped(
    unmapped_source: list[str],
    samples: dict,
    catalog: list[dict],
    llm_complete: t.Callable[[str], str] | None,
    used_targets: set | None = None,
) -> list[dict]:
    """Run the Tier-2 LLM pass. Returns proposals with basis='llm'.

    If no llm_complete is injected, returns [] (caller keeps unmapped → review).
    """
    if not llm_complete or not unmapped_source:
        return []
    used = set(used_targets or set())
    prompt = _build_llm_mapping_prompt(unmapped_source, samples, catalog)
    try:
        raw = llm_complete(prompt)
        # tolerate code-fenced JSON
        txt = raw.strip()
        if "```" in txt:
            txt = txt.split("```")[1].lstrip("json").strip() if txt.count("```") >= 2 else txt
        data = json.loads(txt)
    except Exception:
        frappe.log_error(message=frappe.get_traceback(), title="ETL Tier-2 LLM mapping parse failed")
        return []

    valid_targets = {tf["fieldname"] for tf in catalog}
    out: list[dict] = []
    for m in (data.get("mappings") or []):
        tf = m.get("target_field")
        if not tf or tf in (None, "null") or tf not in valid_targets or tf in used:
            continue
        src = m.get("source_header")
        if src not in unmapped_source:
            continue
        used.add(tf)
        out.append({
            "source_header": src,
            "target_doctype": None,  # filled by caller (knows target_doctype)
            "target_field": tf,
            "confidence": float(m.get("confidence") or 0.5),
            "basis": "llm",
            "reason": (m.get("reason") or "")[:140],
        })
    return out


@frappe.whitelist(allow_guest=False)
def propose_mapping_agentic(
    target_doctype: str,
    records_json: str | None = None,
    file_url: str | None = None,
    array_policy: str = _DEFAULT_ARRAY_POLICY,
    profile_name: str | None = None,
    min_confidence: float = 0.7,
    save: int = 1,
    use_llm: int = 0,
    _llm_complete: t.Callable[[str], str] | None = None,
) -> dict:
    """Full agentic proposer: Tier-1 deterministic + Tier-2 LLM, persisting a
    'Needs Review' profile (propose-and-pause). Reuses an Approved profile
    automatically when the source schema signature already matches.

    Tier-2 LLM fires when a callable is available. Resolution order:
      1. caller-injected `_llm_complete` (in-process, e.g. eaia passes a callable);
      2. if `use_llm` is truthy and (1) is absent, the server-side default Gemini
         callable (lets a REST trigger enable the LLM tier without a callable).
    If neither resolves, Tier-2 degrades to [] and unmapped fields go to review.
    """
    if _llm_complete is None and int(use_llm):
        _llm_complete = _default_llm_complete()

    pv = preview_records(records_json=records_json, file_url=file_url, array_policy=array_policy, max_rows=5)
    source_fields = pv["headers"]

    # Auto-reuse: if an Approved profile already covers this exact schema, use it.
    reusable = find_reusable_profile(target_doctype, source_fields)
    if reusable:
        return {
            "target_doctype": target_doctype,
            "reused_profile": reusable,
            "status": "Approved",
            "message": "Reused previously approved mapping for this schema.",
        }

    # Tier-1 deterministic.
    t1 = propose_mapping(
        target_doctype=target_doctype, records_json=records_json, file_url=file_url,
        array_policy=array_policy, min_confidence=min_confidence, save=0,
    )
    proposals = t1["proposals"]
    used_targets = {p["target_field"] for p in proposals}

    # Tier-2 LLM on whatever Tier-1 left unmapped.
    catalog = _target_field_catalog(target_doctype)
    samples = {h: (pv["sample"][0][i] if pv["sample"] and i < len(pv["sample"][0]) else None)
               for i, h in enumerate(source_fields)}
    t2 = llm_complete_unmapped(t1["unmapped_source"], samples, catalog, _llm_complete, used_targets)
    for p in t2:
        p["target_doctype"] = target_doctype
    proposals = proposals + t2

    still_unmapped = [s for s in t1["unmapped_source"] if s not in {p["source_header"] for p in t2}]

    saved = None
    if int(save) and profile_name:
        # propose-and-pause: a freshly proposed mapping for a new schema always
        # lands as "Needs Review" (whether or not the LLM tier fired). It is only
        # auto-reused after a human flips it to "Approved".
        saved = _save_mapping_profile(profile_name, target_doctype, proposals,
                                      source_fields=source_fields, status="Needs Review")

    return {
        "target_doctype": target_doctype,
        "source_fields": source_fields,
        "proposals": proposals,
        "tier1_count": len(t1["proposals"]),
        "tier2_llm_count": len(t2),
        "unmapped_source": still_unmapped,
        "unmapped_required": t1["unmapped_required"],
        "saved_profile": saved,
        "status": "Needs Review" if saved else "Draft",
    }
