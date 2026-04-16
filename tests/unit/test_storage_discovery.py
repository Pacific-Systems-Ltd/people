"""Tests for storage discovery (SP-17, SP-18)."""

import httpx
import pytest
import respx
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._discovery.storage import discover_storage
from pacific_solid._http.client import AuthenticatedClient


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


_PIM_STORAGE_TYPE = "http://www.w3.org/ns/pim/space#Storage"
_LDP_CONTAINER_TYPE = "http://www.w3.org/ns/ldp#Container"


class TestRDFBasedDiscovery:
    """SP-18: discover storage via pim:storage triple in RDF representation."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_discovers_storage_from_rdf(self):
        turtle = """\
@prefix pim: <http://www.w3.org/ns/pim/space#>.
<#me> pim:storage <https://pod.example.com/alice/> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        result = await discover_storage(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()
        assert result == "https://pod.example.com/alice/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_rdf_discovery_no_storage_triple(self):
        """Resource has no pim:storage triple — falls through to link traversal."""
        turtle = '<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .'
        respx.get("https://pod.example.com/alice/notes/n1").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        # Link traversal also finds nothing
        respx.route(method="HEAD").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        client = _make_client()
        result = await discover_storage(
            "https://pod.example.com/alice/notes/n1", client,
        )
        await client.close()
        assert result is None


class TestLinkHeaderTraversal:
    """SP-17: walk up path hierarchy checking Link rel=type for pim:Storage."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_discovers_storage_at_pod_root(self):
        """HEAD on pod root returns Link type pim:Storage."""
        # GET on the resource (RDF-based strategy) — no storage triple
        respx.get("https://pod.example.com/alice/notes/hello").mock(
            return_value=httpx.Response(
                200,
                text='<#x> <http://schema.org/name> "X" .',
                headers={"content-type": "text/turtle"},
            )
        )
        # HEAD on /alice/notes/ — just a container
        respx.head("https://pod.example.com/alice/notes/").mock(
            return_value=httpx.Response(
                200,
                headers={
                    "link": f'<{_LDP_CONTAINER_TYPE}>; rel="type"',
                },
            )
        )
        # HEAD on /alice/ — the storage root
        respx.head("https://pod.example.com/alice/").mock(
            return_value=httpx.Response(
                200,
                headers={
                    "link": (
                        f'<{_LDP_CONTAINER_TYPE}>; rel="type", '
                        f'<{_PIM_STORAGE_TYPE}>; rel="type"'
                    ),
                },
            )
        )
        client = _make_client()
        result = await discover_storage(
            "https://pod.example.com/alice/notes/hello", client,
        )
        await client.close()
        assert result == "https://pod.example.com/alice/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_storage_at_server_root(self):
        """Storage is at the server root (single-pod server)."""
        respx.get("https://pod.example.com/notes/hello").mock(
            return_value=httpx.Response(
                200,
                text='<#x> <http://schema.org/name> "X" .',
                headers={"content-type": "text/turtle"},
            )
        )
        respx.head("https://pod.example.com/notes/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        respx.head("https://pod.example.com/").mock(
            return_value=httpx.Response(
                200,
                headers={"link": f'<{_PIM_STORAGE_TYPE}>; rel="type"'},
            )
        )
        client = _make_client()
        result = await discover_storage(
            "https://pod.example.com/notes/hello", client,
        )
        await client.close()
        assert result == "https://pod.example.com/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_traversal_stops_at_storage(self):
        """Once storage is found, no further HEAD requests are made."""
        respx.get("https://pod.example.com/a/b/c/d").mock(
            return_value=httpx.Response(
                200,
                text='<#x> <http://schema.org/name> "X" .',
                headers={"content-type": "text/turtle"},
            )
        )
        respx.head("https://pod.example.com/a/b/c/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        respx.head("https://pod.example.com/a/b/").mock(
            return_value=httpx.Response(
                200,
                headers={"link": f'<{_PIM_STORAGE_TYPE}>; rel="type"'},
            )
        )
        # These should NOT be called
        head_a = respx.head("https://pod.example.com/a/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        head_root = respx.head("https://pod.example.com/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        client = _make_client()
        result = await discover_storage(
            "https://pod.example.com/a/b/c/d", client,
        )
        await client.close()
        assert result == "https://pod.example.com/a/b/"
        assert not head_a.called
        assert not head_root.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_storage_found(self):
        """No Link header with pim:Storage anywhere — returns None."""
        respx.get("https://pod.example.com/x/y").mock(
            return_value=httpx.Response(
                200,
                text='<#x> <http://schema.org/name> "X" .',
                headers={"content-type": "text/turtle"},
            )
        )
        respx.head("https://pod.example.com/x/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        respx.head("https://pod.example.com/").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        client = _make_client()
        result = await discover_storage("https://pod.example.com/x/y", client)
        await client.close()
        assert result is None


class TestLinkHeaderMultiValue:
    """Verify parse_link_headers_multi handles multiple rel=type values."""

    def test_single_type(self):
        from pacific_solid._http.headers import parse_link_headers_multi
        header = f'<{_PIM_STORAGE_TYPE}>; rel="type"'
        result = parse_link_headers_multi(header)
        assert result["type"] == [_PIM_STORAGE_TYPE]

    def test_multiple_types(self):
        from pacific_solid._http.headers import parse_link_headers_multi
        header = (
            f'<{_LDP_CONTAINER_TYPE}>; rel="type", '
            f'<{_PIM_STORAGE_TYPE}>; rel="type"'
        )
        result = parse_link_headers_multi(header)
        assert len(result["type"]) == 2
        assert _LDP_CONTAINER_TYPE in result["type"]
        assert _PIM_STORAGE_TYPE in result["type"]

    def test_mixed_rels(self):
        from pacific_solid._http.headers import parse_link_headers_multi
        header = '<.acl>; rel="acl", <http://example.org/Type>; rel="type"'
        result = parse_link_headers_multi(header)
        assert result["acl"] == [".acl"]
        assert result["type"] == ["http://example.org/Type"]

    def test_empty_header(self):
        from pacific_solid._http.headers import parse_link_headers_multi
        result = parse_link_headers_multi("")
        assert result == {}
