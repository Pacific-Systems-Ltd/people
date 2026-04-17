"""ACP detection — determine whether a server uses WAC or ACP.

Per Solid Protocol Section 11, a server MUST conform to either WAC or ACP.
A client must detect which scheme is in use before managing permissions.
ACP itself has no client-side requirements — it is evaluated server-side.
But a client must not blindly PUT WAC ACLs on an ACP server.

Detection strategy:
- Link header with rel="acl" → WAC
- Link header with rel containing "acp" → ACP
- Otherwise → unknown
"""

from __future__ import annotations

from pacific_solid._http.errors import SolidError


class AuthSchemeError(SolidError):
    """Raised when a WAC operation is attempted on an ACP server."""

    def __init__(self, url: str) -> None:
        super().__init__(
            "This server uses Access Control Policy (ACP), not Web Access Control (WAC). "
            "WAC operations (grant, revoke, grants) are not applicable. "
            "See https://solid.github.io/authorization-panel/acp-specification/",
            status_code=0,
            url=url,
        )


def detect_auth_scheme(link_headers: dict[str, str]) -> str:
    """Detect the authorization scheme from Link headers.

    Returns:
        "wac" if rel="acl" is present (Web Access Control).
        "acp" if any rel contains "acp" (Access Control Policy).
        "unknown" otherwise.
    """
    if "acl" in link_headers:
        return "wac"

    for rel in link_headers:
        if "acp" in rel.lower():
            return "acp"

    return "unknown"
