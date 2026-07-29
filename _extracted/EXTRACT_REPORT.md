# Extract report — 2026-07-29

## Pulled (ff-only, no force)

| Tree | Before | After | Match origin/main |
|------|--------|-------|-------------------|
| workspace root | c42037ea | ac318eb5 → then 05166e89 (extract) | origin/main = ac318eb5; local main **1 commit ahead** (extract only) |
| nested `crm-deployment/` | c20e0d65 | ac318eb5 | yes |

## Remote-only work that was NOT on main — now extracted

`origin/rebuild/tenant-agnostic-outreach` (3 commits, Jun 1) — **never merged to main**.

Landed on branch `extract/rebuild-tenant-agnostic` and fast-forwarded into local `main`:

- NEW `eaia/tenant/` (TenantPack + crispro/acme YAML packs)
- UPDATED score.py, write.py, challenger_email_writer.py, lead_scoring_tool.py, jr1.py

Conflict resolved in `score.py`: kept tenant prompt scaffold + pack-driven scoring (quarantine gate retained).

Snapshot + patch also under `_extracted/rebuild-tenant-agnostic-outreach/`.

## Intentionally NOT merged into main

| Branch | Why |
|--------|-----|
| `origin/fc-app-only` | FC Pre-build slim tree / cache-bust — would gut local full app tree |
| `origin/fc-hotfix-prebuild` | Packaging pin only; already reflected on main via Jul 13 commits |

## Bench CRM sync (additive)

Copied missing Nyx/enrichment APIs + doctypes + Tasks/Nyx UI from deploy → `frappe-bench/apps/crm`.
Preserved bench-only: `nyx_inbound_hook.py`, `sequence_manager.py`.
See `BENCH_SYNC_MANIFEST.txt`.

## Not done (would break or needs ops)

- No `git push`
- Custom field installer `add_nyx_custom_fields.py` still only in bench (was never on remote main)
- EAIA `.env` still missing FRAPPE_*/BRIGHTDATA_API_KEY/LLM keys
- Frontend Vite rebuild for bench not run
