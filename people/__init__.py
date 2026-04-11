"""people — The Python SDK for the Solid Project.

    import people as ps

    me = await ps.login(issuer, client_id, client_secret)
    alice = me.pod("https://pod.example/alice/")
    graph = await alice.read("health/gp-records")
"""

__version__ = "0.1.0"

# Primitives
# Access control
# Errors
from people._acl.acp import AuthSchemeError
from people._acl.grant import Grant
from people._acl.wac import evaluate_wac

# Auth flows
from people._auth.auth_code import start_auth_flow

# Server-side building blocks
from people._auth.dpop import compute_ath
from people._auth.dpop import verify_dpop_proof as verify_dpop
from people._auth.pod import Pod

# Discovery
from people._discovery.storage import discover_storage
from people._graph.graph import Graph
from people._graph.triple import URI, Literal, Triple
from people._http.errors import (
    AccessDeniedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PatchError,
    PreconditionFailedError,
    SolidError,
)
from people._identity.webid import WebIDProfile

# LDN
from people._ldn.inbox import (
    discover_inbox,
    list_notifications,
    read_notification,
    send_notification,
)

# Model layer
from people._model.decorator import ModelTypeMismatchError, model
from people._model.fields import field

# Notifications
from people._notifications.discovery import ChannelInfo, discover_channels
from people._notifications.message import Notification, parse_notification
from people._notifications.subscription import (
    InvalidSubscriptionError,
    SubscriptionResult,
    UnsupportedChannelError,
    subscribe,
)
from people._notifications.websocket import NotificationStream

# Namespaces
from people._rdf.namespaces import (
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
from people._rdf.patch import apply_patch, build_n3_patch

# Access modes (shorthand)
Read = ACL.Read
Write = ACL.Write
Append = ACL.Append
Control = ACL.Control


async def login(issuer: str, client_id: str, client_secret: str):
    """Authenticate with a Solid OIDC issuer. Returns a SolidSession.

    Args:
        issuer: The OIDC issuer URL (e.g. "http://localhost:3000")
        client_id: The client ID
        client_secret: The client secret

    Usage:
        me = await ps.login("http://localhost:3000", "my-id", "my-secret")
        alice = me.pod("http://localhost:3000/alice/")
        graph = await alice.read("notes/hello")
    """
    from people._auth.session import SolidSession
    return await SolidSession.login(issuer, client_id, client_secret)


async def login_interactive(
    issuer: str,
    client_id: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
):
    """Authenticate via Authorization Code Flow with PKCE.

    See start_auth_flow() for generating the authorization URL and PKCE parameters.

    Args:
        issuer: The OIDC issuer URL
        client_id: The client identifier
        redirect_uri: The redirect URI used in the authorization request
        code: The authorization code from the callback
        code_verifier: The PKCE code_verifier from start_auth_flow()

    Usage:
        from people import start_auth_flow, login_interactive
        auth_url, verifier, state = start_auth_flow(auth_endpoint, client_id, redirect_uri)
        # User visits auth_url, gets redirected with ?code=...
        me = await login_interactive(issuer, client_id, redirect_uri, code, verifier)
    """
    from people._auth.session import SolidSession
    return await SolidSession.login_interactive(
        issuer, client_id, redirect_uri, code, code_verifier,
    )


__all__ = [
    # Entry points
    "login", "login_interactive", "start_auth_flow",
    # Primitives
    "URI", "Literal", "Triple", "Graph", "Pod", "WebIDProfile",
    # Model layer
    "model", "field", "ModelTypeMismatchError", "Grant",
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
