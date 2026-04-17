"""ps.field() — maps a Python attribute to an RDF predicate.

Usage:
    @ps.model
    class Note:
        rdf_type = SCHEMA.NoteDigitalDocument
        title: str = ps.field(SCHEMA.name)
        tags: list[str] = ps.field(SCHEMA.keywords, multiple=True)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDescriptor:
    """Describes the mapping between a Python attribute and an RDF predicate."""

    predicate: str
    multiple: bool = False
    python_name: str = ""  # set by the model decorator


def field(predicate: str, *, multiple: bool = False) -> Any:
    """Define a field mapping to an RDF predicate.

    Args:
        predicate: The RDF predicate URI (e.g. SCHEMA.name)
        multiple: If True, the field holds a list of values (default: False)

    Returns:
        A FieldDescriptor (used by @ps.model to set up the class).
    """
    return FieldDescriptor(predicate=str(predicate), multiple=multiple)
