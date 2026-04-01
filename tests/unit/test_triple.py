"""Tests for Triple, URI, and Literal primitives."""

from people import URI, Literal, Triple


class TestURI:
    def test_is_str(self):
        u = URI("http://example.org/foo")
        assert isinstance(u, str)
        assert u == "http://example.org/foo"

    def test_repr(self):
        u = URI("http://example.org/foo")
        assert repr(u) == "URI('http://example.org/foo')"

    def test_equality_with_str(self):
        u = URI("http://example.org/foo")
        assert u == "http://example.org/foo"

    def test_hashable(self):
        u1 = URI("http://example.org/foo")
        u2 = URI("http://example.org/foo")
        assert hash(u1) == hash(u2)
        assert len({u1, u2}) == 1


class TestLiteral:
    def test_plain_literal(self):
        lit = Literal("hello")
        assert lit.value == "hello"
        assert lit.datatype is None
        assert lit.language is None

    def test_typed_literal(self):
        lit = Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer")
        assert lit.value == "42"
        assert lit.datatype == "http://www.w3.org/2001/XMLSchema#integer"

    def test_language_literal(self):
        lit = Literal("bonjour", language="fr")
        assert lit.language == "fr"

    def test_equality(self):
        a = Literal("hello")
        b = Literal("hello")
        assert a == b

    def test_equality_with_str(self):
        lit = Literal("hello")
        assert lit == "hello"

    def test_typed_not_equal_to_plain_str(self):
        lit = Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer")
        assert lit != "42"

    def test_hashable(self):
        a = Literal("hello")
        b = Literal("hello")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_different_types_not_equal(self):
        a = Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer")
        b = Literal("42", datatype="http://www.w3.org/2001/XMLSchema#string")
        assert a != b

    def test_str(self):
        lit = Literal("hello")
        assert str(lit) == "hello"

    def test_repr(self):
        lit = Literal("hello", language="en")
        assert "language='en'" in repr(lit)


class TestTriple:
    def test_create(self):
        t = Triple(
            URI("http://example.org/alice"),
            URI("http://xmlns.com/foaf/0.1/name"),
            Literal("Alice"),
        )
        assert t.subject == "http://example.org/alice"
        assert t.predicate == "http://xmlns.com/foaf/0.1/name"
        assert t.object == Literal("Alice")

    def test_named_tuple_unpacking(self):
        t = Triple(
            URI("http://example.org/s"),
            URI("http://example.org/p"),
            URI("http://example.org/o"),
        )
        s, p, o = t
        assert s == "http://example.org/s"
        assert p == "http://example.org/p"
        assert o == "http://example.org/o"

    def test_equality(self):
        t1 = Triple(URI("s"), URI("p"), Literal("o"))
        t2 = Triple(URI("s"), URI("p"), Literal("o"))
        assert t1 == t2

    def test_hashable(self):
        t1 = Triple(URI("s"), URI("p"), Literal("o"))
        t2 = Triple(URI("s"), URI("p"), Literal("o"))
        assert len({t1, t2}) == 1
