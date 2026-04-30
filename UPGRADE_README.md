# CRM Self-Hosted Deployment Guide

> **Goal**: Run the full Frappe CRM + EAIA Agent + Farfalle Chat stack on your own infrastructure — no Frappe Cloud dependency, no vendor lock-in.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current State (Frappe Cloud)](#2-current-state-frappe-cloud)
3. [Target Architecture (Docker Self-Hosted)](#3-target-architecture-docker-self-hosted)
4. [Local Development Guide](#4-local-development-guide)
5. [Production Deployment](#5-production-deployment)
6. [Post-Deploy Steps](#6-post-deploy-steps)
7. [Environment Variable Reference](#7-environment-variable-reference)

---

## 1. System Overview

This repository contains three interconnected services:

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **Frappe CRM** | Frappe Framework + Python | 8000 | Core CRM — leads, deals, contacts, outreach sequences, DocTypes |
| **EAIA Agent** (Nyx) | FastAPI + LangGraph | 8001 | AI agent — email triage, lead enrichment, outreach automation |
| **Farfalle Chat** | Next.js + FastAPI | 3000 | Conversational search UI over CRM data |

### Key Custom Logic (preserved in Docker)

- **30+ custom DocTypes**: `CRM Lead`, `CRM Deal`, `Lead Prospect`, `LeadGen Job`, `Outreach Sequence`, `Outreach Sequence Step`, and more
- **LeadGen collectors**: ASCO, NIH, ClinicalTrials.gov scrapers (`frappe-bench/apps/crm/crm/leadgen/`)
- **MCP Server**: Frappe tools exposed as Model Context Protocol endpoints (`mcp_server.py`)
- **EAIA pipeline**: LangGraph-based email → lead enrichment → CRM write pipeline (`assistant/executive-ai-assistant-main/`)
- **Outreach sequences**: Multi-step email/LinkedIn cadences with scheduling

---

## 2. Current State (Frappe Cloud)

The app currently runs on **Frappe Cloud** at `jedilabs2.v.frappe.cloud`. This means:

- Frappe Cloud manages MariaDB, Redis, workers, and SSL
- You cannot SSH into the server or change infrastructure
- Scaling, backups, and upgrades are controlled by Frappe Cloud
- Monthly cost scales with usage and seats

### What changes when you self-host

| Concern | Frappe Cloud | Self-Hosted Docker |
|---------|-------------|-------------------|
| Database | Managed MariaDB | Your MariaDB container (or managed DB) |
| Redis | Managed | Your Redis containers |
| SSL | Automatic | Caddy / nginx / platform-managed |
| Backups | Automatic | Your responsibility (see §6) |
| Upgrades | Frappe Cloud UI | `docker-compose pull && docker-compose up` |
| Cost | Per-seat SaaS | Infrastructure cost only |

### Hardcoded URLs (already handled)

Nine files reference `jedilabs2.v.frappe.cloud`. All are already guarded by environment variable fallbacks:

```python
# Example from frappe_tool.py
FRAPPE_SITE_URL = os.getenv("FRAPPE_SITE_URL", "https://jedilabs2.v.frappe.cloud")
```

Setting `FRAPPE_SITE_URL` in your `.env` file is all that's needed — no code changes required.

---

## 3. Target Architecture (Docker Self-Hosted)

```
┌─────────────────────────────────────────────────────────────────┐
│                        docker-compose                           │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  frappe-web  │  │ eaia-agent   │  │  farfalle-frontend   │  │
│  │  :8000       │  │  :8001       │  │  :3000               │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                     │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────────────────┐  │
│  │frappe-worker │  │  mariadb     │  │  farfalle-backend    │  │
│  │frappe-sched  │  │  :3306       │  │  :8080               │  │
│  │frappe-socket │  └──────────────┘  └──────────────────────┘  │
│  └──────────────┘                                               │
│                    ┌──────────────┐  ┌──────────────────────┐  │
│                    │ redis-cache  │  │  farfalle-db         │  │
│                    │ :13000       │  │  (postgres)          │  │
│                    │ redis-queue  │  └──────────────────────┘  │
│                    │ :11000       │                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Files in this repo

```
crm-deployment/
├── Dockerfile.frappe          # Frappe bench image (python:3.11-slim + Node 18)
├── Dockerfile.eaia            # EAIA agent image (Poetry + FastAPI)
├── docker-compose.yml         # Full 9-service stack
├── init-site.sh               # Idempotent Frappe site bootstrap script
├── docker/
│   └── mariadb.cnf            # MariaDB tuning (utf8mb4, InnoDB settings)
├── .env.example               # All env vars documented — copy to .env
├── render.yaml                # Render Blueprint (one-click deploy)
├── fly.toml                   # Fly.io config (frappe-web service)
└── UPGRADE_README.md          # This file
```

---

## 4. Local Development Guide

### Prerequisites

- Docker Desktop ≥ 24 (or Docker Engine + Compose plugin)
- 8 GB RAM available to Docker
- Git

### Step 1 — Clone and configure

```bash
git clone https://github.com/fjkiani/crm-deployment.git
cd crm-deployment
cp .env.example .env
```

Open `.env` and fill in at minimum:

```env
ADMIN_PASSWORD=changeme
DB_PASSWORD=changeme
DB_ROOT_PASSWORD=changeme
OPENAI_API_KEY=sk-...
```

### Step 2 — Build and start

```bash
# First boot takes 5-10 minutes (builds images, installs bench, creates site)
docker-compose up --build
```

Watch the logs:

```bash
docker-compose logs -f frappe-web
```

You'll see `init-site.sh` run through:
1. Wait for MariaDB to be ready
2. `bench init` (downloads Frappe framework)
3. `bench get-app crm` (installs your custom CRM app)
4. `bench new-site` (creates the database and site)
5. `bench install-app crm`
6. `bench migrate`
7. Print API key/secret for the EAIA agent

### Step 3 — Access the services

| Service | URL |
|---------|-----|
| Frappe CRM | http://localhost:8000 |
| EAIA Agent | http://localhost:8001/docs |
| Farfalle Chat | http://localhost:3000 |

Login with `Administrator` / `<ADMIN_PASSWORD>`.

### Step 4 — Connect EAIA to Frappe

After first boot, copy the API key from the frappe-web logs:

```bash
docker-compose logs frappe-web | grep -A2 "API Key"
```

Add to `.env`:

```env
FRAPPE_API_KEY=<key from logs>
FRAPPE_API_SECRET=<secret from logs>
```

Restart the EAIA agent:

```bash
docker-compose restart eaia-agent
```

### Useful development commands

```bash
# Open a bench shell
docker-compose exec frappe-web bash -c "cd /home/frappe/frappe-bench && bash"

# Run a bench command
docker-compose exec frappe-web bench --site crm.localhost console

# Run migrations after code changes
docker-compose exec frappe-web bench --site crm.localhost migrate

# Tail all logs
docker-compose logs -f

# Stop everything
docker-compose down

# Wipe data and start fresh (DESTRUCTIVE)
docker-compose down -v
```

---

## 5. Production Deployment

### Option A — Render (recommended for simplicity)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically
4. Set secret env vars in the Render dashboard:
   - `ADMIN_PASSWORD`
   - `DB_PASSWORD`
   - `DB_ROOT_PASSWORD`
   - `ENCRYPTION_KEY` (generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
   - `OPENAI_API_KEY`
   - `FRAPPE_API_KEY` / `FRAPPE_API_SECRET` (after first deploy)
5. Update `FRAPPE_SITE_NAME` in `render.yaml` to your Render URL or custom domain
6. Click **Apply**

**Cost estimate**: ~$35/month (Standard web + 2× Starter workers + Starter Redis + Starter MySQL)

### Option B — Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Create the app
fly launch --no-deploy --name crm-frappe

# Create a persistent volume for Frappe sites
fly volumes create frappe_sites --size 10 --region iad

# Set secrets
fly secrets set \
  ADMIN_PASSWORD=<password> \
  DB_PASSWORD=<password> \
  DB_ROOT_PASSWORD=<password> \
  ENCRYPTION_KEY=<key> \
  OPENAI_API_KEY=<key>

# Deploy
fly deploy
```

For workers and scheduler, create separate Fly apps pointing to the same image with different `CMD` overrides.

**Note**: Fly.io doesn't have managed MariaDB. Use [PlanetScale](https://planetscale.com) (MySQL-compatible) or run MariaDB as a separate Fly Machine with a persistent volume.

### Option C — VPS (DigitalOcean, Hetzner, Linode)

```bash
# On your VPS (Ubuntu 22.04 recommended)
apt update && apt install -y docker.io docker-compose-plugin git

git clone https://github.com/fjkiani/crm-deployment.git
cd crm-deployment
cp .env.example .env
# edit .env with production values

# Start with Caddy for automatic SSL
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Add a `docker-compose.prod.yml` override:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - frappe-web

volumes:
  caddy_data:
```

`Caddyfile`:

```
crm.yourdomain.com {
    reverse_proxy frappe-web:8000
}

agent.yourdomain.com {
    reverse_proxy eaia-agent:8001
}
```

---

## 6. Post-Deploy Steps

### 6.1 — Generate EAIA API credentials

```bash
# Create a dedicated system manager for the agent
docker-compose exec frappe-web \
  bench --site $FRAPPE_SITE_NAME add-system-manager eaia@yourdomain.com

# Generate API key
docker-compose exec frappe-web \
  bench --site $FRAPPE_SITE_NAME generate-api-key eaia@yourdomain.com
```

Copy the output into `FRAPPE_API_KEY` and `FRAPPE_API_SECRET` in your `.env` (or platform secrets), then restart `eaia-agent`.

### 6.2 — Set up automated backups

```bash
# Add to crontab (runs daily at 2am)
0 2 * * * docker-compose exec frappe-web \
  bench --site $FRAPPE_SITE_NAME backup --with-files \
  >> /var/log/frappe-backup.log 2>&1
```

Backups land in `frappe-bench/sites/<site>/private/backups/`. Copy to S3:

```bash
aws s3 sync /path/to/frappe-bench/sites/crm.localhost/private/backups/ \
  s3://your-bucket/frappe-backups/
```

### 6.3 — Configure Gmail for EAIA

1. Create a Google Cloud project and enable the Gmail API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download `client_secret.json`
4. Run the OAuth flow locally:
   ```bash
   cd assistant/executive-ai-assistant-main
   python scripts/authorize_gmail.py
   ```
5. This creates `token.json`. Base64-encode both files:
   ```bash
   base64 -w0 client_secret.json
   base64 -w0 token.json
   ```
6. Set `GMAIL_SECRET` and `GMAIL_TOKEN` in your `.env` to the base64 strings

### 6.4 — Verify MCP server

```bash
curl http://localhost:8001/mcp/tools
# Should return list of Frappe MCP tools
```

### 6.5 — Run LeadGen collectors

```bash
docker-compose exec frappe-web \
  bench --site $FRAPPE_SITE_NAME execute crm.leadgen.asco.collect
```

---

## 7. Environment Variable Reference

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `FRAPPE_SITE_NAME` | frappe-* | ✅ | Hostname for the Frappe site (e.g. `crm.localhost`) |
| `ADMIN_PASSWORD` | frappe-web | ✅ | Frappe Administrator account password |
| `DB_NAME` | frappe-*, mariadb | ✅ | MariaDB database name |
| `DB_PASSWORD` | frappe-*, mariadb | ✅ | MariaDB user password |
| `DB_ROOT_PASSWORD` | mariadb | ✅ | MariaDB root password (first-boot only) |
| `ENCRYPTION_KEY` | frappe-web | ⚠️ | Fernet key for encrypted fields — back this up |
| `REDIS_CACHE_URL` | frappe-* | ✅ | Redis URL for cache (default: `redis://redis-cache:13000`) |
| `REDIS_QUEUE_URL` | frappe-* | ✅ | Redis URL for job queue (default: `redis://redis-queue:11000`) |
| `FRAPPE_SITE_URL` | eaia-agent | ✅ | Full URL of Frappe (default: `http://frappe-web:8000`) |
| `FRAPPE_API_KEY` | eaia-agent | ✅ | Frappe API key for agent user |
| `FRAPPE_API_SECRET` | eaia-agent | ✅ | Frappe API secret for agent user |
| `OPENAI_API_KEY` | eaia-agent | ✅ | GPT-4o for enrichment and email drafting |
| `ANTHROPIC_API_KEY` | eaia-agent | ➖ | Claude fallback (optional) |
| `LANGSMITH_API_KEY` | eaia-agent | ➖ | LangSmith tracing (optional) |
| `GMAIL_SECRET` | eaia-agent | ✅ | Google OAuth client secret (base64) |
| `GMAIL_TOKEN` | eaia-agent | ✅ | Gmail OAuth token (base64) |
| `TAVILY_API_KEY` | eaia-agent, farfalle | ➖ | Web search for lead enrichment |
| `POSTGRES_USER` | farfalle-db | ✅ | Farfalle Postgres user |
| `POSTGRES_PASSWORD` | farfalle-db | ✅ | Farfalle Postgres password |
| `POSTGRES_DB` | farfalle-db | ✅ | Farfalle Postgres database name |

**Legend**: ✅ Required · ⚠️ Required in production · ➖ Optional

---

## Troubleshooting

### Frappe site not created after 10 minutes

```bash
docker-compose logs frappe-web | tail -50
```

Common causes:
- MariaDB not ready → `init-site.sh` retries 30× with 5s delay; check `docker-compose logs mariadb`
- Wrong `DB_ROOT_PASSWORD` → matches `MYSQL_ROOT_PASSWORD` in mariadb service

### EAIA agent can't reach Frappe

```bash
docker-compose exec eaia-agent curl http://frappe-web:8000/api/method/ping
```

If this fails, check that `frappe-web` is healthy and `FRAPPE_SITE_URL` is set correctly.

### Bench migrate fails

```bash
docker-compose exec frappe-web \
  bench --site $FRAPPE_SITE_NAME migrate --verbose
```

Usually caused by a DocType schema conflict. Check the Frappe error log:

```bash
docker-compose exec frappe-web \
  cat /home/frappe/frappe-bench/sites/$FRAPPE_SITE_NAME/logs/frappe.log | tail -100
```

### Out of memory

Frappe + MariaDB + Redis needs ~4 GB minimum. Increase Docker Desktop memory limit or upgrade your VPS.
