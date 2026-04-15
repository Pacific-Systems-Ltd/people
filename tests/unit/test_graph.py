"""Tests for Graph — the core data primitive."""

import pytest
from people import FOAF, RDF, SCHEMA, URI, Graph, Literal, Triple


def _alice_graph() -> Graph:
    """Create a test graph with Alice's data."""
    g = Graph()
    alice = URI("http://example.org/alice")
    g.add(alice, RDF.type, FOAF.Person)
    g.add(alice, FOAF.name, Literal("Alice"))
    g.add(alice, FOAF.mbox, Literal("alice@example.org"))
    g.add(alice, FOAF.knows, URI("http://example.org/bob"))
    return g


class TestGraphBasics:
    def test_empty_graph(self):
        g = Graph()
        assert len(g) == 0
        assert not g
        assert g.triples == []

    def test_add_triples(self):
        g = _alice_graph()
        assert len(g) == 4
        assert g

    def test_add_duplicate_ignored(self):
        g = Graph()
        g.add(URI("s"), URI("p"), Literal("o"))
        g.add(URI("s"), URI("p"), Literal("o"))
        assert len(g) == 1

    def test_remove_triple(self):
        g = _alice_graph()
        alice = URI("http://example.org/alice")
        g.remove(alice, FOAF.mbox, Literal("alice@example.org"))
        assert len(g) == 3

    def test_remove_nonexistent_is_noop(self):
        g = _alice_graph()
        g.remove(URI("nonexistent"), URI("p"), Literal("o"))
        assert len(g) == 4

    def test_contains(self):
        g = _alice_graph()
        alice = URI("http://example.org/alice")
        assert Triple(alice, FOAF.name, Literal("Alice")) in g
        assert Triple(alice, FOAF.name, Literal("Bob")) not in g

    def test_subjects(self):
        g = _alice_graph()
        assert g.subjects == {URI("http://example.org/alice")}

    def test_predicates(self):
        g = _alice_graph()
        assert FOAF.name in g.predicates
        assert FOAF.knows in g.predicates

    def test_repr(self):
        g = _alice_graph()
        assert "4 triples" in repr(g)


class TestGraphQuery:
    def test_query_by_predicate(self):
        g = _alice_graph()
        results = g.query(predicate=FOAF.name)
        assert len(results) == 1
        assert results[0].object == Literal("Alice")

    def test_query_by_subject(self):
        g = _alice_graph()
        results = g.query(subject=URI("http://example.org/alice"))
        assert len(results) == 4

    def test_query_by_value_string(self):
        g = _alice_graph()
        results = g.query(value="Alice")
        assert len(results) == 1

    def test_query_by_predicate_and_value(self):
        g = _alice_graph()
        results = g.query(predicate=FOAF.name, value="Alice")
        assert len(results) == 1

    def test_query_no_match(self):
        g = _alice_graph()
        results = g.query(predicate=SCHEMA.name)
        assert len(results) == 0

    def test_query_by_uri_value(self):
        g = _alice_graph()
        bob = URI("http://example.org/bob")
        results = g.query(predicate=FOAF.knows, value=bob)
        assert len(results) == 1


class TestGraphSnapshot:
    def test_no_snapshot_by_default(self):
        g = _alice_graph()
        assert not g.has_snapshot

    def test_take_snapshot(self):
        g = _alice_graph()
        g.take_snapshot()
        assert g.has_snapshot

    def test_diff_no_changes(self):
        g = _alice_graph()
        g.take_snapshot()
        inserts, deletes = g.diff()
        assert inserts == []
        assert deletes == []

    def test_diff_insert(self):
        g = _alice_graph()
        g.take_snapshot()
        g.add(URI("http://example.org/alice"), FOAF.age, Literal("30"))
        inserts, deletes = g.diff()
        assert len(inserts) == 1
        assert len(deletes) == 0
        assert inserts[0].predicate == FOAF.age

    def test_diff_delete(self):
        g = _alice_graph()
        g.take_snapshot()
        g.remove(URI("http://example.org/alice"), FOAF.mbox, Literal("alice@example.org"))
        inserts, deletes = g.diff()
        assert len(inserts) == 0
        assert len(deletes) == 1

    def test_diff_modify(self):
        g = _alice_graph()
        g.take_snapshot()
        alice = URI("http://example.org/alice")
        g.remove(alice, FOAF.name, Literal("Alice"))
        g.add(alice, FOAF.name, Literal("Alice Smith"))
        inserts, deletes = g.diff()
        assert len(inserts) == 1
        assert len(deletes) == 1

    def test_diff_without_snapshot_raises(self):
        g = _alice_graph()
        with pytest.raises(ValueError):
            g.diff()

    def test_reset_snapshot(self):
        g = _alice_graph()
        g.take_snapshot()
        g.add(URI("http://example.org/alice"), FOAF.age, Literal("30"))
        g.reset_snapshot()
        inserts, deletes = g.diff()
        assert inserts == []
        assert deletes == []


class TestGraphTurtle:
    def test_round_trip(self):
        g = _alice_graph()
        turtle = g.to_turtle()
        assert "Alice" in turtle
        g2 = Graph.from_turtle(turtle)
        assert len(g2) == len(g)

    def test_from_turtle(self):
        data = """
        @prefix foaf: <http://xmlns.com/foaf/0.1/>.
        <http://example.org/alice> foaf:name "Alice" .
        """
        g = Graph.from_turtle(data)
        assert len(g) == 1
        assert g.query(predicate=FOAF.name)[0].object == Literal("Alice")


class TestGraphConverters:
    def test_to_dict_round_trip(self):
        g = _alice_graph()
        d = g.to_dict()
        assert len(d) == 4
        g2 = Graph.from_dict(d)
        assert len(g2) == 4

    def test_to_dict_literal(self):
        g = Graph()
        g.add(URI("s"), URI("p"), Literal("hello", language="en"))
        d = g.to_dict()
        assert d[0]["object"]["type"] == "literal"
        assert d[0]["object"]["language"] == "en"

    def test_to_dict_uri(self):
        g = Graph()
        g.add(URI("s"), URI("p"), URI("o"))
        d = g.to_dict()
        assert d[0]["object"]["type"] == "uri"
        assert d[0]["object"]["value"] == "o"
