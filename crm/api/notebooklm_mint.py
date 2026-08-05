"""notebooklm_mint.py — mint REAL NotebookLM content from a source bundle.

Bundle-driven companion to ``notebooklm_engine.py``. Where the engine mints from
a single CRM-lead dossier, this mints from a *folder of source documents* (the
``notebooklm_bundle`` format: markdown/txt/json + figures) by driving the real
Google NotebookLM client (notebooklm-py) end to end:

    create notebook  ->  add every bundle source  ->  generate <kind> --wait

Supported kinds: slides (literal NotebookLM slide-deck), audio, video,
infographic, report. The output is a LITERAL NotebookLM artifact, downloaded and
copied to ``out_dir``.

Fail-loud contract: with no logged-in Google session it raises
``NotebookLMCredentialError`` and produces nothing. It never fabricates an
artifact and never falls back to local synthesis (no python-pptx, no espeak).

CLI:
    python -m crm.api.notebooklm_mint --bundle /path/to/notebooklm_bundle \
        --kind slides --out /path/out [--storage /path/storage_state.json]

Credential: run ``notebooklm login`` (writes the default session) or pass
``--storage`` / set ``NOTEBOOKLM_STORAGE`` to a saved ``storage_state.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import notebooklm_engine as E  # reuse credentials, errors, and argv builder


# kind -> NotebookLM CLI `generate` subcommand
CLI_KINDS = {
    "slides": "slide-deck",
    "audio": "audio",
    "video": "video",
    "infographic": "infographic",
    "report": "report",
}

TEXT_EXTS = {".md", ".txt", ".json"}       # ingested as --type text
FIGURE_EXTS = {".png", ".pdf"}             # uploaded as --type file
_MIME = {".png": "image/png", ".pdf": "application/pdf"}


def _default_desc(kind):
    """Grounding prompt per kind, mirroring the bundle README's discipline."""
    return {
        "slides": (
            "Executive slide deck telling the gap-first trial-matching story, "
            "grounded strictly in the uploaded sources. Lead with the "
            "eligibility-vs-mechanism-overlap gap; end with a clear next step. "
            "Do not invent trial IDs, p-values, or recall metrics; output TBD "
            "when a value is not in the sources."
        ),
        "audio": (
            "Two-host deep-dive audio overview, gap-first narrative, grounded "
            "strictly in the uploaded sources."
        ),
        "video": (
            "Short explainer video, gap-first narrative, grounded strictly in "
            "the uploaded sources."
        ),
        "infographic": (
            "One-board scientific poster: gap-first story, colorblind-safe, "
            "color = meaning only, no invented numbers, RUO footer."
        ),
        "report": (
            "Briefing document grounded strictly in the uploaded sources; "
            "gap-first; TBD for any value not present in the sources."
        ),
    }[kind]


def collect_bundle_sources(bundle_dir, order_file="00_UPLOAD_ORDER.txt", include_figures=True):
    """Assemble the bundle's sources.

    Returns ``(text_sources, figure_sources)`` where each is a list of
    ``(title, absolute_path)``. Text files (.md/.txt/.json) are ordered by
    ``00_UPLOAD_ORDER.txt`` when present, then any remaining text files sorted
    deterministically. Figures come from ``figures/*.png``.

    Raises ``NotebookLMError`` if the bundle has no usable text source.
    """
    root = Path(bundle_dir)
    if not root.is_dir():
        raise E.NotebookLMError("bundle dir not found: {}".format(bundle_dir))

    ordered = []
    seen = set()
    order_path = root / order_file
    if order_path.exists():
        raw = order_path.read_text(encoding="utf-8", errors="replace")
        for line in raw.splitlines():
            for tok in line.replace("\t", " ").split():
                low = tok.lower().strip(",;()")
                if any(low.endswith(e) for e in TEXT_EXTS):
                    p = (root / tok.strip(",;()")).resolve()
                    if p.exists() and p not in seen:
                        ordered.append(p)
                        seen.add(p)

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rp = p.resolve()
        if p.suffix.lower() in TEXT_EXTS and rp not in seen:
            ordered.append(rp)
            seen.add(rp)

    text_sources = [(p.relative_to(root).as_posix(), str(p)) for p in ordered]

    figure_sources = []
    if include_figures:
        figdir = root / "figures"
        if figdir.is_dir():
            for p in sorted(figdir.glob("*.png")):
                figure_sources.append((p.name, str(p)))

    if not text_sources:
        raise E.NotebookLMError(
            "bundle has no .md/.txt/.json sources: {}".format(bundle_dir))
    return text_sources, figure_sources


def file_source_argv(cli, storage, notebook_id, path, title=None, mime=None):
    """argv for ``source add --type file`` (figures / PDFs)."""
    argv = [cli, "--storage", storage, "--quiet", "source", "add",
            "-n", notebook_id, "--type", "file"]
    if mime:
        argv += ["--mime-type", mime]
    if title:
        argv += ["--title", title]
    argv += [path, "--json"]
    return argv


def gen_argv(cli, storage, cli_sub, notebook_id, description, fmt=None, length=None, timeout=900):
    """argv for ``generate <cli_sub>`` for kinds beyond slides/audio/video."""
    argv = [cli, "--storage", storage, "--quiet", "generate", cli_sub]
    if description:
        argv.append(description)
    argv += ["-n", notebook_id]
    if fmt:
        argv += ["--format", fmt]
    if length:
        argv += ["--length", length]
    argv += ["--wait", "--timeout", str(timeout), "--json"]
    return argv


def _run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise E.NotebookLMError("notebooklm CLI failed ({}): {}".format(
            proc.returncode, (proc.stderr or proc.stdout or "")[:800]))
    out = (proc.stdout or "").strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}


def _resolve_artifact(res):
    """Find a real, existing artifact file path in a CLI --json result."""
    if not isinstance(res, dict):
        return None
    for k in ("path", "file", "output", "download_path", "downloadPath"):
        v = res.get(k)
        if isinstance(v, str) and os.path.exists(v):
            return v
    art = res.get("artifact") or {}
    if isinstance(art, dict):
        for k in ("path", "file"):
            v = art.get(k)
            if isinstance(v, str) and os.path.exists(v):
                return v
    return None


def mint_from_bundle(bundle_dir, kind="slides", provider="unofficial",
                     out_dir="/mnt/results/notebooklm_minted", storage=None,
                     title=None, description=None, fmt=None, length=None,
                     include_figures=True, timeout=900):
    """Mint a REAL NotebookLM artifact from a source bundle. Fail-loud.

    Returns a dict with the real downloaded ``path``, the ``notebook_id``, and
    the list of sources actually added. Raises ``NotebookLMCredentialError`` if
    no Google session is present, or ``NotebookLMError`` if the mint yields no
    downloadable file. Never fabricates an artifact.
    """
    if kind not in CLI_KINDS:
        raise E.NotebookLMError("kind must be one of {}".format(sorted(CLI_KINDS)))
    if provider not in ("unofficial", "auto"):
        raise E.NotebookLMError(
            "bundle mint requires provider 'unofficial' (literal NotebookLM). "
            "For a gemini/enterprise brief-based mint use "
            "notebooklm_engine.generate().")

    cli = E._unofficial_cli()
    storage = storage or E._unofficial_storage()
    missing = []
    if not cli:
        missing.append("notebooklm CLI (pip install notebooklm-py)")
    if not storage:
        missing.append("Google session (run: notebooklm login)")
    if missing:
        raise E.NotebookLMCredentialError(
            "unofficial", missing,
            "Run `notebooklm login` (opens a browser) to create a session, or "
            "pass --storage / set NOTEBOOKLM_STORAGE to a saved "
            "storage_state.json.")

    text_sources, figure_sources = collect_bundle_sources(
        bundle_dir, include_figures=include_figures)

    os.makedirs(out_dir, exist_ok=True)
    title = title or ("Brenus / CrisPRO — " + Path(bundle_dir).name)

    # 1. create the notebook
    nb = _run(E.unofficial_argv(cli, storage, "create", title=title))
    nb_id = (nb.get("id") or nb.get("notebookId")
             or (nb.get("notebook") or {}).get("id"))
    if not nb_id:
        raise E.NotebookLMError("could not resolve notebook id from: {}".format(nb))

    # 2. add every source: text first (upload order), then figures
    added = []
    for src_title, path in text_sources:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        _run(E.unofficial_argv(cli, storage, "source-add", notebook_id=nb_id,
                               source_text=content, source_title=src_title))
        added.append(src_title)
    for fig_title, path in figure_sources:
        mime = _MIME.get(Path(path).suffix.lower())
        _run(file_source_argv(cli, storage, nb_id, path, title=fig_title, mime=mime))
        added.append(fig_title)

    # 3. generate the artifact (literal NotebookLM output)
    desc = description or _default_desc(kind)
    if kind == "slides":
        argv = E.unofficial_argv(cli, storage, "slide-deck", notebook_id=nb_id,
                                 description=desc, fmt=(fmt or "detailed"),
                                 length=(length or "default"))
    elif kind == "audio":
        argv = E.unofficial_argv(cli, storage, "audio", notebook_id=nb_id,
                                 description=desc, fmt=fmt, length=length)
    elif kind == "video":
        argv = E.unofficial_argv(cli, storage, "video", notebook_id=nb_id,
                                 description=desc)
    else:  # infographic / report
        argv = gen_argv(cli, storage, CLI_KINDS[kind], nb_id, desc,
                        fmt=fmt, length=length, timeout=timeout)
    res = _run(argv)

    artifact = _resolve_artifact(res)
    if not artifact:
        raise E.NotebookLMError(
            "NotebookLM returned no downloadable file for '{}': {}".format(kind, res))

    dest = os.path.join(out_dir, "{}_{}{}".format(
        Path(bundle_dir).name, kind, Path(artifact).suffix or ""))
    shutil.copy(artifact, dest)
    return {"provider": "unofficial", "kind": kind, "notebook_id": nb_id,
            "sources_added": added, "path": dest, "live": True,
            "meta": {"note": "literal NotebookLM artifact", "source_file": artifact}}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Mint real NotebookLM content from a source bundle.")
    ap.add_argument("--bundle", required=True, help="path to the notebooklm_bundle folder")
    ap.add_argument("--kind", default="slides", choices=sorted(CLI_KINDS))
    ap.add_argument("--provider", default="unofficial", choices=["unofficial", "auto"])
    ap.add_argument("--out", default="/mnt/results/notebooklm_minted")
    ap.add_argument("--storage", default=None, help="path to storage_state.json")
    ap.add_argument("--title", default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--format", dest="fmt", default=None)
    ap.add_argument("--length", default=None)
    ap.add_argument("--no-figures", dest="include_figures", action="store_false")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args(argv)
    try:
        res = mint_from_bundle(
            args.bundle, kind=args.kind, provider=args.provider, out_dir=args.out,
            storage=args.storage, title=args.title, description=args.description,
            fmt=args.fmt, length=args.length, include_figures=args.include_figures,
            timeout=args.timeout)
    except E.NotebookLMCredentialError as e:
        print("BLOCKED (no Google credential): {}".format(e), file=sys.stderr)
        return 2
    except E.NotebookLMError as e:
        print("ERROR: {}".format(e), file=sys.stderr)
        return 1
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
