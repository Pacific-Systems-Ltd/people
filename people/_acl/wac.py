"""WAC evaluation — server-side building block.

Evaluates whether a WebID is authorized for a given access mode
on a resource, based on the ACL graph.
"""

from __future__ import annotations

from people._graph.graph import Graph
from people._graph.triple import URI
from people._rdf.namespaces import ACL, FOAF, RDF

# Map HTTP methods to required WAC modes
METHOD_TO_MODE: dict[str, URI] = {
    "GET": ACL.Read,
    "HEAD": ACL.Read,
    "OPTIONS": ACL.Read,
    "PUT": ACL.Write,
    "DELETE": ACL.Write,
    "POST": ACL.Append,
    "PATCH": ACL.Append,
}


def evaluate_wac(
    webid: str,
    acl_graph: Graph,
    method_or_mode: str,
    resource_url: str | None = None,
    *,
    patch_has_deletes: bool = False,
) -> bool:
    """Evaluate whether a WebID is authorized for an access mode.

    Args:
        webid: The WebID URI of the requesting agent
        acl_graph: The ACL graph (parsed from the .acl resource)
        method_or_mode: HTTP method (GET, PUT, etc.) or WAC mode URI
        resource_url: The resource URL to check accessTo against (optional)
        patch_has_deletes: If True and method is PATCH, require Write not just Append.
            Per Solid spec: PATCH with solid:deletes is a Write operation.

    Returns:
        True if access is granted, False otherwise.
    """
    # Resolve method to mode
    if method_or_mode in METHOD_TO_MODE:
        required_mode = METHOD_TO_MODE[method_or_mode]
        # PATCH with deletes requires Write, not just Append
        if method_or_mode == "PATCH" and patch_has_deletes:
            required_mode = ACL.Write
    else:
        required_mode = URI(method_or_mode)

    # Find all Authorization subjects
    auth_triples = acl_graph.query(predicate=URI(str(RDF.type)), value=ACL.Authorization)

    for auth_triple in auth_triples:
        subject = auth_triple.subject

        # Check if this authorization grants the required mode
        mode_triples = acl_graph.query(subject=subject, predicate=ACL.mode)
        granted_modes = {str(t.object) for t in mode_triples}

        if str(required_mode) not in granted_modes:
            # Also check if Write is granted when Append is required
            # (Append is a subclass of Write per WAC spec)
            if str(required_mode) == str(ACL.Append) and str(ACL.Write) in granted_modes:
                pass  # Write implies Append
            else:
                continue

        # Check if the resource matches (accessTo or default)
        if resource_url:
            access_to = acl_graph.query(subject=subject, predicate=ACL.accessTo)
            defaults = acl_graph.query(subject=subject, predicate=ACL.default)
            resource_matches = any(
                str(t.object) == resource_url for t in access_to
            ) or any(
                # acl:default: container must end with / and resource must be under it
                _resource_under_container(resource_url, str(t.object)) for t in defaults
            )
            if not resource_matches:
                continue

        # Check agent matching
        if _agent_matches(webid, subject, acl_graph):
            return True

    return False


def _resource_under_container(resource_url: str, container_url: str) -> bool:
    """Check if a resource URL is under a container URL.

    Enforces trailing-slash on the container to prevent path-traversal bypass.
    e.g. /alice/public/ covers /alice/public/doc but NOT /alice/public-secrets/doc
    """
    if not container_url.endswith("/"):
        container_url = container_url + "/"
    return resource_url.startswith(container_url) or resource_url == container_url.rstrip("/")


def _agent_matches(webid: str, auth_subject: URI, acl_graph: Graph) -> bool:
    """Check if a WebID matches any agent specification in an authorization."""
    # Check acl:agent (specific agent)
    agent_triples = acl_graph.query(subject=auth_subject, predicate=ACL.agent)
    for t in agent_triples:
        if str(t.object) == webid:
            return True

    # Check acl:agentClass foaf:Agent (public access)
    class_triples = acl_graph.query(subject=auth_subject, predicate=ACL.agentClass)
    for t in class_triples:
        if str(t.object) == str(FOAF.Agent):
            return True
        # acl:AuthenticatedAgent — any authenticated user
        if str(t.object) == str(ACL.AuthenticatedAgent) and webid:
            return True

    # Check acl:agentGroup (group membership)
    # Note: full group resolution requires fetching the group document,
    # which is a network call. For now, we check if the webid is listed
    # directly in the ACL graph as a vcard:hasMember.
    group_triples = acl_graph.query(subject=auth_subject, predicate=ACL.agentGroup)
    for t in group_triples:
        group_uri = t.object
        from people._rdf.namespaces import VCARD
        members = acl_graph.query(subject=URI(str(group_uri)), predicate=VCARD.hasMember)
        for m in members:
            if str(m.object) == webid:
                return True

    return False
