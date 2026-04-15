# N3 Patch — Client Construction Requirements

Source: https://solidproject.org/TR/protocol (Section 5.3.1)

## Overview

N3 Patch is the REQUIRED patch format for modifying RDF resources on Solid servers. Servers MUST accept PATCH requests with N3 Patch bodies targeting RDF documents and indicate support by listing `text/n3` in the `Accept-Patch` header field.

## N3 Patch Structure

An N3 Patch document must conform to these constraints:

**Basic Composition:**
- Contain one or more patch resources
- Each patch resource identified by a URI or blank node (referenced as `?patch`)
- May contain `?patch rdf:type solid:Patch`

**Core Triple Patterns:**
- At most one triple: `?patch solid:deletes ?deletions`
- At most one triple: `?patch solid:inserts ?insertions`
- At most one triple: `?patch solid:where ?conditions`

**Formula Requirements:**
When present, `?deletions`, `?insertions`, and `?conditions` must be non-nested cited formulae containing only triples and triple patterns. When absent, they default to empty.

## Default/Simplified N3 Patch Constraints (InsertDeletePatch)

The specification governs N3 Patch documents adhering to these additional constraints:

- Exactly one patch resource with consistent `?patch` subject
- Must contain `?patch rdf:type solid:InsertDeletePatch`
- Variables in `?insertions` and `?deletions` must appear in `?conditions`
- Neither `?insertions` nor `?deletions` may contain blank nodes

## Processing Semantics

Servers process patches sequentially:

1. Start with the RDF dataset from the target document (or empty if nonexistent)
2. Match `?conditions` against existing triples; find all variable mappings
3. Reject with `409` if zero or multiple mappings exist
4. Propagate mappings to both deletion and insertion formulae
5. Reject with `409` if deletion set is non-empty but dataset lacks all those triples
6. Remove deletion triples; add insertion triples (creating new blank nodes as needed)
7. Respond with appropriate status code

## Error Handling

- `422` status if patch documents violate structural constraints
- `409` status if conditions match zero or multiple times, or deletions don't exist

## Operation Classification (WAC implications)

- `?conditions` non-empty: Read operation
- `?insertions` non-empty: Append operation
- `?deletions` non-empty: Read and Write operations

## Example N3 Patch

```n3
@prefix solid: <http://www.w3.org/ns/solid/terms#>.
@prefix ex: <http://example.org/>.

_:patch a solid:InsertDeletePatch;
  solid:where   { ?person ex:name "Alice". };
  solid:deletes { ?person ex:age 30. };
  solid:inserts { ?person ex:age 31. }.
```
