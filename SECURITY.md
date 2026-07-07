# Security Policy

## Supported Versions

The `master` branch is the active development version.

## Reporting a Vulnerability

Please open a private security advisory on GitHub if available, or contact the maintainer privately before publishing exploit details.

Do not include real audiobook files, personal documents, passwords, or private filesystem paths in public issues.

## Local Network Use

BookForge is designed for trusted local networks. Set these before exposing it on your LAN:

```bash
export BOOKFORGE_ADMIN_USERNAME="admin"
export BOOKFORGE_ADMIN_PASSWORD="change-me"
export BOOKFORGE_SESSION_SECRET="change-this-too"
```

## macOS GPU Metrics

Do not run BookForge as root. If GPU metrics are needed on macOS, grant only the exact `powermetrics` command documented in the README.

