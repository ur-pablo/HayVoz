# Security Policy

## Supported version

Security fixes target the latest `main` branch until formal releases exist.

## Reporting a vulnerability

Use GitHub private vulnerability reporting for `ur-pablo/HayVoz` when enabled.
Do not open a public issue containing credentials, recordings, transcripts,
private paths, exploit details, or identifying metadata.

Include affected version, operating system, reproduction conditions, impact, and
a minimal synthetic proof. Never test against data or systems you do not own or
have permission to assess.

## Security expectations

- No inbound network service.
- No first-party telemetry.
- Explicit consent for external text processing.
- Provider credentials only from environment/private config.
- Owner-only local storage permissions where supported.
- Content-free, secret-redacted logs.

The detailed model and known residual risks are in
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).
