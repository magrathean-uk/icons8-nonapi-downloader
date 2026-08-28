# Icons8 Licensed Asset Pipeline

A local Python workflow for account holders who need to build a reviewed icon pack from Icons8 Liquid Glass assets they are already entitled to download.

The repository contains tooling only. It does not contain Icons8 artwork, cookies, account data, paid tokens, or generated asset packs.

## Use and licensing

This project is not an access-control bypass and does not grant rights to Icons8 content. Use it only with an account you control, only where your subscription and the applicable Icons8 terms permit the requested downloads, and only within the licence attached to those assets.

Prefer official export or API tooling where it meets the requirement. You are responsible for download limits, attribution, redistribution restrictions, derivative-work rights, and the licence status of every generated pack.

## Capabilities

1. Crawl supported Icons8 style and category pages into a deterministic manifest.
2. Map application asset names to search queries for smaller, app-specific packs.
3. Resolve queries through the Icons8 MCP search surface.
4. Download SVG masters using an account-holder key supplied at runtime.
5. Recolour Liquid Glass SVG gradients into an application palette.
6. Render PNG outputs and generate a review contact sheet.

## Authentication

Preferred:

```bash
export ICONS8_PUBLIC_API_KEY="your-own-icons8-public-api-key"
```

For local convenience on macOS with Chrome:

```bash
python3 scripts/icons8_pipeline.py token-from-chrome
```

That helper reads the local Icons8 cookie for the current macOS user, extracts only the account's public API key, and prints an `export` command. It does not upload the cookie. Review the script before use and never commit or paste the resulting key into issues, logs, fixtures, or documentation.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install librsvg
```

`librsvg` provides `rsvg-convert`, used for PNG rendering.

## Full style or category workflow

Start with one or more Icons8 style or set pages:

```text
https://icons8.com/icons/glassmorphism
https://icons8.com/icons/set/business--style-glassmorphism
https://icons8.com/icons/set/science--style-glassmorphism
```

Build a manifest:

```bash
python3 scripts/icons8_pipeline.py page-manifest \
  --urls-file work/icons8-pages.txt \
  --out work/page-manifest.csv \
  --json-out work/page-manifest.json
```

A root style page can expand to linked set pages. Category pages are parsed from the page's application data so the manifest reflects the full page inventory rather than a partial search result.

Download the manifest SVGs:

```bash
python3 scripts/icons8_pipeline.py download-manifest \
  --manifest work/page-manifest.csv \
  --out work/svg-original \
  --resolved work/resolved-page-icons.csv \
  --failed work/failed-page-icons.csv \
  --workers 2
```

Keep worker counts conservative. A successful local run does not override provider rate limits or acceptable-use requirements.

## App-specific workflow

Start from a reviewed query CSV:

```csv
asset_key,icons8_query,sf_symbols
lg_car,car,car.fill;car.circle
lg_battery_full,battery full,battery.100percent
```

Download resolved SVG masters:

```bash
python3 scripts/icons8_pipeline.py download \
  --queries examples/asset-queries.example.csv \
  --overrides examples/overrides.example.csv \
  --out work/svg-original \
  --resolved work/resolved-icons.csv \
  --failed work/failed-icons.csv
```

Theme the SVGs:

```bash
python3 scripts/icons8_pipeline.py theme \
  --in-dir work/svg-original \
  --out-dir work/svg-themed
```

Render PNGs:

```bash
python3 scripts/icons8_pipeline.py render \
  --in-dir work/svg-themed \
  --out-dir work/png-themed \
  --size 512
```

Generate a review contact sheet:

```bash
python3 scripts/icons8_pipeline.py contact-sheet \
  --png-dir work/png-themed \
  --resolved work/resolved-icons.csv \
  --out work/contact-sheet.png
```

## SwiftUI discovery

For a SwiftUI project that uses SF Symbols:

```bash
python3 scripts/discover_swiftui_symbols.py \
  --source /path/to/AppSource \
  --out work/symbols.csv \
  --queries work/asset-queries.csv
```

Generated search queries are candidates, not approved matches. Review them visually and add explicit overrides before producing a release asset pack.

Override CSV format:

```csv
asset_key,icons8_id,icons8_name,icons8_common_name
lg_car,2GEdGXRMcSaj,Car,car
```

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

Tests use local fixtures and do not require a live Icons8 account.

## Data handling

- Credentials are supplied at runtime and are not written into generated manifests.
- Generated SVG and PNG files are ignored by Git by default because they are licensed content.
- Resolved and failed CSV files may expose the names of private application assets; review them before sharing.
- Do not use real cookies, keys, or paid assets as test fixtures.

## Security, licence, and trademarks

Report security issues through [`SECURITY.md`](./SECURITY.md). The tooling is licensed under the [MIT Licence](./LICENSE); third-party notices are in [`license.md`](./license.md). Icons8 and related marks belong to their respective owner; see [`TRADEMARKS.md`](./TRADEMARKS.md).

This project is independent and is not affiliated with, endorsed by, sponsored by, or supported by Icons8.
