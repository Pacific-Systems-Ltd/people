"""Tests for N3 Patch solid:where clause support (SP-11)."""

import pytest
from pacific_solid._graph.triple import URI, Literal, Triple
from pacific_solid._rdf.patch import build_n3_patch


class TestWhereClause:
    def test_patch_with_where_clause(self):
        inserts = [Triple(URI("?person"), URI("http://example.org/age"), Literal("31"))]
        deletes = [Triple(URI("?person"), URI("http://example.org/age"), Literal("30"))]
        where = [("?person", "http://example.org/name", '"Alice"')]

        result = build_n3_patch(inserts, deletes, where=where)
        assert "solid:where" in result
        assert "?person" in result
        assert "solid:deletes" in result
        assert "solid:inserts" in result

    def test_where_clause_serialization(self):
        inserts = [Triple(URI("?x"), URI("http://example.org/status"), Literal("active"))]
        where = [("?x", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/User")]

        result = build_n3_patch(inserts, [], where=where)
        assert "solid:where" in result
        assert "?x" in result
        assert "<http://example.org/User>" in result

    def test_where_clause_before_deletes_and_inserts(self):
        inserts = [Triple(URI("?s"), URI("http://example.org/p"), Literal("new"))]
        deletes = [Triple(URI("?s"), URI("http://example.org/p"), Literal("old"))]
        where = [("?s", "http://example.org/id", '"123"')]

        result = build_n3_patch(inserts, deletes, where=where)
        where_pos = result.index("solid:where")
        deletes_pos = result.index("solid:deletes")
        inserts_pos = result.index("solid:inserts")
        assert where_pos < deletes_pos < inserts_pos


class TestWhereClauseValidation:
    def test_unbound_variable_in_inserts_raises(self):
        inserts = [Triple(URI("?unbound"), URI("http://example.org/p"), Literal("v"))]
        where = [("?other", "http://example.org/q", '"w"')]

        with pytest.raises(ValueError, match="not bound"):
            build_n3_patch(inserts, [], where=where)

    def test_unbound_variable_in_deletes_raises(self):
        deletes = [Triple(URI("?unbound"), URI("http://example.org/p"), Literal("v"))]
        where = [("?other", "http://example.org/q", '"w"')]

        with pytest.raises(ValueError, match="not bound"):
            build_n3_patch([], deletes, where=where)

    def test_bound_variables_pass(self):
        inserts = [Triple(URI("?person"), URI("http://example.org/age"), Literal("31"))]
        deletes = [Triple(URI("?person"), URI("http://example.org/age"), Literal("30"))]
        where = [("?person", "http://example.org/name", '"Alice"')]

        result = build_n3_patch(inserts, deletes, where=where)
        assert "solid:InsertDeletePatch" in result

    def test_no_where_clause_allows_plain_triples(self):
        inserts = [Triple(URI("http://example.org/s"), URI("http://example.org/p"), Literal("v"))]
        result = build_n3_patch(inserts, [])
        assert "solid:where" not in result

    def test_variable_in_object_position(self):
        inserts = [
            Triple(URI("http://example.org/s"), URI("http://example.org/p"), Literal("?val"))
        ]
        where = [("?val", "http://example.org/q", '"w"')]

        # ?val as a Literal value is not a variable — it's a string that starts with ?
        result = build_n3_patch(inserts, [], where=where)
        assert "solid:InsertDeletePatch" in result


class TestWhereClauseOutput:
    def test_produces_valid_n3_patch_document(self):
        inserts = [Triple(URI("?person"), URI("http://example.org/age"), Literal("31"))]
        deletes = [Triple(URI("?person"), URI("http://example.org/age"), Literal("30"))]
        where = [("?person", "http://example.org/name", '"Alice"')]

        result = build_n3_patch(inserts, deletes, where=where)

        assert result.startswith("@prefix solid:")
        assert "_:patch a solid:InsertDeletePatch;" in result
        assert result.strip().endswith(".")

    def test_insert_only_with_where(self):
        inserts = [Triple(URI("?s"), URI("http://example.org/status"), Literal("done"))]
        where = [("?s", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/Task")]

        result = build_n3_patch(inserts, [], where=where)
        assert "solid:where" in result
        assert "solid:inserts" in result
        assert "solid:deletes" not in result

    def test_delete_only_with_where(self):
        deletes = [Triple(URI("?s"), URI("http://example.org/old"), Literal("val"))]
        where = [("?s", "http://example.org/id", '"abc"')]

        result = build_n3_patch([], deletes, where=where)
        assert "solid:where" in result
        assert "solid:deletes" in result
        assert "solid:inserts" not in result
