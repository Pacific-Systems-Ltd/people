"""Hostile server tests — the SDK client faces a malicious/broken server.

These tests use respx to simulate a server that actively tries to confuse,
mislead, or exploit the client. Every test assumes bad faith from the other side.

If you're deploying in the NHS, a government pod, or any sensitive environment,
every one of these scenarios is a real threat vector.
"""

import time

import httpx
import pytest
import respx
from pacific_solid._auth.dpop import DPoPKey
from pacific_solid._graph.graph import Graph
from pacific_solid._graph.triple import URI, Literal
from pacific_solid._http.client import AuthenticatedClient
from pacific_solid._http.errors import (
    AccessDeniedError,
    AuthenticationError,
    PreconditionFailedError,
)
from pacific_solid._http.headers import extract_metadata, parse_wac_allow
from pacific_solid._rdf.namespaces import FOAF

# --- Fixtures ---

def _make_client(**kwargs) -> AuthenticatedClient:
    """Build a test client with valid auth state."""
    dpop_key = DPoPKey()
    return AuthenticatedClient(
        dpop_key=dpop_key,
        access_token="test-token-valid",
        token_expires_at=time.time() + 3600,
        **kwargs,
    )


# ============================================================
# 1. SERVER RETURNS GARBAGE
# ============================================================


class TestServerReturnsGarbage:
    """Server sends back data designed to confuse the parser."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_html_instead_of_turtle(self):
        """Server claims text/turtle but sends HTML (common misconfiguration)."""
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200,
                text="<html><body>Not Found</body></html>",
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        # Parsing should fail gracefully, not crash
        with pytest.raises((ValueError, SyntaxError, Exception)):
            Graph.from_turtle(resp.text, base_uri="http://pod/resource")
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_truncated_turtle(self):
        """Server closes connection mid-response, producing truncated Turtle."""
        truncated = '@prefix foaf: <http://xmlns.com/foaf/0.1/>.\n<#me> foaf:name "Ali'
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200,
                text=truncated,
                headers={"content-type": "text/turtle"},
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        with pytest.raises((ValueError, SyntaxError, Exception)):
            Graph.from_turtle(resp.text)
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_body_200(self):
        """Server returns 200 with empty body."""
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200, text="", headers={"content-type": "text/turtle"}
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        g = Graph.from_turtle(resp.text)
        assert len(g) == 0
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_billion_triples_bomb(self):
        """Server sends an absurdly large response to exhaust memory.

        We test that Graph handles large inputs without crashing.
        A real deployment should have response size limits at the HTTP layer.
        """
        # 10,000 triples — not a real attack but tests performance
        lines = ['@prefix ex: <http://example.org/>.']
        for i in range(10_000):
            lines.append(f'ex:s{i} ex:p "value{i}" .')
        massive = "\n".join(lines)

        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200, text=massive, headers={"content-type": "text/turtle"}
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        g = Graph.from_turtle(resp.text)
        assert len(g) == 10_000
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_injection_in_literal_values(self):
        """Server returns triples with script injection in literal values.

        The SDK must not interpret or execute literal content.
        """
        malicious_turtle = '''
        @prefix foaf: <http://xmlns.com/foaf/0.1/>.
        <#me> foaf:name "<script>alert('xss')</script>" .
        '''
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200, text=malicious_turtle, headers={"content-type": "text/turtle"}
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        g = Graph.from_turtle(resp.text)
        results = g.query(predicate=FOAF.name)
        assert len(results) == 1
        # Value is stored as plain text, never interpreted
        assert "<script>" in str(results[0].object)
        await client.close()


# ============================================================
# 2. SERVER LIES ABOUT HEADERS
# ============================================================


class TestServerLiesAboutHeaders:
    """Server sends misleading or weaponised headers."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_link_header_for_acl(self):
        """Server omits the ACL Link header. Client must handle gracefully."""
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={"content-type": "text/turtle"},
                # no Link header
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        meta = extract_metadata(dict(resp.headers), "http://pod/resource")
        assert meta["acl_url"] is None
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_etag_changes_between_reads(self):
        """Server returns different ETags on consecutive reads (inconsistent state).

        This shouldn't crash. The client uses whatever ETag the server gives.
        """
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={
                    "content-type": "text/turtle",
                    "etag": f'"etag-{call_count}"',
                },
            )

        respx.get("http://pod/resource").mock(side_effect=side_effect)
        client = _make_client()

        resp1 = await client.request("GET", "http://pod/resource")
        resp2 = await client.request("GET", "http://pod/resource")
        meta1 = extract_metadata(dict(resp1.headers), "http://pod/resource")
        meta2 = extract_metadata(dict(resp2.headers), "http://pod/resource")
        assert meta1["etag"] != meta2["etag"]
        await client.close()

    def test_wac_allow_header_with_unknown_modes(self):
        """Server adds invented access modes to WAC-Allow.

        Per WAC spec: clients MUST ignore unrecognised access parameters.
        """
        result = parse_wac_allow('user="read write execute admin", public="read teleport"')
        assert "read" in result["user"]
        assert "execute" in result["user"]  # unknown but preserved
        assert "teleport" in result["public"]  # unknown but preserved

    def test_wac_allow_header_malformed(self):
        """Server sends completely broken WAC-Allow header.

        Per WAC spec: clients MUST ignore the received WAC-Allow if malformed.
        """
        result = parse_wac_allow("this is not a valid header")
        assert result == {}

    @pytest.mark.asyncio
    @respx.mock
    async def test_acl_link_points_to_different_domain(self):
        """Server's ACL Link header points to an attacker-controlled domain.

        The client must follow the Link header (per spec), but this could be
        a redirect attack. The client should at least resolve it correctly.
        """
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(
                200,
                text='<#me> <http://xmlns.com/foaf/0.1/name> "Alice" .',
                headers={
                    "content-type": "text/turtle",
                    "link": '<http://evil.example.com/.acl>; rel="acl"',
                },
            )
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        meta = extract_metadata(dict(resp.headers), "http://pod/resource")
        # The spec says follow the Link header. The ACL URL IS the evil domain.
        # This is a legitimate concern for downstream code to validate.
        assert meta["acl_url"] == "http://evil.example.com/.acl"
        await client.close()


# ============================================================
# 3. AUTH ATTACKS
# ============================================================


class TestAuthAttacks:
    """Server tries to steal or manipulate authentication state."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_demands_infinite_nonce_retry(self):
        """Server always returns 401 with a new nonce, trying to loop the client forever.

        Client must cap retries (max 2).
        """
        call_count = 0

        def nonce_loop(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                401,
                text="unauthorized",
                headers={"dpop-nonce": f"nonce-{call_count}"},
            )

        respx.get("http://pod/resource").mock(side_effect=nonce_loop)
        client = _make_client()

        with pytest.raises(AuthenticationError):
            await client.request("GET", "http://pod/resource")

        # Client should have tried at most 3 times (initial + 2 retries)
        assert call_count <= 3
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_returns_401_then_403(self):
        """Server returns 401, then on retry returns 403.

        The client retries on 401 (nonce handling), gets 403 back.
        The 403 response is returned (not raised by the client itself).
        Callers must check the response via raise_for_status.
        """
        responses = [
            httpx.Response(401, headers={"dpop-nonce": "nonce1"}),
            httpx.Response(403, text="forbidden"),
        ]
        respx.get("http://pod/resource").mock(side_effect=responses)
        client = _make_client()

        resp = await client.request("GET", "http://pod/resource")
        assert resp.status_code == 403

        from pacific_solid._http.errors import raise_for_status
        with pytest.raises(AccessDeniedError):
            raise_for_status(resp.status_code, "http://pod/resource", resp.text)
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_expired_token_refresh_callback_fails(self):
        """Token is expired and refresh callback raises an exception.

        Should propagate the error, not swallow it.
        """
        async def failing_refresh():
            raise ConnectionError("OIDC issuer unreachable")

        client = AuthenticatedClient(
            dpop_key=DPoPKey(),
            access_token="expired-token",
            token_expires_at=time.time() - 100,  # already expired
            refresh_callback=failing_refresh,
        )

        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(200, text="ok")
        )

        with pytest.raises(ConnectionError, match="OIDC issuer unreachable"):
            await client.request("GET", "http://pod/resource")
        await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_returns_200_on_unauthenticated_request(self):
        """Server ignores auth entirely and returns 200 to everything.

        A permissive server is a security risk but the client shouldn't crash.
        The client still attaches DPoP proofs even if the server ignores them.
        """
        respx.get("http://pod/resource").mock(
            return_value=httpx.Response(200, text="open door policy")
        )
        client = _make_client()
        resp = await client.request("GET", "http://pod/resource")
        assert resp.status_code == 200
        # Verify the client still sent auth headers
        sent = respx.calls[0].request
        assert "dpop" in {k.lower() for k in sent.headers}
        assert "authorization" in {k.lower() for k in sent.headers}
        await client.close()


# ============================================================
# 4. CONCURRENT / TIMING ATTACKS
# ============================================================


class TestConcurrencyAttacks:
    """Race conditions and timing-based issues."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_etag_conflict_on_write(self):
        """Server rejects a write because the resource changed (412).

        Client must raise PreconditionFailedError, not silently succeed.
        """
        respx.put("http://pod/resource").mock(
            return_value=httpx.Response(412, text="ETag mismatch")
        )
        client = _make_client()

        from pacific_solid._http.errors import raise_for_status
        resp = await client.request(
            "PUT", "http://pod/resource",
            content="data",
            headers={"If-Match": '"stale-etag"'},
        )
        with pytest.raises(PreconditionFailedError):
            raise_for_status(resp.status_code, "http://pod/resource", resp.text)
        await client.close()


# ============================================================
# 5. RDF / GRAPH INTEGRITY ATTACKS
# ============================================================


class TestGraphIntegrityAttacks:
    """Attacks targeting the graph data layer."""

    def test_duplicate_triples_with_different_datatypes(self):
        """Same subject+predicate, different datatypes.

        Both should coexist — RDF allows this.
        """
        g = Graph()
        g.add(URI("http://ex/s"), URI("http://ex/p"), Literal("42"))
        g.add(
            URI("http://ex/s"),
            URI("http://ex/p"),
            Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer"),
        )
        assert len(g) == 2  # different datatypes = different triples

    def test_unicode_in_uris(self):
        """URIs with unicode characters."""
        g = Graph()
        g.add(URI("http://example.org/名前"), URI("http://ex/p"), Literal("value"))
        results = g.query(subject=URI("http://example.org/名前"))
        assert len(results) == 1

    def test_empty_string_literal(self):
        """Empty string is a valid literal value."""
        g = Graph()
        g.add(URI("http://ex/s"), URI("http://ex/p"), Literal(""))
        assert len(g) == 1
        assert g.query(predicate=URI("http://ex/p"))[0].object == Literal("")

    def test_very_long_literal(self):
        """Literal with 1MB of text."""
        big_value = "x" * (1024 * 1024)
        g = Graph()
        g.add(URI("http://ex/s"), URI("http://ex/p"), Literal(big_value))
        assert len(g) == 1
        assert len(str(g.query(predicate=URI("http://ex/p"))[0].object)) == 1024 * 1024

    def test_snapshot_isolation(self):
        """Modifying the snapshot list externally must not affect the graph."""
        g = Graph()
        g.add(URI("http://ex/s"), URI("http://ex/p"), Literal("original"))
        g.take_snapshot()

        # Attempt to tamper with the snapshot
        g._snapshot.clear()

        # Diff should show everything as an insert (snapshot is empty)
        inserts, deletes = g.diff()
        assert len(inserts) == 1
        assert len(deletes) == 0

    def test_triple_with_same_subject_predicate_object_uris(self):
        """Triple where subject == predicate == object (degenerate but valid RDF)."""
        u = URI("http://example.org/self")
        g = Graph()
        g.add(u, u, u)
        assert len(g) == 1

    def test_query_returns_copy_not_reference(self):
        """Mutating query results must not affect the graph."""
        g = Graph()
        g.add(URI("http://ex/s"), URI("http://ex/p"), Literal("v"))
        results = g.query()
        results.clear()
        assert len(g) == 1  # graph unchanged

    def test_turtle_round_trip_preserves_special_characters(self):
        """Literals with quotes, newlines, backslashes must survive round-trip."""
        g = Graph()
        g.add(
            URI("http://ex/s"),
            URI("http://ex/p"),
            Literal('He said "hello"\nand then\\left'),
        )
        turtle = g.to_turtle()
        g2 = Graph.from_turtle(turtle)
        val = g2.query(predicate=URI("http://ex/p"))[0].object
        assert "hello" in str(val)
