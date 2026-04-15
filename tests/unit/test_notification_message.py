"""Tests for notification message parsing (NOT-08, NOT-10, NOT-11)."""

import json

import pytest
from people._notifications.message import parse_notification


class TestParseNotification:
    def test_basic_create_notification(self):
        """NOT-10: Parse Activity Streams Create notification."""
        data = json.dumps({
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "urn:uuid:12345",
            "type": "Create",
            "object": "https://pod.example.com/resource",
            "published": "2026-04-03T12:00:00Z",
        })
        n = parse_notification(data)
        assert n.id == "urn:uuid:12345"
        assert "Create" in n.activity_type
        assert n.object_url == "https://pod.example.com/resource"
        assert n.published == "2026-04-03T12:00:00Z"

    def test_update_notification(self):
        data = json.dumps({
            "id": "urn:uuid:67890",
            "type": "Update",
            "object": "https://pod.example.com/notes/hello",
            "published": "2026-04-03T12:30:00Z",
        })
        n = parse_notification(data)
        assert "Update" in n.activity_type

    def test_delete_notification(self):
        data = json.dumps({
            "id": "urn:uuid:abcde",
            "type": "Delete",
            "object": "https://pod.example.com/notes/goodbye",
        })
        n = parse_notification(data)
        assert "Delete" in n.activity_type
        assert n.published is None

    def test_multiple_types(self):
        data = json.dumps({
            "id": "urn:uuid:multi",
            "type": ["Update", "http://www.w3.org/ns/solid/notifications#Notification"],
            "object": "https://pod.example.com/resource",
        })
        n = parse_notification(data)
        assert len(n.activity_type) == 2

    def test_object_as_dict(self):
        data = json.dumps({
            "id": "urn:uuid:obj",
            "type": "Create",
            "object": {"id": "https://pod.example.com/resource"},
        })
        n = parse_notification(data)
        assert n.object_url == "https://pod.example.com/resource"

    def test_target_field(self):
        data = json.dumps({
            "id": "urn:uuid:tgt",
            "type": "Add",
            "object": "https://pod.example.com/resource",
            "target": "https://pod.example.com/container/",
        })
        n = parse_notification(data)
        assert "https://pod.example.com/container/" in n.target

    def test_state_field(self):
        data = json.dumps({
            "id": "urn:uuid:state",
            "type": "Update",
            "object": "https://pod.example.com/resource",
            "state": "urn:state:abc123",
        })
        n = parse_notification(data)
        assert n.state == "urn:state:abc123"

    def test_actor_field(self):
        data = json.dumps({
            "id": "urn:uuid:actor",
            "type": "Update",
            "object": "https://pod.example.com/resource",
            "actor": "https://pod.example.com/alice/profile/card#me",
        })
        n = parse_notification(data)
        assert n.actor == "https://pod.example.com/alice/profile/card#me"

    def test_actor_as_dict(self):
        data = json.dumps({
            "id": "urn:uuid:actor2",
            "type": "Update",
            "object": "https://pod.example.com/resource",
            "actor": {"id": "https://pod.example.com/bob/profile/card#me"},
        })
        n = parse_notification(data)
        assert n.actor == "https://pod.example.com/bob/profile/card#me"


class TestExtendedContent:
    """NOT-11: Be prepared for extended notification content."""

    def test_unknown_fields_preserved_in_raw(self):
        data = json.dumps({
            "id": "urn:uuid:ext",
            "type": "Update",
            "object": "https://pod.example.com/resource",
            "customExtension": {"key": "value"},
            "vendorField": 42,
        })
        n = parse_notification(data)
        assert n.raw["customExtension"] == {"key": "value"}
        assert n.raw["vendorField"] == 42

    def test_extended_context_does_not_crash(self):
        data = json.dumps({
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"custom": "https://vendor.example/ns#"},
            ],
            "id": "urn:uuid:ctx",
            "type": "Update",
            "object": "https://pod.example.com/resource",
        })
        n = parse_notification(data)
        assert n.id == "urn:uuid:ctx"


class TestInvalidInput:
    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            parse_notification("not json at all")

    def test_missing_fields_produce_defaults(self):
        data = json.dumps({})
        n = parse_notification(data)
        assert n.id == ""
        assert n.activity_type == []
        assert n.object_url == ""
        assert n.published is None
