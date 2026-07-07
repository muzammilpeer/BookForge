# macOS Launchd Service

This guide shows how to run BookForge automatically on macOS login/restart using `launchd`.

Use a LaunchAgent when BookForge should run as your macOS user. This is the recommended setup because BookForge needs access to user-owned folders, MimikaStudio output files, and the user-level Python virtual environment.

## Prerequisites

Install BookForge first:

```bash
cd /path/to/BookForge
./scripts/install.sh
```

Confirm the app runs manually:

```bash
export BOOKFORGE_ADMIN_USERNAME="admin"
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_SESSION_SECRET="change-this-too"
./scripts/run.sh
```

Then stop it with `Ctrl+C`.

## Create Log Directory

```bash
mkdir -p /Users/$(whoami)/Library/Logs/BookForge
```

## Create LaunchAgent

Create this file:

```bash
nano ~/Library/LaunchAgents/com.bookforge.server.plist
```

Paste the template below.

Replace:

- `/path/to/BookForge` with your real BookForge repo path.
- `change-me` with a real admin password.
- `change-this-too` with a long random session secret.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.bookforge.server</string>

    <key>WorkingDirectory</key>
    <string>/path/to/BookForge</string>

    <key>ProgramArguments</key>
    <array>
      <string>/path/to/BookForge/.venv/bin/uvicorn</string>
      <string>app.main:app</string>
      <string>--host</string>
      <string>0.0.0.0</string>
      <string>--port</string>
      <string>8787</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
      <key>BOOKFORGE_ADMIN_USERNAME</key>
      <string>admin</string>
      <key>BOOKFORGE_ADMIN_PASSWORD</key>
      <string>change-me</string>
      <key>BOOKFORGE_SESSION_SECRET</key>
      <string>change-this-too</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/BookForge/bookforge.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Library/Logs/BookForge/bookforge.err.log</string>
  </dict>
</plist>
```

Replace `YOUR_USERNAME` in the log paths with:

```bash
whoami
```

## Start BookForge

Load and start:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bookforge.server.plist
launchctl enable gui/$(id -u)/com.bookforge.server
launchctl kickstart -k gui/$(id -u)/com.bookforge.server
```

Check status:

```bash
launchctl print gui/$(id -u)/com.bookforge.server
```

Open:

```text
http://localhost:8787
```

Or test with curl:

```bash
curl -fsS http://127.0.0.1:8787/login | head
```

## Stop, Restart, Status

Restart:

```bash
launchctl kickstart -k gui/$(id -u)/com.bookforge.server
```

Stop and unload:

```bash
launchctl bootout gui/$(id -u)/com.bookforge.server
```

Status:

```bash
launchctl print gui/$(id -u)/com.bookforge.server
```

Logs:

```bash
tail -f ~/Library/Logs/BookForge/bookforge.out.log
tail -f ~/Library/Logs/BookForge/bookforge.err.log
```

List logs:

```bash
ls -lh ~/Library/Logs/BookForge/
```

## Important Launchctl Behavior

`bootout` unloads the service.

After this command:

```bash
launchctl bootout gui/$(id -u)/com.bookforge.server
```

This command will fail:

```bash
launchctl print gui/$(id -u)/com.bookforge.server
```

because the service is no longer loaded.

To start it again, bootstrap it again:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bookforge.server.plist
launchctl enable gui/$(id -u)/com.bookforge.server
launchctl kickstart -k gui/$(id -u)/com.bookforge.server
```

If `bootstrap` says the service is already loaded, use:

```bash
launchctl kickstart -k gui/$(id -u)/com.bookforge.server
```

## MimikaStudio Backend

BookForge still requires the MimikaStudio backend to be running.

If the MimikaStudio app does not start the backend automatically, run:

```bash
cd /Applications/MimikaStudio.app/Contents/Resources/backend
./venv/bin/python main.py
```

You can create a separate LaunchAgent for MimikaStudio backend if you want it to start automatically too.

## Security Notes

- Do not commit your real `.plist` file if it contains a real password.
- Use a long random `BOOKFORGE_SESSION_SECRET`.
- Keep BookForge on a trusted LAN unless you put it behind a proper reverse proxy and HTTPS.

