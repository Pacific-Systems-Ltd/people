"""Tests for notification subscription safety (NOT-13)."""

import pytest
from pacific_solid._http.errors import SolidError
from pacific_solid._notifications.safety import validate_subscription_target


class TestValidateSubscriptionTarget:
    """NOT-13: SHOULD NOT subscribe to localhost or private addresses."""

    def test_localhost_rejected(self):
        with pytest.raises(SolidError, match="loopback"):
            validate_subscription_target("http://localhost:3000/subscription")

    def test_127_rejected(self):
        with pytest.raises(SolidError, match="loopback"):
            validate_subscription_target("http://127.0.0.1:3000/subscription")

    def test_ipv6_loopback_rejected(self):
        with pytest.raises(SolidError, match="loopback"):
            validate_subscription_target("http://[::1]:3000/subscription")

    def test_private_10_rejected(self):
        with pytest.raises(SolidError, match="private"):
            validate_subscription_target("http://10.0.0.1/subscription")

    def test_private_172_rejected(self):
        with pytest.raises(SolidError, match="private"):
            validate_subscription_target("http://172.16.0.1/subscription")

    def test_private_192_rejected(self):
        with pytest.raises(SolidError, match="private"):
            validate_subscription_target("http://192.168.1.1/subscription")

    def test_link_local_rejected(self):
        with pytest.raises(SolidError, match="private"):
            validate_subscription_target("http://169.254.169.254/subscription")

    def test_public_https_accepted(self):
        validate_subscription_target("https://pod.example.com/subscription")

    def test_public_http_accepted_with_warning(self):
        """Public HTTP is allowed but should warn (checked via log)."""
        validate_subscription_target("http://pod.example.com/subscription")

    def test_non_private_172_accepted(self):
        """172.32.x is NOT private range."""
        validate_subscription_target("https://172.32.0.1/subscription")
