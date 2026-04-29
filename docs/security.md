# Security And Secret Hygiene

Do not commit:

- Icons8 `i8token`
- Icons8 `publicApiKey`
- browser cookie databases
- generated paid SVGs unless your license and repo visibility allow it
- generated paid PNGs unless your license and repo visibility allow it

Use `.env` locally if needed, but keep it ignored:

```bash
export ICONS8_PUBLIC_API_KEY="..."
```

The Chrome extraction command is local-only convenience. It should only be run on your own Mac profile and your own Icons8 account.

If this repo is public, keep only:

- scripts
- docs
- example CSVs
- generated manifests without private account data

Before publishing:

```bash
rg -n "i8token|publicApiKey|Bearer|eyJ|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+|icons8_public" .
```

Review any matches manually. Some strings like `publicApiKey` in code/docs are expected. Real JWTs usually start with `eyJ`.
