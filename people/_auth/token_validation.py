"""OIDC ID Token validation and WebID issuer verification.

OIDC-09: Validate ID Token per OIDC Core Section 3.1.3.7.
OIDC-10: Verify the token's issuer is authorised via the WebID profile.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
import jwt

from people._http.errors import AuthenticationError

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


async def validate_id_token(
    token: str,
    issuer: str,
    client_id: str,
    jwks_uri: str,
) -> dict[str, Any]:
    """Validate an OIDC ID Token per OIDC Core Section 3.1.3.7 (OIDC-09).

    Fetches the issuer's public keys from jwks_uri and verifies:
    - Signature (ES256 or RS256)
    - iss matches the expected issuer
    - aud contains the client_id
    - exp is in the future
    - iat is reasonable (not in the far future)

    Args:
        token: The raw JWT ID Token string.
        issuer: The expected OIDC issuer URL.
        client_id: The client_id that should appear in the aud claim.
        jwks_uri: The URL to fetch the issuer's JSON Web Key Set.

    Returns:
        The decoded token claims dict.

    Raises:
        AuthenticationError: If any validation check fails.
    """
    # Fetch the issuer's public keys
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_uri)
            resp.raise_for_status()
            jwks_data = resp.json()
    except Exception as e:
        raise AuthenticationError(
            f"Failed to fetch JWKS from {jwks_uri}: {e}",
            status_code=0,
            url=jwks_uri,
        ) from e

    # Decode and verify the token
    try:
        # Build the JWK client from the fetched key set
        jwk_client = jwt.PyJWKSet.from_dict(jwks_data)

        # Get the signing key from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "RS256")

        signing_key = None
        for key in jwk_client.keys:
            if kid and key.key_id == kid:
                signing_key = key
                break
            if not kid and key.public_key_use in ("sig", None):
                signing_key = key
                break

        if signing_key is None:
            raise AuthenticationError(
                f"No matching signing key found for kid={kid} in JWKS",
                status_code=0,
                url=jwks_uri,
            )

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            issuer=issuer,
            audience=client_id,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )

    except jwt.InvalidIssuerError as e:
        raise AuthenticationError(
            f"ID Token issuer mismatch: expected {issuer}",
            status_code=0,
            url=issuer,
        ) from e
    except jwt.InvalidAudienceError as e:
        raise AuthenticationError(
            f"ID Token audience mismatch: expected {client_id}",
            status_code=0,
            url=issuer,
        ) from e
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError(
            "ID Token has expired",
            status_code=0,
            url=issuer,
        ) from e
    except jwt.InvalidSignatureError as e:
        raise AuthenticationError(
            "ID Token signature verification failed",
            status_code=0,
            url=issuer,
        ) from e
    except jwt.PyJWTError as e:
        raise AuthenticationError(
            f"ID Token validation failed: {e}",
            status_code=0,
            url=issuer,
        ) from e

    logger.debug("ID Token validated: iss=%s, sub=%s", claims.get("iss"), claims.get("sub"))
    return claims


async def verify_webid_issuer(
    webid: str,
    expected_issuer: str,
    client: AuthenticatedClient,
) -> None:
    """Verify the OIDC issuer is authorised for a WebID (OIDC-10).

    Dereferences the WebID profile and checks that solid:oidcIssuer
    includes the expected_issuer. If it does not, the token's issuer
    is not trusted to speak for this WebID.

    Args:
        webid: The WebID URI from the token's webid claim.
        expected_issuer: The issuer URL from the token's iss claim.
        client: An authenticated HTTP client for fetching the profile.

    Raises:
        AuthenticationError: If the issuer is not authorised.
    """
    from people._identity.webid import resolve_webid

    profile = await resolve_webid(webid, client)

    if not profile.issuers:
        raise AuthenticationError(
            f"WebID {webid} has no solid:oidcIssuer — cannot verify issuer",
            status_code=0,
            url=webid,
        )

    # Normalize for comparison (strip trailing slashes)
    normalised_expected = expected_issuer.rstrip("/")
    normalised_issuers = {iss.rstrip("/") for iss in profile.issuers}

    if normalised_expected not in normalised_issuers:
        raise AuthenticationError(
            f"Issuer {expected_issuer} is not authorised for WebID {webid}. "
            f"Authorised issuers: {profile.issuers}",
            status_code=0,
            url=webid,
        )

    logger.debug(
        "Verified issuer %s is authorised for WebID %s",
        expected_issuer, webid,
    )
