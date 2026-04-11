"""WebSocket notification channel (NOT-09).

Provides an async iterator for receiving real-time notifications
over a WebSocket connection.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from people._notifications.message import Notification, parse_notification

logger = logging.getLogger("people")


class NotificationStream:
    """Async context manager and iterator for WebSocket notifications.

    Usage:
        async with NotificationStream(ws_url) as stream:
            async for notification in stream:
                print(notification.activity_type, notification.object_url)
    """

    def __init__(self, receive_from: str) -> None:
        self._url = receive_from
        self._ws = None

    async def __aenter__(self) -> NotificationStream:
        import websockets

        self._ws = await websockets.connect(self._url)
        logger.debug("WebSocket connected to %s", self._url)
        return self

    async def __aexit__(self, *args) -> None:
        if self._ws:
            await self._ws.close()
            logger.debug("WebSocket disconnected from %s", self._url)

    def __aiter__(self) -> AsyncIterator[Notification]:
        return self

    async def __anext__(self) -> Notification:
        if not self._ws:
            raise StopAsyncIteration

        try:
            message = await self._ws.recv()
        except Exception:
            raise StopAsyncIteration from None

        return parse_notification(str(message))

    async def close(self) -> None:
        """Explicitly close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
