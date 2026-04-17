"""Grant — pre-built @ps.model for WAC Authorization.

Usage:
    acl = await pod.read(graph.acl_url)
    for grant in acl.all(Grant):
        print(grant.agent, grant.modes)
"""

from pacific_solid._model.decorator import model
from pacific_solid._model.fields import field
from pacific_solid._rdf.namespaces import ACL


@model
class Grant:
    """A WAC Authorization — maps to acl:Authorization triples."""

    rdf_type = ACL.Authorization
    agent: str = field(ACL.agent)
    resource: str = field(ACL.accessTo)
    default_for: str = field(ACL.default)
    modes: list[str] = field(ACL.mode, multiple=True)
