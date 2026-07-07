# BookForge Codex Guide

This file is the first stop for future Codex sessions working in this repo.

## Project

BookForge is a native macOS/Pi-friendly FastAPI web app that wraps a local MimikaStudio backend for audiobook generation.

The app:

- Uploads PDF/EPUB/TXT/MD/DOCX files.
- Queues local jobs in SQLite.
- Starts and polls MimikaStudio audiobook jobs.
- Shows a live dashboard using Server-Sent Events.
- Supports login, settings, voice selection, job tracking, cancellation, retry, download, and Audiobookshelf copy.

## Read These First

Before adding features, read:

- [docs/MEMORY.md](docs/MEMORY.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/MACOS_LAUNCHD.md](docs/MACOS_LAUNCHD.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)

## Local Context

- Workspace: repository root
- MimikaStudio backend: `http://127.0.0.1:7693`
- BookForge app port: `8787`
- Python app entry point: `app/main.py`
- Config file: `config.yaml`
- SQLite database: `bookforge.sqlite3`

## Important Rules

- Do not use Docker.
- Keep the app native and lightweight for Mac mini / Raspberry Pi style hosts.
- Prefer small FastAPI/Jinja/vanilla JS changes over heavy frontend frameworks.
- Dashboard live updates must remain SSE/JSON based, not full HTML polling.
- Keep settings configurable through `/settings` and persisted in `config.yaml`.
- Do not expose arbitrary filesystem paths through downloads.
- Do not run the whole app as root. macOS GPU metrics use a narrow sudoers rule for `powermetrics`.

## Useful Commands

```bash
./scripts/install.sh
./scripts/run.sh
python3 -m compileall app
```

For login-enabled local smoke tests:

```bash
BOOKFORGE_ADMIN_PASSWORD=change-me BOOKFORGE_SESSION_SECRET=change-this-too .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787
```

## Current High-Value Files

- `app/main.py`: routes, auth middleware, SSE endpoint, settings save flow.
- `app/worker.py`: async queue worker that starts and polls Mimika jobs.
- `app/mimika_client.py`: defensive client for MimikaStudio API shapes.
- `app/system_metrics.py`: CPU/RAM/GPU metrics for dashboard SSE payload.
- `app/db.py`: SQLite schema and job helpers.
- `app/config.py`: dataclass settings and YAML persistence.
- `app/templates/partials/dashboard_sections.html`: dashboard markup.
- `app/static/dashboard.js`: SSE client and live table patching.
- `app/static/upload.js`: voice demo UI behavior.
