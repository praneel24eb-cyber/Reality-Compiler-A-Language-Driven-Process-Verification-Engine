"""Readable errors shared by all API-backed pages."""

import httpx


def request_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        try:
            detail = error.response.json().get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail[:1000]
        except (ValueError, AttributeError):
            pass
        return f"The request failed (HTTP {error.response.status_code}). Please retry."
    if isinstance(error, httpx.TimeoutException):
        return "The request timed out. Please retry; check saved workflows before repeating an analysis."
    if isinstance(error, httpx.HTTPError):
        return "Cannot reach the backend. Check that the local API is running, then retry."
    return "The backend returned an invalid response. Please retry."
