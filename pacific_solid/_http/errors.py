"""Solid error hierarchy — maps HTTP status codes to meaningful exceptions."""

from __future__ import annotations


class SolidError(Exception):
    """Base exception for all people errors."""

    def __init__(self, message: str, status_code: int | None = None, url: str | None = None):
        self.status_code = status_code
        self.url = url
        super().__init__(message)


class AuthenticationError(SolidError):
    """401 — DPoP proof or token validation failed."""


class AccessDeniedError(SolidError):
    """403 — WAC denied access. Not Python's built-in PermissionError."""


class NotFoundError(SolidError):
    """404 — Resource does not exist."""


class ConflictError(SolidError):
    """409 — Container conflict or patch condition mismatch."""


class PreconditionFailedError(SolidError):
    """412 — ETag mismatch. Resource changed since last read."""


class PatchError(SolidError):
    """422 — N3 Patch violates constraints or cannot be applied."""


def raise_for_status(status_code: int, url: str, body: str = "") -> None:
    """Raise the appropriate SolidError for an HTTP error status code."""
    if status_code < 400:
        return

    detail = body[:500] if body else ""
    msg = f"HTTP {status_code} for {url}"
    if detail:
        msg = f"{msg}: {detail}"

    if status_code == 401:
        raise AuthenticationError(msg, status_code=status_code, url=url)
    if status_code == 403:
        raise AccessDeniedError(msg, status_code=status_code, url=url)
    if status_code == 404:
        raise NotFoundError(msg, status_code=status_code, url=url)
    if status_code == 409:
        raise ConflictError(msg, status_code=status_code, url=url)
    if status_code == 412:
        raise PreconditionFailedError(msg, status_code=status_code, url=url)
    if status_code == 422:
        raise PatchError(msg, status_code=status_code, url=url)

    raise SolidError(msg, status_code=status_code, url=url)
