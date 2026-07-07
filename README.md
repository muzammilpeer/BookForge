# BookForge

BookForge is a local web portal for managing audiobook generation through a running [MimikaStudio](https://github.com/BoltzmannEntropy/MimikaStudio) backend.

It is designed as a companion wrapper for users who downloaded the MimikaStudio macOS app from the official GitHub project and want a browser-based queue/dashboard around the local API.

- MimikaStudio source: [BoltzmannEntropy/MimikaStudio](https://github.com/BoltzmannEntropy/MimikaStudio)
- MimikaStudio releases/macOS downloads: [MimikaStudio Releases](https://github.com/BoltzmannEntropy/MimikaStudio/releases)
- MimikaStudio website: [boltzmannentropy.github.io/mimikastudio.github.io](https://boltzmannentropy.github.io/mimikastudio.github.io/)

BookForge is not affiliated with or endorsed by MimikaStudio. It only talks to the local backend exposed by the MimikaStudio app.

By default, MimikaStudio is expected at:

```text
http://127.0.0.1:7693
```

## How It Fits Together

1. Install and start the MimikaStudio macOS app from the official GitHub release.
2. Wait for MimikaStudio's bundled local backend to start.
3. Start BookForge.
4. Open BookForge in your browser.
5. Upload books/documents, monitor the queue, download final audio, or copy output to Audiobookshelf.

## Start MimikaStudio Backend

BookForge requires the MimikaStudio backend to be running first. If the MimikaStudio app does not start it automatically, start the bundled backend manually:

```bash
cd /Applications/MimikaStudio.app/Contents/Resources/backend
./venv/bin/python main.py
```

You should see Uvicorn startup logs similar to:

```text
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Then confirm the backend is reachable at:

```text
http://127.0.0.1:7693
```

## Features

- Upload PDF, EPUB, TXT, Markdown, and DOCX files.
- Queue jobs in SQLite and run them with a configurable parallel limit.
- Track queued, running, completed, failed, and canceled jobs from a single dashboard table.
- Poll MimikaStudio for progress, ETA, chars/sec, errors, and output paths.
- Select jobs for bulk cancel, retry, copy, or local record deletion.
- Cancel running/queued jobs and download completed audio directly from dashboard rows.
- Browse MimikaStudio jobs/audio lists and delete supported generated audio files.
- Simple admin protection with `BOOKFORGE_ADMIN_PASSWORD`.
- Browser login with a signed session cookie.
- Lightweight Server-Sent Events dashboard updates instead of full-page polling.
- Configurable dashboard live update interval.
- Live host metrics on the dashboard: CPU load, available RAM, and best-effort GPU detail.

## Project Status

BookForge is an independent open source companion project. It depends on MimikaStudio's local API behavior, so some features may need updates when MimikaStudio changes response shapes or endpoint behavior.

## Install

Clone this repository:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/BookForge.git
cd BookForge
```

Install dependencies:

```bash
./scripts/install.sh
```

The install script creates `.venv`, installs dependencies, copies `config.yaml.example` to `config.yaml` if needed, and creates configured folders.

## Run

Start the MimikaStudio backend first, then run:

```bash
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_ADMIN_USERNAME="admin"
export BOOKFORGE_SESSION_SECRET="change-this-too"
./scripts/run.sh
```

Open:

```text
http://localhost:8787
```

If `BOOKFORGE_ADMIN_PASSWORD` is missing, BookForge logs a warning and only loopback clients bypass login. Set the password before exposing BookForge on your LAN.

## Configuration

Edit `config.yaml` directly or use the Settings page.

Default paths:

```yaml
incoming_dir: "/Volumes/media/apps/bookforge/incoming"
work_dir: "/Volumes/media/apps/bookforge/work"
completed_dir: "/Volumes/media/apps/bookforge/completed"
failed_dir: "/Volumes/media/apps/bookforge/failed"
audiobookshelf_dir: "/Volumes/media/apps/audiobookshelf/audiobooks"
```

For a Mac mini M4, keep `max_parallel_jobs: 1` unless you have tested higher concurrency with your local MimikaStudio setup.

The Settings page also controls MimikaStudio backend URL, all BookForge input/output/archive paths, upload size, dashboard SSE interval, whether completed jobs are auto-copied to Audiobookshelf, and the target `audiobookshelf_dir` path used by copy actions.

System metrics are intentionally lightweight for small hosts such as Raspberry Pi 5. CPU is estimated from one-minute load average normalized by core count. RAM uses `/proc/meminfo` on Linux and `vm_stat`/`sysctl` on macOS. On macOS, GPU usage uses:

```bash
sudo -n /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

Grant only that exact command through sudoers if you want GPU percentage, frequency, and power on the dashboard.

To configure that permission:

```bash
whoami
sudo visudo -f /etc/sudoers.d/bookforge-powermetrics
```

Add this line, replacing `YOUR_USERNAME` with the output from `whoami`:

```text
YOUR_USERNAME ALL=(root) NOPASSWD: /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

Then test it:

```bash
sudo -n /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

## Pages

- `/` dashboard with SSE live updates
- `/upload` upload and queue files
- `/jobs/{id}` job details and actions
- `/settings` defaults and queue concurrency
- `/voices` MimikaStudio voice browser and default selector
- `/mimika` raw MimikaStudio browser

## Notes

BookForge serves downloads only from the configured completed folder and accepts only the requested document extensions. MimikaStudio response parsing is defensive because local backend builds may return slightly different JSON shapes.

## License

BookForge is released under the [MIT License](LICENSE).

MimikaStudio is a separate project with its own license terms. Check the official [MimikaStudio repository](https://github.com/BoltzmannEntropy/MimikaStudio) for its source and binary licensing.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), then read [AGENTS.md](AGENTS.md) and the docs in `docs/`.

## Maintainer Docs

For future Codex sessions and feature work, start with:

- [AGENTS.md](AGENTS.md)
- [docs/MEMORY.md](docs/MEMORY.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)
