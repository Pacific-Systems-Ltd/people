# Solid Protocol Client Requirements

Source: https://solidproject.org/TR/protocol

## 2. HTTP Client

**2.2 HTTP Client**

- **MUST** conform to HTTP Semantics [RFC9110]
- **MAY** conform to HTTP Caching [RFC9111]
- **MUST** conform to HTTP/1.1 [RFC9112]
- **MAY** conform to HTTP/2 [RFC9113]

**Client Authentication Different Credentials**
- **MAY** repeat requests with different credentials when receiving 403/404 responses

**Client Content-Type Includes**
- **MUST** use `Content-Type` header in `PUT`, `POST`, `PATCH` requests containing content

## 3. URI

**Client Storage Discovery**
- Can determine storage by moving up URI path hierarchy until finding response with `Link` header targeting `pim:Storage`

**Client RDF Storage**
- Can discover storage by making `GET` request to retrieve RDF representation containing `pim:storage` relation

## 4. Resources - Storage

**Client Link Storage**
- Can determine storage type by making `HEAD`/`GET` request and checking `Link` header with `rel="type"` targeting `http://www.w3.org/ns/pim/space#Storage`

## 4.2 Resource Containment

**URI Allocation (Note)**
- Clients can use `PUT`/`PATCH` requests to assign URIs to resources
- Clients can use `POST` requests to have servers assign URIs

## 5. Reading and Writing Resources

**5.2 Reading Resources - Allow Methods**
- Servers MUST indicate supported methods; implicitly, clients read these indicators

**5.2 Accept Headers**
- Clients benefit from servers indicating media types via `Accept-Patch`, `Accept-Post`, `Accept-Put` headers

**5.3 Writing Resources**

**Conditional Update (Note)**
- Clients are "encouraged to use" `If-None-Match: "*"` to prevent inadvertent modification of existing resources

**Client Usage of ETag**
- Servers MAY use strong validators for RDF; implicitly, clients can opt-in to `If-Match` headers

**5.3.1 N3 Patch**

- Servers MUST accept `PATCH` with N3 Patch body when target is RDF document
- Servers MUST advertise N3 Patch support via `Accept-Patch: text/n3` header

**Implied Client Behavior:**
- Clients can construct N3 Patch documents conforming to specified constraints
- Clients can send PATCH requests with `text/n3` media type

## 5.5 Resource Representations

**Server Representation Requirements**
- When servers create RDF sources via `PUT`, `POST`, `PATCH`, they MUST satisfy `GET` requests with `Accept: text/turtle` or `application/ld+json`

**Implied Client Usage:**
- Clients can request RDF representations using these media types

## 6. Linked Data Notifications

**Client LDN Compliance**
- **MUST** conform to LDN specification by implementing Sender or Consumer parts
- **MUST** discover location of resource's Inbox
- **MUST** send notifications to Inbox or retrieve Inbox contents

## 7.1 Solid Notifications Protocol

- Clients implicitly discover subscription resources and notification channels available to resources/storage through server implementation

## 8. CORS

**CORS implications for clients:**
- Servers disable cross-origin protections; clients operate under authorization control rather than browser CORS restrictions

## 9.1 WebID

- Clients can dereference WebIDs to obtain RDF representations of WebID Profiles

## 10. Authentication

**10.1 Solid-OIDC**
- Clients operate within Solid-OIDC authentication framework defined by specification

**10.2 WebID-TLS (Non-normative)**
- Clients can use WebID-TLS as authentication mechanism

## 11. Authorization

**11.1 Web Access Control**
- **MUST** conform to WAC specification [WAC]
- Can discover authorization rules associated with resources
- Can control authorization rules as directed by agents

**11.2 Access Control Policy**
- **MUST** conform to ACP specification [ACP]

---

**Note:** The specification contains minimal explicit client requirements; most describe server behavior with clients implicitly adapting. Primary client obligations involve HTTP compliance, N3 Patch construction, WAC/ACP conformance, and proper header usage.
