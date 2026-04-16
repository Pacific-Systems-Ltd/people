"""pacific-solid — The Python SDK for the Solid Project.

    import pacific_solid as ps

    me = await ps.login(issuer, client_id, client_secret)
    alice = me.pod("https://pod.example/alice/")
    graph = await alice.read("health/gp-records")
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pacific_solid._auth.session import SolidSession

__version__ = "0.1.0"

# Primitives
# Access control
# Errors
from pacific_solid._acl.acp import AuthSchemeError
from pacific_solid._acl.grant import Grant
from pacific_solid._acl.wac import evaluate_wac

# Auth flows
from pacific_solid._auth.auth_code import start_auth_flow

# Server-side building blocks
from pacific_solid._auth.dpop import compute_ath
from pacific_solid._auth.dpop import verify_dpop_proof as verify_dpop
from pacific_solid._auth.pod import Pod

# Discovery
from pacific_solid._discovery.storage import discover_storage
from pacific_solid._graph.graph import Graph
from pacific_solid._graph.triple import URI, Literal, Triple
from pacific_solid._http.errors import (
    AccessDeniedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PatchError,
    PreconditionFailedError,
    SolidError,
)
from pacific_solid._identity.webid import WebIDProfile

# LDN
from pacific_solid._ldn.inbox import (
    discover_inbox,
    list_notifications,
    read_notification,
    send_notification,
)

# Model layer
from pacific_solid._model.base import Model
from pacific_solid._model.decorator import ModelTypeMismatchError, model
from pacific_solid._model.fields import field

# Notifications
from pacific_solid._notifications.discovery import ChannelInfo, discover_channels
from pacific_solid._notifications.message import Notification, parse_notification
from pacific_solid._notifications.subscription import (
    InvalidSubscriptionError,
    SubscriptionResult,
    UnsupportedChannelError,
    subscribe,
)
from pacific_solid._notifications.websocket import NotificationStream

# Namespaces
from pacific_solid._rdf.namespaces import (
    ACL,
    DCTERMS,
    FOAF,
    LDP,
    OWL,
    PIM,
    RDF,
    RDFS,
    SCHEMA,
    SOLID,
    VCARD,
    XSD,
    Namespace,
)
from pacific_solid._rdf.patch import apply_patch, build_n3_patch

# Access modes (shorthand)
Read = ACL.Read
Write = ACL.Write
Append = ACL.Append
Control = ACL.Control


async def login(
    issuer: str, client_id: str, client_secret: str, *, discovery_url: str = ""
) -> "SolidSession":
    """Authenticate with a Solid OIDC issuer. Returns a SolidSession.

    Args:
        issuer: The OIDC issuer URL (e.g. "http://localhost:3000")
        client_id: The client ID
        client_secret: The client secret
        discovery_url: HTTP endpoint for OIDC discovery. Defaults to issuer.

    Usage:
        me = await ps.login("http://localhost:3000", "my-id", "my-secret")
        alice = me.pod("http://localhost:3000/alice/")
        graph = await alice.read("notes/hello")
    """
    from pacific_solid._auth.session import SolidSession
    return await SolidSession.login(issuer, client_id, client_secret, discovery_url=discovery_url)


async def login_interactive(
    issuer: str,
    client_id: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> "SolidSession":
    """Authenticate via Authorization Code Flow with PKCE.

    See start_auth_flow() for generating the authorization URL and PKCE parameters.

    Args:
        issuer: The OIDC issuer URL
        client_id: The client identifier
        redirect_uri: The redirect URI used in the authorization request
        code: The authorization code from the callback
        code_verifier: The PKCE code_verifier from start_auth_flow()

    Usage:
        from pacific_solid import start_auth_flow, login_interactive
        auth_url, verifier, state = start_auth_flow(auth_endpoint, client_id, redirect_uri)
        # User visits auth_url, gets redirected with ?code=...
        me = await login_interactive(issuer, client_id, redirect_uri, code, verifier)
    """
    from pacific_solid._auth.session import SolidSession
    return await SolidSession.login_interactive(
        issuer, client_id, redirect_uri, code, code_verifier,
    )


__all__ = [
    # Entry points
    "login", "login_interactive", "start_auth_flow",
    # Primitives
    "URI", "Literal", "Triple", "Graph", "Pod", "WebIDProfile",
    # Model layer
    "model", "field", "Model", "ModelTypeMismatchError", "Grant",
    # Access control
    "evaluate_wac",
    # Access modes
    "Read", "Write", "Append", "Control",
    # Namespaces
    "Namespace",
    "RDF", "RDFS", "XSD", "OWL", "LDP", "SOLID", "ACL", "PIM",
    "FOAF", "SCHEMA", "DCTERMS", "VCARD",
    # Errors
    "SolidError", "AuthenticationError", "AccessDeniedError",
    "NotFoundError", "ConflictError", "PreconditionFailedError", "PatchError",
    "AuthSchemeError",
    # Discovery
    "discover_storage",
    # LDN
    "discover_inbox", "send_notification", "list_notifications", "read_notification",
    # Notifications
    "discover_channels", "subscribe", "ChannelInfo", "SubscriptionResult",
    "Notification", "parse_notification", "NotificationStream",
    "UnsupportedChannelError", "InvalidSubscriptionError",
    # Server building blocks
    "verify_dpop", "compute_ath", "apply_patch", "build_n3_patch",
]
