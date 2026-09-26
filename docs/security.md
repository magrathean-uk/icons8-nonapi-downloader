# Security and Secret Hygiene

## Keep private material out of the repository

Do not commit or attach to issues:

- Icons8 `i8token` values or `publicApiKey` values
- browser cookie databases or Keychain exports
- generated SVG or PNG assets unless the asset license and repository visibility permit it
- resolved or failed CSV files when they expose private application asset names

Supply `ICONS8_PUBLIC_API_KEY` through the process environment. A `.env` file can be an ignored local convention, but the scripts do not load it themselves.

```bash
export ICONS8_PUBLIC_API_KEY="..."
```

`token-from-chrome` is a local macOS convenience command. Run it only for a Chrome profile and Icons8 account you control. It reads the local cookie database and Keychain, extracts the API key, and prints an export command. Do not paste the result into tickets, logs, examples, or documentation.

The download request includes the key as the `token` URL parameter. Keep command output, network captures, shell history, and shared logs free of real credentials.

## Treat input and SVGs as untrusted

Review CSVs before using them. The download commands use `asset_key` directly when forming output filenames and do not sanitize path separators. Do not use untrusted CSV values for output paths. Resolved CSV files include output paths, and failed CSV files can include provider response text or local error details, so review them before sharing.

The theming step performs text substitutions on SVG input, and the render step passes each SVG to `rsvg-convert`; neither step sanitizes SVG content. Treat downloaded or supplied SVGs as untrusted input and validate them for the consumer that will receive the result.

## Before sharing generated output

Review generated files for private asset names and licensed content. A local text scan can help find candidate secrets, but review matches manually because code and documentation intentionally mention some identifiers.

```bash
rg -n "i8token|publicApiKey|Bearer|eyJ|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+|ICONS8_PUBLIC_API_KEY" .
```

For vulnerability reports, follow the repository [security policy](../SECURITY.md).
