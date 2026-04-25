"""Tests for WebhookHandler — framework-agnostic webhook payload parser."""

import json

import pytest
from pacific_solid._notifications.webhook import WebhookHandler


_VALID_NOTIFICATION = {
    "@context": ["https://www.w3.org/ns/solid/notification/v1"],
    "id": "https://pod.example.com/notifications/n1",
    "type": ["Update"],
    "object": "https://pod.example.com/resource",
    "published": "2024-01-01T00:00:00Z",
}


def _body(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


class TestWebhookHandlerProcess:
    """WebhookHandler.process() — validates and parses incoming POST bodies."""

    def test_valid_notification_returns_notification(self):
        handler = WebhookHandler()
        notification = handler.process(
            _body(_VALID_NOTIFICATION), "application/ld+json"
        )
        assert notification.id == "https://pod.example.com/notifications/n1"
        assert "Update" in notification.activity_type
        assert notification.object_url == "https://pod.example.com/resource"
        assert notification.published == "2024-01-01T00:00:00Z"

    def test_content_type_with_charset_accepted(self):
        handler = WebhookHandler()
        notification = handler.process(
            _body(_VALID_NOTIFICATION), "application/ld+json; charset=utf-8"
        )
        assert notification.object_url == "https://pod.example.com/resource"

    def test_wrong_content_type_raises_value_error(self):
        handler = WebhookHandler()
        with pytest.raises(ValueError, match="Content-Type"):
            handler.process(_body(_VALID_NOTIFICATION), "application/json")

    def test_empty_content_type_raises_value_error(self):
        handler = WebhookHandler()
        with pytest.raises(ValueError, match="Content-Type"):
            handler.process(_body(_VALID_NOTIFICATION), "")

    def test_invalid_json_raises_value_error(self):
        handler = WebhookHandler()
        with pytest.raises(ValueError):
            handler.process(b"{not valid json", "application/ld+json")

    def test_empty_body_raises_value_error(self):
        handler = WebhookHandler()
        with pytest.raises(ValueError):
            handler.process(b"", "application/ld+json")

    def test_invalid_utf8_raises_value_error(self):
        handler = WebhookHandler()
        with pytest.raises(ValueError, match="UTF-8"):
            handler.process(b"\xff\xfe", "application/ld+json")

    def test_notification_with_object_as_dict(self):
        """object field can be a dict with id key."""
        payload = dict(_VALID_NOTIFICATION)
        payload["object"] = {"id": "https://pod.example.com/resource", "type": "File"}
        handler = WebhookHandler()
        notification = handler.process(_body(payload), "application/ld+json")
        assert notification.object_url == "https://pod.example.com/resource"

    def test_notification_with_type_string(self):
        """type field can be a bare string instead of a list."""
        payload = dict(_VALID_NOTIFICATION)
        payload["type"] = "Add"
        handler = WebhookHandler()
        notification = handler.process(_body(payload), "application/ld+json")
        assert "Add" in notification.activity_type

    def test_raw_preserved(self):
        """Extra fields are accessible via notification.raw."""
        payload = dict(_VALID_NOTIFICATION)
        payload["customField"] = "custom-value"
        handler = WebhookHandler()
        notification = handler.process(_body(payload), "application/ld+json")
        assert notification.raw["customField"] == "custom-value"
