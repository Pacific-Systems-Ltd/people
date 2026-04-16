"""Tests for notification channel discovery (NOT-01, NOT-02)."""

import json

import httpx
import pytest
import respx
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._notifications.discovery import discover_channels


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


_DESCRIPTION_JSONLD = json.dumps({
    "@context": "https://www.w3.org/ns/solid/notification/v1",
    "id": "https://pod.example.com/.well-known/solid",
    "subscription": [
        {
            "id": "https://pod.example.com/subscription/ws",
            "channelType": "http://www.w3.org/ns/solid/notifications#WebSocketChannel2023",
            "feature": ["state", "rate"],
        },
    ],
})


class TestDiscoverChannels:
    @pytest.mark.asyncio
    @respx.mock
    async def test_discovers_via_describedby(self):
        respx.head("https://pod.example.com/resource").mock(
            return_value=httpx.Response(
                200,
                headers={
                    "link": '<https://pod.example.com/.desc>; rel="describedby"',
                },
            )
        )
        respx.get("https://pod.example.com/.desc").mock(
            return_value=httpx.Response(
                200,
                text=_DESCRIPTION_JSONLD,
                headers={"content-type": "application/ld+json"},
            )
        )
        client = _make_client()
        channels = await discover_channels("https://pod.example.com/resource", client)
        await client.close()

        assert len(channels) == 1
        assert channels[0].subscription_url == "https://pod.example.com/subscription/ws"
        assert "WebSocket" in channels[0].channel_type

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_describedby_returns_empty(self):
        respx.head("https://pod.example.com/resource").mock(
            return_value=httpx.Response(200, headers={"link": ""})
        )
        client = _make_client()
        channels = await discover_channels("https://pod.example.com/resource", client)
        await client.close()
        assert channels == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_head_failure_returns_empty(self):
        respx.head("https://pod.example.com/resource").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        client = _make_client()
        channels = await discover_channels("https://pod.example.com/resource", client)
        await client.close()
        assert channels == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_description_not_json_returns_empty(self):
        respx.head("https://pod.example.com/resource").mock(
            return_value=httpx.Response(
                200,
                headers={"link": '</.desc>; rel="describedby"'},
            )
        )
        respx.get("https://pod.example.com/.desc").mock(
            return_value=httpx.Response(200, text="not json")
        )
        client = _make_client()
        channels = await discover_channels("https://pod.example.com/resource", client)
        await client.close()
        assert channels == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_features_extracted(self):
        respx.head("https://pod.example.com/resource").mock(
            return_value=httpx.Response(
                200,
                headers={"link": '</.desc>; rel="describedby"'},
            )
        )
        respx.get("https://pod.example.com/.desc").mock(
            return_value=httpx.Response(
                200,
                text=_DESCRIPTION_JSONLD,
                headers={"content-type": "application/ld+json"},
            )
        )
        client = _make_client()
        channels = await discover_channels("https://pod.example.com/resource", client)
        await client.close()
        assert "state" in channels[0].features
        assert "rate" in channels[0].features
