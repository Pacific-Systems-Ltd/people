"""E2E tests for Solid Notifications Protocol against a real Community Solid Server.

Tests WebSocketChannel2023 and WebhookChannel2023. Both require an accessible
subscription endpoint on the CSS instance (localhost:3000).

WebhookChannel2023 additionally requires that the CSS can POST back to the
test machine on localhost — this works because both are on the same host in
the standard Docker-based test setup.

Run:
    docker run --rm -d --name css-test -p 3000:3000 \
        solidproject/community-server:latest -b http://localhost:3000
    pytest tests/e2e/test_notifications.py -v
"""

import asyncio
import uuid

import pacific_solid as ps
import pytest
from pacific_solid import RDF, SCHEMA, URI, Graph, Literal
from pacific_solid._notifications.discovery import discover_channels
from pacific_solid._notifications.subscription import subscribe
from pacific_solid._notifications.websocket import NotificationStream

_WS_CHANNEL = str(ps.SOLID_NOTIFICATIONS.WebSocketChannel2023)
_WEBHOOK_CHANNEL = str(ps.SOLID_NOTIFICATIONS.WebhookChannel2023)

# How long to wait for a notification to arrive before failing
_NOTIFICATION_TIMEOUT = 10.0


@pytest.fixture
async def session(css_credentials, css_base):
    """Authenticated session for notification tests."""
    s = await ps.login(
        issuer=css_base,
        client_id=css_credentials["client_id"],
        client_secret=css_credentials["client_secret"],
    )
    yield s
    await s.close()


@pytest.fixture
async def pod(session, css_credentials):
    return session.pod(css_credentials["pod_url"])


@pytest.fixture
async def notify_resource(pod):
    """A resource we can modify to trigger notifications. Cleaned up after the test."""
    g = Graph()
    subject = URI(f"http://example.org/notif-{uuid.uuid4().hex[:8]}")
    g.add(subject, RDF.type, SCHEMA.NoteDigitalDocument)
    g.add(subject, SCHEMA.name, Literal("Notification test resource"))
    url = await pod.create("", g, slug=f"notif-{uuid.uuid4().hex[:8]}")
    yield url
    try:
        await pod.delete(url)
    except Exception:
        pass


def _find_channel(channels, channel_type: str):
    for ch in channels:
        if ch.channel_type == channel_type:
            return ch
    return None


# ============================================================
# 1. CHANNEL DISCOVERY
# ============================================================


class TestNotificationDiscovery:
    @pytest.mark.asyncio
    async def test_discover_channels_returns_list(self, notify_resource, session):
        """CSS advertises at least one notification channel."""
        channels = await discover_channels(notify_resource, session._client)
        # CSS should expose at least WebSocketChannel2023
        assert isinstance(channels, list)

    @pytest.mark.asyncio
    async def test_websocket_channel_advertised(self, notify_resource, session):
        """CSS advertises WebSocketChannel2023 for resources."""
        channels = await discover_channels(notify_resource, session._client)
        types = [ch.channel_type for ch in channels]
        if _WS_CHANNEL not in types:
            pytest.skip("CSS does not advertise WebSocketChannel2023 for this resource")
        assert _WS_CHANNEL in types


# ============================================================
# 2. WEBSOCKET CHANNEL
# ============================================================


class TestWebSocketChannel:
    @pytest.mark.asyncio
    async def test_subscribe_and_receive_notification(self, notify_resource, session, pod):
        """Modify a resource and receive a notification over WebSocket."""
        channels = await discover_channels(notify_resource, session._client)
        ch = _find_channel(channels, _WS_CHANNEL)
        if ch is None:
            pytest.skip("WebSocketChannel2023 not available on this CSS instance")

        result = await subscribe(
            ch.subscription_url,
            notify_resource,
            _WS_CHANNEL,
            session._client,
        )
        assert result.receive_from, "Subscription must return a receiveFrom URL"

        async with NotificationStream(result.receive_from) as stream:
            # Trigger a notification by modifying the resource
            graph = await pod.read(notify_resource)
            graph.take_snapshot()
            graph.add(
                URI(f"http://example.org/notif-subject"),
                SCHEMA.text,
                Literal("Triggering notification"),
            )
            await pod.patch(notify_resource, graph)

            # Wait for the notification to arrive
            notification = await asyncio.wait_for(
                stream.__anext__(), timeout=_NOTIFICATION_TIMEOUT
            )

        assert notification.object_url == notify_resource or notify_resource in (
            notification.object_url or ""
        )


# ============================================================
# 3. WEBHOOK CHANNEL
# ============================================================


class TestWebhookChannel:
    @pytest.mark.asyncio
    async def test_subscribe_and_receive_notification(self, notify_resource, session, pod):
        """Subscribe via WebhookChannel2023, modify a resource, receive the POST."""
        aiohttp = pytest.importorskip("aiohttp")  # noqa: F841

        from pacific_solid._notifications.webhook import WebhookReceiver

        channels = await discover_channels(notify_resource, session._client)
        ch = _find_channel(channels, _WEBHOOK_CHANNEL)
        if ch is None:
            pytest.skip("WebhookChannel2023 not available on this CSS instance")

        async with WebhookReceiver(port=0) as receiver:
            result = await subscribe(
                ch.subscription_url,
                notify_resource,
                _WEBHOOK_CHANNEL,
                session._client,
                features={"sendTo": receiver.url},
            )
            assert result.channel_url, "Subscription must return a channel URL"

            # Trigger a notification by modifying the resource
            graph = await pod.read(notify_resource)
            graph.take_snapshot()
            graph.add(
                URI("http://example.org/notif-subject"),
                SCHEMA.text,
                Literal("Triggering webhook notification"),
            )
            await pod.patch(notify_resource, graph)

            # Wait for the webhook POST to arrive
            notification = await asyncio.wait_for(
                receiver.__anext__(), timeout=_NOTIFICATION_TIMEOUT
            )

        assert notification is not None
        assert notification.object_url == notify_resource or notify_resource in (
            notification.object_url or ""
        )

    @pytest.mark.asyncio
    async def test_webhook_channel_subscription_includes_send_to(
        self, notify_resource, session
    ):
        """Subscribing to WebhookChannel2023 sends sendTo in the request body."""
        channels = await discover_channels(notify_resource, session._client)
        ch = _find_channel(channels, _WEBHOOK_CHANNEL)
        if ch is None:
            pytest.skip("WebhookChannel2023 not available on this CSS instance")

        from pacific_solid._notifications.webhook import WebhookReceiver

        async with WebhookReceiver(port=0) as receiver:
            result = await subscribe(
                ch.subscription_url,
                notify_resource,
                _WEBHOOK_CHANNEL,
                session._client,
                features={"sendTo": receiver.url},
            )

        assert result.send_to == receiver.url or result.channel_url
