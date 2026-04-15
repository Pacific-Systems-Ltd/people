# Solid Notifications Protocol Client Requirements

Source: https://solidproject.org/TR/notifications-protocol

## Discovery Requirements

**Section 2.1 (Discovery)**

- **MUST** discover description resources associated with a topic resource
  - Client must follow `describedby` link relations in HTTP responses
  - Client must also check for `http://www.w3.org/ns/solid/terms#storageDescription` links for storage-level descriptions

- **MUST** accept responses in `application/ld+json` format
  - Client should send appropriate Accept headers

## Subscription Requirements

**Section 2.2 (Subscription)**

- **MUST** use the Notification Channel Data Model when creating subscriptions
  - Client must construct subscription requests following the defined data model

- **MUST** send `Content-Type: application/ld+json` in subscription requests

- **MUST** handle `415` status responses for unsupported profile parameters

- **MUST** handle `422` status responses for unprocessable entities

- **MUST** support interaction with subscription services via GET, HEAD, OPTIONS, and POST methods

## Notification Channel Requirements

**Section 2.3 (Notification Channel)**

- **MUST** process notification messages using the Notification Message Data Model

- **MUST** conform to a specific notification channel type (WebSocket, Webhook, etc.)

## Notification Message Requirements

**Section 2.4 (Notification Message)**

- **MUST** process Activity Streams vocabulary notifications
  - Client must understand JSON-LD with Activity Streams and Solid Notifications vocabularies

- **SHOULD** be prepared for extended notification content

- **MAY** include data about agents controlling the client

## Security & Privacy Requirements

**Section 4.1-4.3 (Security Considerations)**

- **STRONGLY DISCOURAGED** from sending subscription requests to untrusted services (including localhost/loopback)

- **ENCOURAGED** to minimize information exposure in subscription requests

## Data Model Requirements

**Section 3 (Data Model)**

Clients must understand and construct/parse:

1. **Description Resources** containing:
   - One `id` property
   - Zero or more `subscription` properties
   - Zero or more `channel` properties

2. **Subscription Services** containing:
   - One `id` property
   - One `channelType` property
   - Zero or more `feature` properties

3. **Notification Channels** containing:
   - One `id` property
   - One `type` property (channel type)
   - At least one `topic` property
   - Optional `receiveFrom` property (pull-based)
   - Optional `sendTo` property (push-based)
   - Optional feature properties (startAt, endAt, state, rate, accept)

4. **Notification Messages** containing:
   - One `id` property
   - At least one `type` property (Activity type)
   - One `object` property (topic resource)
   - One `published` property (timestamp)
   - Zero or more `target` properties
   - Optional `state` property

## Authentication & Authorization

**Section 2 (Protocol)**

- **ENCOURAGED** to use Solid Protocol authentication mechanisms
- Must respect access controls on subscription services and notification messages

## General Implementation Notes

- Clients must use the JSON-LD context at `https://www.w3.org/ns/solid/notifications-context/v1`
- Notification channel types are registered independently; clients must support whichever types their implementation targets
