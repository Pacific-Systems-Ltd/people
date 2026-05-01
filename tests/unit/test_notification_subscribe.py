"""Tests for notification subscription (NOT-03 through NOT-07)."""

import json

import httpx
import pytest
import respx
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._notifications.subscription import (
    InvalidSubscriptionError,
    UnsupportedChannelError,
    subscribe,
)


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


_WS_CHANNEL = "http://www.w3.org/ns/solid/notifications#WebSocketChannel2023"
_WEBHOOK_CHANNEL = "http://www.w3.org/ns/solid/notifications#WebhookChannel2023"


class TestSubscribe:
    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_subscription(self):
        response_body = json.dumps({
            "@context": "https://www.w3.org/ns/solid/notification/v1",
            "id": "https://pod.example.com/channels/ws-abc",
            "type": _WS_CHANNEL,
            "topic": "https://pod.example.com/resource",
            "receiveFrom": "wss://pod.example.com/ws/abc",
        })
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(200, text=response_body)
        )
        client = _make_client()
        result = await subscribe(
            "https://pod.example.com/subscription",
            "https://pod.example.com/resource",
            _WS_CHANNEL,
            client,
        )
        await client.close()

        assert result.channel_url == "https://pod.example.com/channels/ws-abc"
        assert result.receive_from == "wss://pod.example.com/ws/abc"
        assert result.topic == "https://pod.example.com/resource"

    @pytest.mark.asyncio
    @respx.mock
    async def test_sends_jsonld_content_type(self):
        """NOT-04: Content-Type must be application/ld+json."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(
                200,
                text=json.dumps({"id": "ch", "receiveFrom": "wss://x"}),
            )
        )
        client = _make_client()
        await subscribe(
            "https://pod.example.com/subscription",
            "https://pod.example.com/resource",
            _WS_CHANNEL,
            client,
        )
        await client.close()

        sent = respx.calls[0].request
        assert sent.headers.get("content-type") == "application/ld+json"

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_body_contains_required_fields(self):
        """NOT-03: Subscription must follow the Notification Channel Data Model."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(
                200,
                text=json.dumps({"id": "ch", "receiveFrom": "wss://x"}),
            )
        )
        client = _make_client()
        await subscribe(
            "https://pod.example.com/subscription",
            "https://pod.example.com/resource",
            _WS_CHANNEL,
            client,
        )
        await client.close()

        sent_body = json.loads(respx.calls[0].request.content)
        assert sent_body["type"] == _WS_CHANNEL
        assert sent_body["topic"] == "https://pod.example.com/resource"
        assert "@context" in sent_body


    @pytest.mark.asyncio
    @respx.mock
    async def test_send_to_included_in_webhook_subscription_body(self):
        """WebhookChannel2023: sendTo must appear in the POST body."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(
                200,
                text=json.dumps({
                    "id": "https://pod.example.com/channels/hook-abc",
                    "type": _WEBHOOK_CHANNEL,
                    "topic": "https://pod.example.com/resource",
                    "sendTo": "https://my-server.example/hook",
                }),
            )
        )
        client = _make_client()
        result = await subscribe(
            "https://pod.example.com/subscription",
            "https://pod.example.com/resource",
            _WEBHOOK_CHANNEL,
            client,
            features={"sendTo": "https://my-server.example/hook"},
        )
        await client.close()

        sent_body = json.loads(respx.calls[0].request.content)
        assert sent_body["sendTo"] == "https://my-server.example/hook"
        assert sent_body["type"] == _WEBHOOK_CHANNEL
        assert result.send_to == "https://my-server.example/hook"

    @pytest.mark.asyncio
    @respx.mock
    async def test_send_to_not_stripped_by_subscription(self):
        """Regression guard: features dict must NOT be stripped before sending."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(
                200,
                text=json.dumps({"id": "ch", "sendTo": "https://my-server.example/hook"}),
            )
        )
        client = _make_client()
        await subscribe(
            "https://pod.example.com/subscription",
            "https://pod.example.com/resource",
            _WEBHOOK_CHANNEL,
            client,
            features={"sendTo": "https://my-server.example/hook"},
        )
        await client.close()

        sent_body = json.loads(respx.calls[0].request.content)
        assert "sendTo" in sent_body, (
            "sendTo was stripped from the subscription body — "
            "check that strip_excess_fields() is not called in subscribe()"
        )


class TestSubscriptionErrors:
    @pytest.mark.asyncio
    @respx.mock
    async def test_415_raises_unsupported_channel(self):
        """NOT-05: Handle 415 for unsupported channel types."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(415, text="Unsupported channel type")
        )
        client = _make_client()
        with pytest.raises(UnsupportedChannelError):
            await subscribe(
                "https://pod.example.com/subscription",
                "https://pod.example.com/resource",
                "http://unsupported/channel",
                client,
            )
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_422_raises_invalid_subscription(self):
        """NOT-06: Handle 422 for malformed subscription requests."""
        respx.post("https://pod.example.com/subscription").mock(
            return_value=httpx.Response(422, text="Missing required field: topic")
        )
        client = _make_client()
        with pytest.raises(InvalidSubscriptionError, match="topic"):
            await subscribe(
                "https://pod.example.com/subscription",
                "https://pod.example.com/resource",
                _WS_CHANNEL,
                client,
            )
        await client.close()
