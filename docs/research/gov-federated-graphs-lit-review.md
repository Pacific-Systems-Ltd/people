# Literature Review: Sovereign Graphs

**Briefing title:** "Sovereign Graphs: How governments are using federated knowledge graphs to build institutional memory."

**Prepared for:** [The Institutional Architecture Lab](https://www.tial.org)

**Date:** 2026-04-06

---

## Annotated Bibliography

### 1. Federated Infrastructure & National Models

**Puura, A., Soe, R.-M., & Thabit, S. (2026).** "Advancing interoperability of data exchange in Europe: Insights from Estonia's experience for the common European data spaces." *Data in Brief*, 64, 112361. DOI: [10.1016/j.dib.2025.112361](https://www.sciencedirect.com/science/article/pii/S2352340925010753)

> The definitive recent assessment of Estonia's X-Road as a model for European-scale federated data exchange. The authors argue that the primary obstacles to interoperability are organisational, political, and legal — not technological. Directly relevant to the briefing's core thesis: sovereign graphs require institutional architecture, not just graph architecture. The paper bridges a 20+ year national deployment with the EU's emerging Common European Data Spaces programme.

**Hardy, A. (2024).** "Estonia's digital diplomacy: Nordic interoperability and the challenges of cross-border e-governance." *Internet Policy Review*, 13(3). [PDF](https://policyreview.info/pdf/policyreview-2024-3-1785.pdf)

> Examines the X-Road federation between Estonia, Finland, Iceland, Faroe Islands, and Åland — the most mature cross-border federated data exchange in operation. Key source for the briefing's argument that sovereign graphs can federate *across* national boundaries without surrendering sovereignty. Surfaces the diplomatic and governance challenges that technical interoperability alone cannot solve.

---

### 2. Sovereignty & Political Economy

**Baura, A. (2025).** "European ambitions captured by American clouds: digital sovereignty through Gaia-X?" *Information, Communication & Society*, 29(2). DOI: [10.1080/1369118X.2025.2516545](https://www.tandfonline.com/doi/full/10.1080/1369118X.2025.2516545)

> A critical analysis of GAIA-X — the EU's flagship federated data infrastructure initiative (350+ members, 180+ data spaces). Exposes the central paradox: an initiative designed to contest hyperscaler dominance has invited those same hyperscalers into its governance. Essential for the briefing as a cautionary frame: sovereign infrastructure requires sovereign governance, not just sovereign branding.

**Calzati, S. & van Loenen, B. (2023).** "Beyond federated data: a data commoning proposition for the EU's citizen-centric digital strategy." *AI & Society*. DOI: [10.1007/s00146-023-01743-9](https://link.springer.com/article/10.1007/s00146-023-01743-9)

> Argues that the EU's "citizen-centric" digital governance is more rhetorical than operational — the actual architecture enables a corporate-driven, economic-oriented federated data system. Proposes "data commoning" as a complement to federation. Provides the briefing with a theoretical framework: federated knowledge graphs can either reinforce extractive data relations or enable genuine institutional memory that serves publics. The distinction depends on governance design.

---

### 3. Knowledge Graphs for Government

**Meroño-Peñuela, A., Simperl, E., Kurteva, A., & Reklos, I. (2025).** "KG.GOV: Knowledge graphs as the backbone of data governance in AI." *Journal of Web Semantics*, 85, 100847. DOI: [10.1016/j.websem.2024.100847](https://www.sciencedirect.com/science/article/pii/S1570826824000337)

> Positions knowledge graphs at a higher abstraction layer within AI workflows — not as data stores but as *governance backbones*. Proposes three dimensions: modelling data, alternative representations, and describing behaviour. Directly supports the briefing's framing of knowledge graphs as institutional infrastructure (not merely technical tooling). The Croissant vocabulary case study demonstrates how KGs can make datasets self-describing and auditable across organisations.

**Serderidis, K., Konstantinidis, I., Meditskos, G., Peristeras, V., & Bassiliades, N. (2024).** "d2kg: An integrated ontology for knowledge graph-based representation of government decisions and acts." *Semantic Web Journal*. DOI: [10.3233/SW-243535](https://journals.sagepub.com/doi/full/10.3233/SW-243535)

> Addresses the specific problem of encoding government decisions and legislative acts as linked data. Most government documents are published as PDFs — opaque, unlinkable, semantically dead. d2kg provides an ontology that makes the *reasoning* behind government decisions machine-readable and queryable. This is institutional memory in the most literal sense: a knowledge graph that captures not just what a government decided, but the legal and evidential structure of *why*.

---

### 4. Civic Technology & Participatory Governance

**Cui, P.J.-W. (2023).** Interview in Kurihara, K., "Privacy Talk with Peter Jia-Wei Cui, Contributor of vTaiwan Community." *Medium / Privacy Talk*. [Link](https://medium.com/@kuriharan/privacy-talk-with-%E5%B4%94%E5%AE%B6%E7%91%8B-peter-jia-wei-cui-contributor-of-vtaiwan-community-why-did-you-start-to-b4954c28ad34)

> First-person account from a core vTaiwan contributor on the intersection of civic tech, digital rights, and participatory governance. vTaiwan — winner of an OpenAI "Democratic Input to AI" grant — demonstrates that sovereign institutional memory is not only a *technical* problem but a *democratic* one: who gets to contribute to the knowledge graph, and whose deliberations does it encode? The g0v community's budget-visualisation project (transforming opaque government Excel files into queryable public data) is an early prototype of the sovereign graph concept applied to fiscal transparency.

---

### 5. Knowledge Graphs & Policy Analysis

**Zhang, Y., Porter, A.L., Cunningham, S.W., Chiavetta, D., & Newman, N. (2021).** "Parallel or Intersecting Lines? Intelligent Bibliometrics for Investigating the Involvement of Data Science in Policy Analysis." *IEEE Transactions on Engineering Management*, 68(5), 1259–1271. DOI: [10.1109/TEM.2020.2974761](https://ieeexplore.ieee.org/document/9028088/)

> From Yi Zhang's team at UTS Sydney. Maps the convergence of data science methods (including graph-based representations) with policy analysis as an emergent cross-disciplinary field. The "intelligent bibliometrics" framework itself — charting evolutionary pathways of scientific innovation through knowledge graph methods — demonstrates the technique the briefing describes: using graph structures to make the *development of knowledge itself* legible and queryable. Provides academic grounding for the claim that graph-based methods are now entering the policy domain.

---

### 6. Government Deployment: Solid Protocol at Scale

**Inrupt / Athumi (2023).** "Flanders Government strengthens a trusted data economy with Inrupt's Enterprise Solid Server." *Case Study*. [Link](https://www.inrupt.com/case-study/flanders-strengthens-trusted-data-economy)

> The most advanced government-scale deployment of the Solid protocol. The Flemish government created Athumi — a public data utility company — to issue Solid Pods to citizens, beginning with diploma verification for recruitment. Citizens control access to their own data through a "Personal Data Safe" in their Citizen Profile. This is the briefing's clearest real-world example of a sovereign graph in which the *citizen* is a node with agency: granting, revoking, and auditing data access. Built on W3C standards (RDF, Linked Data), it demonstrates that the Solid/knowledge-graph stack is production-ready for national-scale institutional use.

---

## Coverage Matrix

| Dimension | Sources |
|---|---|
| Federated infrastructure (deployed) | Puura et al. (X-Road), Hardy (Nordic federation), Flanders/Athumi (Solid) |
| Political economy of sovereignty | Baura (GAIA-X), Calzati & van Loenen (data commoning) |
| Knowledge graphs for government | Meroño-Peñuela et al. (KG.GOV), Serderidis et al. (d2kg) |
| Civic tech & democratic participation | Cui / vTaiwan |
| Graph methods in policy analysis | Zhang et al. (UTS) |

## Potential Utility of the `people` SDK

The literature describes *what* governments are building — federated knowledge graphs as institutional memory. The `people` SDK (`pacific-solid`) is a concrete *how*: a Python-native programmatic interface to the Solid protocol, which is the W3C-backed standard underpinning the most advanced of these deployments.

### Where the SDK maps onto the literature

**Athumi / Flanders (Source 9).** The SDK's lead use case. `people` implements the full Solid-OIDC + DPoP authentication flow, WAC access control, and CRUD operations required to interact with Athumi's pod infrastructure. The README code sample — a citizen granting Randstad read access to a diploma credential — is a working illustration of what the Flanders deployment enables. The SDK makes this pattern accessible to any Python developer, not just those fluent in JavaScript or the Inrupt toolchain.

**d2kg / Government decisions as knowledge graphs (Source 6).** The `@ps.model` decorator maps Python classes to RDF types and predicates, with snapshot-based dirty tracking. A `GovernmentDecision` model mapping to the d2kg ontology could be defined in a few lines, stored in a Solid pod, and queried with `graph.query()`. The N3 Patch builder ensures that only changed triples are transmitted — critical for audit trails where the *delta* between decisions matters as much as their content.

**KG.GOV / Knowledge graphs as governance backbone (Source 5).** Meroño-Peñuela et al. argue that knowledge graphs should sit at a higher abstraction layer — not as data stores but as governance infrastructure. The SDK's `Graph` converters (`to_dataframe()`, `to_networkx()`, `to_dict()`) position it as the bridge between the Solid protocol layer and Python's analytical ecosystem. A governance knowledge graph stored in Solid pods becomes directly analysable in pandas or NetworkX without intermediate ETL.

**X-Road / Estonia (Sources 1–2).** X-Road and Solid solve different layers of the same problem. X-Road is federated *transport* middleware: it moves data between information systems with cryptographic integrity. Solid is federated *storage* with consent: it stores data in pods under the data subject's control. They are complementary. A Python service running `people` could read from a citizen's Solid pod (with their consent) and expose that data via an X-Road security server — bridging person-centric and system-centric federation. The SDK's storage discovery module (`discover_storage()`) and LDN inbox (`discover_inbox()`, `send_notification()`) provide the plumbing for this kind of cross-system integration.

**vTaiwan / Civic tech (Source 7).** The g0v community's budget-visualisation project transformed opaque government spreadsheets into queryable public data. The SDK extends this pattern: citizen deliberation inputs stored in Solid pods, with selective disclosure to policymakers via WAC grants. The Linked Data Notifications module enables reactive workflows — when a citizen contributes to a deliberation, downstream systems are notified. The `NotificationStream` WebSocket interface supports real-time processing of these events. This makes it possible to build a vTaiwan-style deliberation platform where participants *own* their contributions.

**Zhang et al. / Graph methods for policy analysis (Source 8).** Zhang's work at UTS demonstrates that graph-based representations are entering the policy analysis domain. The SDK's `to_networkx()` converter provides a direct path: a policy knowledge graph stored in Solid can be loaded into NetworkX for the kind of bibliometric and evolutionary-pathway analysis Zhang describes. Python is already the dominant language for this work; the SDK removes the Solid authentication barrier that has historically blocked Python developers from accessing linked data stores.

### What the SDK enables that the literature does not yet describe

The literature treats federation, knowledge graphs, and data sovereignty as separate (if converging) threads. The SDK collapses them into a single developer experience:

1. **Authenticate** (`ps.login`) — one call, handles Solid-OIDC + DPoP transparently.
2. **Discover** (`discover_storage`, `discover_inbox`, `discover_channels`) — find pods, inboxes, and notification channels without hardcoding URLs.
3. **Read/write linked data** (`pod.read`, `pod.write`, `pod.patch`, `pod.create`) — five methods, five HTTP verbs, no raw triples.
4. **Model as Python objects** (`@ps.model`) — RDF triples in, Python objects out.
5. **Control access** (`evaluate_wac`, `pod.grant`, `pod.revoke`) — server-side WAC evaluation and client-side grant management.
6. **Subscribe to changes** (`subscribe`, `NotificationStream`) — real-time WebSocket notifications when pod data changes.

This is the toolchain a government data team would need to build a sovereign graph prototype: not a research framework, but a production-grade SDK with adversarial security tests (`test_hostile_server.py`, `test_hostile_client.py`) and spec-level protocol coverage.

### Implication for the briefing

The existence of `people` changes the nature of the argument. The briefing can move beyond "governments *should* build sovereign graphs" to "governments *can* build them, today, in the language their data scientists already use." The Flanders deployment proves the protocol works at national scale. The SDK proves the developer experience is ready for the Python ecosystem. The gap is institutional architecture — which is what the briefing is about.

## Notes

The bibliography spans **3 deployed national systems** (Estonia, Finland/Nordic, Flanders), **2 EU-scale policy initiatives** (GAIA-X, Common European Data Spaces), **1 civic-tech community** (vTaiwan/g0v), and **3 academic frameworks** for how knowledge graphs serve governance. It covers the period 2021–2026 and draws from computer science, political science, law, and science & technology studies.
