"""Regression tests for lead_tabs._content engine availability.

Proves the Content tab NEVER claims the content engine is live unless a provider
is actually authenticated — the exact sandbag this audit fixed (the old code
computed engine availability then returned available=True unconditionally).

Frappe-free: `frappe` is stubbed and the REAL notebooklm_engine is wired in as
`crm.api.notebooklm_engine`, so `_content` runs its real derivation logic without
a Frappe bench. Provider detectors are monkeypatched so the result is
deterministic regardless of ambient env / PATH / home directory.

Guarded under run()/__main__ so importing never executes tests as a side effect.
"""
import importlib.util
import os
import sys
import types

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_modules():
    """Stub frappe, load the real engine, wire crm.api, load lead_tabs by path."""
    # --- stub frappe (only `frappe` and `frappe._` are used at module load;
    #     _content uses frappe.get_all for the file list) ---
    frappe = types.ModuleType("frappe")
    frappe._ = lambda s, *a, **k: s
    frappe.get_all = lambda *a, **k: []

    class _DB:
        def exists(self, *a, **k):
            return True

    frappe.db = _DB()

    def _throw(*a, **k):
        raise Exception(a[0] if a else "frappe.throw")

    frappe.throw = _throw
    # @frappe.whitelist() is applied at module load; return the function unchanged.
    frappe.whitelist = lambda *a, **k: (lambda f: f)
    sys.modules["frappe"] = frappe

    # --- load the REAL engine by file path (frappe-free at import) ---
    eng_path = os.path.join(_API_DIR, "notebooklm_engine.py")
    spec = importlib.util.spec_from_file_location("notebooklm_engine", eng_path)
    eng = importlib.util.module_from_spec(spec)
    sys.modules["notebooklm_engine"] = eng
    spec.loader.exec_module(eng)

    # --- fake crm / crm.api packages wiring the real engine ---
    crm = types.ModuleType("crm")
    crm.__path__ = []
    crm_api = types.ModuleType("crm.api")
    crm_api.__path__ = []
    crm_api.notebooklm_engine = eng
    sys.modules["crm"] = crm
    sys.modules["crm.api"] = crm_api
    sys.modules["crm.api.notebooklm_engine"] = eng

    # --- load lead_tabs by file path (import frappe now resolves to the stub) ---
    lt_path = os.path.join(_API_DIR, "lead_tabs.py")
    spec2 = importlib.util.spec_from_file_location("lead_tabs", lt_path)
    lt = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(lt)
    return lt, eng


def _set_provider_state(eng, gemini=False, enterprise=False, unofficial=False):
    """Monkeypatch the engine detectors so availability is deterministic."""
    eng._gemini_key = (lambda: "fake-key") if gemini else (lambda: None)
    if enterprise:
        eng._enterprise_creds = lambda: {"token": "t", "project": "p", "location": "us"}
    else:
        eng._enterprise_creds = lambda: {"token": None, "project": None, "location": "us"}
    eng._unofficial_cli = (lambda: "/usr/bin/notebooklm") if unofficial else (lambda: None)
    eng._unofficial_storage = (lambda: "/tmp/session.json") if unofficial else (lambda: None)


def run():
    lt, eng = _load_modules()
    passed = failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            print("PASS:", name)
            passed += 1
        else:
            print("FAIL:", name)
            failed += 1

    doc = {"name": "TEST-LEAD-0001"}

    # 1) No credentials anywhere -> engine must report NOT live (the core regression)
    _set_provider_state(eng, gemini=False, enterprise=False, unofficial=False)
    r = lt._content(doc)
    eng_block = r["engine"]
    check("payload ok + files list present", r["ok"] is True and r["files"] == [])
    check("no cred -> engine.available is False", eng_block["available"] is False)
    check("no cred -> reason is no_provider_authenticated",
          eng_block["reason"] == "no_provider_authenticated")
    check("no cred -> every provider live=False",
          all(p["live"] is False for p in eng_block["providers"].values()))
    check("no cred -> live_kinds empty", eng_block["live_kinds"] == [])
    check("no cred -> supported_kinds still advertised (honest capability list)",
          len(eng_block["supported_kinds"]) > 0)
    check("no cred -> gemini lists GEMINI_API_KEY as missing",
          "GEMINI_API_KEY" in eng_block["providers"]["gemini"]["missing"])

    # 2) A credential present -> engine reports live, honestly
    _set_provider_state(eng, gemini=True, enterprise=False, unofficial=False)
    r = lt._content(doc)
    eng_block = r["engine"]
    check("gemini key -> engine.available is True", eng_block["available"] is True)
    check("gemini key -> reason cleared", eng_block["reason"] == "")
    check("gemini key -> gemini.live True", eng_block["providers"]["gemini"]["live"] is True)
    check("gemini key -> live_kinds non-empty", len(eng_block["live_kinds"]) > 0)
    check("gemini key -> enterprise still not live",
          eng_block["providers"]["enterprise"]["live"] is False)

    # 3) Engine import/derivation failure -> honest available=False, never faked-live
    real_ap = eng.available_providers

    def _boom():
        raise RuntimeError("simulated engine failure")

    eng.available_providers = _boom
    try:
        r = lt._content(doc)
    finally:
        eng.available_providers = real_ap
    eng_block = r["engine"]
    check("engine failure -> available False", eng_block["available"] is False)
    check("engine failure -> reason surfaced (engine_unavailable)",
          eng_block["reason"].startswith("engine_unavailable"))
    check("engine failure -> providers empty, not fabricated", eng_block["providers"] == {})

    print("\n{}/{} passed".format(passed, passed + failed))
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
