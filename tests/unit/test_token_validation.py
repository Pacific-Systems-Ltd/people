"""Tests for OIDC ID Token validation (OIDC-09) and issuer verification (OIDC-10)."""

import time

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import ec
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._auth.token_validation import validate_id_token, verify_webid_issuer
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._http.errors import AuthenticationError


def _make_client() -> AuthenticatedClient:
    return AuthenticatedClient(
        dpop_key=DPoPKey(),
        access_token="test-token",
        token_expires_at=9999999999.0,
    )


def _generate_issuer_keys():
    """Generate an EC P-256 key pair and return (private_key, jwks_dict)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    import base64

    def _b64url(n: int, length: int) -> str:
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()

    jwks = {
        "keys": [{
            "kty": "EC",
            "crv": "P-256",
            "x": _b64url(public_numbers.x, 32),
            "y": _b64url(public_numbers.y, 32),
            "kid": "test-key-1",
            "use": "sig",
            "alg": "ES256",
        }],
    }
    return private_key, jwks


def _sign_id_token(
    private_key,
    issuer: str = "https://issuer.example.com",
    audience: str = "test-client-id",
    subject: str = "user-123",
    webid: str | None = None,
    exp_offset: int = 3600,
    kid: str = "test-key-1",
) -> str:
    """Sign an ID Token JWT with the given claims."""
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "iat": now,
        "exp": now + exp_offset,
    }
    if webid:
        payload["webid"] = webid
    return jwt.encode(
        payload, private_key, algorithm="ES256",
        headers={"kid": kid, "alg": "ES256"},
    )


class TestValidateIdToken:
    @pytest.mark.asyncio
    @respx.mock
    async def test_valid_token_accepted(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key)

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        claims = await validate_id_token(
            token, "https://issuer.example.com", "test-client-id",
            "https://issuer.example.com/.well-known/jwks.json",
        )
        assert claims["iss"] == "https://issuer.example.com"
        assert claims["sub"] == "user-123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_wrong_issuer_rejected(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key, issuer="https://evil.example.com")

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        with pytest.raises(AuthenticationError, match="issuer"):
            await validate_id_token(
                token, "https://issuer.example.com", "test-client-id",
                "https://issuer.example.com/.well-known/jwks.json",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_wrong_audience_rejected(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key, audience="other-client")

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        with pytest.raises(AuthenticationError, match="audience"):
            await validate_id_token(
                token, "https://issuer.example.com", "test-client-id",
                "https://issuer.example.com/.well-known/jwks.json",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_expired_token_rejected(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key, exp_offset=-3600)  # expired 1h ago

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        with pytest.raises(AuthenticationError, match="expired"):
            await validate_id_token(
                token, "https://issuer.example.com", "test-client-id",
                "https://issuer.example.com/.well-known/jwks.json",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_tampered_signature_rejected(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key)
        # Tamper with the signature by changing the last character
        parts = token.rsplit(".", 1)
        tampered = parts[0] + "." + parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        with pytest.raises(AuthenticationError, match="signature"):
            await validate_id_token(
                tampered, "https://issuer.example.com", "test-client-id",
                "https://issuer.example.com/.well-known/jwks.json",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_jwks_fetch_failure_raises(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(private_key)

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(AuthenticationError, match="Failed to fetch JWKS"):
            await validate_id_token(
                token, "https://issuer.example.com", "test-client-id",
                "https://issuer.example.com/.well-known/jwks.json",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_with_webid_claim(self):
        private_key, jwks = _generate_issuer_keys()
        token = _sign_id_token(
            private_key, webid="https://pod.example.com/alice/profile/card#me",
        )

        respx.get("https://issuer.example.com/.well-known/jwks.json").mock(
            return_value=httpx.Response(200, json=jwks)
        )

        claims = await validate_id_token(
            token, "https://issuer.example.com", "test-client-id",
            "https://issuer.example.com/.well-known/jwks.json",
        )
        assert claims["webid"] == "https://pod.example.com/alice/profile/card#me"


class TestVerifyWebIDIssuer:
    @pytest.mark.asyncio
    @respx.mock
    async def test_matching_issuer_passes(self):
        turtle = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
<#me> solid:oidcIssuer <https://issuer.example.com> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        # Should not raise
        await verify_webid_issuer(
            "https://pod.example.com/alice/profile/card",
            "https://issuer.example.com",
            client,
        )
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_matching_issuer_rejected(self):
        turtle = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
<#me> solid:oidcIssuer <https://legit-issuer.example.com> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        with pytest.raises(AuthenticationError, match="not authorised"):
            await verify_webid_issuer(
                "https://pod.example.com/alice/profile/card",
                "https://evil-issuer.example.com",
                client,
            )
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_issuers_in_profile_rejected(self):
        turtle = """\
@prefix foaf: <http://xmlns.com/foaf/0.1/>.
<#me> foaf:name "Alice" .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        with pytest.raises(AuthenticationError, match="no solid:oidcIssuer"):
            await verify_webid_issuer(
                "https://pod.example.com/alice/profile/card",
                "https://issuer.example.com",
                client,
            )
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_trailing_slash_normalisation(self):
        """Issuer URLs with/without trailing slash should match."""
        turtle = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
<#me> solid:oidcIssuer <https://issuer.example.com/> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        # No trailing slash in expected — should still match
        await verify_webid_issuer(
            "https://pod.example.com/alice/profile/card",
            "https://issuer.example.com",
            client,
        )
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_multiple_issuers_any_match(self):
        """WebID with multiple issuers — any match is accepted."""
        turtle = """\
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
<#me>
    solid:oidcIssuer <https://issuer-a.example.com> ;
    solid:oidcIssuer <https://issuer-b.example.com> .
"""
        respx.get("https://pod.example.com/alice/profile/card").mock(
            return_value=httpx.Response(
                200, text=turtle, headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        await verify_webid_issuer(
            "https://pod.example.com/alice/profile/card",
            "https://issuer-b.example.com",
            client,
        )
        await client.close()
