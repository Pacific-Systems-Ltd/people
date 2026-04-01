"""DPoP (Demonstration of Proof-of-Possession) proof generation and verification.

Bidirectional: client generates proofs, server verifies them.
RFC 9449: https://www.rfc-editor.org/rfc/rfc9449
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec


class DPoPKey:
    """An EC key pair for DPoP proof generation."""

    def __init__(self) -> None:
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()
        self._jwk = self._compute_jwk()
        self._thumbprint = self._compute_thumbprint()

    @property
    def jwk(self) -> dict[str, str]:
        """Public key as a JWK dict."""
        return dict(self._jwk)

    @property
    def thumbprint(self) -> str:
        """JWK thumbprint (RFC 7638) — used to bind DPoP key to token."""
        return self._thumbprint

    def sign_proof(
        self,
        htm: str,
        htu: str,
        *,
        nonce: str | None = None,
        ath: str | None = None,
    ) -> str:
        """Create a DPoP proof JWT.

        Args:
            htm: HTTP method (e.g. "GET", "POST")
            htu: HTTP target URI (without query/fragment)
            nonce: Server-provided DPoP-Nonce value
            ath: Access token hash (SHA256, base64url) for resource requests
        """
        now = int(time.time())
        payload: dict[str, str | int] = {
            "htm": htm,
            "htu": htu,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        if nonce:
            payload["nonce"] = nonce
        if ath:
            payload["ath"] = ath

        headers = {
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": self._jwk,
        }

        return jwt.encode(
            payload,
            self._private_key,
            algorithm="ES256",
            headers=headers,
        )

    def _compute_jwk(self) -> dict[str, str]:
        public_numbers = self._public_key.public_numbers()
        x_bytes = public_numbers.x.to_bytes(32, "big")
        y_bytes = public_numbers.y.to_bytes(32, "big")
        return {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(x_bytes).rstrip(b"=").decode(),
            "y": base64.urlsafe_b64encode(y_bytes).rstrip(b"=").decode(),
        }

    def _compute_thumbprint(self) -> str:
        """JWK Thumbprint per RFC 7638."""
        thumbprint_input = json.dumps(
            {
                "crv": self._jwk["crv"],
                "kty": self._jwk["kty"],
                "x": self._jwk["x"],
                "y": self._jwk["y"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return (
            base64.urlsafe_b64encode(
                hashlib.sha256(thumbprint_input.encode()).digest()
            )
            .rstrip(b"=")
            .decode()
        )


def compute_ath(access_token: str) -> str:
    """Compute the access token hash (ath) for DPoP resource requests.

    SHA256 of the access token, base64url-encoded without padding.
    """
    return (
        base64.urlsafe_b64encode(
            hashlib.sha256(access_token.encode()).digest()
        )
        .rstrip(b"=")
        .decode()
    )


def verify_dpop_proof(
    proof: str,
    access_token: str,
    method: str,
    url: str,
    *,
    max_age: int = 300,
    clock_skew: int = 60,
    seen_jti: set[str] | None = None,
) -> dict:
    """Verify a DPoP proof JWT (server-side).

    Args:
        proof: The DPoP proof JWT string
        access_token: The access token from the Authorization header
        method: The HTTP method of the request
        url: The HTTP URL of the request
        max_age: Maximum age of the proof in seconds (default 5 min)
        clock_skew: Allowed clock skew in seconds (default 60s)
        seen_jti: Optional set for replay prevention. If provided, the jti is
            checked for uniqueness and added to the set. Callers should use a
            TTL-bounded set and clear entries older than max_age + clock_skew.

    Returns:
        The decoded proof payload if valid.

    Raises:
        ValueError: If the proof is invalid.
    """
    # Decode header without verification first to get the JWK
    unverified_header = jwt.get_unverified_header(proof)

    if unverified_header.get("typ") != "dpop+jwt":
        raise ValueError("DPoP proof must have typ=dpop+jwt")
    if unverified_header.get("alg") != "ES256":
        raise ValueError("DPoP proof must use ES256 algorithm")

    jwk_data = unverified_header.get("jwk")
    if not jwk_data:
        raise ValueError("DPoP proof must include jwk in header")

    # Reconstruct the public key from the JWK
    public_key = _jwk_to_public_key(jwk_data)

    # Verify signature and decode
    payload = jwt.decode(
        proof,
        public_key,
        algorithms=["ES256"],
        options={
            "verify_exp": False,  # DPoP proofs use iat, not exp
            "verify_aud": False,
        },
    )

    # Verify htm (HTTP method)
    if payload.get("htm") != method:
        raise ValueError(f"DPoP htm mismatch: expected {method}, got {payload.get('htm')}")

    # Verify htu (HTTP target URI)
    if payload.get("htu") != url:
        raise ValueError(f"DPoP htu mismatch: expected {url}, got {payload.get('htu')}")

    # Verify iat (issued at) within acceptable range
    now = int(time.time())
    iat = payload.get("iat", 0)
    if iat > now + clock_skew:
        raise ValueError("DPoP proof issued in the future")
    if iat < now - max_age - clock_skew:
        raise ValueError("DPoP proof expired")

    # Verify jti exists and is not replayed
    jti = payload.get("jti")
    if not jti:
        raise ValueError("DPoP proof missing jti")
    if seen_jti is not None:
        if jti in seen_jti:
            raise ValueError("DPoP proof replayed — jti already seen")
        seen_jti.add(jti)

    # Verify ath (access token hash)
    # RFC 9449: ath is REQUIRED when DPoP proof is used with an access token
    if access_token:
        if "ath" not in payload:
            raise ValueError("DPoP proof missing ath claim — required for resource requests")
        expected_ath = compute_ath(access_token)
        if payload["ath"] != expected_ath:
            raise ValueError("DPoP ath mismatch — access token hash doesn't match")

    # Reject private keys in JWK (RFC 9449 Section 4.3)
    if "d" in jwk_data:
        raise ValueError("DPoP JWK must not contain private key")

    return payload


def _jwk_to_public_key(jwk_data: dict) -> ec.EllipticCurvePublicKey:
    """Reconstruct an EC public key from JWK data."""
    if jwk_data.get("kty") != "EC" or jwk_data.get("crv") != "P-256":
        raise ValueError("DPoP JWK must be EC P-256")

    x = jwk_data["x"]
    y = jwk_data["y"]

    # Add base64url padding
    x_bytes = base64.urlsafe_b64decode(x + "==")
    y_bytes = base64.urlsafe_b64decode(y + "==")

    x_int = int.from_bytes(x_bytes, "big")
    y_int = int.from_bytes(y_bytes, "big")

    public_numbers = ec.EllipticCurvePublicNumbers(x_int, y_int, ec.SECP256R1())
    return public_numbers.public_key()
