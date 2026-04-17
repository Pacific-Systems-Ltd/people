"""Authenticated httpx client with DPoP proof generation and retry logic.

Handles:
- DPoP proof attached to every request
- DPoP-Nonce retry (401 with nonce header)
- Token refresh on expiry
- asyncio.Lock for concurrent safety
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from pacific_solid._auth.dpop import DPoPKey, compute_ath
from pacific_solid._http.errors import raise_for_status

logger = logging.getLogger("people")

MAX_RETRIES = 2


class AuthenticatedClient:
    """An httpx.AsyncClient wrapper that adds DPoP proofs to every request."""

    def __init__(
        self,
        dpop_key: DPoPKey,
        access_token: str,
        token_expires_at: float,
        refresh_callback: Any = None,
    ) -> None:
        self._dpop_key = dpop_key
        self._access_token = access_token
        self._token_expires_at = token_expires_at
        self._refresh_callback = refresh_callback
        self._dpop_nonce: str | None = None
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient()

    @property
    def is_token_expired(self) -> bool:
        return time.time() >= self._token_expires_at

    async def request(
        self,
        method: str,
        url: str,
        *,
        content: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an authenticated request with DPoP proof and retry logic.

        Retry state machine:
          Request -> 401?
            Has DPoP-Nonce? -> retry with nonce -> 401 again?
              Token expired? -> refresh + new nonce -> retry (max 2)
              Not expired -> raise
            No nonce, token expired? -> refresh -> retry -> 401 again?
              Has DPoP-Nonce now? -> retry with nonce (max 2)
              No nonce -> raise
            Not 401 -> return response
        """
        retries = 0

        while retries <= MAX_RETRIES:
            # Refresh token if expired
            if self.is_token_expired and self._refresh_callback:
                async with self._lock:
                    if self.is_token_expired:
                        logger.debug("Token expired, refreshing...")
                        token_data = await self._refresh_callback()
                        self._access_token = token_data["access_token"]
                        self._token_expires_at = time.time() + token_data.get("expires_in", 600)

            # Build DPoP proof
            ath = compute_ath(self._access_token)
            dpop_proof = self._dpop_key.sign_proof(
                method, url, nonce=self._dpop_nonce, ath=ath
            )

            # Build request headers
            req_headers = {
                "Authorization": f"DPoP {self._access_token}",
                "DPoP": dpop_proof,
            }
            if headers:
                req_headers.update(headers)

            logger.debug("Request: %s %s (retry %d)", method, url, retries)

            resp = await self._client.request(
                method, url, headers=req_headers, content=content
            )

            logger.debug("Response: %s %s -> %d", method, url, resp.status_code)

            if resp.status_code != 401:
                return resp

            # 401: check for DPoP-Nonce
            new_nonce = resp.headers.get("dpop-nonce") or resp.headers.get("DPoP-Nonce")
            if new_nonce:
                logger.debug("Server requires DPoP nonce: %s", new_nonce)
                async with self._lock:
                    self._dpop_nonce = new_nonce

            retries += 1
            if retries > MAX_RETRIES:
                break

            # If token might be expired, refresh before retry
            if self.is_token_expired and self._refresh_callback:
                async with self._lock:
                    if self.is_token_expired:
                        logger.debug("Token expired during retry, refreshing...")
                        token_data = await self._refresh_callback()
                        self._access_token = token_data["access_token"]
                        self._token_expires_at = time.time() + token_data.get("expires_in", 600)

        # All retries exhausted
        raise_for_status(401, url, resp.text if resp else "")
        return resp  # unreachable, but makes type checker happy

    async def close(self) -> None:
        await self._client.aclose()
