from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from ipaddress import ip_address

from fastapi import Request
from fastapi.responses import RedirectResponse


SESSION_COOKIE = "bookforge_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12


def admin_password() -> str | None:
    return os.getenv("BOOKFORGE_ADMIN_PASSWORD")


def admin_username() -> str:
    return os.getenv("BOOKFORGE_ADMIN_USERNAME", "admin")


def session_secret() -> bytes:
    secret = os.getenv("BOOKFORGE_SESSION_SECRET") or admin_password() or "bookforge-local-dev"
    return secret.encode("utf-8")


def is_local_client(request: Request) -> bool:
    host = request.client.host if request.client else ""
    try:
        parsed = ip_address(host)
    except ValueError:
        return host in {"localhost", "127.0.0.1", "::1"}
    return parsed.is_loopback


def password_enabled(request: Request) -> bool:
    password = admin_password()
    if not password:
        return not is_local_client(request)
    return True


def valid_credentials(username: str, password: str) -> bool:
    expected_password = admin_password()
    if not expected_password:
        return False
    return secrets.compare_digest(username, admin_username()) and secrets.compare_digest(
        password, expected_password
    )


def create_session_token(username: str) -> str:
    issued = str(int(time.time()))
    payload = f"{username}:{issued}"
    signature = hmac.new(session_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    raw = f"{payload}:{base64.urlsafe_b64encode(signature).decode('ascii')}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def verify_session_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, issued, supplied_signature = raw.rsplit(":", 2)
        issued_at = int(issued)
    except (ValueError, TypeError):
        return False
    if username != admin_username() or time.time() - issued_at > SESSION_MAX_AGE_SECONDS:
        return False
    payload = f"{username}:{issued}"
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(session_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")
    return secrets.compare_digest(supplied_signature, expected_signature)


def has_access(request: Request) -> bool:
    if not password_enabled(request):
        return True
    return verify_session_token(request.cookies.get(SESSION_COOKIE))


def redirect_to_login(request: Request) -> RedirectResponse:
    next_url = request.url.path
    if request.url.query:
        next_url = f"{next_url}?{request.url.query}"
    return RedirectResponse(url=f"/login?next={next_url}", status_code=303)
