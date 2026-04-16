"""RDF vocabulary namespace constants.

Usage:
    from pacific_solid._rdf.namespaces import SCHEMA, FOAF, ACL

    SCHEMA.name      -> URI("http://schema.org/name")
    FOAF.Person      -> URI("http://xmlns.com/foaf/0.1/Person")
    ACL.Read         -> URI("http://www.w3.org/ns/auth/acl#Read")
"""

from __future__ import annotations

from pacific_solid._graph.triple import URI


class Namespace:
    """A namespace prefix that generates URIs on attribute access."""

    __slots__ = ("_base",)

    def __init__(self, base: str) -> None:
        self._base = base

    def __getattr__(self, name: str) -> URI:
        return URI(f"{self._base}{name}")

    def __repr__(self) -> str:
        return f"Namespace({self._base!r})"

    @property
    def base(self) -> str:
        return self._base


# W3C / Solid Protocol vocabularies
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
LDP = Namespace("http://www.w3.org/ns/ldp#")
SOLID = Namespace("http://www.w3.org/ns/solid/terms#")
ACL = Namespace("http://www.w3.org/ns/auth/acl#")
PIM = Namespace("http://www.w3.org/ns/pim/space#")

# Common vocabularies
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("http://schema.org/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
