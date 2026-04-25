"""WebhookChannel2023 notification receiver.

Provides a framework-agnostic handler for incoming webhook notifications
and a built-in async HTTP listener for standalone use.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from pacific_solid._notifications.message import Notification, parse_notification

logger = logging.getLogger("people")


class WebhookHandler:
    """Framework-agnostic parser for incoming webhook notification POSTs.

    Mount in your own web framework (FastAPI, aiohttp, Flask, etc.)::

        handler = ps.WebhookHandler()

        @app.post("/webhook")
        async def receive(request):
            notification = handler.process(await request.body(), request.content_type)
            ...
    """

    def process(self, body: bytes, content_type: str) -> Notification:
        """Parse and validate an incoming webhook notification POST.

        Args:
            body: Raw request body bytes.
            content_type: Value of the Content-Type request header.

        Returns:
            A parsed Notification.

        Raises:
            ValueError: If Content-Type is not ``application/ld+json``, or body
                is not valid UTF-8 JSON-LD.
        """
        if "application/ld+json" not in content_type:
            raise ValueError(
                f"Expected Content-Type: application/ld+json, got: {content_type!r}"
            )
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Notification body is not valid UTF-8: {exc}") from exc
        return parse_notification(text)


class WebhookReceiver:
    """Built-in async HTTP server for receiving WebhookChannel2023 notifications.

    Requires the ``webhook`` extra::

        pip install 'pacific-solid[webhook]'

    Usage::

        async with ps.WebhookReceiver(port=8080) as receiver:
            await ps.subscribe(
                sub_url, topic,
                str(ps.SOLID_NOTIFICATIONS.WebhookChannel2023),
                client,
                features={"sendTo": receiver.url},
            )
            async for notification in receiver:
                print(notification.activity_type)

    In production behind a reverse proxy, set ``public_url`` to the
    externally reachable address the pod will POST to::

        async with ps.WebhookReceiver(port=8080, public_url="https://app.example/hook") as r:
            ...

    The ``path`` parameter restricts which request path is handled (default ``/``).
    All other paths return 404; all non-POST methods return 405.
    """

    def __init__(
        self,
        port: int = 8080,
        *,
        path: str = "/",
        public_url: str | None = None,
    ) -> None:
        self._port = port
        self._path = path
        self._public_url = public_url
        self._queue: asyncio.Queue[Notification | None] = asyncio.Queue()
        self._runner: Any = None
        self._bound_port: int = port

    @property
    def url(self) -> str:
        """URL to pass as ``sendTo`` when subscribing.

        Returns ``public_url`` if set; otherwise ``http://localhost:{port}{path}``.
        """
        if self._public_url is not None:
            return self._public_url
        return f"http://localhost:{self._bound_port}{self._path}"

    async def __aenter__(self) -> WebhookReceiver:
        try:
            from aiohttp import web as _web
        except ImportError as exc:
            raise ImportError(
                "WebhookReceiver requires aiohttp. "
                "Install with: pip install 'pacific-solid[webhook]'"
            ) from exc

        app = _web.Application()
        app.router.add_post(self._path, self._handle_post)

        self._runner = _web.AppRunner(app)
        await self._runner.setup()
        site = _web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()

        # Resolve actual port when OS assigned one (port=0)
        if self._port == 0 and site._server is not None:
            sockets = getattr(site._server, "sockets", None)
            if sockets:
                self._bound_port = sockets[0].getsockname()[1]

        logger.debug("WebhookReceiver listening on :%d%s", self._bound_port, self._path)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        await self._queue.put(None)  # unblock __anext__

    def __aiter__(self) -> AsyncIterator[Notification]:
        return self  # type: ignore[return-value]

    async def __anext__(self) -> Notification:
        item = await self._queue.get()
        if item is None:
            # Re-queue sentinel so subsequent calls don't block indefinitely
            await self._queue.put(None)
            raise StopAsyncIteration
        return item

    async def _handle_post(self, request: Any) -> Any:
        from aiohttp import web as _web

        content_type = request.headers.get("Content-Type", "")
        body = await request.read()
        handler = WebhookHandler()
        try:
            notification = handler.process(body, content_type)
        except ValueError as exc:
            status = 415 if "Content-Type" in str(exc) else 400
            return _web.Response(status=status, text=str(exc))

        await self._queue.put(notification)
        return _web.Response(status=200)
