"""Notification channel subscription (NOT-03, NOT-04, NOT-05, NOT-06, NOT-07).

Handles creating subscriptions to notification channels via JSON-LD POST.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from people._http.errors import SolidError, raise_for_status

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


@dataclass
class SubscriptionResult:
    """The result of subscribing to a notification channel."""

    channel_url: str
    receive_from: str | None = None
    send_to: str | None = None
    topic: str = ""


class UnsupportedChannelError(SolidError):
    """Raised when the server returns 415 for an unsupported channel type (NOT-05)."""

    def __init__(self, channel_type: str, url: str) -> None:
        super().__init__(
            f"Server does not support channel type '{channel_type}'. "
            f"Try a different channel type.",
            status_code=415,
            url=url,
        )


class InvalidSubscriptionError(SolidError):
    """Raised when the server returns 422 for a malformed subscription (NOT-06)."""

    def __init__(self, detail: str, url: str) -> None:
        super().__init__(
            f"Subscription request rejected: {detail}",
            status_code=422,
            url=url,
        )


async def subscribe(
    subscription_url: str,
    topic: str,
    channel_type: str,
    client: AuthenticatedClient,
    *,
    features: dict[str, str] | None = None,
) -> SubscriptionResult:
    """Subscribe to a notification channel (NOT-03).

    Sends a JSON-LD subscription request per the Notification Channel Data Model.

    Args:
        subscription_url: The subscription service URL.
        topic: The resource URL to receive notifications about.
        channel_type: The notification channel type URI
            (e.g. "http://www.w3.org/ns/solid/notifications#WebSocketChannel2023").
        client: An authenticated HTTP client.
        features: Optional channel features (startAt, endAt, rate, etc.).

    Returns:
        A SubscriptionResult with the channel URL and connection details.

    Raises:
        UnsupportedChannelError: If the server returns 415 (NOT-05).
        InvalidSubscriptionError: If the server returns 422 (NOT-06).
        SolidError: For other server errors.
    """
    from people._notifications.safety import validate_subscription_target
    validate_subscription_target(subscription_url)

    # Build the JSON-LD subscription body (NOT-03, NOT-04)
    body: dict = {
        "@context": ["https://www.w3.org/ns/solid/notification/v1"],
        "type": channel_type,
        "topic": topic,
    }
    if features:
        body.update(features)

    payload = json.dumps(body)

    # NOT-04: Content-Type must be application/ld+json
    resp = await client.request(
        "POST", subscription_url,
        content=payload,
        headers={"Content-Type": "application/ld+json"},
    )

    # NOT-05: Handle 415
    if resp.status_code == 415:
        raise UnsupportedChannelError(channel_type, subscription_url)

    # NOT-06: Handle 422
    if resp.status_code == 422:
        raise InvalidSubscriptionError(resp.text, subscription_url)

    raise_for_status(resp.status_code, subscription_url, resp.text)

    # Parse the response
    try:
        result_data = json.loads(resp.text)
    except json.JSONDecodeError as e:
        raise SolidError(
            "Subscription response is not valid JSON",
            status_code=resp.status_code,
            url=subscription_url,
        ) from e

    return SubscriptionResult(
        channel_url=result_data.get("id", result_data.get("@id", "")),
        receive_from=result_data.get("receiveFrom"),
        send_to=result_data.get("sendTo"),
        topic=topic,
    )
