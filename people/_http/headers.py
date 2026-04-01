"""HTTP header parsing for Solid responses — Link, WAC-Allow, ETag."""

from __future__ import annotations

import re
from typing import Any


def parse_link_headers(header_value: str) -> dict[str, str]:
    """Parse HTTP Link headers into a dict keyed by rel value.

    Example:
        '<.acl>; rel="acl"' -> {"acl": ".acl"}
    """
    result: dict[str, str] = {}
    if not header_value:
        return result

    for part in header_value.split(","):
        part = part.strip()
        match = re.match(r'<([^>]+)>\s*;\s*rel="([^"]+)"', part)
        if match:
            uri, rel = match.groups()
            result[rel] = uri

    return result


def parse_wac_allow(header_value: str) -> dict[str, set[str]]:
    """Parse the WAC-Allow header into access mode sets.

    Example:
        'user="read write", public="read"'
        -> {"user": {"read", "write"}, "public": {"read"}}
    """
    result: dict[str, set[str]] = {}
    if not header_value:
        return result

    for part in header_value.split(","):
        part = part.strip()
        match = re.match(r'(\w+)="([^"]*)"', part)
        if match:
            key, modes_str = match.groups()
            modes = {m.strip() for m in modes_str.split() if m.strip()}
            result[key] = modes

    return result


def resolve_acl_url(resource_url: str, link_headers: dict[str, str]) -> str | None:
    """Resolve the ACL URL from Link headers.

    Per WAC spec: clients MUST NOT derive ACL URI through string manipulation.
    Must use the Link header with rel="acl".
    """
    acl_relative = link_headers.get("acl")
    if not acl_relative:
        return None

    if acl_relative.startswith("http://") or acl_relative.startswith("https://"):
        return acl_relative

    # Resolve relative URL against resource URL
    if acl_relative.startswith("/"):
        # Absolute path — resolve against origin
        from urllib.parse import urlparse
        parsed = urlparse(resource_url)
        return f"{parsed.scheme}://{parsed.netloc}{acl_relative}"

    # Relative path — resolve against resource URL
    if resource_url.endswith("/"):
        return f"{resource_url}{acl_relative}"
    base = resource_url.rsplit("/", 1)[0]
    return f"{base}/{acl_relative}"


def extract_metadata(
    response_headers: dict[str, Any],
    url: str,
) -> dict[str, Any]:
    """Extract Solid-relevant metadata from HTTP response headers.

    Returns a dict with: etag, acl_url, permissions, content_type.
    """
    link_headers = parse_link_headers(response_headers.get("link", ""))
    wac_allow = parse_wac_allow(response_headers.get("wac-allow", ""))

    return {
        "etag": response_headers.get("etag"),
        "acl_url": resolve_acl_url(url, link_headers),
        "permissions": wac_allow if wac_allow else None,
        "content_type": response_headers.get("content-type"),
        "link_headers": link_headers,
    }
