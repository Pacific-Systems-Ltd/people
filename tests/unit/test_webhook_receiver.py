"""Tests for WebhookReceiver — built-in async HTTP server for webhook notifications."""

import asyncio
import json

import pytest
import pytest_asyncio

pytest_asyncio  # noqa: used for asyncio_mode=auto

aiohttp = pytest.importorskip("aiohttp")

from pacific_solid._notifications.webhook import WebhookReceiver  # noqa: E402

_NOTIFICATION_BODY = json.dumps({
    "@context": ["https://www.w3.org/ns/solid/notification/v1"],
    "id": "https://pod.example.com/notifications/n1",
    "type": ["Update"],
    "object": "https://pod.example.com/resource",
    "published": "2024-01-01T00:00:00Z",
}).encode("utf-8")


async def _post(session, url: str, body: bytes, content_type: str = "application/ld+json") -> int:
    async with session.post(url, data=body, headers={"Content-Type": content_type}) as resp:
        return resp.status


class TestWebhookReceiverUrl:
    """receiver.url returns the correct address."""

    def test_default_url_uses_localhost_and_port(self):
        receiver = WebhookReceiver(port=9876)
        assert receiver.url == "http://localhost:9876/"

    def test_custom_path_included_in_url(self):
        receiver = WebhookReceiver(port=9876, path="/webhook")
        assert receiver.url == "http://localhost:9876/webhook"

    def test_public_url_overrides_localhost(self):
        receiver = WebhookReceiver(port=9876, public_url="https://app.example/hook")
        assert receiver.url == "https://app.example/hook"

    def test_public_url_ignores_port(self):
        receiver = WebhookReceiver(port=0, public_url="https://app.example/hook")
        assert receiver.url == "https://app.example/hook"


class TestWebhookReceiverServer:
    """WebhookReceiver HTTP server behavior."""

    @pytest.mark.asyncio
    async def test_starts_and_stops(self):
        async with WebhookReceiver(port=0) as receiver:
            assert receiver._bound_port > 0

    @pytest.mark.asyncio
    async def test_resolves_port_zero(self):
        async with WebhookReceiver(port=0) as receiver:
            bound = receiver._bound_port
            assert bound > 0
            # url reflects actual port
            assert f":{bound}" in receiver.url

    @pytest.mark.asyncio
    async def test_valid_post_returns_200(self):
        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            status = await _post(session, receiver.url, _NOTIFICATION_BODY)
            assert status == 200

    @pytest.mark.asyncio
    async def test_wrong_content_type_returns_415(self):
        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            status = await _post(
                session, receiver.url, _NOTIFICATION_BODY, "application/json"
            )
            assert status == 415

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self):
        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            status = await _post(session, receiver.url, b"{bad json", "application/ld+json")
            assert status == 400

    @pytest.mark.asyncio
    async def test_non_post_method_returns_405(self):
        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            async with session.get(receiver.url) as resp:
                assert resp.status == 405

    @pytest.mark.asyncio
    async def test_path_filtering_wrong_path_returns_404(self):
        async with WebhookReceiver(port=0, path="/webhook") as receiver, aiohttp.ClientSession() as session:
            root = receiver.url.replace("/webhook", "/")
            async with session.post(root, data=_NOTIFICATION_BODY, headers={"Content-Type": "application/ld+json"}) as resp:
                assert resp.status == 404


class TestWebhookReceiverIterator:
    """WebhookReceiver async iterator delivers notifications."""

    @pytest.mark.asyncio
    async def test_notification_delivered_to_iterator(self):
        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            await _post(session, receiver.url, _NOTIFICATION_BODY)
            notification = await asyncio.wait_for(receiver.__anext__(), timeout=2.0)
            assert notification.object_url == "https://pod.example.com/resource"
            assert "Update" in notification.activity_type

    @pytest.mark.asyncio
    async def test_multiple_notifications_delivered_in_order(self):
        bodies = []
        for i in range(3):
            bodies.append(json.dumps({
                "id": f"https://pod.example.com/n{i}",
                "type": ["Update"],
                "object": f"https://pod.example.com/resource-{i}",
            }).encode())

        async with WebhookReceiver(port=0) as receiver, aiohttp.ClientSession() as session:
            for body in bodies:
                await _post(session, receiver.url, body)

            for i in range(3):
                notification = await asyncio.wait_for(receiver.__anext__(), timeout=2.0)
                assert f"resource-{i}" in notification.object_url

    @pytest.mark.asyncio
    async def test_stop_async_iteration_after_exit(self):
        async with WebhookReceiver(port=0) as receiver:
            pass  # exits immediately — sentinel enqueued

        with pytest.raises(StopAsyncIteration):
            await receiver.__anext__()

    @pytest.mark.asyncio
    async def test_sentinel_requeued_for_subsequent_calls(self):
        async with WebhookReceiver(port=0) as receiver:
            pass

        with pytest.raises(StopAsyncIteration):
            await receiver.__anext__()

        # Second call also raises, not blocks indefinitely
        with pytest.raises(StopAsyncIteration):
            await receiver.__anext__()


class TestWebhookReceiverImportError:
    """WebhookReceiver raises ImportError if aiohttp is not installed."""

    @pytest.mark.asyncio
    async def test_import_error_message(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "aiohttp":
                raise ImportError("No module named 'aiohttp'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        receiver = WebhookReceiver(port=8080)
        with pytest.raises(ImportError, match="pacific-solid\\[webhook\\]"):
            await receiver.__aenter__()
