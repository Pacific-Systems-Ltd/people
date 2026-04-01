"""
Explore the Solid Protocol hands-on.

This script walks through every step of the Solid auth + CRUD flow
against a local Community Solid Server. No libraries except standard
crypto primitives — feel the protocol in your hands.

Prerequisites:
    docker run --rm -d --name css-test -p 3000:3000 solidproject/community-server:latest -b http://localhost:3000
"""

import json
import time
import uuid
import base64
import hashlib
import urllib.parse
import urllib.request

# pip install PyJWT cryptography
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# ──────────────────────────────────────────────────────────
# Config from account setup (already done via curl above)
# ──────────────────────────────────────────────────────────
CSS_BASE = "http://localhost:3000"
CLIENT_ID = "test-token_50d0ee3a-5968-4e20-a638-1d185eed7415"
CLIENT_SECRET = "3830b7725b7b21daf56c93870bda1c84f7ceb87b3e74d4aab0c61aad7afa6dbd89e045f75de90cca7dcf1c20d75f7fb5d788cdd3bc94f1214fb2c011a7ddad6a"
TOKEN_ENDPOINT = f"{CSS_BASE}/.oidc/token"
POD_URL = f"{CSS_BASE}/test-pod/"
WEBID = f"{CSS_BASE}/test-pod/profile/card#me"


def http_request(url, method="GET", headers=None, data=None):
    """Minimal HTTP helper — no libraries, raw urllib."""
    if headers is None:
        headers = {}
    if data and isinstance(data, str):
        data = data.encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, dict(e.headers), body


# ──────────────────────────────────────────────────────────
# STEP 1: Generate an EC key pair for DPoP
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Generate EC key pair for DPoP")
print("=" * 60)

private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()

# Extract the JWK components for the public key
public_numbers = public_key.public_numbers()
x_bytes = public_numbers.x.to_bytes(32, "big")
y_bytes = public_numbers.y.to_bytes(32, "big")

jwk_public = {
    "kty": "EC",
    "crv": "P-256",
    "x": base64.urlsafe_b64encode(x_bytes).rstrip(b"=").decode(),
    "y": base64.urlsafe_b64encode(y_bytes).rstrip(b"=").decode(),
}

# JWK thumbprint (RFC 7638) — used to bind the DPoP key to the token
thumbprint_input = json.dumps(
    {"crv": jwk_public["crv"], "kty": jwk_public["kty"], "x": jwk_public["x"], "y": jwk_public["y"]},
    separators=(",", ":"),
    sort_keys=True,
)
jwk_thumbprint = base64.urlsafe_b64encode(
    hashlib.sha256(thumbprint_input.encode()).digest()
).rstrip(b"=").decode()

print(f"  Public JWK: {json.dumps(jwk_public, indent=2)}")
print(f"  JWK Thumbprint: {jwk_thumbprint}")
print()


# ──────────────────────────────────────────────────────────
# STEP 2: Create a DPoP proof for the token endpoint
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 2: Create DPoP proof for token request")
print("=" * 60)


def create_dpop_proof(htm, htu, nonce=None, ath=None):
    """
    Build a DPoP proof JWT (RFC 9449).

    htm:   HTTP method (e.g., "POST", "GET")
    htu:   HTTP URI (the target URL, without query/fragment)
    nonce: Server-provided nonce (from DPoP-Nonce header)
    ath:   Access token hash (for resource requests, not token requests)
    """
    now = int(time.time())
    payload = {
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
        "jwk": jwk_public,
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers=headers,
    )
    return token


dpop_proof = create_dpop_proof("POST", TOKEN_ENDPOINT)
print(f"  DPoP proof (truncated): {dpop_proof[:80]}...")
print(f"  Decoded header: {jwt.get_unverified_header(dpop_proof)}")
print(f"  Decoded payload: {jwt.decode(dpop_proof, options={'verify_signature': False})}")
print()


# ──────────────────────────────────────────────────────────
# STEP 3: Exchange client credentials for access token
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 3: Token exchange (client_credentials + DPoP)")
print("=" * 60)

# Basic auth: base64(urlencoded(id):urlencoded(secret))
auth_string = f"{urllib.parse.quote(CLIENT_ID, safe='')}:{urllib.parse.quote(CLIENT_SECRET, safe='')}"
basic_auth = base64.b64encode(auth_string.encode()).decode()

token_body = "grant_type=client_credentials&scope=webid"

status, resp_headers, resp_body = http_request(
    TOKEN_ENDPOINT,
    method="POST",
    headers={
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
        "DPoP": dpop_proof,
    },
    data=token_body,
)

print(f"  Status: {status}")

if status == 400 or status == 401:
    print(f"  Response: {resp_body}")
    # Check for DPoP-Nonce requirement
    dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
    if dpop_nonce:
        print(f"\n  Server requires DPoP nonce: {dpop_nonce}")
        print("  Retrying with nonce...")
        dpop_proof_with_nonce = create_dpop_proof("POST", TOKEN_ENDPOINT, nonce=dpop_nonce)
        status, resp_headers, resp_body = http_request(
            TOKEN_ENDPOINT,
            method="POST",
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "DPoP": dpop_proof_with_nonce,
            },
            data=token_body,
        )
        print(f"  Retry status: {status}")

token_data = json.loads(resp_body)
print(f"  Token response: {json.dumps(token_data, indent=2)}")

if "access_token" not in token_data:
    print("\n  FAILED to get access token. Check the error above.")
    exit(1)

access_token = token_data["access_token"]
print(f"\n  Access token (truncated): {access_token[:60]}...")
print(f"  Token type: {token_data.get('token_type')}")
print(f"  Expires in: {token_data.get('expires_in')} seconds")
print()


# ──────────────────────────────────────────────────────────
# STEP 4: Make an authenticated request to read the pod
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 4: Authenticated read of pod container")
print("=" * 60)

# For resource requests, we need an access token hash (ath)
ath = base64.urlsafe_b64encode(
    hashlib.sha256(access_token.encode()).digest()
).rstrip(b"=").decode()

dpop_resource = create_dpop_proof("GET", POD_URL, ath=ath)

status, resp_headers, resp_body = http_request(
    POD_URL,
    method="GET",
    headers={
        "Authorization": f"DPoP {access_token}",
        "DPoP": dpop_resource,
        "Accept": "text/turtle",
    },
)

if status == 401:
    # Check for nonce requirement on resource server too
    dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
    if dpop_nonce:
        print(f"  Resource server requires nonce: {dpop_nonce}")
        dpop_resource = create_dpop_proof("GET", POD_URL, nonce=dpop_nonce, ath=ath)
        status, resp_headers, resp_body = http_request(
            POD_URL,
            method="GET",
            headers={
                "Authorization": f"DPoP {access_token}",
                "DPoP": dpop_resource,
                "Accept": "text/turtle",
            },
        )

print(f"  Status: {status}")
print(f"  WAC-Allow: {resp_headers.get('WAC-Allow', 'N/A')}")
print(f"\n  Body (Turtle):")
print(resp_body)
print()


# ──────────────────────────────────────────────────────────
# STEP 5: Create a new RDF resource in the pod
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 5: Create a new RDF resource (POST to container)")
print("=" * 60)

interview_turtle = """@prefix schema: <http://schema.org/>.
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
@prefix pac: <http://pacific.dev/ontology#>.

<#interview-001>
    a pac:Interview;
    schema:name "Onboarding Interview - Client Alpha";
    schema:dateCreated "2026-03-31"^^xsd:date;
    pac:status "completed";
    pac:interviewer <http://localhost:3000/test-pod/profile/card#me>;
    pac:finding "Manual process takes 3 hours per candidate";
    pac:finding "No standardized checklist exists";
    pac:recommendation "Automate document verification step".
"""

create_url = POD_URL
dpop_create = create_dpop_proof("POST", create_url, ath=ath)

status, resp_headers, resp_body = http_request(
    create_url,
    method="POST",
    headers={
        "Authorization": f"DPoP {access_token}",
        "DPoP": dpop_create,
        "Content-Type": "text/turtle",
        "Slug": "interview-001",
    },
    data=interview_turtle,
)

if status == 401:
    dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
    if dpop_nonce:
        print(f"  Nonce required: {dpop_nonce}")
        dpop_create = create_dpop_proof("POST", create_url, nonce=dpop_nonce, ath=ath)
        status, resp_headers, resp_body = http_request(
            create_url,
            method="POST",
            headers={
                "Authorization": f"DPoP {access_token}",
                "DPoP": dpop_create,
                "Content-Type": "text/turtle",
                "Slug": "interview-001",
            },
            data=interview_turtle,
        )

print(f"  Status: {status}")
created_url = resp_headers.get("Location", "N/A")
print(f"  Location: {created_url}")
print()


# ──────────────────────────────────────────────────────────
# STEP 6: Read back the created resource
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 6: Read back the created resource")
print("=" * 60)

if created_url and created_url != "N/A":
    dpop_read = create_dpop_proof("GET", created_url, ath=ath)
    status, resp_headers, resp_body = http_request(
        created_url,
        method="GET",
        headers={
            "Authorization": f"DPoP {access_token}",
            "DPoP": dpop_read,
            "Accept": "text/turtle",
        },
    )

    if status == 401:
        dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
        if dpop_nonce:
            dpop_read = create_dpop_proof("GET", created_url, nonce=dpop_nonce, ath=ath)
            status, resp_headers, resp_body = http_request(
                created_url,
                method="GET",
                headers={
                    "Authorization": f"DPoP {access_token}",
                    "DPoP": dpop_read,
                    "Accept": "text/turtle",
                },
            )

    print(f"  Status: {status}")
    print(f"  ETag: {resp_headers.get('ETag', 'N/A')}")
    print(f"\n  Body (Turtle):")
    print(resp_body)
else:
    print("  Skipped — no created URL from previous step")
print()


# ──────────────────────────────────────────────────────────
# STEP 7: Update with N3 Patch (add a triple)
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 7: N3 Patch — add a triple to the resource")
print("=" * 60)

if created_url and created_url != "N/A":
    n3_patch = f"""@prefix solid: <http://www.w3.org/ns/solid/terms#>.
@prefix pac: <http://pacific.dev/ontology#>.

_:patch a solid:InsertDeletePatch;
    solid:inserts {{
        <#interview-001> pac:resolution "Implement automated document verification via Pacific agent".
    }}.
"""

    dpop_patch = create_dpop_proof("PATCH", created_url, ath=ath)
    status, resp_headers, resp_body = http_request(
        created_url,
        method="PATCH",
        headers={
            "Authorization": f"DPoP {access_token}",
            "DPoP": dpop_patch,
            "Content-Type": "text/n3",
        },
        data=n3_patch,
    )

    if status == 401:
        dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
        if dpop_nonce:
            dpop_patch = create_dpop_proof("PATCH", created_url, nonce=dpop_nonce, ath=ath)
            status, resp_headers, resp_body = http_request(
                created_url,
                method="PATCH",
                headers={
                    "Authorization": f"DPoP {access_token}",
                    "DPoP": dpop_patch,
                    "Content-Type": "text/n3",
                },
                data=n3_patch,
            )

    print(f"  Status: {status}")
    if status >= 400:
        print(f"  Response: {resp_body}")

    # Read back to verify the patch
    if status < 400:
        print("  Patch applied! Reading back...")
        dpop_verify = create_dpop_proof("GET", created_url, ath=ath)
        status2, _, body2 = http_request(
            created_url,
            method="GET",
            headers={
                "Authorization": f"DPoP {access_token}",
                "DPoP": dpop_verify,
                "Accept": "text/turtle",
            },
        )
        print(f"\n  Updated resource:")
        print(body2)
else:
    print("  Skipped — no created URL")
print()


# ──────────────────────────────────────────────────────────
# STEP 8: Read the ACL resource
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 8: Read the ACL for the pod container")
print("=" * 60)

acl_url = f"{POD_URL}.acl"
dpop_acl = create_dpop_proof("GET", acl_url, ath=ath)

status, resp_headers, resp_body = http_request(
    acl_url,
    method="GET",
    headers={
        "Authorization": f"DPoP {access_token}",
        "DPoP": dpop_acl,
        "Accept": "text/turtle",
    },
)

if status == 401:
    dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
    if dpop_nonce:
        dpop_acl = create_dpop_proof("GET", acl_url, nonce=dpop_nonce, ath=ath)
        status, resp_headers, resp_body = http_request(
            acl_url,
            method="GET",
            headers={
                "Authorization": f"DPoP {access_token}",
                "DPoP": dpop_acl,
                "Accept": "text/turtle",
            },
        )

print(f"  Status: {status}")
print(f"\n  ACL (Turtle):")
print(resp_body)
print()


# ──────────────────────────────────────────────────────────
# STEP 9: Delete the resource
# ──────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 9: Delete the resource")
print("=" * 60)

if created_url and created_url != "N/A":
    dpop_delete = create_dpop_proof("DELETE", created_url, ath=ath)
    status, resp_headers, resp_body = http_request(
        created_url,
        method="DELETE",
        headers={
            "Authorization": f"DPoP {access_token}",
            "DPoP": dpop_delete,
        },
    )

    if status == 401:
        dpop_nonce = resp_headers.get("DPoP-Nonce") or resp_headers.get("dpop-nonce")
        if dpop_nonce:
            dpop_delete = create_dpop_proof("DELETE", created_url, nonce=dpop_nonce, ath=ath)
            status, resp_headers, resp_body = http_request(
                created_url,
                method="DELETE",
                headers={
                    "Authorization": f"DPoP {access_token}",
                    "DPoP": dpop_delete,
                },
            )

    print(f"  Status: {status}")
    print(f"  Resource deleted: {created_url}")

    # Verify it's gone
    dpop_check = create_dpop_proof("GET", created_url, ath=ath)
    status2, _, _ = http_request(
        created_url,
        method="GET",
        headers={
            "Authorization": f"DPoP {access_token}",
            "DPoP": dpop_check,
            "Accept": "text/turtle",
        },
    )
    print(f"  Verify (expect 404): {status2}")
else:
    print("  Skipped — no created URL")

print()
print("=" * 60)
print("DONE — Full Solid Protocol flow completed.")
print("=" * 60)
