# Solid-OIDC Client Requirements

Source: https://solidproject.org/TR/oidc

## Client Identifiers

**Section 5: Client Identifiers**
- **SHOULD** (5): Use a URI as client identifier that can be dereferenced as a Client ID Document
- **MUST** (5.1): Dereference to `application/ld+json` unless content negotiation requires otherwise
- **MUST** (5.1): Supply parameters matching values in Client ID Document
- **MUST** (5.1): Include `redirect_uri` in registration `redirect_uris` list

**Section 5.2: OIDC Registration**
- **MUST** (5.2): If not using dereferenced identifier, present client identifier registered via OIDC dynamic or static registration

## Token Request & DPoP

**Section 8: Token Instantiation**
- **MUST** (8): Send either (1) Client ID + Secret + valid DPoP Proof, or (2) Dereferencable Client Identifier + proper Client ID Document + valid DPoP Proof

**Section 8.1: DPoP-bound OIDC ID Token**
- **MUST** (8.1): Send DPoP proof JWT valid per OAuth 2.0 DPoP § 5 when requesting DPoP-bound ID Token
- **MUST** (9.3): Present valid DPoP Proof when using DPoP-bound OIDC ID Token

## Token Validation

**Section 8.1.1: ID Token Validation**
- **MUST** (8.1.1): Validate ID Token per OIDC.Core Section 3.1.3.7
- **MUST** (8.1.1): Perform OIDC Issuer Discovery using `webid` claim value to dereference WebID Profile
- **MUST** (8.1.1): Unless acquiring OP keys through other means, follow OpenID Connect Discovery 1.0 to find signing keys (JWK)

## WebID Verification

**Section 6.1: OIDC Issuer Discovery**
- **MUST** (6.1): Check WebID Profile for statements matching pattern: `?webid <http://www.w3.org/ns/solid/terms#oidcIssuer> ?iss`
- **MAY** (6.1.1): Use Link Header values as optimization but treat RDF in body as canonical

## Authorization & Scopes

**Section 3: Core Concepts**
- **SHOULD** (3): Use Authorization Code Flow with PKCE per OAuth and OIDC best practices

**Section 7: Requesting the WebID Claim**
- **REQUIRED** (7): Request `webid` scope to access End-User's `webid` claim

## Security & Storage

**Section 11.1: TLS Requirements**
- **MUST** (11.1): Transmit tokens, client, and user credentials only over TLS

**Section 11.3: Client Secrets**
- **SHOULD NOT** (11.3): Store client secrets in browser local storage
