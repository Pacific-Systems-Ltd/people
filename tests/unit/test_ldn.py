"""Tests for Linked Data Notifications (SP-19, SP-20, SP-21)."""

import httpx
import pytest
import respx
from pacific_solid import URI, Graph, Literal
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._ldn.inbox import (
    discover_inbox,
    list_notifications,
    read_notification,
    send_notification,
)
from pacific_solid._rdf.namespaces import SCHEMA


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


_LDP_INBOX_REL = "http://www.w3.org/ns/ldp#inbox"


class TestInboxDiscovery:
    """SP-20: Discover the location of a resource's Inbox."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_discover_via_link_header(self):
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={
                    "content-type": "text/turtle",
                    "link": f'<https://pod.example.com/alice/inbox/>; rel="{_LDP_INBOX_REL}"',
                },
            )
        )
        client = _make_client()
        inbox = await discover_inbox(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()
        assert inbox == "https://pod.example.com/alice/inbox/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_discover_via_rdf_predicate(self):
        turtle = """\
@prefix ldp: <http://www.w3.org/ns/ldp#>.
<#me> ldp:inbox <https://pod.example.com/alice/inbox/> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        inbox = await discover_inbox(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()
        assert inbox == "https://pod.example.com/alice/inbox/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_inbox_returns_none(self):
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        inbox = await discover_inbox(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()
        assert inbox is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_returns_none(self):
        respx.get("https://pod.example.com/gone").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        client = _make_client()
        inbox = await discover_inbox("https://pod.example.com/gone", client)
        await client.close()
        assert inbox is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_link_header_preferred_over_rdf(self):
        """Link header is checked first — if present, RDF body is not parsed."""
        turtle = """\
@prefix ldp: <http://www.w3.org/ns/ldp#>.
<#me> ldp:inbox <https://pod.example.com/rdf-inbox/> .
"""
        respx.get("https://pod.example.com/resource").mock(
            return_value=httpx.Response(
                200,
                text=turtle,
                headers={
                    "content-type": "text/turtle",
                    "link": f'<https://pod.example.com/link-inbox/>; rel="{_LDP_INBOX_REL}"',
                },
            )
        )
        client = _make_client()
        inbox = await discover_inbox("https://pod.example.com/resource", client)
        await client.close()
        assert inbox == "https://pod.example.com/link-inbox/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_relative_inbox_url_resolved(self):
        """Relative inbox URL in Link header is resolved against the resource URL."""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={
                    "content-type": "text/turtle",
                    "link": f'<../inbox/>; rel="{_LDP_INBOX_REL}"',
                },
            )
        )
        client = _make_client()
        inbox = await discover_inbox(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()
        assert inbox == "https://pod.example.com/alice/inbox/"


class TestSendNotification:
    """SP-21: Send notifications to Inbox (LDN Sender)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_returns_location(self):
        respx.post("https://pod.example.com/alice/inbox/").mock(
            return_value=httpx.Response(
                201,
                headers={"location": "https://pod.example.com/alice/inbox/notif-1"},
            )
        )
        client = _make_client()
        g = Graph()
        g.add(URI("urn:notif:1"), SCHEMA.name, Literal("Test notification"))
        url = await send_notification(
            "https://pod.example.com/alice/inbox/", g, client,
        )
        await client.close()
        assert url == "https://pod.example.com/alice/inbox/notif-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_sets_content_type_turtle(self):
        respx.post("https://pod.example.com/alice/inbox/").mock(
            return_value=httpx.Response(
                201,
                headers={"location": "https://pod.example.com/alice/inbox/n"},
            )
        )
        client = _make_client()
        g = Graph()
        g.add(URI("urn:notif:1"), SCHEMA.name, Literal("Test"))
        await send_notification("https://pod.example.com/alice/inbox/", g, client)
        await client.close()

        sent = respx.calls[0].request
        assert sent.headers.get("content-type") == "text/turtle"

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_no_location_raises(self):
        respx.post("https://pod.example.com/alice/inbox/").mock(
            return_value=httpx.Response(201)  # No Location header
        )
        client = _make_client()
        g = Graph()
        g.add(URI("urn:notif:1"), SCHEMA.name, Literal("Test"))
        with pytest.raises(ValueError, match="Location"):
            await send_notification(
                "https://pod.example.com/alice/inbox/", g, client,
            )
        await client.close()


class TestListNotifications:
    """SP-21: Retrieve Inbox contents (LDN Consumer)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_returns_urls(self):
        turtle = """\
@prefix ldp: <http://www.w3.org/ns/ldp#>.
<> ldp:contains <notif-1>, <notif-2>, <notif-3> .
"""
        respx.get("https://pod.example.com/alice/inbox/").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        urls = await list_notifications(
            "https://pod.example.com/alice/inbox/", client,
        )
        await client.close()
        assert len(urls) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_inbox(self):
        turtle = "@prefix ldp: <http://www.w3.org/ns/ldp#>.\n<> a ldp:Container ."
        respx.get("https://pod.example.com/alice/inbox/").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        urls = await list_notifications(
            "https://pod.example.com/alice/inbox/", client,
        )
        await client.close()
        assert urls == []


class TestReadNotification:
    @pytest.mark.asyncio
    @respx.mock
    async def test_read_returns_graph(self):
        turtle = """\
@prefix schema: <http://schema.org/>.
<> schema:name "Important notification" .
"""
        respx.get("https://pod.example.com/alice/inbox/notif-1").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        graph = await read_notification(
            "https://pod.example.com/alice/inbox/notif-1", client,
        )
        await client.close()
        results = graph.query(predicate=SCHEMA.name)
        assert len(results) == 1
        assert str(results[0].object) == "Important notification"
