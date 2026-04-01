"""Turtle parsing via rdflib. Internal — never exposed in public API."""

from __future__ import annotations

from rdflib import Graph as RDFLibGraph
from rdflib import Literal as RDFLiteral
from rdflib.term import Node

from people._graph.triple import URI, Literal, Triple


def parse_turtle(data: str, base_uri: str | None = None) -> list[Triple]:
    """Parse a Turtle string into a list of Triples."""
    g = RDFLibGraph()
    g.parse(data=data, format="turtle", publicID=base_uri)
    return [_convert_triple(s, p, o) for s, p, o in g]


def _convert_triple(s: Node, p: Node, o: Node) -> Triple:
    subject = URI(str(s))
    predicate = URI(str(p))

    if isinstance(o, RDFLiteral):
        obj = Literal(
            str(o),
            datatype=str(o.datatype) if o.datatype else None,
            language=o.language,
        )
    else:
        obj = URI(str(o))

    return Triple(subject, predicate, obj)
