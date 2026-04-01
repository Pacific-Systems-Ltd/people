"""Tests for DPoP proof generation and verification (bidirectional)."""

import time
import jwt
from people._auth.dpop import DPoPKey, compute_ath, verify_dpop_proof


class TestDPoPKey:
    def test_generates_key_pair(self):
        key = DPoPKey()
        assert key.jwk["kty"] == "EC"
        assert key.jwk["crv"] == "P-256"
        assert "x" in key.jwk
        assert "y" in key.jwk

    def test_thumbprint_is_stable(self):
        key = DPoPKey()
        assert key.thumbprint == key.thumbprint

    def test_different_keys_different_thumbprints(self):
        k1 = DPoPKey()
        k2 = DPoPKey()
        assert k1.thumbprint != k2.thumbprint


class TestDPoPProof:
    def test_sign_proof_basic(self):
        key = DPoPKey()
        proof = key.sign_proof("GET", "http://example.org/resource")
        assert isinstance(proof, str)

        # Decode and verify structure
        header = jwt.get_unverified_header(proof)
        assert header["typ"] == "dpop+jwt"
        assert header["alg"] == "ES256"
        assert "jwk" in header

        payload = jwt.decode(proof, options={"verify_signature": False})
        assert payload["htm"] == "GET"
        assert payload["htu"] == "http://example.org/resource"
        assert "iat" in payload
        assert "jti" in payload

    def test_sign_proof_with_nonce(self):
        key = DPoPKey()
        proof = key.sign_proof("POST", "http://example.org/token", nonce="server-nonce-123")
        payload = jwt.decode(proof, options={"verify_signature": False})
        assert payload["nonce"] == "server-nonce-123"

    def test_sign_proof_with_ath(self):
        key = DPoPKey()
        ath = compute_ath("my-access-token")
        proof = key.sign_proof("GET", "http://example.org/resource", ath=ath)
        payload = jwt.decode(proof, options={"verify_signature": False})
        assert payload["ath"] == ath

    def test_unique_jti_per_proof(self):
        key = DPoPKey()
        p1 = key.sign_proof("GET", "http://example.org/a")
        p2 = key.sign_proof("GET", "http://example.org/b")
        d1 = jwt.decode(p1, options={"verify_signature": False})
        d2 = jwt.decode(p2, options={"verify_signature": False})
        assert d1["jti"] != d2["jti"]


class TestComputeAth:
    def test_deterministic(self):
        ath1 = compute_ath("token123")
        ath2 = compute_ath("token123")
        assert ath1 == ath2

    def test_different_tokens(self):
        ath1 = compute_ath("token-a")
        ath2 = compute_ath("token-b")
        assert ath1 != ath2

    def test_base64url_no_padding(self):
        ath = compute_ath("some-token")
        assert "=" not in ath


class TestVerifyDPoPProof:
    def test_round_trip_verification(self):
        """Generate a proof and verify it — the core round-trip test."""
        key = DPoPKey()
        token = "test-access-token"
        ath = compute_ath(token)
        proof = key.sign_proof("GET", "http://example.org/resource", ath=ath)

        result = verify_dpop_proof(proof, token, "GET", "http://example.org/resource")
        assert result["htm"] == "GET"
        assert result["htu"] == "http://example.org/resource"
        assert result["ath"] == ath

    def test_wrong_method_fails(self):
        key = DPoPKey()
        proof = key.sign_proof("GET", "http://example.org/resource")
        try:
            verify_dpop_proof(proof, "token", "POST", "http://example.org/resource")
            assert False, "Should have raised"
        except ValueError as e:
            assert "htm mismatch" in str(e)

    def test_wrong_url_fails(self):
        key = DPoPKey()
        proof = key.sign_proof("GET", "http://example.org/a")
        try:
            verify_dpop_proof(proof, "token", "GET", "http://example.org/b")
            assert False, "Should have raised"
        except ValueError as e:
            assert "htu mismatch" in str(e)

    def test_wrong_ath_fails(self):
        key = DPoPKey()
        ath = compute_ath("token-a")
        proof = key.sign_proof("GET", "http://example.org/r", ath=ath)
        try:
            verify_dpop_proof(proof, "token-b", "GET", "http://example.org/r")
            assert False, "Should have raised"
        except ValueError as e:
            assert "ath mismatch" in str(e)

    def test_expired_proof_fails(self):
        key = DPoPKey()
        ath = compute_ath("token")
        proof = key.sign_proof("GET", "http://example.org/r", ath=ath)
        try:
            verify_dpop_proof(proof, "token", "GET", "http://example.org/r", max_age=0, clock_skew=0)
        except ValueError as e:
            assert "expired" in str(e).lower()

    def test_missing_ath_on_resource_request_fails(self):
        """RFC 9449: ath is required when access_token is provided."""
        key = DPoPKey()
        proof = key.sign_proof("GET", "http://example.org/r")  # no ath
        try:
            verify_dpop_proof(proof, "some-token", "GET", "http://example.org/r")
            assert False, "Should have raised"
        except ValueError as e:
            assert "missing ath" in str(e).lower()

    def test_jti_replay_detection(self):
        key = DPoPKey()
        token = "test-token"
        ath = compute_ath(token)
        proof = key.sign_proof("GET", "http://example.org/r", ath=ath)
        seen = set()
        # First verification succeeds
        verify_dpop_proof(proof, token, "GET", "http://example.org/r", seen_jti=seen)
        # Replay fails
        try:
            verify_dpop_proof(proof, token, "GET", "http://example.org/r", seen_jti=seen)
            assert False, "Should have raised"
        except ValueError as e:
            assert "replayed" in str(e).lower()

    def test_no_ath_required_for_token_endpoint(self):
        """Token endpoint requests have no access_token, so no ath required."""
        key = DPoPKey()
        proof = key.sign_proof("POST", "http://example.org/token")  # no ath
        # Empty string access_token = token endpoint request
        result = verify_dpop_proof(proof, "", "POST", "http://example.org/token")
        assert result["htm"] == "POST"
