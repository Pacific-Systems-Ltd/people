"""Linked Data Notifications — inbox discovery, send, and retrieve.

SP-19: Conform to LDN by implementing Sender or Consumer.
SP-20: Discover the location of a resource's Inbox.
SP-21: Send notifications to Inbox or retrieve Inbox contents.
WID-05: Discover Inbox via ldp:inbox in WebID Profile.

Discovery strategy:
1. Check Link header for rel="http://www.w3.org/ns/ldp#inbox"
2. Fall back to ldp:inbox predicate in the resource's RDF representation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from people._graph.graph import Graph
from people._http.errors import raise_for_status
from people._http.headers import extract_metadata, parse_link_headers
from people._rdf.namespaces import LDP
from people._rdf.parse import parse_rdf

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")

_LDP_INBOX_REL = "http://www.w3.org/ns/ldp#inbox"


async def discover_inbox(
    resource_url: str,
    client: AuthenticatedClient,
) -> str | None:
    """Discover the LDN Inbox for a resource (SP-20).

    Tries the Link header first (lightweight), then falls back to
    parsing the RDF body for an ldp:inbox predicate.

    Args:
        resource_url: The URL of the resource or WebID profile.
        client: An authenticated HTTP client.

    Returns:
        The Inbox URL, or None if no Inbox is advertised.
    """
    resp = await client.request(
        "GET", resource_url,
        headers={"Accept": "text/turtle, application/ld+json;q=0.9"},
    )
    if resp.status_code >= 400:
        logger.debug("Cannot discover inbox for %s: HTTP %d", resource_url, resp.status_code)
        return None

    # Strategy 1: Link header
    link_header = resp.headers.get("link", "")
    link_rels = parse_link_headers(link_header)
    if _LDP_INBOX_REL in link_rels:
        inbox_url = _resolve_url(resource_url, link_rels[_LDP_INBOX_REL])
        logger.debug("Discovered inbox via Link header: %s", inbox_url)
        return inbox_url

    # Strategy 2: RDF predicate
    metadata = extract_metadata(dict(resp.headers), resource_url)
    content_type = metadata.get("content_type", "text/turtle")
    triples = parse_rdf(resp.text, content_type, base_uri=resource_url)
    graph = Graph(triples)

    inbox_triples = graph.query(predicate=LDP.inbox)
    if inbox_triples:
        inbox_url = str(inbox_triples[0].object)
        logger.debug("Discovered inbox via RDF predicate: %s", inbox_url)
        return inbox_url

    logger.debug("No inbox found for %s", resource_url)
    return None


async def send_notification(
    inbox_url: str,
    notification: Graph,
    client: AuthenticatedClient,
) -> str:
    """Send a notification to an LDN Inbox (SP-21, Sender).

    POSTs the notification graph as Turtle to the Inbox URL.

    Args:
        inbox_url: The target Inbox URL.
        notification: The notification graph to send.
        client: An authenticated HTTP client.

    Returns:
        The URL of the created notification resource (from Location header).

    Raises:
        SolidError: If the server rejects the notification.
        ValueError: If the server does not return a Location header.
    """
    turtle = notification.to_turtle()
    resp = await client.request(
        "POST", inbox_url,
        content=turtle,
        headers={"Content-Type": "text/turtle"},
    )
    raise_for_status(resp.status_code, inbox_url, resp.text)

    location = resp.headers.get("location")
    if not location:
        raise ValueError(f"Server did not return Location header for POST to {inbox_url}")

    logger.debug("Notification sent to %s, created at %s", inbox_url, location)
    return location


async def list_notifications(
    inbox_url: str,
    client: AuthenticatedClient,
) -> list[str]:
    """Retrieve the contents of an LDN Inbox (SP-21, Consumer).

    GETs the Inbox as an RDF container and extracts ldp:contains URLs.

    Args:
        inbox_url: The Inbox URL.
        client: An authenticated HTTP client.

    Returns:
        List of notification resource URLs.
    """
    resp = await client.request(
        "GET", inbox_url,
        headers={"Accept": "text/turtle, application/ld+json;q=0.9"},
    )
    raise_for_status(resp.status_code, inbox_url, resp.text)

    metadata = extract_metadata(dict(resp.headers), inbox_url)
    content_type = metadata.get("content_type", "text/turtle")
    triples = parse_rdf(resp.text, content_type, base_uri=inbox_url)
    graph = Graph(triples)

    contains = graph.query(predicate=LDP.contains)
    urls = [str(t.object) for t in contains]
    logger.debug("Inbox %s contains %d notifications", inbox_url, len(urls))
    return urls


async def read_notification(
    notification_url: str,
    client: AuthenticatedClient,
) -> Graph:
    """Read a single notification from an LDN Inbox.

    Args:
        notification_url: The URL of the notification resource.
        client: An authenticated HTTP client.

    Returns:
        The notification as a Graph.
    """
    resp = await client.request(
        "GET", notification_url,
        headers={"Accept": "text/turtle, application/ld+json;q=0.9"},
    )
    raise_for_status(resp.status_code, notification_url, resp.text)

    metadata = extract_metadata(dict(resp.headers), notification_url)
    content_type = metadata.get("content_type", "text/turtle")
    triples = parse_rdf(resp.text, content_type, base_uri=notification_url)
    return Graph(triples)


def _resolve_url(base: str, relative: str) -> str:
    """Resolve a potentially relative URL against a base URL."""
    if relative.startswith("http://") or relative.startswith("https://"):
        return relative

    from urllib.parse import urljoin
    return urljoin(base, relative)
