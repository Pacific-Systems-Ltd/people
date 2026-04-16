<p align="right">
  <img src="https://solidproject.org/assets/img/solid-emblem.svg" alt="Solid logo" height="120">
</p>

# pacific-solid

[![PyPI](https://img.shields.io/pypi/v/pacific-solid.svg)](https://pypi.org/project/pacific-solid/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Solid Protocol](https://img.shields.io/badge/Solid_Protocol-v0.11-green.svg)](https://solidproject.org/TR/protocol)

**The Python SDK for the [Solid Project](https://solidproject.org). From [gopacific.ai](www.gopacific.ai).**

[Python](https://www.python.org) is the world's most popular programming language: the lingua franca of machine learning and data science. [Solid](https://solidproject.org/about) is [Tim Berners-Lee](https://en.wikipedia.org/wiki/Tim_Berners-Lee)'s architecture for a world where people control their own data. Created by the inventor of the [World Wide Web](https://en.wikipedia.org/wiki/World_Wide_Web), now stewarded by the [Open Data Institute](https://theodi.org/). The pacific-solid SDK connects them together.


## What you can build with this

### Citizen Digital Sovereignty

6.5 million Belgian citizens control their data with Solid. [Athumi](https://www.inrupt.com/case-study/flanders-strengthens-trusted-data-economy) was created by the Flemish government as Europe's first data utility company: a feduciary for the selective disclosure of personal data to government, employers, and businesses.

```python
# 1. Applicant grants Randstad read access to their diploma
await applicant_session.grant(
    resource="https://pods.athumi.be/citizen-12345/credentials/diploma",
    agent="https://randstad.be/solid/profile#id",
    modes=[AccessMode.READ],
)

# 2. Randstad reads the credential from the applicant's pod
credential = await randstad_session.read(
    "https://pods.athumi.be/citizen-12345/credentials/diploma",
    VerifiedCredential,
)

# 3. Verify and act
if credential.issuer == "https://kuleuven.be" and credential.valid:
    approve_application(candidate)
```

Randstad uses Solid to [digitise the validation process for academic records](https://www.bbc.co.uk/news/business-68286395). This removes friction in the job market, helping people find work more easily. Meanwhile, citizens remain in control of their data. With pacific-solid, Python developers have easy access to the same toolkit.


### Patient record portability

The [NHS has piloted](https://www.janeirodigital.com/blog/janeiro-digital-at-solid-world-nhs-personal-health-stores-with-xform-health-and-solid/) patient-controlled health records on Solid, and the Solid community is actively working on FHIR RDF in pods. When patients move between services, their medical history should move with them. No data migration, no lost history, fewer patients slipping through the gaps.

```python
patient = await session.read(
    "https://pods.nhs.uk/jane-doe/medical/summary",
    PatientSummary,
)
patient.conditions.append(new_diagnosis)
await session.update(patient)  # Patient controls who else can see this
```

Python is the [dominant language](https://www.unosquare.com/blog/programming-languages-for-biotech-from-drug-discovery-ai-to-clinical-systems/) for health data science, clinical research, and ML. This SDK links those pipelines to the Solid ecosystem.


### Solid is the bedrock of the gopacific sovereign graph

Solid is the core of [gopacific's](https://gopacific.ai) organisational intelligence engine. When users interact in a gopacific network, Solid's disclosure mechanics ensure that sensitive data remain under their owners' control. We built this SDK to unlock the power of the Solid protocol for the Python community. 


## Getting started

pacific-solid requires [Python](https://www.python.org/downloads/) 3.11 or higher.

```bash
pip install pacific-solid
```

### Dependencies

| Package | Purpose |
|---------|---------|
| [httpx](https://www.python-httpx.org/) | Async HTTP client |
| [rdflib](https://rdflib.readthedocs.io/) | RDF parsing and serialization (wrapped internally, never exposed) |
| [PyJWT](https://pyjwt.readthedocs.io/) | DPoP proof-of-possession token generation |
| [cryptography](https://cryptography.io/) | EC key pair generation for DPoP |


## Quick start

### 1. Start a Solid server

For local development, run the open-source [Community Solid Server](https://github.com/CommunitySolidServer/CommunitySolidServer) in Docker:

```bash
docker run --rm -d -p 3000:3000 solidproject/community-server:latest -b http://localhost:3000
```

Open http://localhost:3000, sign up for an account, create a pod, and generate client credentials from the account page. In production, you would point at a hosted Solid provider like [solidcommunity.net](https://solidcommunity.net/) or your organization's own server.

### 2. Authenticate and explore a pod

```python
import asyncio
import pacific_solid as ps

async def main():
    # Login once, reuse. ps = "personal store"
    me = await ps.login(
        issuer="http://localhost:3000",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
    )

    # Scope to a pod for relative-path access
    alice = me.pod("http://localhost:3000/my-pod/")

    # List everything in the pod
    resources = await alice.list("")
    for url in resources:
        print(url)

asyncio.run(main())
```

Authentication handles the full [Solid-OIDC](https://solidproject.org/TR/oidc) flow with DPoP proof-of-possession automatically. Every subsequent request is authenticated. Tokens are refreshed transparently.

### 3. Define a model and work with data

```python
import pacific_solid as ps
from pacific_solid import SCHEMA

@ps.model
class Note:
    rdf_type = SCHEMA.NoteDigitalDocument
    title: str = ps.field(SCHEMA.name)
    body: str = ps.field(SCHEMA.text)
    tags: list[str] = ps.field(SCHEMA.keywords, multiple=True)

# Create a note in a pod
note = Note(title="Hello Solid", body="My first note from Python.", tags=["solid", "python"])
url = await alice.create("notes/", note.graph, slug="hello")

# Read it back as a typed Python object
note = Note.from_graph(await alice.read(url))
print(note.title)  # "Hello Solid"

# Modify and patch (only changed fields are sent via N3 Patch)
note.tags.append("decentralized")
await alice.patch(url, note.graph)

# Delete
await alice.delete(url)
```

No raw triples. No manual Turtle construction. Python objects in, Python objects out.

## Why Python needs Solid. Why Solid needs Python.

Solid stores data as [RDF](https://www.w3.org/RDF/), a graph-based data model built on open W3C standards. Python already has the richest ecosystem for working with graph data, linked data, and knowledge graphs through libraries like rdflib, NetworkX, and the scientific Python stack.

Until now, the Solid SDK ecosystem has been a [JavaScript monoculture](https://docs.inrupt.com/developer-tools/javascript/client-libraries/). Inrupt maintains production-grade JS/TS and Java SDKs. Every other language, Python included, has had either fragmented community efforts or nothing at all. Authentication alone (Solid-OIDC with DPoP) has been the barrier that kills non-JS implementations. The [Solid Community Forum](https://forum.solidproject.org/) has years of threads from Python developers who couldn't get past it.

pacific-solid changes that.

| Python brings to Solid | Solid brings to Python |
|----------------------|----------------------|
| The dominant language in health data, bioinformatics, and clinical pipelines | Patient-controlled health records that Python pipelines can read with consent |
| Data science and ML on structured, linked data | Personal data stores that never leave the user's control |
| The world's largest developer community | A W3C-backed protocol for reading and writing linked data across organizational boundaries |
| AI agent frameworks that need somewhere to store knowledge | Sovereign knowledge graphs that agents populate, users own, and teams share |
| Automation and scripting for backend services | Decentralized authentication that works across providers |
| Mature RDF tooling (rdflib, 2400+ stars, 914K weekly downloads) | A reason for that tooling to exist beyond academic research |

## Features

### Three concepts

```python
import pacific_solid as ps          # ps = "personal store"

me = await ps.login(...)            # Session: who you are
alice = me.pod("https://pod/alice/") # Pod: what you're looking at
graph = await alice.read("notes/")  # Graph: the data
```

**Session** is your authenticated identity. Login once, reuse for any pod.
**Pod** is a scoped view onto a remote pod with relative paths.
**Graph** is a set of triples you can query, convert, and diff.

### Five methods, five HTTP verbs

```python
graph = await alice.read("notes/hello")          # GET
await alice.write("notes/hello", graph)           # PUT  (full replace)
await alice.patch("notes/hello", note.graph)      # PATCH (N3 Patch from diff)
url = await alice.create("notes/", graph)         # POST (new resource)
await alice.delete("notes/hello")                 # DELETE
```

No auto-detection between PUT and PATCH. The SDK does what you ask, explicitly.

### Typed models (optional)

Define Python classes that map to RDF predicates. The `@ps.model` decorator adds graph-awareness and snapshot-based dirty tracking.

```python
@ps.model
class Person:
    rdf_type = ps.FOAF.Person
    name: str = ps.field(ps.FOAF.name)
    email: str = ps.field(ps.FOAF.mbox)
    knows: list[str] = ps.field(ps.FOAF.knows, multiple=True)

person = Person.from_graph(await alice.read("profile/card"))
person.name = "Alice Smith"
await alice.patch("profile/card", person.graph)  # Patches only the name triple
```

Missing fields return `None` for scalars, `[]` for lists. Type checking is strict by default and configurable per-read with `strict=False`.

### Access control

Permissions are just graphs at `.acl` URLs. Grant or revoke access for specific agents, groups, or the public.

```python
# Shorthand
await alice.grant("health/gp-records", agent=dr_patel, modes=[ps.Read])
await alice.revoke("health/gp-records", agent=dr_patel)

# Or read the ACL graph directly
acl = await alice.read(graph.acl_url)
for grant in acl.all(ps.Grant):
    print(grant.agent, grant.modes)
```

### WebID discovery

Resolve a WebID URI to discover OIDC issuers and pod storage URLs.

```python
profile = await me.resolve("https://pods.example/alice/profile/card#me")
print(profile.issuers)   # ["https://solid-server.example/"]
print(profile.storages)  # ["https://pods.example/alice/"]
```

### Graph converters

```python
graph.to_dict()                         # always available
graph.to_dataframe()                    # pip install pacific-solid[pandas]
graph.to_networkx()                     # pip install pacific-solid[science]
```

### Debug logging

Every HTTP request, DPoP proof, token refresh, and retry is logged via Python's standard `logging` module.

```python
import logging
logging.getLogger("pacific_solid").setLevel(logging.DEBUG)
```

## Specifications

pacific-solid implements:

| Specification | Version | Coverage |
|--------------|---------|----------|
| [Solid Protocol](https://solidproject.org/TR/protocol) | 0.11 | CRUD, LDP Containers, Content Negotiation, N3 Patch |
| [Solid-OIDC](https://solidproject.org/TR/oidc) | Draft | Client credentials + DPoP |
| [Web Access Control](https://solid.github.io/web-access-control-spec/) | 1.0 | Read, write, inherited ACLs |
| [WebID Profile](https://solid.github.io/webid-profile/) | Draft | OIDC issuer and storage discovery |

ACP (Access Control Policy), Solid Notifications, and JSON-LD content negotiation are planned for future releases.

## Architecture

```
pacific_solid/
  _auth/         Session, Pod, Solid-OIDC, DPoP proof generation + verification, credentials
  _graph/        Graph, Triple, URI, Literal, dict/pandas/networkx converters
  _rdf/          Turtle parse/serialize (rdflib wrapper), N3 Patch builder, namespace constants
  _model/        @ps.model decorator, ps.field(), snapshot-based dirty tracking
  _acl/          WAC evaluation, Grant model, access modes
  _identity/     WebID profile resolution, OIDC issuer + storage discovery
  _http/         Authenticated httpx client, Link/WAC-Allow/ETag header parsing, error hierarchy
```

Leading underscores = private implementation. The public API is re-exported from `__init__.py`. Users import from `pacific_solid`, never from internal packages.

rdflib is used internally for RDF parsing and serialization but is never exposed in the public API. The abstraction layer allows the RDF backend to be swapped (e.g. to Oxigraph) without breaking changes.

## Development

```bash
git clone https://github.com/Pacific-Systems-Ltd/people.git
cd people
pip install -e ".[dev]"
```

### Running tests

Unit tests (including adversarial/hostile tests) run instantly with no external dependencies. E2E tests run against a real [Community Solid Server](https://github.com/CommunitySolidServer/CommunitySolidServer) in Docker.

```bash
# Unit tests (181 tests, ~2 seconds)
pytest tests/unit/

# E2E tests (requires Docker)
docker compose up -d
pytest tests/e2e/

# Everything
docker compose up -d
pytest

# Lint and type check
ruff check .
mypy pacific_solid/
```

### Test structure

```
tests/
  unit/
    test_triple.py          URI, Literal, Triple primitives
    test_graph.py           Graph CRUD, query, snapshot, Turtle round-trip
    test_model.py           @ps.model, field mapping, dirty tracking, Grant model
    test_dpop.py            DPoP generation + verification round-trip
    test_wac.py             WAC evaluation logic
    test_patch_builder.py   N3 Patch construction
    test_headers.py         Link, WAC-Allow, ETag parsing
    test_errors.py          Error hierarchy, status code mapping
    test_namespaces.py      Vocabulary constants
    test_hostile_server.py  Malicious server responses, header attacks, auth manipulation
    test_hostile_client.py  DPoP forgery, WAC bypass, N3 Patch injection
  e2e/
    test_smoke.py           Full CRUD + Patch + WAC + WebID against real CSS
```

## Feedback and contributions

Bug reports and feature requests are welcome on [GitHub Issues](https://github.com/Pacific-Systems-Ltd/people/issues).

For questions about the Solid ecosystem, see the [Solid Community Forum](https://forum.solidproject.org/) and the [Solid Protocol specification](https://solidproject.org/TR/protocol).

## License

pacific-solid is open source software [licensed under MIT](LICENSE).

Copyright 2026 Pacific.
