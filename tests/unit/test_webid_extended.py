"""Tests for extended WebID Profile resolution (WID-01, WID-02, WID-05)."""

import httpx
import pytest
import respx
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._identity.webid import WebIDProfile, resolve_webid


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


_FULL_PROFILE_TURTLE = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
@prefix pim: <http://www.w3.org/ns/pim/space#>.
@prefix foaf: <http://xmlns.com/foaf/0.1/>.
@prefix ldp: <http://www.w3.org/ns/ldp#>.
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.

<#me>
    a foaf:Person ;
    foaf:name "Alice" ;
    solid:oidcIssuer <https://solid.example.com> ;
    pim:storage <https://pod.example.com/alice/> ;
    ldp:inbox <https://pod.example.com/alice/inbox/> ;
    pim:preferencesFile <https://pod.example.com/alice/settings/prefs.ttl> ;
    rdfs:seeAlso <https://pod.example.com/alice/profile/extended.ttl> ;
    foaf:isPrimaryTopicOf <https://pod.example.com/alice/profile/card> .
"""

_MINIMAL_PROFILE_TURTLE = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
@prefix foaf: <http://xmlns.com/foaf/0.1/>.

<#me>
    a foaf:Person ;
    solid:oidcIssuer <https://solid.example.com> .
"""

_PROFILE_JSONLD = """{
    "@id": "https://pod.example.com/alice/profile/card#me",
    "@type": "http://xmlns.com/foaf/0.1/Person",
    "http://xmlns.com/foaf/0.1/name": "Alice JSON-LD",
    "http://www.w3.org/ns/solid/terms#oidcIssuer": {
        "@id": "https://solid.example.com"
    },
    "http://www.w3.org/ns/pim/space#storage": {
        "@id": "https://pod.example.com/alice/"
    },
    "http://www.w3.org/ns/ldp#inbox": {
        "@id": "https://pod.example.com/alice/inbox/"
    }
}"""


class TestWebIDProfileExtraction:
    @pytest.mark.asyncio
    @respx.mock
    async def test_full_profile_extraction(self):
        """All profile predicates are extracted from a fully-populated profile."""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text=_FULL_PROFILE_TURTLE,
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        profile = await resolve_webid(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()

        assert profile.name == "Alice"
        assert "https://solid.example.com" in profile.issuers
        assert "https://pod.example.com/alice/" in profile.storages
        assert profile.inbox == "https://pod.example.com/alice/inbox/"
        assert profile.preferences_file == (
            "https://pod.example.com/alice/settings/prefs.ttl"
        )
        assert len(profile.see_also) == 2
        assert "https://pod.example.com/alice/profile/extended.ttl" in profile.see_also
        assert "https://pod.example.com/alice/profile/card" in profile.see_also

    @pytest.mark.asyncio
    @respx.mock
    async def test_minimal_profile(self):
        """Missing optional predicates return None / empty lists, never crash."""
        respx.get("https://pod.example.com/bob/profile/card").mock(
            return_value=httpx.Response(
                200,
                text=_MINIMAL_PROFILE_TURTLE,
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        profile = await resolve_webid(
            "https://pod.example.com/bob/profile/card", client,
        )
        await client.close()

        assert profile.issuers == ["https://solid.example.com"]
        assert profile.storages == []
        assert profile.inbox is None
        assert profile.preferences_file is None
        assert profile.see_also == []
        assert profile.name is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_returns_empty_profile(self):
        """A 404 or 500 on the WebID URL returns a stub profile, not a crash."""
        respx.get("https://pod.example.com/gone/profile/card").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        client = _make_client()
        profile = await resolve_webid(
            "https://pod.example.com/gone/profile/card", client,
        )
        await client.close()

        assert profile.webid == "https://pod.example.com/gone/profile/card"
        assert profile.issuers == []
        assert profile.inbox is None


class TestWebIDJsonLD:
    @pytest.mark.asyncio
    @respx.mock
    async def test_jsonld_profile_parsed(self):
        """WID-01: profiles served as JSON-LD are parsed correctly."""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text=_PROFILE_JSONLD,
                headers={"content-type": "application/ld+json"},
            )
        )
        client = _make_client()
        profile = await resolve_webid(
            "https://pod.example.com/alice/profile/card", client,
        )
        await client.close()

        assert profile.name == "Alice JSON-LD"
        assert "https://solid.example.com" in profile.issuers
        assert "https://pod.example.com/alice/" in profile.storages
        assert profile.inbox == "https://pod.example.com/alice/inbox/"

    @pytest.mark.asyncio
    @respx.mock
    async def test_accept_header_negotiates_both_formats(self):
        """The request Accept header asks for both Turtle and JSON-LD."""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200,
                text=_MINIMAL_PROFILE_TURTLE,
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        await resolve_webid("https://pod.example.com/alice/profile/card", client)
        await client.close()

        sent_request = respx.calls[0].request
        accept = sent_request.headers.get("accept", "")
        assert "text/turtle" in accept
        assert "application/ld+json" in accept


class TestWebIDMultipleIssuers:
    @pytest.mark.asyncio
    @respx.mock
    async def test_multiple_oidc_issuers(self):
        """Profile with multiple solid:oidcIssuer values — all extracted."""
        turtle = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
<#me>
    solid:oidcIssuer <https://issuer-a.example.com>, <https://issuer-b.example.com> .
"""
        respx.get("https://pod.example.com/multi/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        profile = await resolve_webid(
            "https://pod.example.com/multi/profile/card", client,
        )
        await client.close()

        assert len(profile.issuers) == 2
        assert "https://issuer-a.example.com" in profile.issuers
        assert "https://issuer-b.example.com" in profile.issuers


class TestWebIDDataclass:
    def test_default_values(self):
        """WebIDProfile defaults are safe — no shared mutable state."""
        p1 = WebIDProfile(webid="https://a")
        p2 = WebIDProfile(webid="https://b")
        p1.issuers.append("x")
        assert p2.issuers == []

    def test_all_fields_represented(self):
        """All spec-required fields are present on WebIDProfile."""
        p = WebIDProfile(
            webid="https://x",
            name="X",
            issuers=["https://iss"],
            storages=["https://pod/"],
            inbox="https://pod/inbox/",
            preferences_file="https://pod/prefs.ttl",
            see_also=["https://pod/ext.ttl"],
        )
        assert p.inbox == "https://pod/inbox/"
        assert p.preferences_file == "https://pod/prefs.ttl"
        assert p.see_also == ["https://pod/ext.ttl"]
