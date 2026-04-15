"""Hostile client tests — server building blocks face crafted attacks.

These tests verify that verify_dpop, evaluate_wac, and apply_patch
correctly reject malicious inputs. Every test assumes the caller is
an attacker trying to bypass authentication or authorization.
"""

import time
import uuid

import jwt
import pytest
from people._acl.wac import evaluate_wac
from people._auth.dpop import DPoPKey, compute_ath, verify_dpop_proof
from people._graph.graph import Graph
from people._graph.triple import URI, Literal
from people._rdf.namespaces import ACL, RDF
from people._rdf.patch import build_n3_patch

# ============================================================
# 1. DPoP PROOF ATTACKS
# ============================================================


class TestDPoPForgery:
    """Attacker crafts DPoP proofs to bypass authentication."""

    def test_wrong_algorithm(self):
        """Attacker uses HS256 (symmetric) instead of ES256.

        HS256 with a known secret would let anyone forge proofs.
        """
        # Create a proof with HS256
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        fake_proof = jwt.encode(payload, "secret", algorithm="HS256", headers={
            "typ": "dpop+jwt",
            "alg": "HS256",
            "jwk": {"kty": "oct", "k": "secret"},
        })
        with pytest.raises(ValueError, match="ES256"):
            verify_dpop_proof(fake_proof, "", "GET", "http://pod/resource")

    def test_missing_typ_header(self):
        """Attacker sends a regular JWT instead of a DPoP proof."""
        key = DPoPKey()
        # Manually create a JWT without typ=dpop+jwt
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        fake = jwt.encode(payload, key._private_key, algorithm="ES256", headers={
            "typ": "JWT",  # wrong type
            "alg": "ES256",
            "jwk": key.jwk,
        })
        with pytest.raises(ValueError, match="dpop\\+jwt"):
            verify_dpop_proof(fake, "", "GET", "http://pod/resource")

    def test_no_jwk_in_header(self):
        """Attacker omits the JWK from the proof header."""
        key = DPoPKey()
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        fake = jwt.encode(payload, key._private_key, algorithm="ES256", headers={
            "typ": "dpop+jwt",
            "alg": "ES256",
            # no jwk
        })
        with pytest.raises(ValueError, match="jwk"):
            verify_dpop_proof(fake, "", "GET", "http://pod/resource")

    def test_proof_signed_with_different_key(self):
        """Attacker signs proof with key A but includes key B's JWK in the header.

        Signature verification must fail because the JWK doesn't match the signer.
        """
        key_a = DPoPKey()
        key_b = DPoPKey()
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        # Sign with key A but claim to be key B
        fake = jwt.encode(payload, key_a._private_key, algorithm="ES256", headers={
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": key_b.jwk,  # key B's public key
        })
        with pytest.raises((ValueError, jwt.exceptions.InvalidSignatureError)):
            verify_dpop_proof(fake, "", "GET", "http://pod/resource")

    def test_private_key_in_jwk_rejected(self):
        """Attacker includes private key component in the JWK header.

        RFC 9449: JWK MUST NOT contain private key.
        """
        key = DPoPKey()
        ath = compute_ath("token")
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
            "ath": ath,
        }
        jwk_with_private = dict(key.jwk)
        jwk_with_private["d"] = "fake-private-key-component"
        fake = jwt.encode(payload, key._private_key, algorithm="ES256", headers={
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": jwk_with_private,
        })
        with pytest.raises(ValueError, match="private key"):
            verify_dpop_proof(fake, "token", "GET", "http://pod/resource")

    def test_future_proof_rejected(self):
        """Attacker sets iat to the future (pre-generated proofs for later use).

        PyJWT's built-in iat validation catches this before our code does.
        That's correct — two layers of defense.
        """
        key = DPoPKey()
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()) + 3600,  # 1 hour in the future
            "jti": str(uuid.uuid4()),
        }
        proof = jwt.encode(payload, key._private_key, algorithm="ES256", headers={
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": key.jwk,
        })
        with pytest.raises((ValueError, jwt.exceptions.ImmatureSignatureError)):
            verify_dpop_proof(proof, "", "GET", "http://pod/resource", clock_skew=60)

    def test_replay_attack(self):
        """Attacker captures and replays a valid DPoP proof."""
        key = DPoPKey()
        token = "legitimate-token"
        ath = compute_ath(token)
        proof = key.sign_proof("GET", "http://pod/resource", ath=ath)

        seen = set()
        # First use: legitimate
        verify_dpop_proof(proof, token, "GET", "http://pod/resource", seen_jti=seen)

        # Replay: must fail
        with pytest.raises(ValueError, match="replayed"):
            verify_dpop_proof(proof, token, "GET", "http://pod/resource", seen_jti=seen)

    def test_method_confusion(self):
        """Attacker captures a GET proof and uses it for a DELETE request."""
        key = DPoPKey()
        ath = compute_ath("token")
        proof = key.sign_proof("GET", "http://pod/resource", ath=ath)
        with pytest.raises(ValueError, match="htm mismatch"):
            verify_dpop_proof(proof, "token", "DELETE", "http://pod/resource")

    def test_url_confusion(self):
        """Attacker captures a proof for /public and uses it for /private."""
        key = DPoPKey()
        ath = compute_ath("token")
        proof = key.sign_proof("GET", "http://pod/public", ath=ath)
        with pytest.raises(ValueError, match="htu mismatch"):
            verify_dpop_proof(proof, "token", "GET", "http://pod/private")

    def test_ath_token_swap(self):
        """Attacker has proof for token A, tries to use it with stolen token B."""
        key = DPoPKey()
        token_a = "victim-token"
        token_b = "attacker-token"
        ath = compute_ath(token_a)
        proof = key.sign_proof("GET", "http://pod/resource", ath=ath)

        with pytest.raises(ValueError, match="ath mismatch"):
            verify_dpop_proof(proof, token_b, "GET", "http://pod/resource")

    def test_missing_jti(self):
        """Attacker removes jti to bypass replay detection."""
        key = DPoPKey()
        payload = {
            "htm": "GET",
            "htu": "http://pod/resource",
            "iat": int(time.time()),
            # no jti
        }
        proof = jwt.encode(payload, key._private_key, algorithm="ES256", headers={
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": key.jwk,
        })
        with pytest.raises(ValueError, match="jti"):
            verify_dpop_proof(proof, "", "GET", "http://pod/resource")


# ============================================================
# 2. WAC AUTHORIZATION BYPASS ATTACKS
# ============================================================


class TestWACBypass:
    """Attacker tries to access resources they shouldn't have access to."""

    def _make_acl(self, rules: list[dict]) -> Graph:
        """Build an ACL graph from a list of rule dicts."""
        g = Graph()
        for i, rule in enumerate(rules):
            rule_uri = URI(f"http://pod/.acl#rule{i}")
            g.add(rule_uri, URI(str(RDF.type)), ACL.Authorization)
            if "agent" in rule:
                g.add(rule_uri, ACL.agent, URI(rule["agent"]))
            if "agent_class" in rule:
                g.add(rule_uri, ACL.agentClass, URI(rule["agent_class"]))
            if "resource" in rule:
                g.add(rule_uri, ACL.accessTo, URI(rule["resource"]))
            if "default" in rule:
                g.add(rule_uri, ACL.default, URI(rule["default"]))
            for mode in rule.get("modes", []):
                g.add(rule_uri, ACL.mode, URI(mode))
        return g

    def test_path_traversal_via_default_acl(self):
        """Attacker accesses /alice/public-secrets/ through /alice/public/ default ACL.

        This is the P1 bug we fixed. Verify the fix holds.
        """
        acl = self._make_acl([{
            "agent": "http://attacker/card#me",
            "default": "http://pod/alice/public",  # no trailing slash
            "modes": [str(ACL.Read)],
        }])

        # Should have access to children of /alice/public/
        assert evaluate_wac(
            "http://attacker/card#me", acl, "GET",
            "http://pod/alice/public/doc.ttl"
        )
        # MUST NOT have access to /alice/public-secrets/
        assert not evaluate_wac(
            "http://attacker/card#me", acl, "GET",
            "http://pod/alice/public-secrets/medical.ttl"
        )

    def test_impersonation_via_different_webid(self):
        """Attacker uses their own WebID but claims to be someone else.

        WAC evaluates against the WebID in the token, not a request parameter.
        """
        acl = self._make_acl([{
            "agent": "http://pod/alice/card#me",
            "resource": "http://pod/alice/health",
            "modes": [str(ACL.Read)],
        }])

        # Alice can access
        assert evaluate_wac("http://pod/alice/card#me", acl, "GET", "http://pod/alice/health")
        # Attacker cannot
        assert not evaluate_wac("http://attacker/card#me", acl, "GET", "http://pod/alice/health")

    def test_write_as_append_only_agent(self):
        """Attacker has Append-only access but tries to DELETE (requires Write)."""
        acl = self._make_acl([{
            "agent": "http://attacker/card#me",
            "resource": "http://pod/data",
            "modes": [str(ACL.Append)],
        }])

        assert evaluate_wac("http://attacker/card#me", acl, "POST", "http://pod/data")
        assert not evaluate_wac("http://attacker/card#me", acl, "DELETE", "http://pod/data")
        assert not evaluate_wac("http://attacker/card#me", acl, "PUT", "http://pod/data")

    def test_patch_with_deletes_requires_write(self):
        """Attacker has Append access, sends PATCH with solid:deletes.

        Per Solid spec, PATCH with deletes requires Write, not just Append.
        """
        acl = self._make_acl([{
            "agent": "http://attacker/card#me",
            "resource": "http://pod/data",
            "modes": [str(ACL.Append)],
        }])

        # Insert-only PATCH: allowed (Append suffices)
        assert evaluate_wac(
            "http://attacker/card#me", acl, "PATCH", "http://pod/data",
            patch_has_deletes=False,
        )
        # PATCH with deletes: denied (needs Write)
        assert not evaluate_wac(
            "http://attacker/card#me", acl, "PATCH", "http://pod/data",
            patch_has_deletes=True,
        )

    def test_empty_acl_denies_everything(self):
        """An ACL with no rules should deny all access."""
        acl = Graph()  # empty
        assert not evaluate_wac("http://anyone/card#me", acl, "GET", "http://pod/data")
        assert not evaluate_wac("http://anyone/card#me", acl, "PUT", "http://pod/data")

    def test_acl_without_modes_denies(self):
        """An ACL rule that names an agent but grants no modes."""
        acl = self._make_acl([{
            "agent": "http://alice/card#me",
            "resource": "http://pod/data",
            "modes": [],  # no modes granted
        }])
        assert not evaluate_wac("http://alice/card#me", acl, "GET", "http://pod/data")

    def test_acl_without_resource_scope(self):
        """ACL rule has agent and modes but no accessTo or default.

        Should not grant access to anything.
        """
        g = Graph()
        rule = URI("http://pod/.acl#rule1")
        g.add(rule, URI(str(RDF.type)), ACL.Authorization)
        g.add(rule, ACL.agent, URI("http://alice/card#me"))
        g.add(rule, ACL.mode, ACL.Read)
        # no accessTo or default

        # With no resource_url check, this WOULD grant access (bad)
        # With resource_url check, it must deny
        assert not evaluate_wac(
            "http://alice/card#me", g, "GET", "http://pod/data"
        )

    def test_control_mode_does_not_imply_read(self):
        """Having Control on an ACL doesn't mean you can Read the resource itself.

        Control lets you modify the .acl, not read the data.
        """
        acl = self._make_acl([{
            "agent": "http://admin/card#me",
            "resource": "http://pod/data",
            "modes": [str(ACL.Control)],
        }])
        assert not evaluate_wac("http://admin/card#me", acl, "GET", "http://pod/data")


# ============================================================
# 3. N3 PATCH ATTACKS
# ============================================================


class TestPatchAttacks:
    """Attacker crafts malicious N3 Patches."""

    def test_patch_build_empty_raises(self):
        """Building a patch with no inserts or deletes must fail, not produce garbage."""
        with pytest.raises(ValueError, match="no inserts or deletes"):
            build_n3_patch([], [])

    def test_patch_builder_escapes_quotes_in_literals(self):
        """Attacker includes quotes in literal values to break N3 syntax."""
        from people import Triple
        payload = '"; <http://evil> <http://evil> "injection'
        inserts = [
            Triple(URI("http://ex/s"), URI("http://ex/p"), Literal(payload)),
        ]
        body = build_n3_patch(inserts, [])
        # The quotes must be escaped
        assert '\\"' in body
        # The injection attempt must be inside a quoted string, not free
        assert '<http://evil>' not in body.split('"')[0]

    def test_patch_with_special_characters_in_uris(self):
        """URIs with special characters in N3 Patch."""
        from people import Triple
        inserts = [
            Triple(URI("http://ex/s"), URI("http://ex/p"), URI("http://ex/o?query=1&foo=bar")),
        ]
        body = build_n3_patch(inserts, [])
        assert "http://ex/o?query=1&foo=bar" in body
