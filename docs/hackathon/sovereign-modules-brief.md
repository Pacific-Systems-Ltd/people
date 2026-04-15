# Solid Forum: Sovereign Deliberation for the Solid Community

**Pacific — Solid Symposium Hackathon 2026**

**Authors:** Ralph Heward-Mills, Pacific Systems Ltd

**Date:** April 2026

---

## Abstract

We present Solid Forum, a public deliberation tool for the Solid community that runs on the Solid protocol itself. Participants log in with their WebID, write short statements about the project's direction, and vote on others' statements — with every contribution stored in the participant's own pod, not on a central server. The forum aggregates contributions with consent, clusters voting patterns to surface consensus and disagreement, and uses AI to summarise the community's position. The process follows vTaiwan's four-stage deliberation model (propose, opine, reflect, decide), adapted for the Solid Symposium. The result is a queryable, linked-data knowledge graph of what the Solid community thinks — owned collectively, controlled individually. Built on `people`, the first production-grade Python SDK for the Solid Protocol.

---

## 1. The Problem

The Solid community has a protocol, a specification process, and a growing ecosystem of deployments. What it lacks is a structured, inclusive mechanism for surfacing community-wide priorities and building consensus on strategic direction.

Discussion currently happens across GitHub issues, the Solid Community Forum (Discourse), Matrix channels, the weekly community call, and ad hoc conversations at events. Each of these channels has a selection effect: GitHub reaches implementers, Discourse reaches engaged enthusiasts, the weekly call reaches those in compatible timezones. None of them provides a systematic picture of where the broader community — including deployers, academics, policymakers, and newcomers — actually stands on the questions that matter.

The Solid Symposium convenes this broader community once a year. The 2026 edition features sessions on "Achieving adoption of Solid at scale," WAC vs. ACP, Solid Notifications, federated learning, and decentralised AI. These are strategic questions with genuine disagreement. But the Symposium's format — talks, panels, hallway conversations — does not produce a legible record of where the community lands.

More pointedly: a community that builds decentralised, user-sovereign infrastructure governs itself with centralised, platform-owned tools. The forum posts belong to Discourse. The issues belong to GitHub. The chat logs belong to Matrix. If the Solid protocol is ready for real applications, it should be ready for this one.

## 2. vTaiwan: A Proven Model

vTaiwan is an open consultation process created by Taiwan's g0v civic hacking community in 2014. It has facilitated deliberation on 20+ legislative issues, with the government acting on 80% of proposals. The process design is the key innovation.

### 2.1 The Four Stages

**Proposal.** Weekly hackathons (in-person + virtual) where anyone — programmers, journalists, public servants, students — can submit an issue for discussion. Both a government body and vTaiwan facilitators must agree to proceed. Research and stakeholder mapping happen here.

**Opinion.** A month-long open collection phase. Two tools work in tandem:
- *Discourse* for questions and long-form responses (government officials must respond within one week)
- *Polis* for short statements and voting. Participants write one- or two-sentence positions and vote agree/disagree/pass on others'. Crucially, **there is no reply button**. This prevents threads from becoming arguments. Polis clusters participants by voting pattern, visualising where consensus exists and where groups diverge. The design incentivises *bridging statements* — positions that attract agreement across clusters.

**Reflection.** In-person stakeholder meetings, livestreamed and open to public questions via chat. Facilitators use the ORID method (Objective → Reflective → Interpretive → Decisional). Raw and analysed reports are published.

**Legislation.** Rough consensus is converted into policy. The government must act or publicly explain why not.

### 2.2 What Makes It Work

The interaction design is inseparable from the outcome:
- Short statements lower the barrier to participation
- No reply button prevents polarisation
- Voting reveals latent consensus that threaded discussion obscures
- Clustering shows the *shape* of disagreement, not just its existence
- Mandatory government response creates accountability
- Hybrid online-offline format combines scale with depth

### 2.3 Alignment Assemblies

Audrey Tang extended this model with Alignment Assemblies (2023–present), developed with the Collective Intelligence Project, Anthropic, and OpenAI. Hundreds of thousands of randomly selected citizens are invited to co-create AI governance guidelines, using Polis as the deliberative engine. The project received the Right Livelihood Award in 2025. It demonstrates that structured public deliberation works at scale — and that AI can assist the process without capturing it.

## 3. Solid Forum

Solid Forum adapts the vTaiwan process for the Solid community, with one structural difference: **the data layer runs on Solid**.

### 3.1 Participation Flow

1. **Log in with your WebID.** Any Solid identity provider — solidcommunity.net, solidweb.org, a self-hosted CSS instance. Authentication uses the Solid-OIDC Authorization Code flow with PKCE, handled by the `people` SDK's `start_auth_flow()` and `login_interactive()`.

2. **Write a statement.** A short position on the current topic. The forum app writes it as an RDF document to the participant's pod at `/forum/statements/`, using `pod.create()`. The statement is typed with `@ps.model` and includes the topic URI, the statement text, and a timestamp.

3. **Vote on others' statements.** Agree, disagree, or pass. Each vote is stored in the participant's pod at `/forum/votes/`. No reply button.

4. **Grant the aggregator read access.** The participant grants the forum's aggregator WebID Read access to their `/forum/` container via WAC. This is the consent boundary: the aggregator can read your contributions only because you said it could.

5. **See the consensus map.** The aggregator reads from all consenting participants' pods, clusters voting patterns, and renders a live D3.js visualisation in the browser.

### 3.2 What Lives Where

| Data | Location | Controlled by |
|---|---|---|
| Your statements | Your pod (`/forum/statements/`) | You |
| Your votes | Your pod (`/forum/votes/`) | You |
| The aggregate consensus | A shared public pod | The community |
| The AI summary | The shared public pod | The community |
| The forum application code | Open source repository | Anyone |

The aggregator never stores participant data. It reads from pods in real time via Solid's CRUD operations and WebSocket notifications. If a participant revokes access, their contributions disappear from the aggregate — because they were never copied.

### 3.3 The AI Layer

An AI assistant (Claude) reads the aggregated consensus data — not individual pods — and produces a structured summary: the main areas of consensus, the points of disagreement, the bridging statements that attracted cross-cluster support, and the questions that remain unresolved. The summary is written as linked data to the shared public pod, attributable and auditable. The AI never accesses participant pods directly; it operates on the already-consented aggregate.

### 3.4 From Hackathon to Symposium

The hackathon (April 27–29) builds the forum and seeds it with topics drawn from the Symposium programme:
- What should be the next specification priority?
- WAC or ACP as the recommended access control mechanism?
- How should Solid engage with EU Data Spaces?
- What does "achieving adoption at scale" require?
- How should Solid engage with AI agent frameworks?

The forum opens during the Symposium (April 30 – May 1). Participants — both in-person attendees and remote contributors with WebIDs — write statements and vote. The consensus map updates live. The AI summary is presented at the closing session.

The forum remains open after the Symposium. If it's useful, it becomes a standing tool for the community. If it isn't, the community will have learned something concrete about what Solid still needs to be ready for applications like this.

## 4. Why This Matters

### 4.1 For the Solid Community

The forum produces a legible, structured record of community priorities — not another thread, but a knowledge graph of positions, clusters, and consensus. Spec editors, implementers, and deployers can see where the broader community actually stands on strategic questions, not just where the loudest voices are.

### 4.2 For the Solid Protocol

Building a real application on Solid, at an event full of Solid experts, is the most honest test of the protocol's readiness. Every friction point the forum encounters — authentication UX, pod provisioning, notification latency, WAC complexity — is a signal about what needs work. The community benefits whether the demo succeeds or struggles.

### 4.3 For Deliberation Technology

vTaiwan works, but participants' data lives on Polis servers. Alignment Assemblies work at scale, but on centralised infrastructure. Solid Forum demonstrates that sovereign deliberation is possible: the same participation design, the same consensus-building interaction, but with data sovereignty at the protocol level. If this works for a 500-person technical community, the pattern generalises.

### 4.4 For the Broader Ecosystem

The research behind this project — a literature review prepared for The Institutional Architecture Lab — examines how governments are using federated knowledge graphs for institutional memory. Estonia's X-Road, Taiwan's T-Road, Flanders' Athumi, the EU's GAIA-X. The common gap across all of them is a consent layer between institutions and the people they serve. Solid Forum is a small, concrete instance of that layer: a community governing itself with sovereign data, demonstrating the pattern that larger institutions need.

## 5. Technical Foundation

Solid Forum is built on `people` (`pacific-solid`), the first production-grade Python SDK for the Solid Protocol. The SDK provides:

- **Solid-OIDC + DPoP** — both client credentials and browser-based auth code flow with PKCE
- **Pod CRUD** — five methods, five HTTP verbs
- **`@ps.model`** — typed RDF models for statements, votes, and summaries
- **WAC** — server-side evaluation and client-side grant/revoke
- **LDN** — inbox discovery and notification delivery
- **Solid Notifications** — WebSocket streaming for real-time aggregation
- **Graph converters** — `to_dataframe()`, `to_networkx()` for analysis

The SDK is MIT-licensed and open source. The forum application code will be open source. The data belongs to the participants.

## 6. Conclusion

The Solid community should govern its own development with the tools it builds. Solid Forum makes this possible: a vTaiwan-style deliberation process where every contribution lives in the participant's pod, the aggregate is a public knowledge graph, and the output belongs to everyone. The hackathon builds it. The Symposium uses it. The community decides what happens next.

---

## References

Baura, A. (2025). European ambitions captured by American clouds: digital sovereignty through Gaia-X? *Information, Communication & Society*, 29(2). DOI: 10.1080/1369118X.2025.2516545

Calzati, S. & van Loenen, B. (2023). Beyond federated data: a data commoning proposition for the EU's citizen-centric digital strategy. *AI & Society*. DOI: 10.1007/s00146-023-01743-9

Cui, P.J.-W. (2023). Interview in Kurihara, K., Privacy Talk with Peter Jia-Wei Cui, Contributor of vTaiwan Community. *Medium / Privacy Talk*.

Hardy, A. (2024). Estonia's digital diplomacy: Nordic interoperability and the challenges of cross-border e-governance. *Internet Policy Review*, 13(3).

Meroño-Peñuela, A., Simperl, E., Kurteva, A., & Reklos, I. (2025). KG.GOV: Knowledge graphs as the backbone of data governance in AI. *Journal of Web Semantics*, 85, 100847. DOI: 10.1016/j.websem.2024.100847

Puura, A., Soe, R.-M., & Thabit, S. (2026). Advancing interoperability of data exchange in Europe: Insights from Estonia's experience for the common European data spaces. *Data in Brief*, 64, 112361. DOI: 10.1016/j.dib.2025.112361

Serderidis, K., Konstantinidis, I., Meditskos, G., Peristeras, V., & Bassiliades, N. (2024). d2kg: An integrated ontology for knowledge graph-based representation of government decisions and acts. *Semantic Web Journal*. DOI: 10.3233/SW-243535

Zhang, Y., Porter, A.L., Cunningham, S.W., Chiavetta, D., & Newman, N. (2021). Parallel or Intersecting Lines? Intelligent Bibliometrics for Investigating the Involvement of Data Science in Policy Analysis. *IEEE Transactions on Engineering Management*, 68(5), 1259–1271. DOI: 10.1109/TEM.2020.2974761
