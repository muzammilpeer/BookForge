# Operations

## Runtime

Start MimikaStudio first.

Then run BookForge:

```bash
export BOOKFORGE_ADMIN_USERNAME="admin"
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_SESSION_SECRET="change-this-too"
./scripts/run.sh
```

BookForge listens on:

```text
http://localhost:8787
```

`scripts/run.sh` binds to `0.0.0.0:8787` for LAN use.

## Login

Use:

```text
username: admin
password: BOOKFORGE_ADMIN_PASSWORD
```

The username can be changed with `BOOKFORGE_ADMIN_USERNAME`.

## GPU Metrics on macOS

BookForge can show real Apple Silicon GPU usage if this command works without prompting:

```bash
sudo -n /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

Configure the narrow permission:

```bash
whoami
sudo visudo -f /etc/sudoers.d/bookforge-powermetrics
```

Add:

```text
YOUR_USERNAME ALL=(root) NOPASSWD: /usr/bin/powermetrics --samplers gpu_power -i 1000 -n 1
```

Replace `YOUR_USERNAME` with the output from `whoami`.

## Important Local Files

Do not commit:

- `config.yaml`
- `bookforge.sqlite3`
- `.venv/`
- `bookforge.egg-info/`

These are local runtime/build artifacts.

## Dashboard Load

The dashboard uses one SSE connection per browser tab. It sends compact JSON at `sse_interval_seconds`, configurable in `/settings`.

Default:

```yaml
sse_interval_seconds: 2.0
```

For slower devices, increase this to `5` or `10`.

## Queue Tuning

For Mac mini M4, default:

```yaml
max_parallel_jobs: 1
```

Increase only after confirming MimikaStudio and the host remain responsive.

## Troubleshooting

If login redirects repeatedly:

- Confirm `BOOKFORGE_ADMIN_PASSWORD` is set.
- Clear browser cookies for `localhost:8787`.
- Confirm `BOOKFORGE_SESSION_SECRET` is stable between restarts.

If GPU says unavailable:

- Run the `sudo -n powermetrics` command manually.
- Confirm the sudoers line exactly matches the command BookForge runs.

If dashboard does not update:

- Check browser console for SSE errors.
- Open `/api/dashboard-state` after login.
- Open `/events/dashboard` after login.
