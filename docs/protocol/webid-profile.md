# Client Requirements for WebID Profile Resolution

Source: https://solid.github.io/webid-profile/

## Profile Discovery & Reading

**Section 3.1 | MUST**
"Reader Application MUST make an HTTP `GET` request targeting a Solid WebID Profile resource and include an `Accept` header requesting a representation in `text/turtle` or `application/ld+json`."

Clients must request profile documents with appropriate content negotiation headers.

## WebID Profile Data Model

**Section 3.1 | Informative**
Clients should expect profiles to contain:
- One `rdf:type` property (value: `foaf:Agent`)
- One `pim:preferencesFile` reference
- Zero or one `ldp:inbox` property
- Zero or more `pim:storage` properties
- Zero or more `rdfs:seeAlso` references (extended profiles)
- Zero or more `foaf:isPrimaryTopicOf` references (extended profiles)

## Extended Profile Documents

**Section 3.3 | MAY**
"Reader Application MAY retrieve a representation of an Extended Profile Document."

Clients may follow `rdfs:seeAlso` and `foaf:isPrimaryTopicOf` links to access supplementary profile information.

## OIDC Identity Provider Discovery

**Section 5 | Informative**
The `solid:oidcIssuer` predicate identifies an OIDC provider for authentication. "Applications can use the value of `solid:oidcIssuer` to initiate the login process."

## Inbox Discovery

**Section 6 | Informative**
Clients can discover notification endpoints via the `ldp:inbox` property. Single inbox per profile is recommended (discouraged to advertise multiple).

## Additional Predicates

**Section 7 | Informative**
Clients should recognize that profiles may contain other predicates beyond core infrastructure properties, including `acl:trustedApp` and `cert:key`.
