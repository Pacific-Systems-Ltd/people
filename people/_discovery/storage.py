"""Storage discovery — find the root of a Solid pod.

Two strategies per Solid Protocol Section 3:

1. RDF-based (SP-18): fetch a resource and look for pim:storage triples.
2. Link-header traversal (SP-17): walk up the URI path hierarchy, issuing
   HEAD requests and checking for a Link header with rel="type" targeting
   http://www.w3.org/ns/pim/space#Storage.

discover_storage() tries RDF-based first, then falls back to traversal.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from people._http.headers import parse_link_headers_multi
from people._rdf.namespaces import PIM

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")

_PIM_STORAGE_TYPE = "http://www.w3.org/ns/pim/space#Storage"


async def discover_storage(
    url: str,
    client: AuthenticatedClient,
) -> str | None:
    """Discover the storage root for a resource URL.

    Tries RDF-based discovery first (faster, works cross-origin), then falls
    back to Link-header hierarchy traversal.

    Args:
        url: Any resource URL within a pod.
        client: An authenticated HTTP client.

    Returns:
        The storage root URL, or None if discovery fails.
    """
    # Strategy 1: RDF-based (SP-18)
    result = await _discover_storage_by_rdf(url, client)
    if result:
        return result

    # Strategy 2: Link-header traversal (SP-17)
    return await _discover_storage_by_link(url, client)


async def _discover_storage_by_rdf(
    url: str,
    client: AuthenticatedClient,
) -> str | None:
    """Discover storage by fetching a resource and checking for pim:storage triples."""
    from people._rdf.parse import parse_rdf

    resp = await client.request(
        "GET", url,
        headers={"Accept": "text/turtle, application/ld+json;q=0.9"},
    )
    if resp.status_code >= 400:
        return None

    content_type = resp.headers.get("content-type", "text/turtle")
    try:
        from people._graph.graph import Graph
        triples = parse_rdf(resp.text, content_type, base_uri=url)
        graph = Graph(triples)
        storage_triples = graph.query(predicate=PIM.storage)
        if storage_triples:
            storage_url = str(storage_triples[0].object)
            logger.debug("Discovered storage via RDF: %s", storage_url)
            return storage_url
    except Exception:
        logger.debug("RDF-based storage discovery failed for %s", url)

    return None


async def _discover_storage_by_link(
    url: str,
    client: AuthenticatedClient,
) -> str | None:
    """Walk up the URI path hierarchy, checking Link headers for pim:Storage type.

    Issues HEAD requests at each level to minimise bandwidth. Stops when a
    response includes a Link header with rel="type" targeting pim:Storage,
    or when the path is exhausted.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # If the URL already ends with /, it's a container — start here.
    # Otherwise start from the parent container.
    path = parsed.path
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0]
    path = path.rstrip("/")

    # Walk up from current container to root
    while True:
        check_url = f"{origin}{path}/" if path else f"{origin}/"

        resp = await client.request("HEAD", check_url)
        if resp.status_code < 400:
            link_header = resp.headers.get("link", "")
            type_uris = parse_link_headers_multi(link_header).get("type", [])
            if _PIM_STORAGE_TYPE in type_uris:
                logger.debug("Discovered storage via Link traversal: %s", check_url)
                return check_url

        if not path:
            break
        # Move up one level
        path = path.rsplit("/", 1)[0]

    logger.debug("Storage discovery failed for %s", url)
    return None
