"""Turtle serialization via rdflib. Internal — never exposed in public API."""

from __future__ import annotations

from rdflib import Graph as RDFLibGraph
from rdflib import Literal as RDFLiteral
from rdflib import URIRef
from rdflib.namespace import Namespace as RDFLibNamespace

from pacific_solid._graph.triple import Literal, Triple


def serialize_turtle(triples: list[Triple], base_uri: str | None = None) -> str:
    """Serialize a list of Triples to Turtle format."""
    g = RDFLibGraph()

    # Bind common prefixes for readable output
    g.bind("schema", RDFLibNamespace("http://schema.org/"))
    g.bind("foaf", RDFLibNamespace("http://xmlns.com/foaf/0.1/"))
    g.bind("solid", RDFLibNamespace("http://www.w3.org/ns/solid/terms#"))
    g.bind("acl", RDFLibNamespace("http://www.w3.org/ns/auth/acl#"))
    g.bind("ldp", RDFLibNamespace("http://www.w3.org/ns/ldp#"))
    g.bind("pim", RDFLibNamespace("http://www.w3.org/ns/pim/space#"))
    g.bind("dcterms", RDFLibNamespace("http://purl.org/dc/terms/"))
    g.bind("vcard", RDFLibNamespace("http://www.w3.org/2006/vcard/ns#"))

    for triple in triples:
        g.add(_to_rdflib(triple))

    return g.serialize(format="turtle")


def _to_rdflib(
    triple: Triple,
) -> tuple[URIRef, URIRef, RDFLiteral | URIRef]:
    s = URIRef(triple.subject)
    p = URIRef(triple.predicate)

    obj = triple.object
    o: RDFLiteral | URIRef
    if isinstance(obj, Literal):
        o = RDFLiteral(
            obj.value,
            datatype=URIRef(obj.datatype) if obj.datatype else None,
            lang=obj.language,
        )
    else:
        o = URIRef(str(obj))

    return (s, p, o)
