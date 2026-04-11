"""TLS enforcement for Solid-OIDC credential transmission.

Per Solid-OIDC Section 11.1, tokens, client credentials, and user credentials
MUST only be transmitted over TLS. Localhost is exempted for local development.
"""

from __future__ import annotations

from urllib.parse import urlparse

from people._http.errors import SolidError

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def enforce_tls(url: str) -> None:
    """Raise SolidError if the URL uses HTTP and the host is not localhost.

    Allows http:// only for localhost/127.0.0.1/[::1] (local development).
    All other hosts require https://.
    """
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOCALHOST_HOSTS:
        return
    raise SolidError(
        f"Refusing to transmit credentials over insecure connection to {url}. "
        f"Solid-OIDC requires TLS for all credential transmission. "
        f"Use https:// or connect to localhost for development.",
        status_code=0,
        url=url,
    )
