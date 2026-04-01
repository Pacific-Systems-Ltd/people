"""Tests for namespace constants."""

from people import SCHEMA, FOAF, ACL, RDF, Namespace, URI


class TestNamespace:
    def test_generates_uri(self):
        assert SCHEMA.name == "http://schema.org/name"

    def test_returns_uri_type(self):
        assert isinstance(SCHEMA.name, URI)

    def test_foaf(self):
        assert FOAF.Person == "http://xmlns.com/foaf/0.1/Person"

    def test_acl(self):
        assert ACL.Read == "http://www.w3.org/ns/auth/acl#Read"

    def test_rdf(self):
        assert RDF.type == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

    def test_custom_namespace(self):
        PAC = Namespace("http://pacific.dev/ontology#")
        assert PAC.Interview == "http://pacific.dev/ontology#Interview"

    def test_repr(self):
        assert "schema.org" in repr(SCHEMA)

    def test_base(self):
        assert SCHEMA.base == "http://schema.org/"
