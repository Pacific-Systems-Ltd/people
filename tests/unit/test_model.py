"""Tests for @ps.model decorator, ps.field(), and dirty tracking."""

import pacific_solid as ps
import pytest
from pacific_solid import FOAF, RDF, SCHEMA, URI, Graph, Literal


@ps.model
class Note:
    rdf_type = SCHEMA.NoteDigitalDocument
    title: str = ps.field(SCHEMA.name)
    body: str = ps.field(SCHEMA.text)
    tags: list[str] = ps.field(SCHEMA.keywords, multiple=True)


@ps.model
class Person:
    rdf_type = FOAF.Person
    name: str = ps.field(FOAF.name)
    email: str = ps.field(FOAF.mbox)
    knows: list[str] = ps.field(FOAF.knows, multiple=True)


class TestModelCreation:
    def test_create_from_kwargs(self):
        note = Note(title="Hello", body="World", tags=["solid", "python"])
        assert note.title == "Hello"
        assert note.body == "World"
        assert note.tags == ["solid", "python"]

    def test_defaults_none_and_empty_list(self):
        note = Note()
        assert note.title is None
        assert note.body is None
        assert note.tags == []

    def test_repr(self):
        note = Note(title="Hello")
        assert "title='Hello'" in repr(note)
        assert "Note(" in repr(note)


class TestModelToGraph:
    def test_graph_has_rdf_type(self):
        note = Note(title="Hello")
        g = note.graph
        type_triples = g.query(predicate=URI(str(RDF.type)))
        assert len(type_triples) == 1
        assert str(type_triples[0].object) == str(SCHEMA.NoteDigitalDocument)

    def test_graph_has_scalar_field(self):
        note = Note(title="Hello", body="World")
        g = note.graph
        title_triples = g.query(predicate=URI(str(SCHEMA.name)))
        assert len(title_triples) == 1
        assert title_triples[0].object == Literal("Hello")

    def test_graph_has_multiple_field(self):
        note = Note(tags=["a", "b", "c"])
        g = note.graph
        tag_triples = g.query(predicate=URI(str(SCHEMA.keywords)))
        assert len(tag_triples) == 3

    def test_none_fields_omitted(self):
        note = Note(title="Hello")
        g = note.graph
        body_triples = g.query(predicate=URI(str(SCHEMA.text)))
        assert len(body_triples) == 0

    def test_empty_list_omitted(self):
        note = Note(title="Hello", tags=[])
        g = note.graph
        tag_triples = g.query(predicate=URI(str(SCHEMA.keywords)))
        assert len(tag_triples) == 0

    def test_default_subject_is_empty_iri(self):
        """A new model with no explicit subject uses `<>`, not a blank node.

        The empty IRI reference resolves against the document's base IRI
        when the serialised Turtle is parsed, producing a self-identifying
        document at its eventual URL.
        """
        note = Note(title="Hello")
        subjects = {t.subject for t in note.graph.triples}
        assert subjects == {URI("")}

    def test_default_subject_serialises_as_empty_iri(self):
        """The serialised Turtle uses `<>` for the default subject."""
        note = Note(title="Hello")
        turtle = note.graph.to_turtle()
        assert "<>" in turtle

    def test_explicit_subject_overrides_default(self):
        """Setting _ps_subject before reading .graph uses that URI."""
        note = Note(title="Hello")
        note._ps_subject = "http://pod.example/notes/1"
        subjects = {t.subject for t in note.graph.triples}
        assert subjects == {URI("http://pod.example/notes/1")}


class TestModelFromGraph:
    def _make_note_graph(self) -> Graph:
        subject = URI("http://pod.example/notes/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(SCHEMA.NoteDigitalDocument)))
        g.add(subject, URI(str(SCHEMA.name)), Literal("Test Note"))
        g.add(subject, URI(str(SCHEMA.text)), Literal("The body."))
        g.add(subject, URI(str(SCHEMA.keywords)), Literal("solid"))
        g.add(subject, URI(str(SCHEMA.keywords)), Literal("python"))
        return g

    def test_from_graph_extracts_fields(self):
        g = self._make_note_graph()
        note = Note.from_graph(g)
        assert note.title == "Test Note"
        assert note.body == "The body."
        assert set(note.tags) == {"solid", "python"}

    def test_from_graph_preserves_subject(self):
        g = self._make_note_graph()
        note = Note.from_graph(g)
        assert note._ps_subject == "http://pod.example/notes/1"

    def test_from_graph_missing_field_is_none(self):
        subject = URI("http://pod.example/notes/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(SCHEMA.NoteDigitalDocument)))
        g.add(subject, URI(str(SCHEMA.name)), Literal("Title Only"))
        note = Note.from_graph(g)
        assert note.title == "Title Only"
        assert note.body is None
        assert note.tags == []

    def test_from_graph_strict_type_mismatch(self):
        subject = URI("http://pod.example/people/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(FOAF.Person)))
        g.add(subject, URI(str(SCHEMA.name)), Literal("Alice"))
        with pytest.raises(ps.ModelTypeMismatchError):
            Note.from_graph(g, strict=True)

    def test_from_graph_non_strict(self):
        subject = URI("http://pod.example/people/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(FOAF.Person)))
        g.add(subject, URI(str(SCHEMA.name)), Literal("Alice"))
        note = Note.from_graph(g, strict=False)
        assert note.title == "Alice"


class TestModelDirtyTracking:
    def _make_note_graph(self) -> Graph:
        subject = URI("http://pod.example/notes/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(SCHEMA.NoteDigitalDocument)))
        g.add(subject, URI(str(SCHEMA.name)), Literal("Original"))
        g.add(subject, URI(str(SCHEMA.text)), Literal("Body"))
        g.url = "http://pod.example/notes/1"
        g.etag = '"etag-123"'
        return g

    def test_no_changes_empty_diff(self):
        g = self._make_note_graph()
        note = Note.from_graph(g)
        inserts, deletes = note.graph.diff()
        assert inserts == []
        assert deletes == []

    def test_scalar_change_produces_diff(self):
        g = self._make_note_graph()
        note = Note.from_graph(g)
        note.title = "Updated"
        inserts, deletes = note.graph.diff()
        assert len(inserts) == 1
        assert len(deletes) == 1
        assert inserts[0].object == Literal("Updated")
        assert deletes[0].object == Literal("Original")

    def test_list_append_produces_diff(self):
        subject = URI("http://pod.example/notes/1")
        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(str(SCHEMA.NoteDigitalDocument)))
        g.add(subject, URI(str(SCHEMA.keywords)), Literal("solid"))
        note = Note.from_graph(g)
        note.tags.append("python")
        inserts, deletes = note.graph.diff()
        assert len(inserts) == 1
        assert inserts[0].object == Literal("python")

    def test_graph_preserves_metadata(self):
        g = self._make_note_graph()
        note = Note.from_graph(g)
        result = note.graph
        assert result.url == "http://pod.example/notes/1"
        assert result.etag == '"etag-123"'
        assert result.has_snapshot


class TestModelNoRdfType:
    def test_missing_rdf_type_raises(self):
        with pytest.raises(TypeError, match="must define rdf_type"):
            @ps.model
            class Bad:
                name: str = ps.field(SCHEMA.name)


class TestGrantModel:
    def test_grant_is_a_model(self):
        assert hasattr(ps.Grant, "_ps_fields")
        assert hasattr(ps.Grant, "_ps_rdf_type")

    def test_create_grant(self):
        grant = ps.Grant(
            agent="http://pod/dr-patel/card#me",
            resource="http://pod/alice/health",
            modes=["http://www.w3.org/ns/auth/acl#Read"],
        )
        assert grant.agent == "http://pod/dr-patel/card#me"
        assert len(grant.modes) == 1

    def test_grant_from_acl_graph(self):
        from pacific_solid._rdf.namespaces import ACL

        g = Graph()
        rule = URI("http://pod/alice/.acl#rule1")
        g.add(rule, URI(str(RDF.type)), ACL.Authorization)
        g.add(rule, ACL.agent, URI("http://pod/dr-patel/card#me"))
        g.add(rule, ACL.accessTo, URI("http://pod/alice/health"))
        g.add(rule, ACL.mode, ACL.Read)

        grants = g.all(ps.Grant)
        assert len(grants) == 1
        assert grants[0].agent == "http://pod/dr-patel/card#me"
        assert str(ACL.Read) in grants[0].modes
