# Project Memory

## User Intent

The user wants BookForge to be a practical local web portal for managing MimikaStudio audiobook generation. The UI should feel like a management console, not a demo page.

Repeated preferences:

- Keep it native on macOS/Pi. No Docker.
- Keep server load low.
- Prefer live JSON updates over full-page or full-partial refreshes.
- Make every operational path and tuning option configurable in the portal.
- Provide clear login protection for LAN access.
- Dashboard should show queue state, active jobs, completed downloads, and machine health.

## Current Behavior

BookForge currently has:

- Browser login with signed cookie.
- Upload page with multi-file upload and voice selection.
- Voice demo button that works when Mimika voice metadata includes a preview/sample/demo/audio URL.
- SQLite-backed jobs table.
- Async worker inside FastAPI.
- Dashboard table with row actions and bulk actions.
- SSE endpoint at `/events/dashboard`.
- JSON state endpoint at `/api/dashboard-state`.
- Settings page for backend URL, paths, defaults, upload size, and SSE interval.
- System metrics in SSE payload.

## Known Backend Details

MimikaStudio local backend:

```text
http://127.0.0.1:7693
```

Known endpoints:

- `POST /api/audiobook/generate-from-file`
- `GET /api/audiobook/status/{job_id}`
- `POST /api/audiobook/cancel/{job_id}`
- `GET /api/audiobook/list`
- `DELETE /api/audiobook/{job_id}`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `DELETE /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/metrics`
- `GET /api/kokoro/voices`
- `GET /api/kokoro/audio/list`
- `DELETE /api/kokoro/audio/{filename}`
- `GET /api/tts/audio/list`
- `DELETE /api/tts/audio/{filename}`

Mimika responses vary, so `app/mimika_client.py` parses defensively.

## Current Local Paths

Defaults in `config.yaml.example`:

```yaml
incoming_dir: "/Volumes/media/apps/bookforge/incoming"
work_dir: "/Volumes/media/apps/bookforge/work"
completed_dir: "/Volumes/media/apps/bookforge/completed"
failed_dir: "/Volumes/media/apps/bookforge/failed"
audiobookshelf_dir: "/Volumes/media/apps/audiobookshelf/audiobooks"
```

Runtime config is in `config.yaml`, which is ignored by git.

## Authentication Memory

Environment variables:

```bash
BOOKFORGE_ADMIN_USERNAME="admin"
BOOKFORGE_ADMIN_PASSWORD="..."
BOOKFORGE_SESSION_SECRET="..."
```

If `BOOKFORGE_ADMIN_PASSWORD` is missing, loopback clients bypass login, but LAN clients should require a password.

## macOS GPU Metrics Memory

The user has confirmed this works:

```bash
sudo -n /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

The user is `muzammilpeer`.

Recommended sudoers file:

```bash
sudo visudo -f /etc/sudoers.d/bookforge-powermetrics
```

Line:

```text
muzammilpeer ALL=(root) NOPASSWD: /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

BookForge parses:

- `GPU HW active residency`
- `GPU HW active frequency`
- `GPU idle residency`
- `GPU Power`

## Active Job Note

During previous smoke tests, MimikaStudio had an already-running audiobook job. Codex did not intentionally upload/start a new job during these checks. Be careful when testing worker behavior because local Mimika may already be busy.

