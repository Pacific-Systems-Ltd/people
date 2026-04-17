"""Subscription safety checks (NOT-13, NOT-14).

NOT-13: Clients SHOULD NOT send subscription requests to untrusted services,
        including localhost or loopback addresses.
NOT-14: Clients SHOULD minimise information exposure in subscription requests.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from pacific_solid._http.errors import SolidError

logger = logging.getLogger("people")

_PRIVATE_RANGES = [
    ("10.", "10."),
    ("172.16.", "172.31."),
    ("192.168.", "192.168."),
]

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def validate_subscription_target(url: str) -> None:
    """Reject subscription targets that point to localhost or private networks (NOT-13).

    This prevents SSRF attacks where a malicious server advertises a subscription
    service on an internal network address, tricking the client into making
    requests to internal resources.

    Raises:
        SolidError: If the URL targets a loopback or private address.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in _LOOPBACK_HOSTS:
        raise SolidError(
            f"Refusing to subscribe to loopback address {url}. "
            f"Per Solid Notifications spec, subscriptions to localhost are discouraged.",
            status_code=0,
            url=url,
        )

    # Check private IP ranges
    if _is_private_ip(hostname):
        raise SolidError(
            f"Refusing to subscribe to private network address {url}. "
            f"Per Solid Notifications spec, subscriptions to untrusted services are discouraged.",
            status_code=0,
            url=url,
        )

    # Check for non-TLS (except localhost, which we already rejected)
    if parsed.scheme == "http":
        logger.warning(
            "Subscription target %s uses HTTP, not HTTPS. "
            "Consider using a secure endpoint.",
            url,
        )


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname is a private IPv4 address."""
    if hostname.startswith("10."):
        return True
    if hostname.startswith("192.168."):
        return True
    if hostname.startswith("169.254."):
        return True
    # 172.16.0.0 - 172.31.255.255
    if hostname.startswith("172."):
        parts = hostname.split(".")
        if len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
            except ValueError:
                pass
    return False


def strip_excess_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove non-essential fields from a subscription request (NOT-14).

    Keeps only the fields required by the Notification Channel Data Model:
    @context, type, and topic. Removes any extra information that could
    be used to track the subscriber.
    """
    required_keys = {"@context", "type", "topic"}
    return {k: v for k, v in payload.items() if k in required_keys}
