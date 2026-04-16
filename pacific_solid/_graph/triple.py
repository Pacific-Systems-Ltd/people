"""Triple, URI, and Literal — the atoms of RDF data."""

from __future__ import annotations

from typing import NamedTuple


class URI(str):
    """An RDF URI reference. Just a string with a distinct type."""

    __slots__ = ()

    def __repr__(self) -> str:
        return f"URI({super().__repr__()})"


class Literal:
    """An RDF literal value with optional language or datatype."""

    __slots__ = ("value", "datatype", "language")

    def __init__(
        self,
        value: str,
        *,
        datatype: str | None = None,
        language: str | None = None,
    ) -> None:
        self.value = value
        self.datatype = datatype
        self.language = language

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Literal):
            return (
                self.value == other.value
                and self.datatype == other.datatype
                and self.language == other.language
            )
        if isinstance(other, str):
            return self.value == other and self.datatype is None and self.language is None
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.value, self.datatype, self.language))

    def __repr__(self) -> str:
        parts = [repr(self.value)]
        if self.datatype:
            parts.append(f"datatype={self.datatype!r}")
        if self.language:
            parts.append(f"language={self.language!r}")
        return f"Literal({', '.join(parts)})"

    def __str__(self) -> str:
        return self.value


class Triple(NamedTuple):
    """A single RDF statement: subject, predicate, object."""

    subject: URI
    predicate: URI
    object: URI | Literal  # noqa: A003


# Type alias for triple object values
TripleObject = URI | Literal
