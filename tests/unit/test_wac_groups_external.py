"""Tests for WAC external group document fetching (WAC-07)."""

from pacific_solid import ACL, RDF, URI, Graph, evaluate_wac
from pacific_solid._rdf.namespaces import VCARD


def _make_group_acl(group_uri: str, resource: str) -> Graph:
    """Build an ACL with acl:agentGroup pointing to a group URI."""
    g = Graph()
    auth = URI("http://pod/resource.acl#team-read")
    g.add(auth, RDF.type, ACL.Authorization)
    g.add(auth, ACL.agentGroup, URI(group_uri))
    g.add(auth, ACL.accessTo, URI(resource))
    g.add(auth, ACL.mode, ACL.Read)
    return g


def _make_group_doc(group_uri: str, members: list[str]) -> Graph:
    """Build a group document with vcard:hasMember triples."""
    g = Graph()
    g.add(URI(group_uri), RDF.type, VCARD.Group)
    for member in members:
        g.add(URI(group_uri), VCARD.hasMember, URI(member))
    return g


class TestExternalGroupFetching:
    def test_external_group_member_granted(self):
        """Agent listed in an external group document gets access."""
        group_uri = "https://teams.example.com/engineering"
        acl = _make_group_acl(group_uri, "http://pod/resource")
        ext_groups = {
            group_uri: _make_group_doc(group_uri, [
                "https://alice.example/profile#me",
                "https://bob.example/profile#me",
            ]),
        }
        assert evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", external_groups=ext_groups,
        )

    def test_external_group_non_member_denied(self):
        """Agent NOT in the external group document is denied."""
        group_uri = "https://teams.example.com/engineering"
        acl = _make_group_acl(group_uri, "http://pod/resource")
        ext_groups = {
            group_uri: _make_group_doc(group_uri, [
                "https://alice.example/profile#me",
            ]),
        }
        assert not evaluate_wac(
            "https://charlie.example/profile#me", acl, "GET",
            "http://pod/resource", external_groups=ext_groups,
        )

    def test_local_group_still_works(self):
        """Group members listed directly in the ACL graph still match."""
        group_uri = "http://pod/groups/team"
        acl = _make_group_acl(group_uri, "http://pod/resource")
        # Add members directly to the ACL graph (local group)
        acl.add(URI(group_uri), RDF.type, VCARD.Group)
        acl.add(URI(group_uri), VCARD.hasMember, URI("https://alice.example/profile#me"))

        # No external_groups needed
        assert evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource",
        )

    def test_external_group_not_provided_denies(self):
        """If the group URI is not in external_groups, membership is unknown — deny."""
        group_uri = "https://teams.example.com/engineering"
        acl = _make_group_acl(group_uri, "http://pod/resource")

        # No external_groups provided at all
        assert not evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource",
        )

        # External groups provided but group not included
        assert not evaluate_wac(
            "https://alice.example/profile#me", acl, "GET",
            "http://pod/resource", external_groups={},
        )

    def test_multiple_groups_checked(self):
        """Authorization references multiple groups — access granted if any matches."""
        group_a = "https://teams.example.com/alpha"
        group_b = "https://teams.example.com/beta"

        acl = Graph()
        auth = URI("http://pod/resource.acl#multi")
        acl.add(auth, RDF.type, ACL.Authorization)
        acl.add(auth, ACL.agentGroup, URI(group_a))
        acl.add(auth, ACL.agentGroup, URI(group_b))
        acl.add(auth, ACL.accessTo, URI("http://pod/resource"))
        acl.add(auth, ACL.mode, ACL.Read)

        ext_groups = {
            group_a: _make_group_doc(group_a, ["https://alice.example/profile#me"]),
            group_b: _make_group_doc(group_b, ["https://bob.example/profile#me"]),
        }

        assert evaluate_wac(
            "https://bob.example/profile#me", acl, "GET",
            "http://pod/resource", external_groups=ext_groups,
        )
