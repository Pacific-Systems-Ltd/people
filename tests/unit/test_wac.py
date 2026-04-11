"""Tests for WAC evaluation — server-side building block."""

from people import URI, Graph, evaluate_wac
from people._rdf.namespaces import ACL, FOAF, RDF


def _make_acl(
    agent: str | None = None,
    agent_class: str | None = None,
    resource: str | None = None,
    modes: list[str] | None = None,
) -> Graph:
    """Build a minimal ACL graph for testing."""
    g = Graph()
    rule = URI("http://pod/.acl#rule1")
    g.add(rule, URI(str(RDF.type)), ACL.Authorization)

    if agent:
        g.add(rule, ACL.agent, URI(agent))
    if agent_class:
        g.add(rule, ACL.agentClass, URI(agent_class))
    if resource:
        g.add(rule, ACL.accessTo, URI(resource))
    if modes:
        for mode in modes:
            g.add(rule, ACL.mode, URI(mode))
    return g


class TestEvaluateWac:
    def test_agent_read_granted(self):
        acl = _make_acl(
            agent="http://pod/alice/card#me",
            resource="http://pod/data/record",
            modes=[str(ACL.Read)],
        )
        assert evaluate_wac("http://pod/alice/card#me", acl, "GET", "http://pod/data/record")

    def test_agent_not_granted(self):
        acl = _make_acl(
            agent="http://pod/bob/card#me",
            resource="http://pod/data/record",
            modes=[str(ACL.Read)],
        )
        assert not evaluate_wac("http://pod/alice/card#me", acl, "GET", "http://pod/data/record")

    def test_wrong_mode_denied(self):
        acl = _make_acl(
            agent="http://pod/alice/card#me",
            resource="http://pod/data/record",
            modes=[str(ACL.Read)],
        )
        assert not evaluate_wac("http://pod/alice/card#me", acl, "PUT", "http://pod/data/record")

    def test_write_implies_append(self):
        """WAC spec: Append is a subclass of Write."""
        acl = _make_acl(
            agent="http://pod/alice/card#me",
            resource="http://pod/data/record",
            modes=[str(ACL.Write)],
        )
        assert evaluate_wac("http://pod/alice/card#me", acl, "POST", "http://pod/data/record")

    def test_public_access(self):
        acl = _make_acl(
            agent_class=str(FOAF.Agent),
            resource="http://pod/data/public",
            modes=[str(ACL.Read)],
        )
        assert evaluate_wac("http://pod/anyone/card#me", acl, "GET", "http://pod/data/public")

    def test_authenticated_agent_class(self):
        acl = _make_acl(
            agent_class=str(ACL.AuthenticatedAgent),
            resource="http://pod/data/record",
            modes=[str(ACL.Read)],
        )
        assert evaluate_wac("http://pod/alice/card#me", acl, "GET", "http://pod/data/record")

    def test_wrong_resource_denied(self):
        acl = _make_acl(
            agent="http://pod/alice/card#me",
            resource="http://pod/data/other",
            modes=[str(ACL.Read)],
        )
        assert not evaluate_wac("http://pod/alice/card#me", acl, "GET", "http://pod/data/record")

    def test_default_acl_covers_children(self):
        """acl:default grants access to resources within a container."""
        g = Graph()
        rule = URI("http://pod/.acl#rule1")
        g.add(rule, URI(str(RDF.type)), ACL.Authorization)
        g.add(rule, ACL.agent, URI("http://pod/alice/card#me"))
        g.add(rule, ACL.default, URI("http://pod/data/"))
        g.add(rule, ACL.mode, ACL.Read)

        assert evaluate_wac(
            "http://pod/alice/card#me", g, "GET", "http://pod/data/child"
        )

    def test_method_mapping(self):
        """Verify HTTP method -> WAC mode mapping."""
        acl = _make_acl(
            agent="http://pod/a/card#me",
            resource="http://pod/r",
            modes=[str(ACL.Read), str(ACL.Write), str(ACL.Control)],
        )
        assert evaluate_wac("http://pod/a/card#me", acl, "GET", "http://pod/r")
        assert evaluate_wac("http://pod/a/card#me", acl, "HEAD", "http://pod/r")
        assert evaluate_wac("http://pod/a/card#me", acl, "PUT", "http://pod/r")
        assert evaluate_wac("http://pod/a/card#me", acl, "DELETE", "http://pod/r")
