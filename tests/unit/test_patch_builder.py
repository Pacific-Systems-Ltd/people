"""Tests for N3 Patch builder."""

from people import URI, Literal, Triple
from people._rdf.patch import build_n3_patch


class TestBuildN3Patch:
    def test_insert_only(self):
        inserts = [Triple(URI("http://ex/s"), URI("http://ex/p"), Literal("new"))]
        body = build_n3_patch(inserts, [])
        assert "solid:InsertDeletePatch" in body
        assert "solid:inserts" in body
        assert "solid:deletes" not in body
        assert '"new"' in body

    def test_delete_only(self):
        deletes = [Triple(URI("http://ex/s"), URI("http://ex/p"), Literal("old"))]
        body = build_n3_patch([], deletes)
        assert "solid:deletes" in body
        assert "solid:inserts" not in body
        assert '"old"' in body

    def test_insert_and_delete(self):
        inserts = [Triple(URI("http://ex/s"), URI("http://ex/p"), Literal("new"))]
        deletes = [Triple(URI("http://ex/s"), URI("http://ex/p"), Literal("old"))]
        body = build_n3_patch(inserts, deletes)
        assert "solid:inserts" in body
        assert "solid:deletes" in body
        assert '"new"' in body
        assert '"old"' in body

    def test_uri_object(self):
        inserts = [Triple(URI("http://ex/s"), URI("http://ex/p"), URI("http://ex/o"))]
        body = build_n3_patch(inserts, [])
        assert "<http://ex/o>" in body

    def test_typed_literal(self):
        inserts = [
            Triple(
                URI("http://ex/s"),
                URI("http://ex/p"),
                Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer"),
            )
        ]
        body = build_n3_patch(inserts, [])
        assert "^^<http://www.w3.org/2001/XMLSchema#integer>" in body

    def test_language_literal(self):
        inserts = [
            Triple(URI("http://ex/s"), URI("http://ex/p"), Literal("bonjour", language="fr"))
        ]
        body = build_n3_patch(inserts, [])
        assert "@fr" in body

    def test_escapes_quotes(self):
        inserts = [Triple(URI("http://ex/s"), URI("http://ex/p"), Literal('say "hello"'))]
        body = build_n3_patch(inserts, [])
        assert '\\"hello\\"' in body
