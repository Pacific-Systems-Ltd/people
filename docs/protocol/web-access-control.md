# Web Access Control (WAC) Client Requirements

Source: https://solid.github.io/web-access-control-spec/

## ACL Resource Discovery

**Section 3.1: ACL Resource Discovery**
- **MUST** discover ACL resources by making HTTP requests to target URLs and checking the `Link` header with `rel=acl` parameter
- **MUST NOT** derive ACL resource URIs through string operations on resource URIs
- Resources and ACL resources can exist on different origins

## ACL Resource Access

**Section 3.2: ACL Resource Representation**
- **MUST** accept responses to ACL resource requests in `text/turtle` format
- Expect `404` status when accessing ACL resources without existing representations
- Clients determine effective ACL resources to perform control operations

## Authorization Evaluation & Matching

**Section 5.2-5.3: Authorization Conformance**
Applicable authorizations require:
- At least one `rdf:type` property with `acl:Authorization` object
- At least one `acl:accessTo` or `acl:default` property
- At least one `acl:mode` property
- At least one subject property: `acl:agent`, `acl:agentGroup`, `acl:agentClass`, or `acl:origin`

**Section 5.3.4: Authorization Matching**
- Process authorizations until access permissions are granted or denied
- Non-matching authorizations have no effect
- When requests require `acl:Append`, access is granted if either `acl:Append` or `acl:Write` is allowed

## Access Modes

**Section 4.2: Access Modes**
Clients must understand these modes:
- `acl:Read`: View resource contents (HTTP GET)
- `acl:Write`: Create, delete, modify resources (PUT, POST, PATCH, DELETE)
- `acl:Append`: Add information without removal (POST, PATCH)
- `acl:Control`: Read/write ACL resources associated with resources

## Access Subjects

**Section 4.3: Access Subjects**

**Agents:**
- `acl:agent`: Individual agent identified by URI
- `acl:agentClass`: Class of agents
  - `foaf:Agent`: Public access (any agent)
  - `acl:AuthenticatedAgent`: Any authenticated agent
- `acl:agentGroup`: Groups defined via `vcard:Group` with `vcard:hasMember` predicates
- `acl:origin`: Origin-based access control (HTTP `Origin` header required)

## Web Origin Authorization

**Section 5.3.2: Web Origin Authorization**
- Access is granted when matching:
  - Authorization for requesting agent (`acl:agent`, `acl:agentGroup`, `acl:agentClass`)
  - `acl:origin` property matching `Origin` header value (when public access not granted)
  - Required access mode for agent and origin

## Permission Inheritance

**Section 5.1: Effective ACL Resource**
- When resource's ACL resource lacks representation, check container's ACL resource
- Inheritance follows hierarchy toward root container
- Algorithm: Check if resource has ACL representation; if not, recursively check parent container

**Section 4.1: Access Objects**
- `acl:accessTo`: Denotes specific resource for access
- `acl:default`: Denotes container whose authorization applies to lower hierarchy

## WAC-Allow HTTP Header

**Section 6.1: WAC-Allow**
Clients must:
- **MUST** discover access privileges via HTTP `GET`/`HEAD` requests by checking `WAC-Allow` header
- Parse header format: `permission-group = access-modes`
  - `user`: Permissions for requesting agent
  - `public`: Permissions for public
  - `access-modes`: "read", "write", "append", "control"
- **MUST** incorporate error handling; ignore malformed headers and unrecognized parameters

When CORS applies: Server includes `WAC-Allow` in `Access-Control-Expose-Headers`.

## Error Handling

**Section 6.1: WAC-Allow Header Parsing**
- Clients **MUST** ignore received `WAC-Allow` headers failing pattern matching
- Clients **MUST** continue processing when encountering unrecognized access parameters

---

**Total Requirements for Clients:** 15+ distinct normative obligations covering discovery, parsing, evaluation, and header handling.
