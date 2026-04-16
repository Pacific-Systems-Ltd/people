"""Tests for TLS enforcement (OIDC-16)."""

import pytest
from pacific_solid._http.errors import SolidError
from pacific_solid._http.tls import enforce_tls


class TestTLSEnforcement:
    def test_https_accepted(self):
        enforce_tls("https://solid.example.com/token")

    def test_http_localhost_accepted(self):
        enforce_tls("http://localhost:3000/.well-known/openid-configuration")

    def test_http_127_accepted(self):
        enforce_tls("http://127.0.0.1:3000/token")

    def test_http_ipv6_loopback_accepted(self):
        enforce_tls("http://[::1]:3000/token")

    def test_http_remote_rejected(self):
        with pytest.raises(SolidError, match="insecure connection"):
            enforce_tls("http://solid.example.com/token")

    def test_http_remote_ip_rejected(self):
        with pytest.raises(SolidError, match="insecure connection"):
            enforce_tls("http://192.168.1.1:3000/token")

    def test_http_remote_with_path_rejected(self):
        with pytest.raises(SolidError, match="TLS"):
            enforce_tls("http://pod.provider.net/.well-known/openid-configuration")

    def test_https_localhost_accepted(self):
        enforce_tls("https://localhost:3000/token")
