# ADR 0002: Local privacy and zero tracking

- Status: Accepted
- Date: 2026-08-24

## Decision

User data and credentials are local by default, outside the checkout, with
owner-only permissions where supported. HayVoz has no first-party tracking or
inbound service. Network use requires an explicit user action.

## Consequences

There is no product telemetry for maintainers. Diagnostics must be user-provided
and scrubbed. Consented providers remain an external trust boundary.
