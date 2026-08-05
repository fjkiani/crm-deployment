"""Real tests for notebooklm_engine.

Proves the integration is REAL (correct wire format to the real Google
endpoints / real CLI) and FAIL-LOUD (no credential -> precise error, never a
local-synthesis fallback). No network calls, no Google auth required.
"""
import importlib.util
import os
import sys

ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "notebooklm_engine.py")
spec = importlib.util.spec_from_file_location("notebooklm_engine", ENGINE_PATH)
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)

def run():
    # Ensure a pristine no-credential environment for the fail-loud tests.
    for v in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "NOTEBOOKLM_OAUTH_TOKEN",
              "NOTEBOOKLM_GCP_PROJECT", "NOTEBOOKLM_STORAGE", "NOTEBOOKLM_CLI"):
        os.environ.pop(v, None)

    RICH = {
        "contact": "Karina Patel", "company": "MD Anderson Cancer Center",
        "title": "PI", "topic": "Overcoming immune exclusion in MSS colorectal cancer",
        "current_focus": "neoadjuvant vaccine strategies to convert cold MSS CRC",
        "pain_points": "MSS CRC refractory to checkpoint blockade; needs priming to turn cold tumors hot",
        "crispro_fit": "STC-1010 haptenated whole-cell vaccine primes polyclonal T-cell responses",
        "fit_rationale": "priming before FOLFOX backbone", "funnel_stage": "first_touch",
    }
    PASS, FAIL = [], []


    def ok(name, cond):
        (PASS if cond else FAIL).append(name)
        print(("PASS " if cond else "FAIL ") + name)


    # 1. Enterprise REST wire format (official docs)
    m, url, h, body = eng.enterprise_notebook_request("123456", "us", "Karina", "TOK")
    ok("enterprise notebook POST", m == "POST")
    ok("enterprise notebook URL",
       url == "https://us-discoveryengine.googleapis.com/v1alpha/projects/123456/locations/us/notebooks")
    ok("enterprise bearer header", h["Authorization"] == "Bearer TOK")
    ok("enterprise notebook body", body == {"title": "Karina"})

    m, url, h, body = eng.enterprise_audio_request("123456", "eu", "NB9", ["s1", "s2"], "focus text", "en", "TOK")
    ok("enterprise audio endpoint", url.endswith("/notebooks/NB9/audioOverviews"))
    ok("enterprise audio region", url.startswith("https://eu-discoveryengine.googleapis.com/"))
    ok("enterprise audio focus+lang", body["episodeFocus"] == "focus text" and body["languageCode"] == "en")
    ok("enterprise audio sourceIds", body["sourceIds"] == [{"id": "s1"}, {"id": "s2"}])
    try:
        eng.enterprise_notebook_request("1", "mars", "x", "T")
        ok("enterprise bad region rejected", False)
    except eng.NotebookLMError:
        ok("enterprise bad region rejected", True)

    # 2. Unofficial CLI argv (real notebooklm CLI interface)
    argv = eng.unofficial_argv("/bin/notebooklm", "/s.json", "slide-deck",
                               notebook_id="nb1", description="deck for Karina")
    ok("unofficial storage flag", argv[:4] == ["/bin/notebooklm", "--storage", "/s.json", "--quiet"])
    ok("unofficial slide-deck cmd", "generate" in argv and "slide-deck" in argv)
    ok("unofficial notebook flag", "-n" in argv and argv[argv.index("-n") + 1] == "nb1")
    ok("unofficial presenter+wait+json", "--format" in argv and "presenter" in argv
       and "--wait" in argv and "--json" in argv)
    argv_a = eng.unofficial_argv("/bin/notebooklm", "/s.json", "audio", notebook_id="nb1", description="d")
    ok("unofficial audio deep-dive", "audio" in argv_a and "deep-dive" in argv_a)

    # 3. Gemini multi-speaker TTS config uses the REAL SDK types
    try:
        cfg = eng.gemini_tts_config([("Host", "Kore"), ("Guest", "Puck")])
        sv = cfg.speech_config.multi_speaker_voice_config.speaker_voice_configs
        ok("gemini tts 2 speakers", len(sv) == 2)
        ok("gemini tts audio modality", list(cfg.response_modalities) == ["AUDIO"])
        ok("gemini tts speaker names", {s.speaker for s in sv} == {"Host", "Guest"})
    except Exception as e:
        ok("gemini tts config builds via real SDK types (%s)" % e, False)

    # 4. Grounding: real intel in, refuse thin intel
    src = eng.build_sources(RICH)
    ok("sources grounded in pain point", "refractory to checkpoint blockade" in src)
    ok("sources grounded in fit", "haptenated whole-cell" in src)
    try:
        eng.build_sources({"contact": "x"})
        ok("thin intel refused", False)
    except eng.NotebookLMError:
        ok("thin intel refused", True)

    # 5. Fail-loud: no credential anywhere -> precise errors, NO fallback
    avail = eng.available_providers()
    ok("gemini not live (no key)", avail["gemini"]["live"] is False
       and "GEMINI_API_KEY" in avail["gemini"]["missing"])
    ok("enterprise not live", avail["enterprise"]["live"] is False)
    ok("unofficial not live (no session)", avail["unofficial"]["live"] is False)

    for prov, needle in [("gemini", "GEMINI_API_KEY"), ("enterprise", "NOTEBOOKLM_OAUTH_TOKEN")]:
        try:
            eng._PROVIDERS[prov]().check()
            ok("%s.check raises without cred" % prov, False)
        except eng.NotebookLMCredentialError as e:
            ok("%s.check raises without cred" % prov, needle in e.missing or any(needle in m for m in e.missing))

    # auto dispatch with no live backend must raise (never synthesise)
    for kind in ("slides", "audio", "video"):
        try:
            eng.generate(kind, RICH, provider="auto")
            ok("auto %s raises (no fallback)" % kind, False)
        except eng.NotebookLMCredentialError as e:
            ok("auto %s raises (no fallback)" % kind, kind in str(e))

    # enterprise cannot do slides -> unsupported kind (clear message)
    os.environ["NOTEBOOKLM_OAUTH_TOKEN"] = "x"
    os.environ["NOTEBOOKLM_GCP_PROJECT"] = "1"
    try:
        eng.EnterpriseProvider().generate("slides", RICH, "/tmp/crm_content")
        ok("enterprise rejects slides", False)
    except eng.NotebookLMUnsupportedKind:
        ok("enterprise rejects slides", True)
    os.environ.pop("NOTEBOOKLM_OAUTH_TOKEN"); os.environ.pop("NOTEBOOKLM_GCP_PROJECT")

    # 6. Credential presence flips availability (no network)
    os.environ["GEMINI_API_KEY"] = "AIza-fake-for-presence-test"
    ok("gemini live when key present", eng.available_providers()["gemini"]["live"] is True)
    try:
        eng.GeminiProvider().check()
        ok("gemini.check passes with key (no network)", True)
    except Exception:
        ok("gemini.check passes with key (no network)", False)
    os.environ.pop("GEMINI_API_KEY")

    print("\n=== %d passed, %d failed ===" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILURES:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    run()
