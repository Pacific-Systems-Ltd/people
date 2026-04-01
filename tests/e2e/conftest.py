"""E2E test fixtures — real Community Solid Server in Docker.

Requires: docker compose up -d (CSS on port 3000)
These tests hit a real server. They create, read, modify, and delete
actual resources. They are the ground truth for spec compliance.

Setup:
    docker run --rm -d --name css-test -p 3000:3000 \
        solidproject/community-server:latest -b http://localhost:3000

    Then create a test account and pod via the CSS account API:
        POST http://localhost:3000/.account/
        POST http://localhost:3000/.account/login/password/register/
        POST http://localhost:3000/.account/pod/
        POST http://localhost:3000/.account/client-credentials/

    Or use the setup_css_account() helper below.
"""

import asyncio
import json
import urllib.parse
import urllib.request

import pytest

CSS_BASE = "http://localhost:3000"
TEST_EMAIL = "test@example.org"
TEST_PASSWORD = "test-password-123"
POD_NAME = "test-pod"


def _http(url, method="GET", headers=None, data=None):
    """Minimal sync HTTP helper for account setup."""
    if headers is None:
        headers = {}
    if data and isinstance(data, str):
        data = data.encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            cookies = resp.headers.get_all("Set-Cookie") or []
            return resp.status, dict(resp.headers), body, cookies
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, dict(e.headers), body, []


def _extract_cookie(cookies, name="css-account"):
    """Extract a cookie value from Set-Cookie headers."""
    for cookie in cookies:
        if cookie.startswith(f"{name}="):
            return cookie.split(";")[0]
    return None


def is_css_running() -> bool:
    """Check if CSS is running on localhost:3000."""
    try:
        status, _, _, _ = _http(CSS_BASE)
        return status == 200
    except Exception:
        return False


def setup_css_account() -> dict:
    """Create a test account, pod, and client credentials on CSS.

    Returns dict with: client_id, client_secret, pod_url, webid.
    """
    all_cookies = []

    # 1. Create account session
    status, headers, body, cookies = _http(
        f"{CSS_BASE}/.account/",
        method="POST",
        headers={"Content-Type": "application/json"},
        data="{}",
    )
    all_cookies.extend(cookies)
    cookie = _extract_cookie(all_cookies)

    # 2. Register with email/password
    status, headers, body, cookies = _http(
        f"{CSS_BASE}/.account/login/password/register/",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie,
        },
        data=json.dumps({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "confirmPassword": TEST_PASSWORD,
        }),
    )
    all_cookies.extend(cookies)
    cookie = _extract_cookie(all_cookies) or cookie

    # 3. Create pod
    status, headers, body, cookies = _http(
        f"{CSS_BASE}/.account/pod/",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie,
        },
        data=json.dumps({"name": POD_NAME}),
    )
    all_cookies.extend(cookies)
    cookie = _extract_cookie(all_cookies) or cookie

    pod_url = f"{CSS_BASE}/{POD_NAME}/"
    webid = f"{CSS_BASE}/{POD_NAME}/profile/card#me"

    # 4. Create client credentials
    status, headers, body, cookies = _http(
        f"{CSS_BASE}/.account/client-credentials/",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie,
        },
        data=json.dumps({"name": "test-credentials", "webId": webid}),
    )

    creds = json.loads(body)
    return {
        "client_id": creds.get("id", ""),
        "client_secret": creds.get("secret", ""),
        "pod_url": pod_url,
        "webid": webid,
    }


@pytest.fixture(scope="session")
def css_credentials():
    """Session-scoped fixture: creates CSS account once, shares across all E2E tests."""
    if not is_css_running():
        pytest.skip("CSS not running on localhost:3000. Run: docker run --rm -d --name css-test -p 3000:3000 solidproject/community-server:latest -b http://localhost:3000")

    try:
        return setup_css_account()
    except Exception as e:
        pytest.skip(f"Failed to set up CSS test account: {e}")


@pytest.fixture(scope="session")
def css_base():
    return CSS_BASE
