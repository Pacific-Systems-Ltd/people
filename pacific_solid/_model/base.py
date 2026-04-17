"""Model — base class for @ps.model-decorated classes.

Declares the attributes and methods that the @ps.model decorator injects
at runtime, so static type checkers (mypy, pyright) see them. The class
itself is intentionally empty at runtime; the decorator does the work.

Usage:

    @ps.model
    class Note(ps.Model):
        rdf_type = SCHEMA.NoteDigitalDocument
        title: str = ps.field(SCHEMA.name)
        body: str = ps.field(SCHEMA.text)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

    from pacific_solid._graph.graph import Graph


class Model:
    """Base for @ps.model classes — type-only stubs for the synthesized API.

    Inheriting from ``Model`` is what tells type checkers about ``.graph``
    and ``.from_graph()``. The @ps.model decorator separately adds an
    ``__init__`` (visible to type checkers via ``@dataclass_transform``).
    """

    if TYPE_CHECKING:
        graph: Graph

        @classmethod
        def from_graph(
            cls, graph: Graph, *, strict: bool = True
        ) -> Self: ...
