# Directory Structure

```text
BookForge/
  AGENTS.md
  README.md
  pyproject.toml
  config.yaml.example
  config.yaml              # local only, gitignored
  bookforge.sqlite3        # local only, gitignored
  app/
    __init__.py
    config.py
    db.py
    files.py
    main.py
    mimika_client.py
    models.py
    security.py
    system_metrics.py
    worker.py
    static/
      dashboard.js
      styles.css
      upload.js
    templates/
      base.html
      dashboard.html
      job_detail.html
      login.html
      mimika.html
      settings.html
      upload.html
      voices.html
      partials/
        dashboard_sections.html
  docs/
    ARCHITECTURE.md
    DEVELOPMENT.md
    DIRECTORY_STRUCTURE.md
    MEMORY.md
    OPERATIONS.md
  scripts/
    install.sh
    run.sh
```

## File Purposes

`AGENTS.md`

Root Codex guide. Read this before working.

`README.md`

User-facing install/run/config documentation.

`config.yaml.example`

Tracked default settings.

`config.yaml`

Local runtime settings. Do not commit.

`bookforge.sqlite3`

Local job database. Do not commit.

`app/templates/partials/dashboard_sections.html`

Initial dashboard markup only. Live changes are applied by `dashboard.js`.

`app/static/dashboard.js`

Dashboard SSE client. Update this when changing dashboard JSON shape.

`app/system_metrics.py`

Host monitoring logic. Keep commands bounded with timeouts.

