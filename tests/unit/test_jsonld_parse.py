"""Tests for JSON-LD parsing and content-type dispatching (SP-16)."""

from pacific_solid._graph.triple import URI
from pacific_solid._rdf.parse import parse_jsonld, parse_rdf


class TestParseJsonLD:
    def test_simple_jsonld(self):
        data = '''
        {
            "@id": "http://example.org/alice",
            "http://xmlns.com/foaf/0.1/name": "Alice"
        }
        '''
        triples = parse_jsonld(data)
        assert len(triples) == 1
        assert triples[0].subject == URI("http://example.org/alice")
        assert triples[0].predicate == URI("http://xmlns.com/foaf/0.1/name")
        assert str(triples[0].object) == "Alice"

    def test_jsonld_with_context(self):
        data = '''
        {
            "@context": {"foaf": "http://xmlns.com/foaf/0.1/"},
            "@id": "http://example.org/bob",
            "foaf:name": "Bob",
            "foaf:mbox": "bob@example.org"
        }
        '''
        triples = parse_jsonld(data)
        assert len(triples) == 2
        predicates = {str(t.predicate) for t in triples}
        assert "http://xmlns.com/foaf/0.1/name" in predicates
        assert "http://xmlns.com/foaf/0.1/mbox" in predicates

    def test_jsonld_with_base_uri(self):
        data = '''
        {
            "@id": "",
            "http://xmlns.com/foaf/0.1/name": "Carol"
        }
        '''
        triples = parse_jsonld(data, base_uri="http://example.org/carol")
        assert len(triples) == 1
        assert triples[0].subject == URI("http://example.org/carol")

    def test_jsonld_array(self):
        data = '''
        [{
            "@id": "http://example.org/a",
            "http://schema.org/name": "A"
        }, {
            "@id": "http://example.org/b",
            "http://schema.org/name": "B"
        }]
        '''
        triples = parse_jsonld(data)
        assert len(triples) == 2

    def test_empty_jsonld(self):
        triples = parse_jsonld("{}")
        assert len(triples) == 0


class TestParseRdfDispatcher:
    def test_dispatches_to_turtle(self):
        data = '<http://example.org/x> <http://schema.org/name> "X" .'
        triples = parse_rdf(data, "text/turtle")
        assert len(triples) == 1
        assert triples[0].subject == URI("http://example.org/x")

    def test_dispatches_to_jsonld(self):
        data = '{"@id": "http://example.org/y", "http://schema.org/name": "Y"}'
        triples = parse_rdf(data, "application/ld+json")
        assert len(triples) == 1
        assert triples[0].subject == URI("http://example.org/y")

    def test_handles_content_type_with_charset(self):
        data = '{"@id": "http://example.org/z", "http://schema.org/name": "Z"}'
        triples = parse_rdf(data, "application/ld+json; charset=utf-8")
        assert len(triples) == 1

    def test_defaults_to_turtle(self):
        data = '<http://example.org/w> <http://schema.org/name> "W" .'
        triples = parse_rdf(data, "text/plain")
        assert len(triples) == 1

    def test_turtle_and_jsonld_produce_same_triples(self):
        turtle = '<http://example.org/s> <http://schema.org/name> "Test" .'
        jsonld = '{"@id": "http://example.org/s", "http://schema.org/name": "Test"}'
        turtle_triples = parse_rdf(turtle, "text/turtle")
        jsonld_triples = parse_rdf(jsonld, "application/ld+json")
        assert len(turtle_triples) == len(jsonld_triples) == 1
        assert str(turtle_triples[0].subject) == str(jsonld_triples[0].subject)
        assert str(turtle_triples[0].predicate) == str(jsonld_triples[0].predicate)
