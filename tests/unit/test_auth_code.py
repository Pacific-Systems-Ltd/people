"""Tests for Authorization Code Flow with PKCE (OIDC-14)."""

import base64
import hashlib
import urllib.parse

import httpx
import pytest
import respx
from pacific_solid._auth.auth_code import exchange_auth_code, generate_pkce, start_auth_flow
from pacific_solid._auth.dpop import DPoPKey


class TestGeneratePKCE:
    def test_generates_verifier_and_challenge(self):
        verifier, challenge = generate_pkce()
        assert len(verifier) > 32
        assert len(challenge) > 32

    def test_challenge_is_sha256_of_verifier(self):
        verifier, challenge = generate_pkce()
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge == expected

    def test_unique_per_call(self):
        v1, _ = generate_pkce()
        v2, _ = generate_pkce()
        assert v1 != v2


class TestStartAuthFlow:
    def test_returns_url_verifier_state(self):
        auth_url, verifier, state = start_auth_flow(
            "https://issuer.example.com/authorize",
            "my-client",
            "https://app.example.com/callback",
        )
        assert "https://issuer.example.com/authorize?" in auth_url
        assert len(verifier) > 32
        assert len(state) > 16

    def test_url_contains_required_params(self):
        auth_url, verifier, state = start_auth_flow(
            "https://issuer.example.com/authorize",
            "my-client",
            "https://app.example.com/callback",
        )
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)

        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["my-client"]
        assert params["redirect_uri"] == ["https://app.example.com/callback"]
        assert params["code_challenge_method"] == ["S256"]
        assert params["state"] == [state]
        assert "code_challenge" in params

    def test_default_scopes(self):
        auth_url, _, _ = start_auth_flow(
            "https://issuer.example.com/authorize",
            "my-client",
            "https://app.example.com/callback",
        )
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        scopes = params["scope"][0].split()
        assert "openid" in scopes
        assert "webid" in scopes

    def test_custom_scopes(self):
        auth_url, _, _ = start_auth_flow(
            "https://issuer.example.com/authorize",
            "my-client",
            "https://app.example.com/callback",
            scopes=["openid", "webid", "offline_access"],
        )
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        assert "offline_access" in params["scope"][0]

    def test_pkce_challenge_matches_verifier(self):
        auth_url, verifier, _ = start_auth_flow(
            "https://issuer.example.com/authorize",
            "my-client",
            "https://app.example.com/callback",
        )
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        challenge_in_url = params["code_challenge"][0]

        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert challenge_in_url == expected

    def test_unique_state_per_call(self):
        _, _, s1 = start_auth_flow("https://x/auth", "c", "https://x/cb")
        _, _, s2 = start_auth_flow("https://x/auth", "c", "https://x/cb")
        assert s1 != s2


class TestExchangeAuthCode:
    @pytest.mark.asyncio
    @respx.mock
    async def test_exchanges_code_for_tokens(self):
        token_response = {
            "access_token": "at-12345",
            "token_type": "DPoP",
            "expires_in": 3600,
            "id_token": "id.jwt.here",
        }
        respx.post("https://issuer.example.com/token").mock(
            return_value=httpx.Response(200, json=token_response)
        )
        key = DPoPKey()
        result = await exchange_auth_code(
            "https://issuer.example.com/token",
            "auth-code-xyz",
            "https://app.example.com/callback",
            "pkce-verifier-abc",
            "my-client",
            key,
        )
        assert result["access_token"] == "at-12345"
        assert result["id_token"] == "id.jwt.here"

    @pytest.mark.asyncio
    @respx.mock
    async def test_sends_correct_body(self):
        respx.post("https://issuer.example.com/token").mock(
            return_value=httpx.Response(200, json={"access_token": "x"})
        )
        key = DPoPKey()
        await exchange_auth_code(
            "https://issuer.example.com/token",
            "code-123",
            "https://app.example.com/cb",
            "verifier-456",
            "client-789",
            key,
        )
        sent = respx.calls[0].request
        body = urllib.parse.parse_qs(sent.content.decode())
        assert body["grant_type"] == ["authorization_code"]
        assert body["code"] == ["code-123"]
        assert body["redirect_uri"] == ["https://app.example.com/cb"]
        assert body["code_verifier"] == ["verifier-456"]
        assert body["client_id"] == ["client-789"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_sends_dpop_proof(self):
        respx.post("https://issuer.example.com/token").mock(
            return_value=httpx.Response(200, json={"access_token": "x"})
        )
        key = DPoPKey()
        await exchange_auth_code(
            "https://issuer.example.com/token",
            "code", "https://x/cb", "verifier", "client", key,
        )
        sent = respx.calls[0].request
        assert "dpop" in {k.lower() for k in sent.headers}

    @pytest.mark.asyncio
    @respx.mock
    async def test_dpop_nonce_retry(self):
        """Server requires a DPoP-Nonce — client retries."""
        respx.post("https://issuer.example.com/token").mock(
            side_effect=[
                httpx.Response(401, headers={"dpop-nonce": "server-nonce"}),
                httpx.Response(200, json={"access_token": "x"}),
            ]
        )
        key = DPoPKey()
        result = await exchange_auth_code(
            "https://issuer.example.com/token",
            "code", "https://x/cb", "verifier", "client", key,
        )
        assert result["access_token"] == "x"
        assert len(respx.calls) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_rejects_http_token_endpoint(self):
        """OIDC-16: Token endpoint must use TLS."""
        from pacific_solid._http.errors import SolidError
        key = DPoPKey()
        with pytest.raises(SolidError, match="insecure"):
            await exchange_auth_code(
                "http://remote.example.com/token",
                "code", "https://x/cb", "verifier", "client", key,
            )
