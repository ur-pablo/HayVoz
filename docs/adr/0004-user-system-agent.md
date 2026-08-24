# ADR 0004: User-scoped system agent

- Status: Accepted
- Date: 2026-08-24

## Decision

Offer an optional per-user recovery agent through LaunchAgent, systemd user
service, or Task Scheduler. It opens no port and never records automatically.

## Consequences

Recovery can occur without a foreground CLI. Install/uninstall remains explicit,
platform adapters need validation, and no privileged daemon is introduced.
