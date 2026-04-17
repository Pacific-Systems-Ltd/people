"""@ps.model — decorator that makes a class graph-aware.

Adds:
    - __init__ from field descriptors
    - .graph property (builds a Graph from current field values)
    - .from_graph(graph) classmethod (projects a Graph through the model)
    - Snapshot-based dirty tracking (diff at RDF level)

Usage:
    @ps.model
    class Note:
        rdf_type = SCHEMA.NoteDigitalDocument
        title: str = ps.field(SCHEMA.name)
        body: str = ps.field(SCHEMA.text)
        tags: list[str] = ps.field(SCHEMA.keywords, multiple=True)

    note = Note(title="Hello", body="World", tags=["solid"])
    note.graph  # -> Graph with triples

    note = Note.from_graph(graph)
    note.title = "Updated"
    note.graph.diff()  # -> (inserts, deletes)
"""

from __future__ import annotations

import copy
from typing import Any, TypeVar, dataclass_transform

from pacific_solid._graph.graph import Graph
from pacific_solid._graph.triple import URI, Literal
from pacific_solid._model.fields import FieldDescriptor, field
from pacific_solid._rdf.namespaces import RDF

_T = TypeVar("_T")


@dataclass_transform(field_specifiers=(field, FieldDescriptor), kw_only_default=True)
def model(cls: type[_T]) -> type[_T]:
    """Decorator that makes a class graph-aware.

    The class must define:
        rdf_type: URI — the RDF type for instances of this model
        fields: defined via ps.field() with type annotations

    The decorator adds __init__, graph property, from_graph classmethod,
    and snapshot-based dirty tracking.

    For type-checker visibility into ``.graph`` and ``.from_graph()``,
    inherit from :class:`people.Model` in addition to using @ps.model.
    """
    # cls_any aliases cls for runtime metaprogramming that mypy can't follow
    # (dynamic attribute injection, method assignment, .__new__/.__init__ calls).
    cls_any: Any = cls

    # Collect field descriptors from class attributes
    fields: dict[str, FieldDescriptor] = {}
    annotations: dict[str, Any] = {}

    # Walk MRO to collect annotations (but not from object)
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        annotations.update(getattr(klass, "__annotations__", {}))

    for attr_name, _annotation in annotations.items():
        if attr_name.startswith("_") or attr_name == "rdf_type":
            continue
        value = getattr(cls, attr_name, None)
        if isinstance(value, FieldDescriptor):
            fields[attr_name] = FieldDescriptor(
                predicate=value.predicate,
                multiple=value.multiple,
                python_name=attr_name,
            )

    if not hasattr(cls, "rdf_type"):
        raise TypeError(f"@ps.model class {cls.__name__} must define rdf_type")

    rdf_type_uri = str(cls_any.rdf_type)

    # Store fields on the class for introspection
    cls_any._ps_fields = fields
    cls_any._ps_rdf_type = rdf_type_uri

    # Build __init__
    def __init__(self: Any, **kwargs: Any) -> None:
        self._ps_subject = None
        self._ps_source_graph = None
        for name, desc in fields.items():
            if desc.multiple:
                setattr(self, name, list(kwargs.get(name, [])))
            else:
                setattr(self, name, kwargs.get(name))

    cls_any.__init__ = __init__

    # Build .graph property
    @property  # type: ignore[misc]
    def graph_property(self: Any) -> Graph:
        """Build a Graph from the current field values."""
        subject = URI(self._ps_subject or f"_:new-{id(self)}")

        g = Graph()
        g.add(subject, URI(str(RDF.type)), URI(rdf_type_uri))

        for name, desc in fields.items():
            value = getattr(self, name, None)
            if value is None:
                continue

            predicate = URI(desc.predicate)
            if desc.multiple:
                for v in value:
                    g.add(subject, predicate, _to_rdf_object(v))
            else:
                g.add(subject, predicate, _to_rdf_object(value))

        # If we have a source graph with a snapshot, take a snapshot of this
        # new graph so diff() works
        if self._ps_source_graph is not None:
            g._snapshot = copy.deepcopy(self._ps_source_graph._triples)
            g.url = self._ps_source_graph.url
            g.etag = self._ps_source_graph.etag
            g.acl_url = self._ps_source_graph.acl_url
            g.permissions = self._ps_source_graph.permissions

        return g

    cls_any.graph = graph_property

    # Build .from_graph classmethod
    @classmethod  # type: ignore[misc]
    def from_graph(cls_inner: Any, graph: Graph, *, strict: bool = True) -> Any:
        """Project a Graph through this model, returning a typed Python object.

        Args:
            graph: The Graph to project
            strict: If True (default), raise if the graph's rdf:type doesn't
                    match the model's rdf_type
        """
        # Find the subject with matching rdf:type
        type_triples = graph.query(
            predicate=URI(str(RDF.type)),
            value=URI(rdf_type_uri),
        )

        if strict and not type_triples:
            raise ModelTypeMismatchError(
                f"Graph has no subject with rdf:type {rdf_type_uri}. "
                f"Use strict=False to skip type checking."
            )

        # Use the first matching subject, or the first subject in the graph
        if type_triples:
            subject = type_triples[0].subject
        elif graph.subjects:
            subject = next(iter(graph.subjects))
        else:
            # Empty graph
            instance = cls_inner.__new__(cls_inner)
            instance.__init__()
            return instance

        # Extract field values
        kwargs: dict[str, Any] = {}
        for name, desc in fields.items():
            predicate = URI(desc.predicate)
            matches = graph.query(subject=subject, predicate=predicate)

            if desc.multiple:
                kwargs[name] = [_from_rdf_object(t.object) for t in matches]
            elif matches:
                kwargs[name] = _from_rdf_object(matches[0].object)
            # else: leave as None (default)

        instance = cls_inner.__new__(cls_inner)
        instance.__init__(**kwargs)
        instance._ps_subject = str(subject)

        # Take a snapshot of the source graph for dirty tracking
        source = Graph(graph.triples)
        source._snapshot = copy.deepcopy(graph._triples)
        source.url = graph.url
        source.etag = graph.etag
        source.acl_url = graph.acl_url
        source.permissions = graph.permissions
        instance._ps_source_graph = source

        return instance

    cls_any.from_graph = from_graph

    # Add repr
    def __repr__(self: Any) -> str:
        field_strs = []
        for name in fields:
            val = getattr(self, name, None)
            if val is not None:
                field_strs.append(f"{name}={val!r}")
        return f"{cls.__name__}({', '.join(field_strs)})"

    cls_any.__repr__ = __repr__

    return cls


class ModelTypeMismatchError(Exception):
    """Raised when a Graph's rdf:type doesn't match the model's rdf_type (strict mode)."""


def _to_rdf_object(value: Any) -> URI | Literal:
    """Convert a Python value to an RDF object (URI or Literal).

    Only produces URIs from explicit URI instances. Strings are always Literals.
    This prevents data corruption when a text field contains a URL.
    """
    if isinstance(value, URI):
        return value
    if isinstance(value, Literal):
        return value
    if isinstance(value, str):
        return Literal(value)
    return Literal(str(value))


def _from_rdf_object(obj: URI | Literal) -> str | Literal:
    """Convert an RDF object to a Python value.

    Plain Literals (no datatype, no language) return str for ergonomics.
    Typed/language Literals return the Literal object to preserve metadata.
    URIs return str.
    """
    if isinstance(obj, Literal):
        if obj.datatype is None and obj.language is None:
            return obj.value
        return obj
    return str(obj)
