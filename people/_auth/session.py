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
    ) -> SolidSession:
        """Authenticate with a Solid OIDC issuer using client credentials.

        Args:
            issuer: The OIDC issuer URL (e.g. "http://localhost:3000")
            client_id: The client ID from the Solid server
            client_secret: The client secret

        Returns:
            An authenticated SolidSession.
        """
        logger.debug("Discovering OIDC configuration at %s", issuer)
        oidc_config = await discover_oidc(issuer)
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

        logger.info("Authenticated with %s (token expires in %ds)", issuer, expires_in)

        return cls(
            client=client,
            issuer=issuer,
            client_id=client_id,
            client_secret=client_secret,
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
            "GET", url, headers={"Accept": "text/turtle"}
        )
        raise_for_status(resp.status_code, url, resp.text)

        metadata = extract_metadata(dict(resp.headers), url)
        graph = Graph.from_turtle(resp.text, base_uri=url)
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
