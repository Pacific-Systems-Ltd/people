"""Tests for WAC origin matching (WAC-08)."""

from people import ACL, FOAF, RDF, URI, Graph, evaluate_wac


def _make_acl_with_origin(
    agent: str,
    resource: str,
    modes: list[str],
    origins: list[str],
) -> Graph:
    """Build an ACL graph with acl:origin constraints."""
    g = Graph()
    auth = URI("http://pod/resource.acl#auth")
    g.add(auth, RDF.type, ACL.Authorization)
    g.add(auth, ACL.agent, URI(agent))
    g.add(auth, ACL.accessTo, URI(resource))
    for mode in modes:
        g.add(auth, ACL.mode, URI(mode))
    for origin in origins:
        g.add(auth, ACL.origin, URI(origin))
    return g


def _make_public_acl_with_origin(
    resource: str,
    modes: list[str],
    origins: list[str],
) -> Graph:
    """Build an ACL graph with public access + acl:origin."""
    g = Graph()
    auth = URI("http://pod/resource.acl#public")
    g.add(auth, RDF.type, ACL.Authorization)
    g.add(auth, ACL.agentClass, FOAF.Agent)
    g.add(auth, ACL.accessTo, URI(resource))
    for mode in modes:
        g.add(auth, ACL.mode, URI(mode))
    for origin in origins:
        g.add(auth, ACL.origin, URI(origin))
    return g


class TestOriginMatching:
    def test_matching_origin_grants_access(self):
        acl = _make_acl_with_origin(
            "https://alice.example/profile#me",
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://trusted-app.example.com"],
        )
        assert evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", origin="https://trusted-app.example.com",
        )

    def test_non_matching_origin_denied(self):
        acl = _make_acl_with_origin(
            "https://alice.example/profile#me",
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://trusted-app.example.com"],
        )
        assert not evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", origin="https://evil-app.example.com",
        )

    def test_no_origin_header_denied_when_origin_required(self):
        """Non-browser client sends no Origin header — denied when acl:origin is set."""
        acl = _make_acl_with_origin(
            "https://alice.example/profile#me",
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://trusted-app.example.com"],
        )
        assert not evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", origin=None,
        )

    def test_no_origin_constraint_allows_any(self):
        """Authorization without acl:origin — any origin (or none) is accepted."""
        g = Graph()
        auth = URI("http://pod/resource.acl#auth")
        g.add(auth, RDF.type, ACL.Authorization)
        g.add(auth, ACL.agent, URI("https://alice.example/profile#me"))
        g.add(auth, ACL.accessTo, URI("http://pod/resource"))
        g.add(auth, ACL.mode, ACL.Read)

        assert evaluate_wac(
            "https://alice.example/profile#me", g, "GET",
            "http://pod/resource", origin="https://any-app.example.com",
        )
        assert evaluate_wac(
            "https://alice.example/profile#me", g, "GET",
            "http://pod/resource", origin=None,
        )

    def test_multiple_allowed_origins(self):
        acl = _make_acl_with_origin(
            "https://alice.example/profile#me",
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://app-a.example.com", "https://app-b.example.com"],
        )
        assert evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", origin="https://app-b.example.com",
        )


class TestPublicAccessBypassesOrigin:
    def test_public_access_ignores_origin(self):
        """WAC-08: public access (foaf:Agent) bypasses origin checks."""
        acl = _make_public_acl_with_origin(
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://restricted-app.example.com"],
        )
        # Even with a non-matching origin, public access is granted
        assert evaluate_wac(
            "https://anyone.example/profile#me", acl, "GET",
            "http://pod/resource", origin="https://other-app.example.com",
        )

    def test_public_access_no_origin_header(self):
        """Public access without Origin header still works."""
        acl = _make_public_acl_with_origin(
            "http://pod/resource",
            [str(ACL.Read)],
            ["https://some-app.example.com"],
        )
        assert evaluate_wac(
            "", acl, "GET",
            "http://pod/resource", origin=None,
        )
