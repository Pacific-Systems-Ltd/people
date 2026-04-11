"""Notification channel discovery (NOT-01, NOT-02).

Discovers available notification channels for a resource or storage by
following describedby Link relations and parsing JSON-LD description resources.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from people._http.headers import parse_link_headers

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


@dataclass
class ChannelInfo:
    """A notification channel available for subscription."""

    subscription_url: str
    channel_type: str
    features: list[str] = field(default_factory=list)


async def discover_channels(
    resource_url: str,
    client: AuthenticatedClient,
) -> list[ChannelInfo]:
    """Discover notification channels available for a resource (NOT-01).

    Follows the describedby or solid:storageDescription Link relation
    to find a description resource, then parses it as JSON-LD (NOT-02)
    to extract subscription services and channel types.

    Args:
        resource_url: URL of the resource to subscribe to.
        client: An authenticated HTTP client.

    Returns:
        List of available ChannelInfo objects.
    """
    # Step 1: Find the description resource via Link header
    resp = await client.request("HEAD", resource_url)
    if resp.status_code >= 400:
        logger.debug("Cannot discover channels for %s: HTTP %d", resource_url, resp.status_code)
        return []

    link_header = resp.headers.get("link", "")
    links = parse_link_headers(link_header)

    desc_url = links.get("describedby") or links.get(
        "http://www.w3.org/ns/solid/terms#storageDescription"
    )
    if not desc_url:
        logger.debug("No describedby or storageDescription link for %s", resource_url)
        return []

    # Resolve relative URL
    if not desc_url.startswith("http"):
        from urllib.parse import urljoin
        desc_url = urljoin(resource_url, desc_url)

    # Step 2: Fetch the description resource as JSON-LD (NOT-02)
    desc_resp = await client.request(
        "GET", desc_url,
        headers={"Accept": "application/ld+json"},
    )
    if desc_resp.status_code >= 400:
        logger.debug(
            "Failed to fetch description resource %s: HTTP %d",
            desc_url, desc_resp.status_code,
        )
        return []

    # Step 3: Parse the JSON-LD response
    try:
        data = json.loads(desc_resp.text)
    except json.JSONDecodeError:
        logger.debug("Description resource %s is not valid JSON", desc_url)
        return []

    return _extract_channels(data)


def _extract_channels(data: dict | list) -> list[ChannelInfo]:
    """Extract channel info from a JSON-LD description resource."""
    channels: list[ChannelInfo] = []

    # Handle both single object and array
    items = data if isinstance(data, list) else [data]

    for item in items:
        # Look for subscription services in the description
        subscriptions = item.get("subscription", [])
        if isinstance(subscriptions, dict):
            subscriptions = [subscriptions]

        for sub in subscriptions:
            sub_url = sub.get("id") or sub.get("@id", "")
            channel_type = sub.get("channelType", "")
            if isinstance(channel_type, dict):
                channel_type = channel_type.get("@id", channel_type.get("id", ""))
            features = sub.get("feature", [])
            if isinstance(features, str):
                features = [features]

            if sub_url:
                channels.append(ChannelInfo(
                    subscription_url=sub_url,
                    channel_type=str(channel_type),
                    features=[str(f) for f in features],
                ))

        # Also check for direct channel entries
        direct_channels = item.get("channel", [])
        if isinstance(direct_channels, dict):
            direct_channels = [direct_channels]

        for ch in direct_channels:
            ch_type = ch.get("type", ch.get("@type", ""))
            if isinstance(ch_type, list):
                ch_type = ch_type[0] if ch_type else ""
            sub_url = ch.get("id") or ch.get("@id", "")
            if sub_url:
                channels.append(ChannelInfo(
                    subscription_url=sub_url,
                    channel_type=str(ch_type),
                ))

    return channels
