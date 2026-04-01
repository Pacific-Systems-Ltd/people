"""people — The Python SDK for the Solid Project.

    import people as ps

    me = await ps.login(issuer, client_id, client_secret)
    alice = me.pod("https://pod.example/alice/")
    graph = await alice.read("health/gp-records")
"""

__version__ = "0.1.0-dev"

# Primitives
# Access control
from people._acl.grant import Grant
from people._acl.wac import evaluate_wac

# Server-side building blocks
from people._auth.dpop import compute_ath
from people._auth.dpop import verify_dpop_proof as verify_dpop
from people._auth.pod import Pod
from people._graph.graph import Graph
from people._graph.triple import URI, Literal, Triple

# Errors
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

# Model layer
from people._model.decorator import ModelTypeMismatchError, model
from people._model.fields import field

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


__all__ = [
    # Entry point
    "login",
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
    # Server building blocks
    "verify_dpop", "compute_ath", "apply_patch", "build_n3_patch",
]
