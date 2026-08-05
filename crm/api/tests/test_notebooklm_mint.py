"""Import-safe tests for notebooklm_mint (bundle-driven NotebookLM mint).

Execution is guarded under run()/__main__ so importing this module never runs
tests as a side effect. The api dir is derived from __file__ so it works from
any CWD without a Frappe bench.
"""
import os
import sys
import tempfile

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

import notebooklm_engine as E   # noqa: E402
import notebooklm_mint as M     # noqa: E402


def _mk_bundle(root):
    """Create a minimal bundle with an explicit upload order + a figure."""
    os.makedirs(os.path.join(root, "manuscript"))
    os.makedirs(os.path.join(root, "figures"))
    with open(os.path.join(root, "00_UPLOAD_ORDER.txt"), "w") as fh:
        fh.write("1. ABSTRACT.md\n2. manuscript/DRAFT.md\n3. figures/*.png\n")
    with open(os.path.join(root, "ABSTRACT.md"), "w") as fh:
        fh.write("# Abstract\ngap-first story")
    with open(os.path.join(root, "manuscript", "DRAFT.md"), "w") as fh:
        fh.write("# Draft\nlong form")
    with open(os.path.join(root, "EXTRA.txt"), "w") as fh:
        fh.write("not in order file")
    # a tiny valid-ish PNG placeholder (content irrelevant to path collection)
    with open(os.path.join(root, "figures", "figure1.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")


CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("upload order is honored, extras appended, figures collected")
def _t_order():
    with tempfile.TemporaryDirectory() as d:
        _mk_bundle(d)
        texts, figs = M.collect_bundle_sources(d)
        titles = [t for t, _ in texts]
        assert titles[0] == "ABSTRACT.md", titles
        assert titles[1] == "manuscript/DRAFT.md", titles
        assert "EXTRA.txt" in titles, titles                # appended remainder
        assert "00_UPLOAD_ORDER.txt" in titles, titles
        assert [t for t, _ in figs] == ["figure1.png"], figs


@check("empty bundle raises NotebookLMError")
def _t_empty():
    with tempfile.TemporaryDirectory() as d:
        try:
            M.collect_bundle_sources(d)
        except E.NotebookLMError:
            return
        raise AssertionError("expected NotebookLMError for empty bundle")


@check("missing bundle dir raises NotebookLMError")
def _t_missing():
    try:
        M.collect_bundle_sources("/no/such/bundle/here")
    except E.NotebookLMError:
        return
    raise AssertionError("expected NotebookLMError for missing dir")


@check("file_source_argv shape is correct")
def _t_file_argv():
    argv = M.file_source_argv("nblm", "/s.json", "NB", "/x/fig.png",
                              title="fig.png", mime="image/png")
    assert argv[:5] == ["nblm", "--storage", "/s.json", "--quiet", "source"], argv
    assert "add" in argv and "--type" in argv and "file" in argv, argv
    assert "--mime-type" in argv and "image/png" in argv, argv
    assert argv[-1] == "--json" and "/x/fig.png" in argv, argv


@check("gen_argv (infographic/report) shape is correct")
def _t_gen_argv():
    argv = M.gen_argv("nblm", "/s.json", "infographic", "NB", "poster desc", timeout=600)
    assert argv[:6] == ["nblm", "--storage", "/s.json", "--quiet", "generate", "infographic"], argv
    assert "poster desc" in argv and "-n" in argv and "NB" in argv, argv
    assert "--wait" in argv and "--timeout" in argv and "600" in argv, argv
    assert argv[-1] == "--json", argv


@check("invalid kind raises")
def _t_bad_kind():
    try:
        M.mint_from_bundle("/tmp", kind="hologram")
    except E.NotebookLMError:
        return
    raise AssertionError("expected NotebookLMError for bad kind")


@check("non-unofficial provider is rejected for bundle mint")
def _t_bad_provider():
    try:
        M.mint_from_bundle("/tmp", kind="slides", provider="gemini")
    except E.NotebookLMError:
        return
    raise AssertionError("expected NotebookLMError for gemini bundle mint")


@check("no Google session => fail-loud NotebookLMCredentialError, no artifact")
def _t_fail_loud():
    saved = os.environ.pop("NOTEBOOKLM_STORAGE", None)
    try:
        with tempfile.TemporaryDirectory() as d:
            _mk_bundle(d)
            try:
                M.mint_from_bundle(d, kind="slides", storage=None)
            except E.NotebookLMCredentialError as e:
                assert e.provider == "unofficial", e.provider
                return
            raise AssertionError("expected NotebookLMCredentialError")
    finally:
        if saved is not None:
            os.environ["NOTEBOOKLM_STORAGE"] = saved


def run():
    passed = failed = 0
    for name, fn in CHECKS:
        try:
            fn()
            print("PASS:", name)
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print("FAIL:", name, "->", repr(exc))
            failed += 1
    print("\n{}/{} passed".format(passed, passed + failed))
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
