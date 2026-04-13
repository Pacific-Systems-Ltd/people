"""TLS enforcement for Solid-OIDC credential transmission.

Per Solid-OIDC Section 11.1, tokens, client credentials, and user credentials
MUST only be transmitted over TLS. Localhost is exempted for local development.
"""

from __future__ import annotations

from urllib.parse import urlparse

from people._http.errors import SolidError

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def enforce_tls(url: str) -> None:
    """Raise SolidError if the URL uses HTTP and the host is not trusted.

    Allows http:// for localhost (local dev) and .internal hosts
    (Fly.io private network — encrypted at the WireGuard layer).
    All other hosts require https://.
    """
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    hostname = parsed.hostname or ""
    if parsed.scheme == "http" and (
        hostname in _LOCALHOST_HOSTS or hostname.endswith(".internal")
    ):
        return
    raise SolidError(
        f"Refusing to transmit credentials over insecure connection to {url}. "
        f"Solid-OIDC requires TLS for all credential transmission. "
        f"Use https:// or connect to localhost for development.",
        status_code=0,
        url=url,
    )
