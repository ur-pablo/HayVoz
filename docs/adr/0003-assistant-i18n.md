# ADR 0003: Stable Assistant identity with localized presentation

- Status: Accepted
- Date: 2026-08-24

## Decision

Use `assistant` for code, schema, and persistence. Resolve a localized display
term and CLI alias from locale. Do not translate the full application in 0.6.0.

## Consequences

Language changes do not break stored sessions or automation. Adding full message
catalogs remains compatible. Existing sessions require a one-time migration.
