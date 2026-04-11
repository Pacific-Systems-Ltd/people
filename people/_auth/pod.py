"""Pod — a scoped view onto a remote Solid pod.

    alice = me.pod("https://pod.example/alice/")
    graph = await alice.read("health/gp-records")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from people._graph.graph import Graph
from people._graph.triple import URI
from people._http.errors import raise_for_status
from people._http.headers import extract_metadata
from people._rdf.namespaces import ACL, LDP, RDF
from people._rdf.parse import parse_rdf

if TYPE_CHECKING:
    from people._http.client import AuthenticatedClient

logger = logging.getLogger("people")


class Pod:
    """A scoped view onto a remote Solid pod with relative paths.

    Five methods, five HTTP verbs:
        read(path)              GET
        write(path, graph)      PUT (full replace)
        patch(path, graph)      PATCH (N3 Patch from snapshot diff)
        create(container, graph) POST (new resource)
        delete(path)            DELETE
    """

    def __init__(self, client: AuthenticatedClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url

    @property
    def base_url(self) -> str:
        return self._base_url

    def _resolve(self, path: str) -> str:
        """Resolve a relative path against the pod base URL."""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base_url}{path.lstrip('/')}"

    async def read(self, path: str) -> Graph:
        """GET — read a resource and return a Graph."""
        url = self._resolve(path)
        resp = await self._client.request(
            "GET", url, headers={"Accept": "text/turtle, application/ld+json;q=0.9"}
        )
        raise_for_status(resp.status_code, url, resp.text)

        metadata = extract_metadata(dict(resp.headers), url)
        content_type = metadata.get("content_type", "text/turtle")
        triples = parse_rdf(resp.text, content_type, base_uri=url)
        graph = Graph(triples)
        graph.url = url
        graph.etag = metadata["etag"]
        graph.acl_url = metadata["acl_url"]
        graph.permissions = metadata["permissions"]
        return graph

    async def write(self, path: str, graph: Graph) -> None:
        """PUT — full replace of a resource."""
        url = self._resolve(path)
        turtle = graph.to_turtle(base_uri=url)

        headers: dict[str, str] = {"Content-Type": "text/turtle"}
        if graph.etag:
            headers["If-Match"] = graph.etag
        else:
            headers["If-None-Match"] = "*"

        resp = await self._client.request("PUT", url, content=turtle, headers=headers)
        raise_for_status(resp.status_code, url, resp.text)

    async def patch(self, path: str, graph: Graph) -> None:
        """PATCH — apply N3 Patch from the graph's snapshot diff."""
        if not graph.has_snapshot:
            raise ValueError(
                "Cannot patch: graph has no snapshot. "
                "Use from_graph() to create a snapshot, or use write() for full replace."
            )

        inserts, deletes = graph.diff()
        if not inserts and not deletes:
            logger.debug("No changes to patch for %s", path)
            return

        from people._rdf.patch import build_n3_patch
        n3_body = build_n3_patch(inserts, deletes)

        url = self._resolve(path)
        headers = {"Content-Type": "text/n3"}
        if graph.etag:
            headers["If-Match"] = graph.etag

        resp = await self._client.request("PATCH", url, content=n3_body, headers=headers)
        raise_for_status(resp.status_code, url, resp.text)
        graph.reset_snapshot()

    async def create(
        self,
        container_path: str,
        graph: Graph,
        slug: str | None = None,
        *,
        container: bool = True,
    ) -> str:
        """POST — create a new resource (or container) inside a parent container.

        Args:
            container_path: Path of the parent container to POST into.
            graph: RDF graph describing the new resource.
            slug: Suggested name for the created resource.
            container: If True, create an LDP BasicContainer (adds Link header).

        Returns the URL of the created resource.
        """
        url = self._resolve(container_path)
        turtle = graph.to_turtle()

        headers: dict[str, str] = {
            "Content-Type": "text/turtle",
            "If-None-Match": "*",
        }
        if slug:
            headers["Slug"] = slug
        if container:
            headers["Link"] = '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'

        resp = await self._client.request("POST", url, content=turtle, headers=headers)
        raise_for_status(resp.status_code, url, resp.text)

        location = resp.headers.get("location")
        if not location:
            raise ValueError(f"Server did not return Location header for POST to {url}")
        return location

    async def delete(self, path: str) -> None:
        """DELETE — remove a resource."""
        url = self._resolve(path)
        resp = await self._client.request("DELETE", url)
        raise_for_status(resp.status_code, url, resp.text)

    async def list(self, container_path: str) -> list[str]:
        """GET — list resources in a container. Returns URLs."""
        url = self._resolve(container_path)
        resp = await self._client.request(
            "GET", url, headers={"Accept": "text/turtle, application/ld+json;q=0.9"}
        )
        raise_for_status(resp.status_code, url, resp.text)

        metadata = extract_metadata(dict(resp.headers), url)
        content_type = metadata.get("content_type", "text/turtle")
        triples = parse_rdf(resp.text, content_type, base_uri=url)
        graph = Graph(triples)
        contains = graph.query(predicate=LDP.contains)
        return [str(t.object) for t in contains]

    async def _require_wac(self, path: str) -> Graph:
        """Read a resource and verify the server uses WAC, not ACP (SP-23).

        Raises AuthSchemeError if the server uses ACP.
        Raises ValueError if no ACL URL is found.
        Returns the resource graph with ACL metadata attached.
        """
        from people._acl.acp import AuthSchemeError, detect_auth_scheme

        resource_graph = await self.read(path)
        link_headers = {}
        if resource_graph.acl_url:
            link_headers["acl"] = resource_graph.acl_url
        scheme = detect_auth_scheme(link_headers)
        if scheme == "acp":
            raise AuthSchemeError(self._resolve(path))
        if not resource_graph.acl_url:
            raise ValueError(f"No ACL URL found for {self._resolve(path)}")
        return resource_graph

    async def grant(
        self,
        path: str,
        *,
        agent: str,
        modes: list[str],
        inherited: bool = False,
    ) -> None:
        """Grant access to a resource. Reads .acl, adds grant, writes back."""
        resource_url = self._resolve(path)

        # Discover ACL URL and verify WAC (SP-23)
        resource_graph = await self._require_wac(path)

        # Read or create the ACL (only catch 404 — any other error must propagate)
        from people._http.errors import NotFoundError
        try:
            acl_graph = await self.read(resource_graph.acl_url)
        except NotFoundError:
            acl_graph = Graph()
            acl_graph.url = resource_graph.acl_url

        # Build the grant triple
        grant_id = URI(f"{resource_graph.acl_url}#grant-{agent.split('/')[-1].split('#')[0]}")
        acl_graph.add(grant_id, RDF.type, ACL.Authorization)
        acl_graph.add(grant_id, ACL.agent, URI(agent))

        if inherited:
            acl_graph.add(grant_id, ACL.default, URI(resource_url))
        else:
            acl_graph.add(grant_id, ACL.accessTo, URI(resource_url))

        for mode in modes:
            acl_graph.add(grant_id, ACL.mode, URI(str(mode)))

        # Write the ACL back
        await self.write(resource_graph.acl_url, acl_graph)

    async def revoke(self, path: str, *, agent: str) -> None:
        """Revoke all access for an agent on a resource."""
        resource_graph = await self._require_wac(path)

        acl_graph = await self.read(resource_graph.acl_url)

        # Find and remove all triples referencing this agent
        agent_uri = URI(agent)
        agent_triples = acl_graph.query(predicate=ACL.agent, value=agent_uri)
        for t in agent_triples:
            # Remove the entire authorization block for this agent
            block_triples = acl_graph.query(subject=t.subject)
            for bt in block_triples:
                acl_graph.remove(bt.subject, bt.predicate, bt.object)

        await self.write(resource_graph.acl_url, acl_graph)

    async def grants(self, path: str) -> list[dict]:
        """List all grants on a resource. Returns list of {agent, modes, resource}."""
        resource_graph = await self._require_wac(path)

        acl_graph = await self.read(resource_graph.acl_url)

        # Find all Authorization subjects
        auth_triples = acl_graph.query(predicate=RDF.type, value=ACL.Authorization)
        results = []
        for t in auth_triples:
            subject = t.subject
            agents = [
                str(at.object) for at in acl_graph.query(subject=subject, predicate=ACL.agent)
            ]
            modes_triples = acl_graph.query(subject=subject, predicate=ACL.mode)
            modes = [str(mt.object) for mt in modes_triples]

            for a in agents:
                results.append({"agent": a, "modes": modes})

        return results

    async def discover_inbox(self, path: str) -> str | None:
        """Discover the LDN Inbox for a resource."""
        from people._ldn.inbox import discover_inbox
        return await discover_inbox(self._resolve(path), self._client)

    async def send_notification(self, inbox_path: str, notification: Graph) -> str:
        """Send a notification to an LDN Inbox. Returns the created URL."""
        from people._ldn.inbox import send_notification
        return await send_notification(self._resolve(inbox_path), notification, self._client)

    async def list_notifications(self, inbox_path: str) -> list[str]:
        """List notification URLs in an LDN Inbox."""
        from people._ldn.inbox import list_notifications
        return await list_notifications(self._resolve(inbox_path), self._client)

    def __repr__(self) -> str:
        return f"Pod({self._base_url!r})"
