from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, status
from fastapi.responses import PlainTextResponse
from starlette.datastructures import FormData, Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CSRF_SESSION_KEY = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
DEFAULT_SECRET_KEY = "change-this-secret-key"
DEFAULT_ADMIN_PASSWORD = "admin123456"


def ensure_csrf_token(request: Request) -> str:
    session = request.scope.setdefault("session", {})
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return str(token)


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        chunks.append(message.get("body", b""))
        more_body = message.get("more_body", False)
    return b"".join(chunks)


def _replay_body(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


async def csrf_token_from_request(scope: Scope, receive: Receive, body: bytes) -> str | None:
    headers = Headers(scope=scope)
    header_token = headers.get("x-csrf-token")
    if header_token:
        return header_token
    request = Request(scope, _replay_body(body))
    form: FormData = await request.form()
    value = form.get(CSRF_FIELD_NAME)
    return str(value) if value is not None else None


class CSRFMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS or scope["path"] == "/login":
            await self.app(scope, receive, send)
            return

        body = await _read_body(receive)
        session = scope.get("session", {})
        expected = session.get(CSRF_SESSION_KEY)
        provided = await csrf_token_from_request(scope, receive, body)
        if not expected or not provided or not secrets.compare_digest(str(expected), provided):
            response = PlainTextResponse("CSRF token missing or invalid", status_code=status.HTTP_403_FORBIDDEN)
            await response(scope, _replay_body(body), send)
            return

        await self.app(scope, _replay_body(body), send)


def assert_safe_production_settings(app_env: str, secret_key: str, admin_password: str) -> None:
    if app_env.lower() not in {"prod", "production"}:
        return
    if secret_key == DEFAULT_SECRET_KEY:
        raise ValueError("SECRET_KEY must be changed in production")
    if admin_password == DEFAULT_ADMIN_PASSWORD:
        raise ValueError("ADMIN_PASSWORD must be changed in production")
