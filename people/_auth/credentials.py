"""Client credentials grant flow for Solid-OIDC with DPoP."""

from __future__ import annotations

import base64
import urllib.parse

import httpx

from people._auth.dpop import DPoPKey


async def exchange_client_credentials(
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    dpop_key: DPoPKey,
) -> dict:
    """Exchange client credentials for a DPoP-bound access token.

    Handles DPoP-Nonce retry: if the server requires a nonce, retries once
    with the provided nonce.

    Args:
        token_endpoint: The OIDC token endpoint URL
        client_id: The client ID
        client_secret: The client secret
        dpop_key: The DPoP key pair for proof generation

    Returns:
        The token response dict containing access_token, token_type, expires_in.

    Raises:
        httpx.HTTPStatusError: If the token exchange fails after retry.
    """
    from people._http.tls import enforce_tls
    enforce_tls(token_endpoint)

    auth_string = (
        f"{urllib.parse.quote(client_id, safe='')}:"
        f"{urllib.parse.quote(client_secret, safe='')}"
    )
    basic_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=client_credentials&scope=webid"

    async with httpx.AsyncClient() as client:
        # First attempt
        dpop_proof = dpop_key.sign_proof("POST", token_endpoint)
        resp = await client.post(
            token_endpoint,
            headers={**headers, "DPoP": dpop_proof},
            content=body,
        )

        # Handle DPoP-Nonce requirement
        if resp.status_code in (400, 401):
            nonce = resp.headers.get("dpop-nonce") or resp.headers.get("DPoP-Nonce")
            if nonce:
                dpop_proof = dpop_key.sign_proof("POST", token_endpoint, nonce=nonce)
                resp = await client.post(
                    token_endpoint,
                    headers={**headers, "DPoP": dpop_proof},
                    content=body,
                )

        resp.raise_for_status()
        return resp.json()
