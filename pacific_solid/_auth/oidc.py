"""Solid-OIDC discovery — fetch OpenID configuration from an issuer."""

from __future__ import annotations

from typing import Any

import httpx


async def discover_oidc(issuer: str) -> dict[str, Any]:
    """Fetch the OpenID Connect discovery document from an issuer.

    Args:
        issuer: The OIDC issuer URL (e.g. "http://localhost:3000")

    Returns:
        The parsed JSON discovery document.

    Raises:
        httpx.HTTPStatusError: If the discovery endpoint returns an error.
    """
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
