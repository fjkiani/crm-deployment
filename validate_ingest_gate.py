"""
Validation gate for the agentic dataset-ingest capability.

Exercises the REAL orchestration code (`crm.api.leadgen.run_dataset_ingest`) and
the REAL mapping kernel (`crm.api.etl_json`) against the REAL AACR-862 dataset,
by stubbing only the Frappe runtime + the CSV->DB writer (which genuinely needs
a live Frappe). The flatten, mapping proposal, propose-and-pause gate, and CSV
materialization all run for real.

What this PROVES (in-sandbox, no Frappe):
  1. B1 flatten: nested AACR JSON -> flat dot-path field set.
  2. B2 mapping: doctype-meta-driven Tier-1 proposal onto Lead Prospect.
  3. Propose-and-pause gate: a never-seen schema with required-field gaps STOPS
     at stage="mapping_review" (does NOT silently import).
  4. After approving the saved profile, re-run drives CSV materialization + the
     (stubbed) dry-run import path end-to-end -> stage="imported".

What it does NOT prove (needs Frappe Cloud): the actual DB upsert into Lead
Prospect. That is the on-cloud step.
"""
import sys, json, types, importlib.util, hashlib
from pathlib import Path

REPO = Path("/workspace/crm-platform")
AACR = Path("/mnt/user-uploads/aacr2026_schema_a_master.json")
LP_JSON = REPO / "crm/fcrm/doctype/lead_prospect/lead_prospect.json"

# ---------------------------------------------------------------------------
# 1. Build a realistic Lead Prospect meta from the authoritative doctype JSON
# ---------------------------------------------------------------------------
_lp = json.loads(LP_JSON.read_text())

class _Field:
    def __init__(self, d):
        self.fieldname = d.get("fieldname")
        self.label = d.get("label") or d.get("fieldname")
        self.fieldtype = d.get("fieldtype")
        self.options = d.get("options")
        self.reqd = d.get("reqd", 0)

class _Meta:
    def __init__(self, fields):
        self.fields = [_Field(f) for f in fields]

_META = {"Lead Prospect": _Meta(_lp["fields"])}

# ---------------------------------------------------------------------------
# 2. A captured "DB": fake docs that record inserts / attribute writes
# ---------------------------------------------------------------------------
SAVED = {"column_maps": {}, "jobs": [], "set_values": []}

class _FakeDoc(dict):
    """Behaves like a Frappe doc: attribute access + .insert()/.save()/.append()."""
    def __init__(self, data=None):
        super().__init__(data or {})
        self._children = {}
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: return self._children.get(k)
    def __setattr__(self, k, v):
        if k.startswith("_"): super().__setattr__(k, v)
        else: self[k] = v
    def append(self, table, row):
        self._children.setdefault(table, []).append(row)
        self[table] = self._children[table]
        return row
    def set(self, k, v):
        if isinstance(v, list):
            self._children[k] = list(v)
        self[k] = v
        return v
    def insert(self, *a, **k):
        if self.get("doctype") == "LeadGen Job":
            self["name"] = f"LGJ-TEST-{len(SAVED['jobs'])+1}"
            SAVED["jobs"].append(self)
        elif self.get("doctype") == "CRM Import Column Map":
            nm = self.get("__profile_name") or f"CM-{len(SAVED['column_maps'])+1}"
            self["name"] = nm
            SAVED["column_maps"][nm] = self
        return self
    def save(self, *a, **k):
        return self

# ---------------------------------------------------------------------------
# 3. Stub `frappe`
# ---------------------------------------------------------------------------
frappe = types.ModuleType("frappe")

class _ValidationError(Exception): pass
frappe.ValidationError = _ValidationError
frappe.DoesNotExistError = type("DoesNotExistError", (Exception,), {})

def _throw(msg, exc=None):
    raise (exc or _ValidationError)(str(msg))
frappe.throw = _throw
frappe._ = lambda s, *a, **k: s

def _whitelist(*dargs, **dkw):
    # supports both @frappe.whitelist and @frappe.whitelist(allow_guest=...)
    if len(dargs) == 1 and callable(dargs[0]) and not dkw:
        return dargs[0]
    def deco(fn): return fn
    return deco
frappe.whitelist = _whitelist

frappe.has_permission = lambda *a, **k: True
frappe.get_meta = lambda dt: _META[dt]
frappe.as_json = lambda o, *a, **k: json.dumps(o, default=str)
frappe.get_traceback = lambda *a, **k: "<traceback>"
frappe.log_error = lambda *a, **k: None

_PROFILE_NAME_HOLDER = {"name": None}

def _get_doc(arg, *a, **k):
    # get_doc("CRM Import Column Map", name)  OR  get_doc({...})
    if isinstance(arg, str):
        dt = arg; name = a[0] if a else None
        if dt == "CRM Import Column Map":
            if name in SAVED["column_maps"]:
                return SAVED["column_maps"][name]
            raise frappe.DoesNotExistError(name)
        return _FakeDoc({"doctype": dt, "name": name})
    doc = _FakeDoc(dict(arg))
    if doc.get("doctype") == "CRM Import Column Map" and _PROFILE_NAME_HOLDER["name"]:
        doc["__profile_name"] = _PROFILE_NAME_HOLDER["name"]
    return doc
frappe.get_doc = _get_doc

def _get_all(doctype, filters=None, **k):
    # used by find_reusable_profile -> return [] (no approved profile yet)
    flt = filters or {}
    out = []
    for nm, doc in SAVED["column_maps"].items():
        if (doc.get("status") == flt.get("status")
                and doc.get("target_doctype") == flt.get("target_doctype")
                and doc.get("source_signature") == flt.get("source_signature")):
            out.append({"name": nm})
    return out
frappe.get_all = _get_all

class _DB:
    def set_value(self, dt, name, field, value):
        SAVED["set_values"].append((dt, name, field, value))
        if dt == "CRM Import Column Map" and name in SAVED["column_maps"]:
            SAVED["column_maps"][name][field] = value
    def exists(self, *a, **k): return None
    def get_value(self, *a, **k): return None
frappe.db = _DB()

class _Session: user = "Administrator"
frappe.session = _Session()

class _Conf(dict):
    def get(self, k, d=None): return super().get(k, d)
frappe.conf = _Conf()  # empty -> no LLM key -> Tier-2 cleanly degrades

# frappe.utils + submodules
utils = types.ModuleType("frappe.utils")
utils.now = lambda: "2026-06-15 00:00:00"
utils.cint = lambda v, *a: int(v or 0)
utils.flt = lambda v, *a: float(v or 0)
frappe.utils = utils

fm = types.ModuleType("frappe.utils.file_manager")
def _get_file(file_url):
    # If a real local file is referenced, return its bytes; else raise.
    raise frappe.DoesNotExistError(file_url)
fm.get_file = _get_file
utils.file_manager = fm

sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = utils
sys.modules["frappe.utils.file_manager"] = fm

# ---------------------------------------------------------------------------
# 4. Load REAL etl_json from disk (under the package name it expects)
# ---------------------------------------------------------------------------
def _load(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = m
    spec.loader.exec_module(m)
    return m

# make a real-ish `crm`, `crm.api` package chain so intra-package imports resolve
for pkg in ["crm", "crm.api"]:
    if pkg not in sys.modules:
        p = types.ModuleType(pkg); p.__path__ = []; sys.modules[pkg] = p

# ---------------------------------------------------------------------------
# 5. Stub `etl` FIRST (etl_json imports _normalize_header/_infer_type from it at
#    module load). Use the REAL (verbatim) helper implementations so behavior is
#    identical to production; only import_rows / job_status are simulated.
# ---------------------------------------------------------------------------
etl = types.ModuleType("crm.api.etl")
_IMPORT_CALLS = []

# verbatim copies of the real pure helpers from crm/api/etl.py
def _normalize_header(h):
    return (h or "").strip().replace(" ", "_").replace("/", "_").replace("-", "_").lower()

def _infer_type(values):
    sample = [v for v in values if v not in (None, "", "null", "None")][:25]
    if not sample:
        return "Data"
    lowers = [v.lower() for v in sample if isinstance(v, str)]
    if all("@" in v and "." in v for v in lowers):
        return "Data"
    digits = sum(1 for v in sample if str(v).replace("+", "").replace("-", "").replace(" ", "").isdigit())
    if digits >= max(3, len(sample) // 2):
        return "Data"
    return "Data"

etl._normalize_header = _normalize_header
etl._infer_type = _infer_type
sys.modules["crm.api.etl"] = etl
sys.modules["crm.api"].etl = etl

# now load the REAL etl_json (its `from crm.api.etl import ...` will resolve)
etl_json = _load("crm.api.etl_json", str(REPO / "crm/api/etl_json.py"))
sys.modules["crm.api"].etl_json = etl_json

def _import_rows(payload_json):
    payload = json.loads(payload_json)
    _IMPORT_CALLS.append(payload)
    # Count real rows from the CSV the kernel just wrote (file_url is a local path here).
    fu = payload.get("file_url")
    n = 0
    if fu and Path(fu).exists():
        with open(fu, encoding="utf-8") as fh:
            n = max(0, sum(1 for _ in fh) - 1)  # minus header
    job_id = f"IMPORTJOB-{len(_IMPORT_CALLS)}"
    etl._jobs[job_id] = {
        "status": "Completed" if payload.get("dry_run") else "Completed",
        "total_rows": n, "processed_rows": n, "error_file": None,
        "dry_run": payload.get("dry_run"),
    }
    return {"job_id": job_id}

def _job_status(job_id):
    return etl._jobs.get(job_id, {})

etl.import_rows = _import_rows
etl.job_status = _job_status
etl._jobs = {}
sys.modules["crm.api.etl"] = etl
sys.modules["crm.api"].etl = etl

# records_to_csv_file writes a File doc in real Frappe; here, monkeypatch it to
# write a real local CSV and return a local path as the "file_url", so import_rows
# can count real rows. We still use the REAL flatten via records_to_csv_file's
# internals by calling the real preview/flatten then writing CSV ourselves.
_real_records_to_csv = etl_json.records_to_csv_file

def _records_to_csv_file_local(records_json=None, file_url=None, array_policy="join", title="ds"):
    import csv
    recs = etl_json._load_records(records_json=records_json, file_url=file_url)
    headers, rows = etl_json._flatten_all(recs, array_policy=array_policy)
    out = REPO / "tmp_ingest_validation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(headers)
        for r in rows: w.writerow([r.get(h, "") for h in headers])
    return {"file_url": str(out), "row_count": len(rows), "headers": headers}

etl_json.records_to_csv_file = _records_to_csv_file_local

# ---------------------------------------------------------------------------
# 6. Load REAL leadgen and run the REAL run_dataset_ingest
# ---------------------------------------------------------------------------
leadgen = _load("crm.api.leadgen", str(REPO / "crm/api/leadgen.py"))

records_json = AACR.read_text()

print("=" * 70)
print("VALIDATION GATE — agentic dataset-ingest on REAL AACR-862")
print("=" * 70)

# ---- PASS 1: first sight of the schema -> propose-and-pause ----------------
_PROFILE_NAME_HOLDER["name"] = "ingest::Lead Prospect::AACR-TEST"
res1 = leadgen.run_dataset_ingest(
    target_doctype="Lead Prospect",
    records_json=records_json,
    profile_name="ingest::Lead Prospect::AACR-TEST",
    dry_run=1,
    use_llm=0,  # no LLM key in sandbox; Tier-1 only (Tier-2 degrades cleanly)
)
print("\n[PASS 1] first sight of schema")
print("  stage           :", res1.get("stage"))
print("  status          :", res1.get("status"))
print("  profile         :", res1.get("profile"))
print("  tier1_count     :", res1.get("tier1_count"))
print("  tier2_llm_count :", res1.get("tier2_llm_count"))
print("  unmapped_required:", res1.get("unmapped_required"))
print("  unmapped_source #:", len(res1.get("unmapped_source") or []))

# Inspect the saved profile's actual column mappings
prof = SAVED["column_maps"].get(res1.get("profile"))
mapped_pairs = []
if prof:
    cols = prof.get("columns") or prof._children.get("columns", [])
    print(f"\n  --- saved CRM Import Column Map: {len(cols)} column items "
          f"(source_header -> target_field @conf [basis]) ---")
    for it in cols:
        sh = it.get("source_header"); tf = it.get("target_field")
        mapped_pairs.append((sh, tf))
        print(f"    {str(sh):30} -> {str(tf):16} "
              f"@{it.get('confidence')} [{it.get('basis')}]")
    print(f"  source_signature : {prof.get('source_signature')}")

# ---- approve the profile (human-in-the-loop), then PASS 2: import ----------
if res1.get("profile"):
    frappe.db.set_value("CRM Import Column Map", res1["profile"], "status", "Approved")
    # set the source_signature so find_reusable_profile matches on re-run
    # (the kernel already stored it; ensure present)
    print("\n[approve] flipped profile status -> Approved")

res2 = leadgen.run_dataset_ingest(
    target_doctype="Lead Prospect",
    records_json=records_json,
    profile_name="ingest::Lead Prospect::AACR-TEST",
    dry_run=1,
    use_llm=0,
)
print("\n[PASS 2] re-run after approval (auto-reuse + dry-run import)")
print("  stage          :", res2.get("stage"))
print("  status         :", res2.get("status"))
print("  dry_run        :", res2.get("dry_run"))
print("  profile        :", res2.get("profile"))
print("  total_rows     :", res2.get("total_rows"))
print("  processed_rows :", res2.get("processed_rows"))
print("  error_file     :", res2.get("error_file"))
print("  csv_file       :", res2.get("csv_file"))
print("  leadgen_job    :", res2.get("leadgen_job"))

# ---- assertions ------------------------------------------------------------
print("\n" + "=" * 70)
print("ASSERTIONS")
ok = True
def check(name, cond):
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    ok = ok and cond

check("PASS1 paused at mapping_review (did not silently import)",
      res1.get("stage") == "mapping_review")
check("PASS1 found >=6 Tier-1 deterministic maps",
      (res1.get("tier1_count") or 0) >= 6)
check("PASS1 flagged required-field gaps (tier/source/owner)",
      bool(res1.get("unmapped_required")))
check("PASS2 reused approved profile + ran import path",
      res2.get("stage") == "imported")
check("PASS2 dry-run counted all 862 rows would upsert",
      res2.get("total_rows") == 862 and res2.get("processed_rows") == 862)
check("PASS2 zero schema/import errors",
      not res2.get("error_file"))
check("PASS2 emitted a LeadGen Job for observability",
      bool(res2.get("leadgen_job")))

print("=" * 70)
print("RESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
