"""Job board connector adapters."""

from __future__ import annotations

import httpx


def is_transient_http_error(exc: BaseException) -> bool:
    """Return True for errors worth retrying (5xx, connect, read timeout)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout))
