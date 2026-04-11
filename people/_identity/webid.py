"""WebID profile resolution — discover OIDC issuers, pod storage, inbox, and more."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from people._graph.graph import Graph
from people._http.headers import extract_metadata
from people._rdf.namespaces import FOAF, LDP, PIM, RDFS, SOLID
from people._rdf.parse import parse_rdf

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


@dataclass
class WebIDProfile:
    """A resolved WebID profile with OIDC issuers, pod storage, inbox, and more.

    Per WebID Profile spec Section 3.1, the profile document is expected to contain:
    - solid:oidcIssuer — OIDC identity providers
    - pim:storage — pod storage root URLs
    - ldp:inbox — LDN notification inbox
    - pim:preferencesFile — user preferences document
    - rdfs:seeAlso — links to extended profile documents
    - foaf:name — display name
    """

    webid: str
    name: str | None = None
    issuers: list[str] = field(default_factory=list)
    storages: list[str] = field(default_factory=list)
    inbox: str | None = None
    preferences_file: str | None = None
    see_also: list[str] = field(default_factory=list)


async def resolve_webid(webid_url: str, client: AuthenticatedClient) -> WebIDProfile:
    """Resolve a WebID URI to discover OIDC issuers, pod storage, inbox, and more.

    Fetches the WebID profile document with content negotiation for both
    text/turtle and application/ld+json (WID-01), and extracts:
    - solid:oidcIssuer values (may be multiple)
    - pim:storage values (pod URLs)
    - ldp:inbox (notification inbox, WID-05)
    - pim:preferencesFile (user preferences, WID-02)
    - rdfs:seeAlso (extended profile links, WID-02)
    - foaf:name (if present)
    """
    logger.debug("Resolving WebID: %s", webid_url)

    resp = await client.request(
        "GET", webid_url,
        headers={"Accept": "text/turtle, application/ld+json;q=0.9"},
    )

    if resp.status_code >= 400:
        logger.warning("Failed to resolve WebID %s: HTTP %d", webid_url, resp.status_code)
        return WebIDProfile(webid=webid_url)

    metadata = extract_metadata(dict(resp.headers), webid_url)
    content_type = metadata.get("content_type", "text/turtle")
    triples = parse_rdf(resp.text, content_type, base_uri=webid_url)
    graph = Graph(triples)

    # Extract OIDC issuers
    issuer_triples = graph.query(predicate=SOLID.oidcIssuer)
    issuers = [str(t.object) for t in issuer_triples]

    # Extract storage URLs
    storage_triples = graph.query(predicate=PIM.storage)
    storages = [str(t.object) for t in storage_triples]

    # Extract name
    name_triples = graph.query(predicate=FOAF.name)
    name = str(name_triples[0].object) if name_triples else None

    # Extract inbox (LDN endpoint, WID-05)
    inbox_triples = graph.query(predicate=LDP.inbox)
    inbox = str(inbox_triples[0].object) if inbox_triples else None

    # Extract preferences file (WID-02)
    prefs_triples = graph.query(predicate=PIM.preferencesFile)
    preferences_file = str(prefs_triples[0].object) if prefs_triples else None

    # Extract extended profile links (WID-02)
    see_also_triples = graph.query(predicate=RDFS.seeAlso)
    primary_topic_triples = graph.query(predicate=FOAF.isPrimaryTopicOf)
    see_also = [str(t.object) for t in see_also_triples + primary_topic_triples]

    profile = WebIDProfile(
        webid=webid_url,
        name=name,
        issuers=issuers,
        storages=storages,
        inbox=inbox,
        preferences_file=preferences_file,
        see_also=see_also,
    )

    logger.debug(
        "Resolved WebID %s: %d issuers, %d storages, inbox=%s",
        webid_url, len(issuers), len(storages), inbox,
    )
    return profile
