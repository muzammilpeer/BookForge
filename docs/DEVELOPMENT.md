# Development Guide

## Setup

```bash
./scripts/install.sh
```

Run:

```bash
export BOOKFORGE_ADMIN_USERNAME="admin"
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_SESSION_SECRET="change-this-too"
./scripts/run.sh
```

Local URL:

```text
http://localhost:8787
```

## Smoke Test Commands

Compile:

```bash
python3 -m compileall app
```

Run with test credentials:

```bash
BOOKFORGE_ADMIN_PASSWORD=change-me BOOKFORGE_SESSION_SECRET=change-this-too .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Login via curl:

```bash
curl -sS -c /tmp/bookforge-cookies.txt \
  -d 'username=admin&password=change-me&next=/' \
  -o /dev/null -w '%{http_code}' \
  http://127.0.0.1:8787/login
```

Check dashboard state:

```bash
curl -fsS -b /tmp/bookforge-cookies.txt http://127.0.0.1:8787/api/dashboard-state
```

Check SSE:

```bash
curl -fsS -b /tmp/bookforge-cookies.txt --max-time 3 http://127.0.0.1:8787/events/dashboard
```

## Adding Features

When adding a new setting:

1. Add it to `Settings` in `app/config.py`.
2. Add it to `save_settings()`.
3. Add it to `config.yaml.example`.
4. Add it to `/settings` form in `app/templates/settings.html`.
5. Add it to `save_settings()` route in `app/main.py`.
6. Validate user input before saving.

When changing dashboard live data:

1. Add the field in `dashboard_state()` in `app/main.py`.
2. Update initial HTML in `app/templates/partials/dashboard_sections.html`.
3. Update live patching in `app/static/dashboard.js`.
4. Confirm selected job checkboxes still stay selected after SSE updates.

When changing job schema:

1. Update `app/models.py`.
2. Update `app/db.py` create table.
3. Add a migration guard in `init_db()` using `pragma table_info(jobs)`.
4. Update serialization in `app/main.py`.

## Testing Discipline

Always run:

```bash
python3 -m compileall app
```

For UI route changes, smoke-test the server and fetch the affected page. Avoid uploading real files unless the user explicitly asks, because MimikaStudio may start a long conversion.

## Style

- Use FastAPI, Jinja2, SQLite, vanilla JS.
- Keep JS small and page-specific.
- Keep long-running shell commands bounded with timeouts.
- Avoid adding new dependencies unless they clearly simplify meaningful complexity.
- Use defensive parsing for MimikaStudio responses.
