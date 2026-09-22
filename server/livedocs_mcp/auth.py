"""
auth.py — the shared-token check on HTTP requests.

Network hygiene, not an auth system: one token, compared in constant time, so a
casually-reachable endpoint is not a casually-readable one. Who can reach the
host at all is the deployment's boundary, not this file's. The SDK's own
`token_verifier` is OAuth-resource-server shaped and answers a different
question, so the check is a plain ASGI wrapper around the app it returns.
"""

from __future__ import annotations

import hmac
from typing import Any, Awaitable, Callable


_UNAUTHORIZED = (
    b"401 Unauthorized: this live_docs endpoint requires a bearer token.\n"
    b"Send 'Authorization: Bearer <token>' with the token the host was started with.\n"
)


class BearerToken:
    """Reject HTTP requests that do not carry the configured bearer token."""

    def __init__(self, app: Callable[..., Awaitable[None]], token: str) -> None:
        self._app = app
        self._token = token

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if self._presented(scope):
            await self._app(scope, receive, send)
            return
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"www-authenticate", b"Bearer"),
                (b"content-length", str(len(_UNAUTHORIZED)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": _UNAUTHORIZED})

    def _presented(self, scope: dict) -> bool:
        for key, value in scope.get("headers", ()):
            if key.lower() != b"authorization":
                continue
            raw = value.decode("latin-1").strip()
            scheme, _, presented = raw.partition(" ")
            if scheme.lower() != "bearer":
                return False
            return hmac.compare_digest(presented.strip(), self._token)
        return False
