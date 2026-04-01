"""WebID profile resolution — discover OIDC issuers and pod storage URLs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from people._graph.graph import Graph
from people._rdf.namespaces import FOAF, PIM, SOLID

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


@dataclass
class WebIDProfile:
    """A resolved WebID profile with OIDC issuers and pod storage URLs."""

    webid: str
    name: str | None = None
    issuers: list[str] = field(default_factory=list)
    storages: list[str] = field(default_factory=list)


async def resolve_webid(webid_url: str, client: AuthenticatedClient) -> WebIDProfile:
    """Resolve a WebID URI to discover OIDC issuers and pod storage URLs.

    Fetches the WebID profile document, parses it as Turtle, and extracts:
    - solid:oidcIssuer values (may be multiple)
    - pim:storage values (pod URLs)
    - foaf:name (if present)
    """
    logger.debug("Resolving WebID: %s", webid_url)

    resp = await client.request("GET", webid_url, headers={"Accept": "text/turtle"})

    if resp.status_code >= 400:
        logger.warning("Failed to resolve WebID %s: HTTP %d", webid_url, resp.status_code)
        return WebIDProfile(webid=webid_url)

    graph = Graph.from_turtle(resp.text, base_uri=webid_url)


    # Extract OIDC issuers
    issuer_triples = graph.query(predicate=SOLID.oidcIssuer)
    issuers = [str(t.object) for t in issuer_triples]

    # Extract storage URLs
    storage_triples = graph.query(predicate=PIM.storage)
    storages = [str(t.object) for t in storage_triples]

    # Extract name
    name_triples = graph.query(predicate=FOAF.name)
    name = str(name_triples[0].object) if name_triples else None

    profile = WebIDProfile(
        webid=webid_url,
        name=name,
        issuers=issuers,
        storages=storages,
    )

    logger.debug(
        "Resolved WebID %s: %d issuers, %d storages", webid_url, len(issuers), len(storages)
    )
    return profile
