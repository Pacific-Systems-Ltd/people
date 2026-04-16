"""Notification message parsing (NOT-08, NOT-10, NOT-11).

Parses notification messages expressed with Activity Streams and
Solid Notifications vocabularies. Tolerates extended content (NOT-11).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("people")


@dataclass
class Notification:
    """A parsed Solid Notification message.

    Based on the Activity Streams 2.0 vocabulary extended with
    Solid Notifications terms.
    """

    id: str
    activity_type: list[str]
    object_url: str
    published: str | None = None
    target: list[str] = field(default_factory=list)
    state: str | None = None
    actor: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def parse_notification(data: str) -> Notification:
    """Parse a JSON-LD notification message (NOT-08, NOT-10).

    Extracts core Activity Streams fields and preserves the raw dict
    for access to extension fields (NOT-11).

    Args:
        data: Raw JSON-LD string from the notification channel.

    Returns:
        A Notification object with parsed fields.

    Raises:
        ValueError: If the data is not valid JSON.
    """
    try:
        doc = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Notification is not valid JSON: {e}") from e

    # Extract ID
    notif_id = doc.get("id", doc.get("@id", ""))

    # Extract type(s) — Activity Streams uses type or @type
    raw_type = doc.get("type", doc.get("@type", []))
    if isinstance(raw_type, str):
        activity_type = [raw_type]
    elif isinstance(raw_type, list):
        activity_type = [str(t) for t in raw_type]
    else:
        activity_type = []

    # Extract object (the resource this notification is about)
    raw_object = doc.get("object", "")
    object_url: str
    if isinstance(raw_object, dict):
        object_url = str(raw_object.get("id", raw_object.get("@id", "")))
    else:
        object_url = str(raw_object)

    # Extract published timestamp
    published = doc.get("published")

    # Extract target(s)
    raw_target = doc.get("target", [])
    if isinstance(raw_target, str):
        target = [raw_target]
    elif isinstance(raw_target, list):
        target = [
            str(t) if isinstance(t, str) else t.get("id", t.get("@id", ""))
            for t in raw_target
        ]
    else:
        target = []

    # Extract state
    state = doc.get("state")

    # Extract actor
    raw_actor = doc.get("actor", "")
    if isinstance(raw_actor, dict):
        actor = raw_actor.get("id", raw_actor.get("@id", ""))
    elif raw_actor:
        actor = str(raw_actor)
    else:
        actor = None

    return Notification(
        id=notif_id,
        activity_type=activity_type,
        object_url=object_url,
        published=published,
        target=target,
        state=state,
        actor=actor,
        raw=doc,
    )
