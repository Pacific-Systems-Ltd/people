"""N3 Patch builder and applicator.

Builds solid:InsertDeletePatch documents for PATCH requests.
Also applies patches to graphs (server-side building block).
"""

from __future__ import annotations

from people._graph.triple import URI, Literal, Triple


def build_n3_patch(inserts: list[Triple], deletes: list[Triple]) -> str:
    """Build an N3 Patch body from insert and delete triple lists.

    Produces a valid solid:InsertDeletePatch document per Solid Protocol 5.3.1.

    Raises ValueError if both inserts and deletes are empty.
    """
    if not inserts and not deletes:
        raise ValueError("Cannot build N3 Patch with no inserts or deletes")

    lines = [
        "@prefix solid: <http://www.w3.org/ns/solid/terms#>.",
        "",
        "_:patch a solid:InsertDeletePatch;",
    ]

    parts = []

    if deletes:
        delete_body = _serialize_triples(deletes)
        parts.append(f"  solid:deletes {{ {delete_body} }}")

    if inserts:
        insert_body = _serialize_triples(inserts)
        parts.append(f"  solid:inserts {{ {insert_body} }}")

    lines.append(";\n".join(parts) + ".")

    return "\n".join(lines)


def apply_patch(graph_triples: list[Triple], patch_body: str) -> list[Triple]:
    """Apply an N3 Patch to a list of triples (server-side).

    Parses the patch body, removes delete triples, adds insert triples.
    Returns the new list of triples.

    Handles solid:InsertDeletePatch with literal insert/delete formulae.
    """
    from rdflib import Graph as RDFLibGraph
    from rdflib import Namespace

    solid_ns = Namespace("http://www.w3.org/ns/solid/terms#")
    rdf_ns = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

    g = RDFLibGraph()
    g.parse(data=patch_body, format="n3")

    result = list(graph_triples)
    deletes_to_remove: list[Triple] = []
    inserts_to_add: list[Triple] = []

    # Find the patch resource (typed as solid:InsertDeletePatch)
    for patch_node in g.subjects(predicate=rdf_ns.type, object=solid_ns.InsertDeletePatch):
        # Process deletes — triples inside the solid:deletes formula graph
        for formula in g.objects(subject=patch_node, predicate=solid_ns.deletes):
            if hasattr(formula, 'identifier'):
                for s, p, o in g.store.triples((None, None, None), context=formula):
                    deletes_to_remove.append(_convert_rdflib_triple(s, p, o))

        # Process inserts — triples inside the solid:inserts formula graph
        for formula in g.objects(subject=patch_node, predicate=solid_ns.inserts):
            if hasattr(formula, 'identifier'):
                for s, p, o in g.store.triples((None, None, None), context=formula):
                    inserts_to_add.append(_convert_rdflib_triple(s, p, o))

    # If rdflib N3 formula parsing didn't yield results, fall back to
    # regex-based extraction from the patch body (common for simple patches)
    if not deletes_to_remove and not inserts_to_add:
        deletes_to_remove, inserts_to_add = _extract_from_patch_text(patch_body)

    # Apply deletes
    for d in deletes_to_remove:
        result = [t for t in result if t != d]

    # Apply inserts (avoid duplicates)
    existing = set(result)
    for i in inserts_to_add:
        if i not in existing:
            result.append(i)
            existing.add(i)

    return result


def _extract_from_patch_text(patch_body: str) -> tuple[list[Triple], list[Triple]]:
    """Fallback: extract insert/delete triples from N3 patch text.

    Parses the content between solid:deletes { ... } and solid:inserts { ... }
    as Turtle fragments.
    """
    import re

    from people._rdf.parse import parse_turtle

    deletes: list[Triple] = []
    inserts: list[Triple] = []

    # Extract deletes block
    delete_match = re.search(r'solid:deletes\s*\{([^}]*)\}', patch_body)
    if delete_match:
        turtle_fragment = delete_match.group(1).strip()
        if turtle_fragment:
            # Add prefixes from the patch document for parsing
            prefixes = _extract_prefixes(patch_body)
            deletes = parse_turtle(prefixes + turtle_fragment)

    # Extract inserts block
    insert_match = re.search(r'solid:inserts\s*\{([^}]*)\}', patch_body)
    if insert_match:
        turtle_fragment = insert_match.group(1).strip()
        if turtle_fragment:
            prefixes = _extract_prefixes(patch_body)
            inserts = parse_turtle(prefixes + turtle_fragment)

    return deletes, inserts


def _extract_prefixes(n3_text: str) -> str:
    """Extract @prefix declarations from N3 text."""
    import re
    prefixes = re.findall(r'@prefix\s+[^.]+\.', n3_text)
    return "\n".join(prefixes) + "\n" if prefixes else ""


def _convert_rdflib_triple(s, p, o) -> Triple:
    """Convert rdflib triple to our Triple type."""
    from rdflib import Literal as RDFLiteral

    subject = URI(str(s))
    predicate = URI(str(p))

    if isinstance(o, RDFLiteral):
        obj = Literal(
            str(o),
            datatype=str(o.datatype) if o.datatype else None,
            language=o.language,
        )
    else:
        obj = URI(str(o))

    return Triple(subject, predicate, obj)


def _serialize_triples(triples: list[Triple]) -> str:
    """Serialize a list of triples to N3 format for patch bodies."""
    parts = []
    for t in triples:
        s = f"<{t.subject}>"
        p = f"<{t.predicate}>"
        obj = t.object
        if isinstance(obj, Literal):
            o = _serialize_literal(obj)
        else:
            o = f"<{obj}>"
        parts.append(f"{s} {p} {o} .")
    return " ".join(parts)


def _serialize_literal(lit: Literal) -> str:
    """Serialize a Literal to N3 format."""
    escaped = lit.value.replace("\\", "\\\\").replace('"', '\\"')
    result = f'"{escaped}"'
    if lit.language:
        result += f"@{lit.language}"
    elif lit.datatype:
        result += f"^^<{lit.datatype}>"
    return result
