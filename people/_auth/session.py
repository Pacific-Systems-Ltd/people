"""SolidSession — authenticated identity for Solid pods.

    me = await ps.login(issuer, client_id, client_secret)
    graph = await me.read("https://pod.example/alice/notes/hello")
    alice = me.pod("https://pod.example/alice/")
"""

from __future__ import annotations

import logging
import time

from people._auth.credentials import exchange_client_credentials
from people._auth.dpop import DPoPKey
from people._auth.oidc import discover_oidc
from people._auth.pod import Pod
from people._graph.graph import Graph
from people._http.client import AuthenticatedClient
from people._http.errors import raise_for_status
from people._http.headers import extract_metadata
from people._identity.webid import WebIDProfile, resolve_webid
from people._rdf.parse import parse_rdf

logger = logging.getLogger("people")


class SolidSession:
    """An authenticated Solid identity. Created via ps.login().

    The session holds DPoP keys and access tokens. It can read/write resources
    at full URLs, or create scoped Pod objects for relative-path access.
    """

    def __init__(
        self,
        client: AuthenticatedClient,
        issuer: str,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
    ) -> None:
        self._client = client
        self._issuer = issuer
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_endpoint = token_endpoint

    @classmethod
    async def login(
        cls,
        issuer: str,
        client_id: str,
        client_secret: str,
        *,
        discovery_url: str = "",
    ) -> SolidSession:
        """Authenticate with a Solid OIDC issuer using client credentials.

        Args:
            issuer: The OIDC issuer URL (e.g. "http://localhost:3000")
            client_id: The client ID from the Solid server
            client_secret: The client secret
            discovery_url: HTTP endpoint for OIDC discovery. Defaults to issuer.
                Use when the issuer (stored in credentials) differs from the
                reachable HTTP address (e.g. after migrating to a new hostname).

        Returns:
            An authenticated SolidSession.
        """
        from people._http.tls import enforce_tls

        discover_at = discovery_url or issuer
        enforce_tls(discover_at)

        logger.debug("Discovering OIDC configuration at %s", discover_at)
        oidc_config = await discover_oidc(discover_at)
        token_endpoint = oidc_config["token_endpoint"]

        dpop_key = DPoPKey()
        logger.debug("Generated DPoP key pair, thumbprint: %s", dpop_key.thumbprint)

        logger.debug("Exchanging client credentials at %s", token_endpoint)
        token_data = await exchange_client_credentials(
            token_endpoint, client_id, client_secret, dpop_key
        )

        expires_in = token_data.get("expires_in", 600)

        # Build refresh callback for the authenticated client
        async def _refresh():
            return await exchange_client_credentials(
                token_endpoint, client_id, client_secret, dpop_key
            )

        client = AuthenticatedClient(
            dpop_key=dpop_key,
            access_token=token_data["access_token"],
            token_expires_at=time.time() + expires_in,
            refresh_callback=_refresh,
        )

        # Validate ID Token if present (OIDC-09)
        id_token = token_data.get("id_token")
        jwks_uri = oidc_config.get("jwks_uri")
        if id_token and jwks_uri:
            from people._auth.token_validation import validate_id_token, verify_webid_issuer

            claims = await validate_id_token(id_token, issuer, client_id, jwks_uri)

            # Verify OIDC issuer against WebID profile (OIDC-10)
            webid = claims.get("webid")
            if webid:
                await verify_webid_issuer(webid, issuer, client)

        logger.info("Authenticated with %s (token expires in %ds)", issuer, expires_in)

        return cls(
            client=client,
            issuer=issuer,
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=token_endpoint,
        )

    @classmethod
    async def login_interactive(
        cls,
        issuer: str,
        client_id: str,
        redirect_uri: str,
        code: str,
        code_verifier: str,
    ) -> SolidSession:
        """Authenticate using Authorization Code Flow with PKCE (OIDC-14).

        This method handles the token exchange phase of the Auth Code flow.
        The caller is responsible for:
        1. Calling start_auth_flow() to get the authorization URL
        2. Directing the user to that URL in a browser
        3. Capturing the authorization code from the redirect callback
        4. Passing the code and code_verifier to this method

        Args:
            issuer: The OIDC issuer URL.
            client_id: The client identifier.
            redirect_uri: The redirect URI used in the authorization request.
            code: The authorization code from the callback.
            code_verifier: The PKCE code_verifier from start_auth_flow().

        Returns:
            An authenticated SolidSession.
        """
        from people._auth.auth_code import exchange_auth_code
        from people._http.tls import enforce_tls

        enforce_tls(issuer)

        logger.debug("Discovering OIDC configuration at %s", issuer)
        oidc_config = await discover_oidc(issuer)
        token_endpoint = oidc_config["token_endpoint"]

        dpop_key = DPoPKey()

        logger.debug("Exchanging auth code at %s", token_endpoint)
        token_data = await exchange_auth_code(
            token_endpoint, code, redirect_uri, code_verifier, client_id, dpop_key,
        )

        expires_in = token_data.get("expires_in", 600)

        # No refresh callback for auth code flow — tokens are one-shot
        client = AuthenticatedClient(
            dpop_key=dpop_key,
            access_token=token_data["access_token"],
            token_expires_at=time.time() + expires_in,
        )

        # Validate ID Token if present (OIDC-09)
        id_token = token_data.get("id_token")
        jwks_uri = oidc_config.get("jwks_uri")
        if id_token and jwks_uri:
            from people._auth.token_validation import validate_id_token, verify_webid_issuer

            claims = await validate_id_token(id_token, issuer, client_id, jwks_uri)

            webid = claims.get("webid")
            if webid:
                await verify_webid_issuer(webid, issuer, client)

        logger.info("Authenticated via auth code with %s", issuer)

        return cls(
            client=client,
            issuer=issuer,
            client_id=client_id,
            client_secret="",
            token_endpoint=token_endpoint,
        )

    def pod(self, base_url: str) -> Pod:
        """Create a scoped Pod view for relative-path access.

        Args:
            base_url: The pod base URL (e.g. "https://pod.example/alice/")
        """
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        return Pod(self._client, base_url)

    async def read(self, url: str) -> Graph:
        """Read a resource at a full URL and return a Graph."""
        resp = await self._client.request(
            "GET", url, headers={"Accept": "text/turtle, application/ld+json;q=0.9"}
        )
        raise_for_status(resp.status_code, url, resp.text)

        metadata = extract_metadata(dict(resp.headers), url)
        content_type = metadata.get("content_type", "text/turtle")
        triples = parse_rdf(resp.text, content_type, base_uri=url)
        graph = Graph(triples)
        graph.url = url
        graph.etag = metadata["etag"]
        graph.acl_url = metadata["acl_url"]
        graph.permissions = metadata["permissions"]
        return graph

    async def resolve(self, webid_url: str) -> WebIDProfile:
        """Resolve a WebID URI to discover OIDC issuers and pod storage URLs."""
        return await resolve_webid(webid_url, self._client)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

    async def __aenter__(self) -> SolidSession:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
