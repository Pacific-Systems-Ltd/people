"""Graph — a set of triples. The core data primitive of people."""

from __future__ import annotations

import copy
from typing import Any

from people._graph.triple import URI, Literal, Triple, TripleObject
from people._rdf.parse import parse_turtle
from people._rdf.serialize import serialize_turtle


class Graph:
    """A set of RDF triples with query, filter, and conversion methods.

    Graph is a value object: it holds data in memory, not a connection to a pod.
    Create via constructor, from Turtle, or from a dict. Convert to dict, pandas,
    NetworkX, or Neo4j via converter methods.
    """

    def __init__(self, triples: list[Triple] | None = None) -> None:
        self._triple_set: set[Triple] = set()
        self._triples: list[Triple] = []  # maintains insertion order for serialization
        self._by_subject: dict[URI, list[Triple]] = {}
        self._by_predicate: dict[URI, list[Triple]] = {}
        self._snapshot: list[Triple] | None = None
        self.url: str | None = None
        self.etag: str | None = None
        self.acl_url: str | None = None
        self.permissions: dict[str, set[str]] | None = None

        if triples:
            for t in triples:
                self._add_triple(t)

    def _add_triple(self, triple: Triple) -> bool:
        """Internal: add a triple with index maintenance. Returns True if new."""
        if triple in self._triple_set:
            return False
        self._triple_set.add(triple)
        self._triples.append(triple)
        self._by_subject.setdefault(triple.subject, []).append(triple)
        self._by_predicate.setdefault(triple.predicate, []).append(triple)
        return True

    def _remove_triple(self, triple: Triple) -> bool:
        """Internal: remove a triple with index maintenance. Returns True if removed."""
        if triple not in self._triple_set:
            return False
        self._triple_set.discard(triple)
        self._triples.remove(triple)
        subj_list = self._by_subject.get(triple.subject)
        if subj_list:
            try:
                subj_list.remove(triple)
            except ValueError:
                pass
        pred_list = self._by_predicate.get(triple.predicate)
        if pred_list:
            try:
                pred_list.remove(triple)
            except ValueError:
                pass
        return True

    @property
    def triples(self) -> list[Triple]:
        """All triples in this graph."""
        return list(self._triples)

    @property
    def subjects(self) -> set[URI]:
        """All unique subjects in this graph."""
        return set(self._by_subject.keys())

    @property
    def predicates(self) -> set[URI]:
        """All unique predicates in this graph."""
        return set(self._by_predicate.keys())

    @property
    def has_snapshot(self) -> bool:
        """Whether this graph has a snapshot for diff-based patching."""
        return self._snapshot is not None

    def add(self, subject: URI, predicate: URI, obj: TripleObject) -> None:
        """Add a triple to this graph. O(1) membership test."""
        self._add_triple(Triple(subject, predicate, obj))

    def remove(self, subject: URI, predicate: URI, obj: TripleObject) -> None:
        """Remove a triple from this graph. No-op if not present."""
        self._remove_triple(Triple(subject, predicate, obj))

    def query(
        self,
        predicate: URI | None = None,
        value: TripleObject | str | None = None,
        subject: URI | None = None,
    ) -> list[Triple]:
        """Filter triples by predicate, value, and/or subject.

        Uses indices for O(1) lookup by subject or predicate when available.
        """
        # Use index when possible
        if subject is not None and predicate is None and value is None:
            return list(self._by_subject.get(subject, []))
        if predicate is not None and subject is None and value is None:
            return list(self._by_predicate.get(predicate, []))

        # Start from the most selective index available
        if subject is not None:
            results = list(self._by_subject.get(subject, []))
            if predicate is not None:
                results = [t for t in results if t.predicate == predicate]
        elif predicate is not None:
            results = list(self._by_predicate.get(predicate, []))
        else:
            results = list(self._triples)

        if value is not None:
            if isinstance(value, str):
                results = [
                    t for t in results
                    if (isinstance(t.object, Literal) and t.object.value == value)
                    or (isinstance(t.object, URI) and str(t.object) == value)
                ]
            else:
                results = [t for t in results if t.object == value]
        return results

    def all(self, model_class: type) -> list:
        """Project all subjects of the model's rdf_type through the model."""
        rdf_type = getattr(model_class, "rdf_type", None)
        if rdf_type is None:
            raise ValueError(f"{model_class.__name__} has no rdf_type")
        from people._rdf.namespaces import RDF
        type_triples = self.query(predicate=RDF.type, value=rdf_type)
        results = []
        for t in type_triples:
            sub_triples = self.query(subject=t.subject)
            sub_graph = Graph(sub_triples)
            sub_graph._snapshot = copy.deepcopy(sub_triples)
            results.append(model_class.from_graph(sub_graph))
        return results

    def take_snapshot(self) -> None:
        """Take a snapshot of the current state for later diffing."""
        self._snapshot = copy.deepcopy(self._triples)

    def diff(self) -> tuple[list[Triple], list[Triple]]:
        """Compute inserts and deletes since the last snapshot.

        Returns (inserts, deletes). Raises ValueError if no snapshot exists.
        """
        if self._snapshot is None:
            raise ValueError("No snapshot — call take_snapshot() or use from_graph()")
        current = self._triple_set
        snapshot = set(self._snapshot)
        inserts = list(current - snapshot)
        deletes = list(snapshot - current)
        return inserts, deletes

    def reset_snapshot(self) -> None:
        """Reset the snapshot to the current state (after a successful patch)."""
        self._snapshot = copy.deepcopy(self._triples)

    # --- Conversion methods ---

    def to_turtle(self, base_uri: str | None = None) -> str:
        """Serialize this graph to Turtle format."""
        return serialize_turtle(self._triples, base_uri=base_uri)

    @classmethod
    def from_turtle(cls, data: str, base_uri: str | None = None) -> Graph:
        """Parse Turtle data into a Graph."""
        triples = parse_turtle(data, base_uri=base_uri)
        return cls(triples)

    def to_dict(self) -> list[dict[str, Any]]:
        """Convert to a list of dicts: [{subject, predicate, object}, ...]."""
        result = []
        for t in self._triples:
            obj = t.object
            if isinstance(obj, Literal):
                obj_dict: dict[str, Any] = {"value": obj.value, "type": "literal"}
                if obj.datatype:
                    obj_dict["datatype"] = obj.datatype
                if obj.language:
                    obj_dict["language"] = obj.language
            else:
                obj_dict = {"value": str(obj), "type": "uri"}
            result.append({
                "subject": str(t.subject),
                "predicate": str(t.predicate),
                "object": obj_dict,
            })
        return result

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> Graph:
        """Create a Graph from a list of dicts."""
        triples = []
        for row in data:
            subject = URI(row["subject"])
            predicate = URI(row["predicate"])
            obj_data = row["object"]
            if obj_data["type"] == "literal":
                obj: TripleObject = Literal(
                    obj_data["value"],
                    datatype=obj_data.get("datatype"),
                    language=obj_data.get("language"),
                )
            else:
                obj = URI(obj_data["value"])
            triples.append(Triple(subject, predicate, obj))
        return cls(triples)

    def to_dataframe(self):
        """Convert to a pandas DataFrame. Requires: pip install people[pandas]."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install it with: pip install people[pandas]"
            ) from None
        rows = []
        for t in self._triples:
            obj = t.object
            rows.append({
                "subject": str(t.subject),
                "predicate": str(t.predicate),
                "object": obj.value if isinstance(obj, Literal) else str(obj),
            })
        return pd.DataFrame(rows)

    def to_networkx(self):
        """Convert to a NetworkX DiGraph. Requires: pip install people[science]."""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError(
                "networkx is required for to_networkx(). "
                "Install it with: pip install people[science]"
            ) from None
        g = nx.DiGraph()
        for t in self._triples:
            obj_val = t.object.value if isinstance(t.object, Literal) else str(t.object)
            g.add_edge(str(t.subject), obj_val, predicate=str(t.predicate))
        return g

    def __len__(self) -> int:
        return len(self._triples)

    def __bool__(self) -> bool:
        return len(self._triples) > 0

    def __contains__(self, triple: Triple) -> bool:
        return triple in self._triple_set

    def __repr__(self) -> str:
        return f"Graph({len(self._triples)} triples)"
