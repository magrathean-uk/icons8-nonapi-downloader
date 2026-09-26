# Security Policy

## Scope

This policy covers the repository's Python scripts, examples, and documentation. It does not cover Icons8 services, accounts, payment systems, or other third-party infrastructure.

The download commands send an account-holder API key to the Icons8 image endpoint and the Chrome helper reads the current user's local Chrome cookie database and Keychain. Treat keys, cookies, generated assets, manifests, and resolved or failed CSV files as sensitive when they identify private application work or licensed content.

## Reporting

Use GitHub private vulnerability reporting when it is available for this repository, or email `contact@magrathean.uk` with subject `SECURITY: Icons8 Pipeline`.

Do not publish credentials, private keys, database dumps, signing certificates, or exploit details. Include the affected version or commit, platform, reproduction steps, impact, and redacted evidence. The repository does not state a monitoring schedule, response time, or supported-version policy.

## Scope and Safe Harbour

Magrathean UK Ltd. will not pursue a good-faith researcher for security disclosures that:

- Target non-production test systems or researcher-owned environments;
- Avoid persistence, destructive changes, denial of service, and access to personal or customer data;
- Report promptly and permit reasonable time for remediation;
- Do not condition non-disclosure on financial compensation.

## Excluded Conduct

No safe harbour covers phishing, credential stuffing, accessing private production infrastructure, large-scale scanning, denial of service, or unlawful conduct.
