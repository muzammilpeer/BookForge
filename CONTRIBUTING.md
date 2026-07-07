# Contributing

Thanks for helping improve BookForge.

## Before You Start

Read:

- [AGENTS.md](AGENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

## Development Setup

```bash
./scripts/install.sh
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_SESSION_SECRET="change-this-too"
./scripts/run.sh
```

Open:

```text
http://localhost:8787
```

## Pull Request Checklist

- Keep the app native. Do not add Docker.
- Keep dashboard updates SSE/JSON based.
- Add settings to `config.yaml.example` and `/settings` when user-configurable.
- Run `python3 -m compileall app`.
- Avoid starting long audiobook conversions in tests unless the PR requires it.
- Update docs for user-visible behavior.

## Code Style

- FastAPI, Jinja2, SQLite, vanilla JavaScript.
- Small focused modules.
- Defensive parsing for MimikaStudio API responses.
- Bounded subprocess calls with timeouts.

## MimikaStudio Compatibility

MimikaStudio response shapes may change. When adding backend integration, prefer tolerant parsing and graceful fallbacks over strict assumptions.

